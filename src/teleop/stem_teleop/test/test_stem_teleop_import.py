"""Placeholder test: the package imports cleanly. Replace as real code lands.

The filename is package qualified on purpose. pytest derives module names from the
file basename, so several packages each holding test/test_import.py collide during
collection.
"""

import stem_teleop


def test_package_imports() -> None:
    assert stem_teleop is not None
