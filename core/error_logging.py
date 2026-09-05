"""
Automatic error logging, mirroring the PC launcher's
~/.config/arch-client-launcher/error_logs/*.txt behavior: every unhandled
exception gets written to a timestamped file with a full traceback,
instead of crashing silently.
"""

import os
import sys
import threading
import traceback
from datetime import datetime

LOG_DIR = os.path.join(os.path.expanduser("~"), ".archclient_mobile", "error_logs")


def _write_log(kind, exc_type, exc_value, exc_tb):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOG_DIR, f"error_{kind}_{ts}.txt")
    with open(path, "w") as f:
        f.write(f"[{kind} thread] {datetime.now().isoformat()}\n\n")
        f.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    return path


def _excepthook(exc_type, exc_value, exc_tb):
    path = _write_log("main", exc_type, exc_value, exc_tb)
    print(f"Unhandled error, log saved to {path}")
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _thread_excepthook(args):
    path = _write_log("background", args.exc_type, args.exc_value, args.exc_traceback)
    print(f"Unhandled error in background thread, log saved to {path}")


def install():
    """Call once at app startup to catch exceptions on the main thread and worker threads."""
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook


def list_logs():
    if not os.path.isdir(LOG_DIR):
        return []
    return sorted(os.listdir(LOG_DIR), reverse=True)
