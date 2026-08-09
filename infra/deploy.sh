#!/usr/bin/env bash
# One-time-ish deploy for Nightwatch. Fill in PROJECT_ID, run `gcloud auth login` and
# `gcloud config set project <id>` first. The whole script is idempotent — re-run it to
# ship updates or to rotate the integration tokens (it adds a new Secret Manager version).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
REGION="${REGION:-us-central1}"
SERVICE="nightwatch"
TOPIC="nightwatch-runs"
# Model must be a real Vertex id. NOTE: gemini-3.5-pro does NOT exist on Vertex yet (404);
# gemini-2.5-pro is the highest available. Override via GEMINI_MODEL once 3.5 ships.
MODEL="${GEMINI_MODEL:-gemini-2.5-pro}"

gcloud config set project "$PROJECT_ID"

# 1. Enable the APIs we use.
gcloud services enable \
  run.googleapis.com aiplatform.googleapis.com firestore.googleapis.com \
  pubsub.googleapis.com cloudscheduler.googleapis.com secretmanager.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com

# 2. Firestore (Native mode) — create once; ignore error if it already exists.
gcloud firestore databases create --location="$REGION" || true

# 3. Optional integrations — push any tokens present in your shell/.env into Secret
#    Manager and let Cloud Run's runtime service account read them. Anything left unset is
#    skipped, and that integration stays a graceful no-op (see app/tools/act.py).
ensure_secret() {                       # ensure_secret <secret-name> <value>
  local name="$1" value="$2"
  [ -z "$value" ] && return 1
  gcloud secrets describe "$name" >/dev/null 2>&1 \
    || gcloud secrets create "$name" --replication-policy="automatic"
  printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
}

SECRET_FLAGS=()
ENV_EXTRA=()
if ensure_secret nightwatch-github-token "${GITHUB_TOKEN:-}"; then
  SECRET_FLAGS+=("GITHUB_TOKEN=nightwatch-github-token:latest")
fi
if ensure_secret nightwatch-telegram-bot-token "${TELEGRAM_BOT_TOKEN:-}"; then
  SECRET_FLAGS+=("TELEGRAM_BOT_TOKEN=nightwatch-telegram-bot-token:latest")
fi
[ -n "${GITHUB_REPO:-}" ]      && ENV_EXTRA+=("GITHUB_REPO=${GITHUB_REPO}")
[ -n "${TELEGRAM_CHAT_ID:-}" ] && ENV_EXTRA+=("TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}")

if [ ${#SECRET_FLAGS[@]} -gt 0 ]; then
  PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
fi

# 4. Deploy the container to Cloud Run. Env vars use gcloud's ^@^ delimiter so any
#    comma-bearing value (e.g. a watchlist) is passed intact.
DEPLOY_ENV="^@^GOOGLE_GENAI_USE_VERTEXAI=TRUE@GOOGLE_CLOUD_PROJECT=${PROJECT_ID}@GOOGLE_CLOUD_LOCATION=${REGION}@GEMINI_MODEL=${MODEL}"
[ ${#ENV_EXTRA[@]} -gt 0 ] && for kv in "${ENV_EXTRA[@]}"; do DEPLOY_ENV="${DEPLOY_ENV}@${kv}"; done

DEPLOY_ARGS=(run deploy "$SERVICE" --source . --region "$REGION" --allow-unauthenticated --quiet --set-env-vars "$DEPLOY_ENV")
if [ ${#SECRET_FLAGS[@]} -gt 0 ]; then
  DEPLOY_ARGS+=(--set-secrets "$(IFS=,; echo "${SECRET_FLAGS[*]}")")
fi
gcloud "${DEPLOY_ARGS[@]}"

SERVICE_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Service: $SERVICE_URL"

# 5. Pub/Sub topic + push subscription -> the /pubsub/push endpoint.
gcloud pubsub topics create "$TOPIC" || true
gcloud pubsub subscriptions create "${TOPIC}-push" \
  --topic "$TOPIC" \
  --push-endpoint "${SERVICE_URL}/pubsub/push" \
  --ack-deadline 600 || true

# 6. Cloud Scheduler -> publishes to the topic nightly (02:00). Adjust cron/timezone.
gcloud scheduler jobs create pubsub nightwatch-nightly \
  --location "$REGION" \
  --schedule "0 2 * * *" \
  --time-zone "Etc/UTC" \
  --topic "$TOPIC" \
  --message-body '{"trigger":"nightly"}' || true

echo "Done. Dashboard: $SERVICE_URL/  |  Manual run: curl -X POST $SERVICE_URL/run"
