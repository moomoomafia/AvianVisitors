"""Windows-only stand-in for POSIX fcntl, for running the parent's frame tests locally.

Used ONLY via PYTHONPATH=.pi/research/pre-v03/stubs (never imported by product code, never
committed to the parent's tree). frame/display.py imports fcntl at module level for its render
lock (`fcntl.flock`, frame/display.py:524-528); this stub makes the module importable and the
lock a no-op. Tests that exercise real locking semantics are therefore NOT valid under this stub;
CI (Linux) remains authoritative.
"""

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def flock(fd, operation):  # noqa: ARG001 - signature mirrors fcntl.flock
    return None
