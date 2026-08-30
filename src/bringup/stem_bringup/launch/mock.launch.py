# Copyright 2026 SailorMoonQ
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Bring up STEM-E against mock hardware.

No simulator and no robot. `mock_components/GenericSystem` echoes commands back as
state, which is enough to exercise controllers, MoveIt planning and the task layer.
This is the backend CI uses.

TODO: load the robot description with use_mock:=true and start the controllers from
stem_control_config.
"""

from launch import LaunchDescription


def generate_launch_description() -> LaunchDescription:
    """Return the launch description for the mock hardware backend."""
    return LaunchDescription([])
