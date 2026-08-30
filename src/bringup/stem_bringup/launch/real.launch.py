"""Bring up STEM-E on the real robot.

Runs on the onboard computer. Every node started here shares a host, so the whole
graph communicates over the Fast DDS shared memory transport and none of it crosses
the wireless link. See docs/adr/0002-fastdds-discovery-server.md.

TODO: load the robot description with the real hardware plugins, start the
controller_manager from stem_control_config, and bring up the camera pipeline with
the throttled and compressed topics from stem_camera_config.
"""

from launch import LaunchDescription


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([])
