#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Agent Engine deployment helper for sample-adk-001
#
# Usage:
#   ./deploy.sh                  # deploy
#   ./deploy.sh delete RESOURCE  # delete a deployed agent
#   ./deploy.sh list             # list all deployed agents
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID="jwlee-argolis-202104"
LOCATION="us-central1"
STAGING_BUCKET="gs://${PROJECT_ID}-adk-staging"

export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export GOOGLE_CLOUD_LOCATION="${LOCATION}"
export GOOGLE_GENAI_USE_VERTEXAI="1"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
err()   { echo "[ERROR] $*" >&2; exit 1; }

check_auth() {
    info "Checking gcloud authentication..."
    if ! gcloud auth print-access-token &>/dev/null; then
        err "Not authenticated. Run: gcloud auth login"
    fi
    gcloud config set project "${PROJECT_ID}" --quiet
    ok "gcloud project set to ${PROJECT_ID}"
}

enable_apis() {
    info "Enabling required GCP APIs..."
    gcloud services enable \
        aiplatform.googleapis.com \
        storage.googleapis.com \
        --project="${PROJECT_ID}" \
        --quiet
    ok "APIs enabled"
}

create_bucket() {
    info "Checking staging bucket ${STAGING_BUCKET}..."
    if ! gsutil ls "${STAGING_BUCKET}" &>/dev/null; then
        info "Creating staging bucket..."
        gsutil mb -l "${LOCATION}" -p "${PROJECT_ID}" "${STAGING_BUCKET}"
        ok "Bucket created: ${STAGING_BUCKET}"
    else
        ok "Bucket already exists: ${STAGING_BUCKET}"
    fi
}

install_deps() {
    info "Installing Python dependencies..."
    if [[ ! -d ".venv" ]]; then
        uv venv .venv
    fi
    uv pip install -q -r requirements.txt --python .venv/bin/python
    ok "Dependencies installed"
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
cmd_deploy() {
    check_auth
    enable_apis
    create_bucket
    install_deps

    info "Starting deployment to Agent Engine (${LOCATION})..."
    .venv/bin/python deploy.py --project "${PROJECT_ID}"
}

cmd_delete() {
    local resource_name="${1:-}"
    [[ -z "${resource_name}" ]] && err "Usage: ./deploy.sh delete RESOURCE_NAME"

    check_auth
    info "Deleting ${resource_name}..."
    python deploy.py --project "${PROJECT_ID}" --delete "${resource_name}"
    ok "Deleted"
}

cmd_list() {
    check_auth
    info "Listing Agent Engine resources in ${PROJECT_ID} / ${LOCATION}..."
    gcloud ai reasoning-engines list \
        --project="${PROJECT_ID}" \
        --location="${LOCATION}" \
        --format="table(name, displayName, createTime)"
}

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
case "${1:-deploy}" in
    deploy) cmd_deploy ;;
    delete) cmd_delete "${2:-}" ;;
    list)   cmd_list ;;
    *)      err "Unknown command '${1}'. Use: deploy | delete <resource> | list" ;;
esac
