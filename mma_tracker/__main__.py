"""Start the app: python -m mma_tracker [--demo]"""

import sys
import tkinter as tk

from . import backup, demo
from .store import Store
from .ui.app import App


def _dpi_aware():
    """Sharp text on high-DPI screens. SetProcessDPIAware exists since Vista."""
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    _dpi_aware()
    demo_mode = "--demo" in sys.argv[1:]
    if demo_mode:
        store = Store(demo.demo_db_path())
        if demo.is_empty(store):
            demo.seed(store)
    else:
        store = Store()
        try:
            backup.daily_backup(store)
        except Exception:  # a failed backup must never stop the coach working
            pass
    root = tk.Tk()
    App(root, store, demo=demo_mode)
    try:
        root.mainloop()
    finally:
        store.close()


if __name__ == "__main__":
    main()
