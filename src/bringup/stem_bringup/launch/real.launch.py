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
Bring up STEM-E on the real robot.

Runs on the onboard computer. Every node started here shares a host, so the whole
graph communicates over the Fast DDS shared memory transport and none of it crosses
the wireless link. See docs/adr/0002-fastdds-discovery-server.md.

TODO: load the robot description with the real hardware plugins, start the
controller_manager from stem_control_config, and bring up the camera pipeline with
the throttled and compressed topics from stem_camera_config.
"""

from launch import LaunchDescription


def generate_launch_description() -> LaunchDescription:
    """Return the launch description for the real hardware backend."""
    return LaunchDescription([])
