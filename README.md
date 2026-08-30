# STEM-E

**S**upply **T**ransfer **E**levating **M**anipulator, **E**arth-class.

A full size dual arm mobile manipulator: wheeled base, vertical lift, two arms and a
sensor head, built on ROS 2 Jazzy.

The name follows the naming grammar of the machines in *WALL-E* (Waste Allocation Load
Lifter, Earth-class): the acronym is a deadpan description of the job, and the `-E`
suffix marks the class.

## Status

Scaffolding. The package layout, the architectural seams and the network discipline are
in place. The subsystems are not implemented yet.

## Architecture

Four seams isolate change. Most of the rest of the design follows from them.

| Seam | Where | What it isolates |
|---|---|---|
| 1. Pure logic vs ROS | `src/core/*` | Algorithms carry no `rclpy` / `rclcpp` dependency and are tested with no ROS installed |
| 2. Hardware backend | `ros2_control` SystemInterface | Real hardware, Gazebo and mock share one URDF and one set of controllers |
| 3. Interface contract | `src/interfaces/stem_msgs` | Message definitions are the single source of truth |
| 4. Visualisation degradation | `src/perception/stem_camera_config` | Only compressed and throttled topics cross the wireless link |

Layer stack, top to bottom:

```
operator tooling (rviz2, teleop, web)       <- crosses WiFi, seam 4
task layer (behaviour trees)
motion layer (MoveIt 2, Nav2, lift, head)
                                            <- seam 3, stem_msgs
control layer (controller_manager @ 500 Hz)
                                            <- seam 2, SystemInterface
hardware layer (CAN, motor controllers)     <- stays onboard, shared memory transport
```

### Key decisions

- **One `controller_manager` at 500 Hz.** Slower components divide down inside their own
  `read()` / `write()`. This keeps `/joint_states` unified and lets MoveIt and Nav2
  attach without cross process timing games.
- **URDF / xacro is the single source of truth** for the robot description. Simulation
  specific tags are injected through xacro conditionals, never hardcoded.
- **Gazebo, not Isaac Sim.** Gazebo integrates natively with `ros2_control` and runs
  headless in CI, which is the shortest path while the control stack is being brought
  up. The seams above keep a second simulation backend cheap to add later.
- **Fast DDS with a discovery server.** No multicast discovery. The onboard ROS graph
  talks over shared memory; only operator traffic crosses the wireless link.
- **No Docker.** CI runs on GitHub Actions; heavy simulation regression runs locally on
  the workstation.

See `docs/adr/` for the reasoning behind each of these.

## Layout

```
src/            colcon workspace
  interfaces/   message contracts
  core/         pure algorithms, no ROS dependency
  description/  URDF / xacro, one package per subsystem
  hardware/     ros2_control SystemInterface implementations
  control/      controllers and controller_manager configuration
  manipulation/ MoveIt 2 configuration
  navigation/   Nav2 configuration
  perception/   perception nodes and camera pipeline configuration
  behavior/     task orchestration
  teleop/       operator input
  sim/          Gazebo worlds and bridge configuration
  bringup/      top level launch entry points
config/         machine level middleware and environment configuration
deploy/         systemd units, udev rules, provisioning scripts
tools/          rosbag capture and sync, network diagnostics
tests/          cross package integration and system tests
docs/           architecture decision records, specs, runbooks
```

## Getting started

Requires Ubuntu 24.04 and ROS 2 Jazzy.

```bash
cp config/env/desktop.env.example config/env/desktop.env
```

Edit the copied file and the matching middleware profile so they carry this machine's
real addresses, then build:

```bash
colcon build --symlink-install
```

The pure logic tests need no ROS installation and run straight from the repository root:

```bash
pytest
```

Launch entry points, once the subsystems land:

```bash
ros2 launch stem_bringup sim.launch.py     # Gazebo
ros2 launch stem_bringup mock.launch.py    # mock hardware, no simulator
ros2 launch stem_bringup real.launch.py    # onboard, real hardware
```

## Licence

Apache-2.0.
