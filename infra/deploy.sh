#!/usr/bin/env bash
# One-time-ish deploy for Nightwatch. Fill in PROJECT_ID, run `gcloud auth login` and
# `gcloud config set project <id>` first. Re-run the `gcloud run deploy` line to ship updates.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
REGION="${REGION:-us-central1}"
SERVICE="nightwatch"
TOPIC="nightwatch-runs"

gcloud config set project "$PROJECT_ID"

# 1. Enable the APIs we use.
gcloud services enable \
  run.googleapis.com aiplatform.googleapis.com firestore.googleapis.com \
  pubsub.googleapis.com cloudscheduler.googleapis.com secretmanager.googleapis.com

# 2. Firestore (Native mode) — create once; ignore error if it already exists.
gcloud firestore databases create --location="$REGION" || true

# 3. Deploy the container to Cloud Run.
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GEMINI_MODEL=gemini-3.5-pro"
  # For secrets (GITHUB_TOKEN, TELEGRAM_BOT_TOKEN, ...), prefer:
  #   --set-secrets "GITHUB_TOKEN=nightwatch-github-token:latest,..."

SERVICE_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Service: $SERVICE_URL"

# 4. Pub/Sub topic + push subscription -> the /pubsub/push endpoint.
gcloud pubsub topics create "$TOPIC" || true
gcloud pubsub subscriptions create "${TOPIC}-push" \
  --topic "$TOPIC" \
  --push-endpoint "${SERVICE_URL}/pubsub/push" \
  --ack-deadline 600 || true

# 5. Cloud Scheduler -> publishes to the topic nightly (02:00). Adjust cron/timezone.
gcloud scheduler jobs create pubsub nightwatch-nightly \
  --location "$REGION" \
  --schedule "0 2 * * *" \
  --time-zone "Etc/UTC" \
  --topic "$TOPIC" \
  --message-body '{"trigger":"nightly"}' || true

echo "Done. Dashboard: $SERVICE_URL/  |  Manual run: curl -X POST $SERVICE_URL/run"
