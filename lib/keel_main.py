"""Start of the command line for bin/keel. Run as a file, so sys.path[0] is lib/ and a folder or module named
keel in the current directory cannot shadow the package (python3 -m would put the current directory first).

`keel hook ...` goes straight to the hook dispatcher, without the argument parser of the other commands: it runs
on every tool call and must start fast."""
import sys



def _bytecode_cache():
    """Hooks start a Python process on every tool call; without cached bytecode each start compiles the package
    again. When the environment forbids writing bytecode (PYTHONDONTWRITEBYTECODE), the cache goes to a private
    folder under the metrics root instead, never next to the plugin's sources."""
    import os
    if not sys.dont_write_bytecode:
        return
    root = os.environ.get("KEEL_METRICS_DIR") or os.path.join(os.path.expanduser("~"), ".keel-metrics")
    sys.pycache_prefix = os.path.join(root, "pycache")
    sys.dont_write_bytecode = False


if __name__ == "__main__":
    if sys.argv[1:2] == ["hook"]:
        _bytecode_cache()
        from keel.interfaces.hooks import main as hook_main
        sys.exit(hook_main(sys.argv[2:]))
    from keel.interfaces.cli import main
    sys.exit(main())
