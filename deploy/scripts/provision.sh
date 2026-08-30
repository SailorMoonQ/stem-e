#!/usr/bin/env bash
#
# Provision a machine for STEM-E: ROS 2 Jazzy, workspace dependencies, and the
# environment file for this machine's role.
#
# Usage: provision.sh <robot|desktop>
#
# There is no container image, so this script is the definition of the environment.
# Keep it working. See docs/adr/0004-no-docker.md.

set -euo pipefail

ROLE="${1:?usage: provision.sh <robot|desktop>}"
case "${ROLE}" in
  robot|desktop) ;;
  *) echo "unknown role: ${ROLE}" >&2; exit 1 ;;
esac

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# TODO: install ROS 2 Jazzy from apt, then rosdep install over src/.

if [[ ! -f "${REPO_ROOT}/config/env/${ROLE}.env" ]]; then
  cp "${REPO_ROOT}/config/env/${ROLE}.env.example" \
     "${REPO_ROOT}/config/env/${ROLE}.env"
  echo "created config/env/${ROLE}.env. Edit the addresses before sourcing it."
fi

if [[ ! -f "${REPO_ROOT}/config/middleware/fastdds_${ROLE}.xml" ]]; then
  cp "${REPO_ROOT}/config/middleware/fastdds_${ROLE}.xml.example" \
     "${REPO_ROOT}/config/middleware/fastdds_${ROLE}.xml"
  echo "created config/middleware/fastdds_${ROLE}.xml. Set the whitelisted address."
fi

echo "next: edit the two files above, then run tools/net/check_dds_binding.sh"
