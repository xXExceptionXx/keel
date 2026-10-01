"""Errors of the core with their exit codes (System-ADR 0019).

0 no or success, 1 yes or rejected on the merits, 2 could not check (usage, tool or internal error).
"""

EXIT_REJECTED = 1
EXIT_CANNOT_CHECK = 2


class KeelError(Exception):
    """Base error; ends a command with exit_code."""

    exit_code = EXIT_CANNOT_CHECK


class UsageError(KeelError):
    """Wrong command line."""


class ToolError(KeelError):
    """An outside tool (git, gh, jq) failed or is missing."""


class Rejected(KeelError):
    """A rule says no; not a failure of the program."""

    exit_code = EXIT_REJECTED


class ReadError(KeelError):
    """A file could not be read (missing, no permission, not UTF-8)."""


class ParseError(KeelError):
    """Text the codec does not understand; names the file and the line."""

    def __init__(self, message, line=None, source=None):
        self.message = message
        self.line = line
        self.source = source
        where = ":".join(str(x) for x in (source, line) if x is not None)
        super().__init__(f"{where}: {message}" if where else message)
