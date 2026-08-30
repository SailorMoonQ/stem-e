# System tests

Layer 4 of the test strategy: full scenarios in headless Gazebo.

These run on the workstation via `tools/dev/sim_regression.sh`, not in CI. See
`docs/adr/0004-no-docker.md` for why this layer is local.

A scenario here should assert on robot behaviour, not on implementation detail: the base
reaches a pose, the arm reaches a grasp without violating a joint limit, the safety layer
stops motion when a deadman times out.
