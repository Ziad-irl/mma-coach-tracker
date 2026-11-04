"""Start the app: python -m mma_tracker"""

import tkinter as tk

from . import backup
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
    store = Store()
    try:
        backup.daily_backup(store)
    except Exception:  # a failed backup must never stop the coach working
        pass
    root = tk.Tk()
    App(root, store)
    try:
        root.mainloop()
    finally:
        store.close()


if __name__ == "__main__":
    main()
