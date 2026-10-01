"""Writing files safely (N6): atomic replace, exclusive locks, atomic appends."""
import contextlib
import fcntl
import hashlib
import os
import stat
import tempfile
from pathlib import Path

from keel.store.paths import lock_dir


def atomic_write(path, text, encoding="utf-8"):
    """Replace path with text in one step: a reader sees the old or the new file, never a part.

    Temp file in the same folder, fsync, permissions of the old file, os.replace, fsync of the folder.
    A symlink is followed: the file it points to is replaced, the link stays (e.g. .claude/settings.json from a
    dotfiles repository).
    """
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode(encoding) if isinstance(text, str) else text
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))
        except FileNotFoundError:
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    _fsync_dir(path.parent)


def _fsync_dir(folder):
    try:
        fd = os.open(str(folder), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


@contextlib.contextmanager
def file_lock(path):
    """Exclusive lock for a read-modify-write of path, across processes.

    The lock file lies under the metrics root, keyed by the resolved path: atomic_write replaces the file
    itself, so a lock on its own inode would not serialize, and a lock file next to it would land in git.
    """
    target = str(Path(path).resolve())
    folder = lock_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(target.encode("utf-8")).hexdigest()[:24] + ".lock"
    fd = os.open(str(folder / name), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def append_line(path, line):
    """Append one line (str or bytes, newline added if missing) with a single write under an exclusive lock.

    Several hooks write the same log at once; printf >> in bash wrote long lines in chunks (N5).
    """
    data = line.encode("utf-8") if isinstance(line, str) else line
    if not data.endswith(b"\n"):
        data += b"\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def create_exclusive(path, text, encoding="utf-8"):
    """Create path with text only if it does not exist yet; False when it exists."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(fd, "wb") as f:
        f.write(text.encode(encoding))
    return True
