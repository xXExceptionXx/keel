"""Start of the command line for bin/keel. Run as a file, so sys.path[0] is lib/ and a folder or module named
keel in the current directory cannot shadow the package (python3 -m would put the current directory first).

`keel hook ...` goes straight to the hook dispatcher, without the argument parser of the other commands: it runs
on every tool call and must start fast."""
import sys

if __name__ == "__main__":
    if sys.argv[1:2] == ["hook"]:
        from keel.interfaces.hooks import main as hook_main
        sys.exit(hook_main(sys.argv[2:]))
    from keel.interfaces.cli import main
    sys.exit(main())
