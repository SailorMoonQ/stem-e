# Runbook: discovery server and DDS binding

The two failures below account for most of the time lost to networking on this project.
Both look like "the robot is not there" and neither produces a useful error.

## Bringing the graph up

On the robot:

```bash
source config/env/robot.env
sudo systemctl status stem-discovery-server
```

On a workstation:

```bash
source config/env/desktop.env
tools/net/check_dds_binding.sh
ros2 node list
```

## Failure 1: partial graph

**Symptom.** `ros2 node list` and `ros2 topic list` show some of the graph or none of it.
rviz2 offers no topics. Nodes that were started together can see each other, but nothing
else is visible.

**Cause.** Under a discovery server, a plain client is only told about endpoints it has
been matched with. Introspection tools need the whole graph, which requires being a super
client.

**Fix.** `export ROS_SUPER_CLIENT=true` on every operator machine. It is in
`config/env/desktop.env.example`; check it survived into the copy.

This is not needed on the robot, where the nodes are the graph.

## Failure 2: DDS bound to the wrong interface

**Symptom.** Discovery appears to work but no data arrives, or peers appear and then time
out. Frequently starts the moment a VPN or proxy client is switched on.

**Cause.** Fast DDS enumerates every interface it can see and advertises addresses on all
of them, including TUN devices. Peers try the unreachable address first.

**Check.**

```bash
tools/net/check_dds_binding.sh
```

Look for an interface whitelist in the profile and confirm the whitelisted address is the
physical interface, not a tunnel.

**Fix.** Both transport profiles under `config/middleware/` pin UDP to one address. Make
sure `FASTRTPS_DEFAULT_PROFILES_FILE` points at the copy, not the `.example`, and that the
address in it matches `ip -o -4 addr show`.

A whitelist alone is not sufficient. The profile must also declare an SHM transport and
set `useBuiltinTransports` to false. Declaring only UDP quietly moves onboard traffic onto
the loopback path and costs a lot of onboard bandwidth for no reason.

## Restarting cleanly

Discovery state is held by the running processes. After changing a profile or an
environment file, restart everything, not just the changed node:

```bash
# robot
sudo systemctl restart stem-discovery-server stem-bringup

# workstation: exit every ros2 process, then re-source
source config/env/desktop.env
```

## When the server is down

Endpoints that already matched keep communicating. New nodes cannot join. If the robot is
mid session, do not restart the discovery server: finish the session first, since a
restart drops every pending match and the running graph will not re-form on its own.
