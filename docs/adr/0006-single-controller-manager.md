# 6. One controller_manager at 500 Hz

- **Date:** 2026-08-30
- **Status:** Accepted

## Context

STEM-E has four actuated subsystems with different natural rates. The arms need a
500 Hz servo loop. The base is comfortable at 100 Hz, and the lift and head are slower
still. `ros2_control` allows one `controller_manager` per process, with a single update
rate, but a URDF may declare several `<ros2_control>` hardware components.

Two structures are possible: one `controller_manager` covering every subsystem, or one
per subsystem in separate processes.

## Decision

One `controller_manager` running at 500 Hz, with every subsystem as a separate hardware
component. Components that do not need 500 Hz divide down internally by returning early
from `read()` and `write()` on cycles they skip.

## Consequences

- `/joint_states` is unified across the whole robot, which is what MoveIt and Nav2 expect.
  Neither needs configuration to stitch sources together.
- No cross process timing coordination, and no ambiguity about which process owns an
  actuator.
- The 500 Hz budget is shared. A slow hardware component that blocks in `read()` degrades
  the arms. Hardware interfaces must be non blocking, which is a requirement worth stating
  explicitly because it is easy to violate with a naive serial or CAN read.
- If CPU headroom runs out, splitting into multiple `controller_manager` processes is a
  launch file change plus separate parameter files. The interfaces above do not move. This
  is the reason the decision is safe to make now rather than deferring it.
