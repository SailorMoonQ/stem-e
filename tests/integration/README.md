# Integration tests

Layer 3 of the test strategy: cross package tests that need a ROS graph but no simulator.

These run against the mock hardware backend (`mock_components/GenericSystem`), which
echoes commands back as state. That is enough to exercise controller loading, MoveIt
planning and the task layer, and it is fast enough to gate every pull request.

Anything that needs physics belongs in `tests/system` instead.
