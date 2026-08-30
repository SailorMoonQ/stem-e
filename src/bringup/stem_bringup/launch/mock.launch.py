"""Bring up STEM-E against mock hardware.

No simulator and no robot. `mock_components/GenericSystem` echoes commands back as
state, which is enough to exercise controllers, MoveIt planning and the task layer.
This is the backend CI uses.

TODO: load the robot description with use_mock:=true and start the controllers from
stem_control_config.
"""

from launch import LaunchDescription


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([])
