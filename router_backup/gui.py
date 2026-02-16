"""
GUI entry point for router-backup-gui command.
"""

import sys
import tkinter as tk
from tkinter import messagebox


def main():
    """Main entry point for router-backup-gui."""
    try:
        # Import and run the GUI
        from router_backup import gui_module

        gui_module.run_gui()
    except ImportError as e:
        messagebox.showerror(
            "Import Error",
            f"Failed to import GUI module: {e}\n\n"
            "Please ensure all dependencies are installed:\n"
            "pip install router-backup[gui]",
        )
        sys.exit(1)
    except Exception as e:
        messagebox.showerror("Error", f"GUI Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
