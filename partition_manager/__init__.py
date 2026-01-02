"""
DiskRim - Modern Open Source Partition Manager

A cross-platform partition manager with GUI and CLI interfaces,
supporting Windows and Linux operating systems.
"""

__version__ = "1.5.0"
__author__ = "DiskRim Contributors"
__license__ = "MIT"

# Public API
from .utils.platform_check import get_platform, is_admin, PlatformInfo
from .utils.validators import DiskValidator, PartitionValidator

__all__ = [
    "__version__",
    "get_platform",
    "is_admin",
    "PlatformInfo",
    "DiskValidator",
    "PartitionValidator",
]
