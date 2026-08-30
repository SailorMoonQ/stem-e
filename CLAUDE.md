# STEM-E

Dual arm mobile manipulator on ROS 2 Jazzy, Ubuntu 24.04.

## Commands

```bash
pytest                                  # pure logic tests, no ROS needed
colcon build --symlink-install          # full workspace
colcon test --packages-select <pkg>     # ROS level tests
```

## Invariants

These are architectural, not stylistic. Breaking one means the design has changed and
the relevant ADR in `docs/adr/` needs revisiting first.

1. **`src/core/*` must not import `rclpy` or link `rclcpp`.** Those packages are pure
   algorithms and must stay testable with no ROS installation. Node code lives elsewhere
   and wraps them.
2. **The robot description lives only in `src/description/`.** No package may hardcode
   link names, joint limits or geometry that belongs in the URDF.
3. **Simulation and real hardware differ only by the `ros2_control` plugin** selected in
   `stem_description`. Controller, MoveIt and Nav2 configuration is identical across
   backends. If a change needs a simulation only branch above the SystemInterface, the
   seam has been broken.
4. **Message definitions live only in `stem_msgs`.** No ad hoc dictionaries or JSON blobs
   on topics.
5. **No real network addresses in tracked files.** `config/` holds `.example` files using
   documentation addresses; real values go in the gitignored copies. This repository is
   public.

## Network

Fast DDS with a discovery server, no multicast. The middleware profiles restrict UDP to
the physical interface so DDS never binds to a VPN or proxy TUN device, and keep the
shared memory transport for onboard traffic. Operator machines must set
`ROS_SUPER_CLIENT=true` or CLI tools will not see the full graph.

## Data

rosbags record to local storage on the robot and sync to the NAS afterwards. Never record
straight to network storage: the robot's only link is WiFi, and a bag with dropped frames
is worthless. See `tools/rosbag/`.
