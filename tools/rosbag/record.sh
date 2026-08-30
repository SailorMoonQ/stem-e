#!/usr/bin/env bash
#
# Record a session to local storage on the robot.
#
# Never point this at an NFS or SMB mount. The robot's only link is WiFi and the
# recorder will silently drop messages when the link cannot keep up, producing a bag
# with holes that are not discovered until analysis.
# See docs/adr/0005-rosbags-record-locally-then-sync.md.
#
# Usage: record.sh <session-name> [additional ros2 bag record args...]

set -euo pipefail

SESSION="${1:?usage: record.sh <session-name> [ros2 bag record args...]}"
shift

BAG_DIR="${STEM_BAG_DIR:?STEM_BAG_DIR is not set. Source config/env/robot.env first.}"

case "$(findmnt -no FSTYPE --target "${BAG_DIR}" 2>/dev/null || echo unknown)" in
  nfs|nfs4|cifs|smb3)
    echo "refusing to record to network storage at ${BAG_DIR}" >&2
    echo "see docs/adr/0005-rosbags-record-locally-then-sync.md" >&2
    exit 1
    ;;
esac

DEST="${BAG_DIR}/$(date +%Y-%m-%d)/${SESSION}"
mkdir -p "$(dirname "${DEST}")"

echo "recording to ${DEST}"

# TODO: replace the topic set once the graph exists. Recording everything is the
# wrong default for a robot with several camera streams.
exec ros2 bag record \
  --storage mcap \
  --output "${DEST}" \
  "$@" \
  --all
