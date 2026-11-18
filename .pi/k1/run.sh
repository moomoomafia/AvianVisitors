#!/bin/bash
# K1 host runner (Plan v0.4 §6). Usage, from the repo root:
#   bash .pi/k1/run.sh            # tracked files of the working tree (git stash create, else HEAD)
#   bash .pi/k1/run.sh 5950f807   # any commit, e.g. the product base
# A run on the base commit exits 1 by design: the educator suite reports BASE (its baseline file is not in a base archive); compare the summaries instead.
# Never bind-mounts the CRLF worktree: an LF archive is piped into the container (fact 23).
# Untracked files are NOT included: commit or `git add` new files first.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
image=${AVIAN_K1_IMAGE:-avian-k1:local}

pin=$(grep -E '^playwright==' frame/requirements-shoot.txt | tr -d '\r')
grep -q "$pin" .pi/k1/Dockerfile || { echo "K1: Dockerfile Playwright pin differs from frame/requirements-shoot.txt ($pin)" >&2; exit 2; }

docker build --quiet --file .pi/k1/Dockerfile --tag "$image" .pi/k1 >/dev/null

ref=${1:-}
if [ -z "$ref" ]; then ref=$(git stash create); ref=${ref:-HEAD}; label="worktree"; else label="$ref"; fi
echo "K1: ref=$label ($(git rev-parse --short "$ref"))"
git -c core.autocrlf=false archive "$ref" | docker run --rm -i "$image" bash -c 'tar -x -C /src && exec suite.sh'
