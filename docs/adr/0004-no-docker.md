# 4. No Docker

- **Date:** 2026-08-30
- **Status:** Accepted

## Context

An earlier draft of the architecture used Docker in one place: running CI on the NAS. The
NAS runs a Debian based appliance OS, so ROS 2 Jazzy cannot be installed on it natively,
and a container was the way to get a Ubuntu 24.04 build environment onto it.

Removing Docker removes that possibility, which forces the question of where each layer
of testing should actually run. The answer turns out to be better than the original.

## Decision

No Docker anywhere in this project. Testing is split by what each machine is good at:

| Layer | Runs on | Why |
|---|---|---|
| Lint and `src/core` unit tests | GitHub Actions | Pure Python, no ROS needed, seconds |
| `colcon build` and `colcon test` | GitHub Actions | `ros-tooling/setup-ros` provides Jazzy, no local infrastructure |
| Mock backend integration tests | GitHub Actions | `mock_components` needs no simulator |
| Headless Gazebo regression | Workstation | Strongest machine in the fleet, and already has the exact environment |

The NAS becomes pure storage: rosbags and datasets over NFS, no compute.

Development machines install ROS 2 Jazzy natively from apt. Deployment to the robot is
`colcon build` plus systemd units, described in `deploy/`.

## Consequences

- Nothing about this project depends on container tooling being installed, working, or
  correctly configured on any machine.
- Environment drift between machines is now a real risk, managed by pinning the ROS
  distribution and keeping provisioning scripted in `deploy/scripts/`. If drift becomes a
  concrete recurring problem rather than a hypothetical one, that is the trigger to
  revisit this record.
- The NAS being storage only removes it from every hot path, which also removes the
  pending 10GbE switch purchase from the critical path.
- Simulation regression is not gated on a pull request unless the workstation is running.
  Accepted: the fast layers do gate, and the slow layer is a local command.
