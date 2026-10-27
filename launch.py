import sys
from pathlib import Path
import traceback

if __name__ == "__main__":
    try:
        from studio.app import main

        if len(sys.argv) == 4 and sys.argv[1] == "--verify-package":
            from studio.diagnostics import verify

            sys.exit(verify(sys.argv[2], sys.argv[3]))
        else:
            main()
    except Exception:
        # A windowed binary has no terminal; preserve useful startup failures.
        log = Path.home() / ".dealerstudio" / "startup-error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        sys.exit(1)
