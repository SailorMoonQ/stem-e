#!/usr/bin/env bash
#
# Stage two of the recording path: move finished bags from the robot to the NAS.
#
# Runs after a session, not during one. Resumable, and the local copy is kept until
# the transfer verifies.
# See docs/adr/0005-rosbags-record-locally-then-sync.md.
#
# Usage: sync_to_nas.sh [--prune]
#
#   --prune   delete local bags after a verified transfer

set -euo pipefail

BAG_DIR="${STEM_BAG_DIR:?STEM_BAG_DIR is not set. Source config/env/robot.env first.}"
REMOTE="${STEM_BAG_REMOTE:?STEM_BAG_REMOTE is not set, e.g. user@nas:/volume/rosbags}"

PRUNE=0
[[ "${1:-}" == "--prune" ]] && PRUNE=1

# --partial with --append-verify survives an interrupted transfer over WiFi without
# restarting from zero. --checksum on the verification pass, not the copy pass.
rsync --archive --partial --progress --human-readable \
      "${BAG_DIR}/" "${REMOTE}/"

echo "verifying"
rsync --archive --checksum --dry-run --itemize-changes \
      "${BAG_DIR}/" "${REMOTE}/" | tee /tmp/stem-bag-verify.txt

if [[ -s /tmp/stem-bag-verify.txt ]]; then
  echo "verification found differences, keeping local copies" >&2
  exit 1
fi

echo "verified"

if [[ "${PRUNE}" -eq 1 ]]; then
  echo "pruning local bags under ${BAG_DIR}"
  find "${BAG_DIR}" -mindepth 1 -maxdepth 2 -type d -exec rm -rf {} +
fi
