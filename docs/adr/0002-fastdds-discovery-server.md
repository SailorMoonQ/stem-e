# 2. Fast DDS with a discovery server, not rmw_zenoh

- **Date:** 2026-08-30
- **Status:** Accepted

## Context

The robot's only network link is WiFi. Multicast discovery over WiFi is unreliable and
does not survive access point behaviour such as IGMP snooping and client isolation, so
discovery must be unicast. Two options were considered: `rmw_zenoh`, and the default
`rmw_fastrtps_cpp` configured with a discovery server.

The decisive fact is where the traffic actually lives. The onboard computer runs the
whole real time graph: the 500 Hz control loop, cameras, and every high rate topic. Those
nodes talk to each other through the Fast DDS shared memory transport and never touch a
network interface. The wireless link carries only operator traffic.

`rmw_zenoh` was attractive for its explicit endpoint configuration and its behaviour on
lossy links, but it optimises a path that is not on the critical path here, at the cost
of a smaller ecosystem and thinner tooling.

## Decision

Use `rmw_fastrtps_cpp` with a Fast DDS discovery server. The server runs on the onboard
computer, which is the one machine that is always up.

The RMW choice is made through the `RMW_IMPLEMENTATION` environment variable and touches
no source code, so this decision is reversible at deployment level.

Three things must hold, and they are enforced in `config/`:

1. **Interface whitelisting.** Transport profiles pin UDP to the physical interface.
   Without this, Fast DDS enumerates every interface including VPN and proxy TUN devices,
   and advertises addresses that peers cannot reach.
2. **Shared memory stays enabled.** The profiles declare both an SHM and a whitelisted
   UDP transport. Declaring only UDP with `useBuiltinTransports` disabled would silently
   push onboard traffic onto the loopback network path.
3. **`ROS_SUPER_CLIENT=true` on operator machines.** Under a discovery server a plain
   client sees only endpoints it has matched, so CLI tools, rqt and rviz2 report a
   partial graph without it.

## Consequences

- No multicast dependency, which is what WiFi required.
- The discovery server is a single point of failure for discovery. Already matched
  endpoints keep communicating if it dies, and redundant servers are available if this
  becomes a real problem in practice.
- The data plane is still DDS over UDP. Subscribing to a camera or point cloud topic from
  a workstation will cross WiFi and behave badly. This is handled at a different layer:
  see seam 4 and `stem_camera_config`.
- Discovery server setup is fiddly enough that it belongs in a runbook, not in tribal
  memory. See `docs/runbooks/`.
