# 5. rosbags record to local storage, then sync to the NAS

- **Date:** 2026-08-30
- **Status:** Accepted

## Context

The NAS is the archive for rosbags and datasets, and it exports both SMB and NFS. The
obvious approach is to mount it on the robot and record straight to it.

That does not survive contact with the link budget. The robot's only network interface is
WiFi. A full recording session on a dual arm mobile manipulator means several camera
streams plus joint state at control rate, and the instantaneous write bandwidth exceeds
what the wireless link will sustain. The failure mode is not a clean error: the recorder
drops messages, and a bag with holes in it is worse than no bag, because the holes are
discovered later during analysis.

## Decision

Two stages, always:

1. **Record to local storage on the robot.** The onboard computer needs a local NVMe
   drive sized for a full session. This is a hardware requirement, not a preference.
2. **Sync to the NAS after the session ends**, with a resumable transfer. Interrupted
   transfers resume rather than restart, and the local copy is only removed after the
   transfer verifies.

Playback and analysis read from the NAS over NFS from the workstation. Tooling for both
stages lives in `tools/rosbag/`.

## Consequences

- Recording quality no longer depends on wireless conditions.
- Bags exist in two places until the sync verifies, which is the correct trade.
- Local disk on the robot becomes a capacity constraint that has to be monitored. A
  session that fills the drive fails the same way that recording over WiFi would.
- Nothing in the recording path depends on the 10GbE switch that has not been bought yet.
  That link only affects how fast the workstation reads the archive.
