"""Bring up STEM-E in Gazebo.

One of three entry points that differ only in which ros2_control backend the robot
description selects. Everything downstream, controllers included, is shared.

    sim.launch.py    Gazebo            use_sim:=true
    mock.launch.py   mock hardware     use_mock:=true
    real.launch.py   onboard hardware  neither

TODO: spawn the Gazebo world from stem_worlds, bridge topics via stem_gz_sim, and
load the controllers from stem_control_config.
"""

from launch import LaunchDescription


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([])
