# STEM-E Platform Design

- **Date:** 2026-08-30
- **Status:** Approved, scaffolding in place
- **Scope:** The skeleton every subsystem plugs into: layering, package decomposition,
  the hardware backend seam, network discipline, data flow and test strategy.
- **Out of scope:** The subsystems themselves. Base kinematics, the arm real time layer,
  the lift, the head, perception and autonomy each get their own spec, plan and build
  cycle against this skeleton.

---

## 1. What is being built

STEM-E, a full size dual arm mobile manipulator: wheeled base, vertical lift, two arms
and a sensor head. Built from zero on ROS 2 Jazzy and Ubuntu 24.04.

The name expands to **S**upply **T**ransfer **E**levating **M**anipulator,
**E**arth-class, following the naming grammar of the machines in *WALL-E*.

This document exists because a robot with four actuated subsystems cannot be specified in
one pass. What can, and must, be settled once is the structure they all share.

## 2. Fleet and constraints

| Machine | Role | Constraint that shapes the design |
|---|---|---|
| Onboard computer | Runs the whole real time graph | WiFi is its only link |
| Workstation | Development, simulation, operator console | Ubuntu on bare metal, no virtualisation layer |
| NAS | rosbag and dataset archive | Appliance OS, storage only, no compute |
| Router | 192.168.x.0/24 flat LAN | No multicast assumptions |

The decisive fact is that the onboard computer runs everything real time. The 500 Hz
control loop, the cameras and every high rate topic live on one host and talk over shared
memory. **The wireless link carries operator traffic only.** Most of the design below
follows from that sentence.

## 3. Layering and seams

Four seams isolate change. Everything else is a consequence.

```
operator tooling (rviz2, teleop, web)       <- crosses WiFi, seam 4
task layer (behaviour trees)
motion layer (MoveIt 2, Nav2, lift, head)
                                            <- seam 3, stem_msgs
control layer (controller_manager @ 500 Hz)
                                            <- seam 2, SystemInterface
hardware layer (CAN, motor controllers)     <- onboard, shared memory
```

**Seam 1, pure logic vs ROS.** Kinematics, trajectory generation, safety logic and wire
protocol live in `src/core/*` with no `rclpy` or `rclcpp` dependency. ROS nodes are thin
wrappers. This is the highest return seam in the design: it makes the algorithmic core
testable in seconds with no ROS installed, which is what layer 1 of CI runs, and it keeps
the hard parts debuggable without starting a graph.

**Seam 2, the hardware backend.** The `ros2_control` SystemInterface is the only place
that differs between real hardware, Gazebo and mock. One URDF, selected through xacro
conditionals:

| Backend | Plugin | Used for |
|---|---|---|
| Real | `stem_*_hardware/*SystemHardware` | The robot |
| Simulation | `gz_ros2_control/GazeboSimSystem` | Primary development |
| Mock | `mock_components/GenericSystem` | CI, no simulator needed |

Controller, MoveIt and Nav2 configuration is byte identical across all three. A change
that needs a simulation only branch above this seam means the seam is broken.

**Seam 3, the interface contract.** Message, service and action definitions live only in
`stem_msgs`. No ad hoc dictionaries on topics.

**Seam 4, visualisation degradation.** The one place where the wireless link is
unavoidable is an operator subscribing to a camera or point cloud from a workstation.
This is handled explicitly rather than discovered painfully: `stem_camera_config` defines
compressed and throttled variants, and operator tooling defaults to those.

## 4. Package decomposition

25 packages, grouped by role rather than by subsystem, because the grouping that matters
is which seam a package sits on.

```
src/interfaces/   stem_msgs
src/core/         stem_kinematics  stem_trajectory  stem_safety  stem_protocol
src/description/  stem_description + one per subsystem
src/hardware/     stem_{base,lift,arm,head}_hardware
src/control/      stem_controllers  stem_control_config
src/manipulation/ stem_moveit_config
src/navigation/   stem_nav_config
src/perception/   stem_perception  stem_camera_config
src/behavior/     stem_task_server
src/teleop/       stem_teleop
src/sim/          stem_gz_sim  stem_worlds
src/bringup/      stem_bringup
```

