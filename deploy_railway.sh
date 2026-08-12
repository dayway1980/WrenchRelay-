#!/usr/bin/env sh
set -eu
PROJECT_ID="379b7e9c-79b9-4e60-bb10-42384e0134a9"
ENVIRONMENT="production"
SERVICE="wrenchrelay-app"
python scripts/commission.py
railway up --project "$PROJECT_ID" --environment "$ENVIRONMENT" --service "$SERVICE"
