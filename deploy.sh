#!/usr/bin/env bash
# deploy.sh — build on the server from source and (re)start the service.
#
# Standard PSI deployment: no registry pull. The image is built locally and
# tagged by the current git commit, so `docker compose ps` / `docker images`
# show exactly which revision is running.
#
#   ./deploy.sh          # pull latest on the current branch, build, restart
#   ./deploy.sh --no-pull # build and restart from the working tree as-is
set -euo pipefail

cd "$(dirname "$0")"

PULL=1
[[ "${1:-}" == "--no-pull" ]] && PULL=0

if (( PULL )); then
  branch="$(git rev-parse --abbrev-ref HEAD)"
  echo "==> git pull origin ${branch}"
  git pull --ff-only origin "${branch}"
fi

IMAGE_TAG="$(git rev-parse --short HEAD)"
export IMAGE_TAG
echo "==> building psi/private-asset-proxy:${IMAGE_TAG}"
docker compose build

echo "==> starting"
docker compose up -d

echo "==> status"
docker compose ps