Descriptions are split per subsystem as xacro macros so a single arm can be loaded on its
own during bring up, which keeps simulation start times short while iterating.

`stem_arm_description` is instantiated twice, left and right, rather than duplicated.

## 5. Control structure

One `controller_manager` at 500 Hz covering every subsystem, each as its own hardware
component. Components slower than 500 Hz divide down inside their own `read()` and
`write()`.

The alternative, one manager per subsystem in separate processes, was rejected: a unified
`/joint_states` is what MoveIt and Nav2 expect, and cross process timing coordination buys
nothing at this stage. The cost is a shared update budget, which makes non blocking
hardware interfaces a hard requirement rather than a style preference. Splitting later is
a launch file change and does not move any interface. See ADR 0006.

## 6. Network and middleware

Fast DDS with a discovery server on the onboard computer. No multicast. See ADR 0002.

Three rules, enforced by files in `config/` rather than by memory:

1. **Interface whitelisting.** Transport profiles pin UDP to the physical interface, so
   DDS cannot bind to a VPN or proxy TUN device.
2. **Shared memory stays declared.** Profiles list both SHM and the whitelisted UDP
   transport. Declaring only UDP pushes onboard traffic onto the loopback path.
3. **`ROS_SUPER_CLIENT=true` on operator machines**, or introspection tools report a
   partial graph.

Real addresses never enter tracked files. `config/` holds `.example` files with
documentation addresses; the working copies are gitignored. The repository is public.

## 7. Data flow

rosbags record to local storage on the robot and sync to the NAS afterwards. Recording
straight to network storage over WiFi drops messages silently, and a bag with holes is
discovered only during analysis. See ADR 0005.

```
onboard NVMe  --record-->  /data/rosbags/<date>/<session>
                             |
                   after the session, resumable
                             v
                     NAS  /rosbags/<date>/<session>
                             |
                     workstation reads over NFS
```

Consequences worth stating: the onboard computer needs a local drive sized for a full
session, and nothing in this path depends on the 10GbE switch that has not been bought.
That link only changes how fast the workstation reads the archive.

## 8. Simulation

Gazebo, not Isaac Sim. See ADR 0003. Gazebo integrates natively with `ros2_control`, runs
headless, and is the shortest path while the control stack is being brought up. Isaac Sim
becomes worth adding when perception and learned policies start; the seams above keep that
cheap, at the cost of a second asset representation in USD when the time comes.

## 9. Test strategy

Four layers, fast to slow. See ADR 0004 for where each runs.

| Layer | What | Where | Speed |
|---|---|---|---|
| 1 | Lint and `src/core` unit tests, no ROS | GitHub Actions | seconds |
| 2 | `colcon build` and `colcon test` | GitHub Actions | minutes |
| 3 | Mock backend integration | GitHub Actions | minutes |
| 4 | Headless Gazebo regression | Workstation | tens of minutes |

No Docker anywhere. The NAS is storage only.

## 10. Open decisions

These are deliberately deferred to the subsystem specs, because settling them now would be
guessing.

1. **Drive actuator class and the CAN topology.** Determines the base and arm hardware
   interfaces and the number of CAN buses.
2. **Whether the arms need a separate real time controller** below the SystemInterface, or
   whether a 500 Hz `controller_manager` on the onboard computer is sufficient.
3. **The safety chain.** A machine this size needs a hardware emergency stop independent
   of all software, plus layered software deadman timers. `stem_safety` holds the pure
   logic; the physical design is a subsystem concern.
4. **Onboard compute selection and local storage sizing**, the latter driven by the
   recording profile in section 7.
5. **Chassis geometry and stability envelope.** Arms extended with payload is the worst
   case for tipping and constrains reach and acceleration limits.

## 11. Non goals

- Autonomy beyond Nav2 based navigation.
- Legged locomotion.
- Multi robot or fleet management.
- Remote operation over the internet. Local network only.
