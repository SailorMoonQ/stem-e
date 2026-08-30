# 3. Gazebo as the simulator, not Isaac Sim

- **Date:** 2026-08-30
- **Status:** Accepted

## Context

Simulation is a first class target: hardware arrives in stages, so simulation is where
most development and all automated regression happens. The workstation has an RTX 4090,
so Isaac Sim is viable on hardware grounds and the choice had to be made on merit.

What actually blocks progress over the next stretch of this project is URDF modelling,
`ros2_control` hardware interfaces, kinematics, controller tuning and the teleoperation
loop. Gazebo integrates with all of that natively through `gz_ros2_control` and
`ros_gz_bridge`. Isaac Sim reaches ROS 2 through a bridge and needs more scaffolding to
reach the same point.

Isaac Sim earns its keep on photorealistic rendering, synthetic data, domain
randomisation and reinforcement learning. Those matter for perception and learned
policies, which come later.

## Decision

Use Gazebo as the simulator. Keep the seams that make a second backend cheap:

- URDF / xacro is the single source of truth for the robot description. Simulator
  specific tags are injected through xacro conditionals, never written inline.
- The `ros2_control` SystemInterface is the switch point between real hardware,
  simulation and mock. Nothing above it knows which backend is running.

## Consequences

- Simulation runs headless, so regression can run without a GPU.
- The workstation GPU is idle for now. It becomes relevant when perception and learned
  policies start, which is also when Isaac Sim becomes worth adding.
- Contact rich manipulation will be less faithful in Gazebo than in a PhysX based
  simulator. Accepted for now; revisit when grasping accuracy becomes the limiting
  factor rather than the control stack.
- Adding Isaac Sim later means maintaining a second asset representation in USD, since
  URDF import is effectively one way. That cost is deferred, not avoided.
