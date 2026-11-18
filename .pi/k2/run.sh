#!/bin/bash
# K2 runner (Plan v0.5 §6, D26/D27): the midnight scenarios end to end, inside the K1 image.
#   bash .pi/k2/run.sh          # tracked + staged worktree state
#   bash .pi/k2/run.sh <ref>    # any commit
# The parent base 5950f807's avian/ tree is extracted to /base as the "outdated station".
# Never bind-mounts the CRLF worktree (fact 23); untracked files are invisible: git add first.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
image=${AVIAN_K1_IMAGE:-avian-k1:local}
docker build --quiet --file .pi/k1/Dockerfile --tag "$image" .pi/k1 >/dev/null

ref=${1:-}
if [ -z "$ref" ]; then ref=$(git stash create); ref=${ref:-HEAD}; fi
echo "K2: ref=$(git rev-parse --short "$ref")"
base_tar=$(mktemp)
trap 'rm -f "$base_tar"' EXIT
git -c core.autocrlf=false archive 5950f807 avian > "$base_tar"
git -c core.autocrlf=false archive "$ref" | docker run --rm -i \
  -v "$(cygpath -m "$base_tar" 2>/dev/null || echo "$base_tar"):/base.tar:ro" "$image" bash -c '
    set -e
    tar -x -C /src
    mkdir -p /tmp/base && tar -x -C /tmp/base -f /base.tar
    cd /src
    K2_BASE_ROOT=/tmp/base PYTHONPATH=.pi/k2/fake_inky \
      python -m pytest -q -rs -p no:cacheprovider .pi/k2/test_k2_midnight.py'
