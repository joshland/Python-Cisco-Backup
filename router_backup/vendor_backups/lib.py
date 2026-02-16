"""Library functions for vendor backup modules."""

from typing import Optional
from router_backup.storage import get_global_storage, write_backup


# Re-export write_backup for backward compatibility
__all__ = ["write_backup"]
