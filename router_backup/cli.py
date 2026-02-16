"""
CLI entry point for router-backup command.
"""

import sys
from router_backup.multivendor_run import app, interactive_menu


def main():
    """Main entry point for router-backup CLI."""
    if len(sys.argv) > 1:
        app()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
