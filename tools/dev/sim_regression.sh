#!/usr/bin/env bash
#
# Layer 4 of the test strategy: headless Gazebo regression.
#
# Runs on the workstation, not in CI. See docs/adr/0004-no-docker.md for why this
# layer is local while layers 1 to 3 run on GitHub Actions.

set -euo pipefail

cd "$(dirname "$0")/../.."

echo "building"
colcon build --symlink-install

# shellcheck disable=SC1091
source install/setup.bash

echo "running scenarios from tests/system"
# TODO: drive the scenarios in tests/system through launch_testing against
# stem_bringup sim.launch.py with rendering disabled.
exec colcon test --packages-select stem_bringup --event-handlers console_direct+
