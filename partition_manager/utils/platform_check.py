"""
Platform detection and system capability checking.

This module provides functions to detect the operating system,
check for administrative privileges, and verify required utilities.
"""

import os
import sys
import platform
import subprocess
import shutil
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class OSType(Enum):
    """Operating system types."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class BootMode(Enum):
    """System boot mode."""
    UEFI = "uefi"
    LEGACY = "legacy"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """Platform information container."""
    os_type: OSType
    os_version: str
    os_release: str
    is_admin: bool
    boot_mode: BootMode
    python_version: str
    architecture: str
    
    def __str__(self) -> str:
        return (
            f"Platform: {self.os_type.value}\n"
            f"Version: {self.os_version} {self.os_release}\n"
            f"Admin: {self.is_admin}\n"
            f"Boot Mode: {self.boot_mode.value}\n"
            f"Python: {self.python_version}\n"
            f"Architecture: {self.architecture}"
        )


def get_os_type() -> OSType:
    """Detect the operating system type."""
    system = platform.system().lower()
    
    if system == "windows":
        return OSType.WINDOWS
    elif system == "linux":
        return OSType.LINUX
    elif system == "darwin":
        return OSType.MACOS
    else:
        return OSType.UNKNOWN


def is_admin() -> bool:
    """
    Check if the current process has administrative privileges.
    
    Returns:
        True if running as admin/root, False otherwise
    """
    os_type = get_os_type()
    
    try:
        if os_type == OSType.WINDOWS:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        elif os_type == OSType.LINUX:
            return os.geteuid() == 0
        else:
            return False
    except Exception:
        return False


def detect_boot_mode() -> BootMode:
    """
    Detect whether the system is booted in UEFI or Legacy mode.
    
    Returns:
        BootMode indicating UEFI, Legacy, or Unknown
    """
    os_type = get_os_type()
    
    try:
        if os_type == OSType.WINDOWS:
            # Check if UEFI firmware variables directory exists
            if os.path.exists("C:\\Windows\\Panther\\setupact.log"):
                with open("C:\\Windows\\Panther\\setupact.log", "r", encoding="utf-16-le") as f:
                    content = f.read()
                    if "Detected boot environment: EFI" in content:
                        return BootMode.UEFI
            
            # Alternative: Check using bcdedit (requires admin)
            if is_admin():
                result = subprocess.run(
                    ["bcdedit"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "path" in result.stdout.lower() and "efi" in result.stdout.lower():
                    return BootMode.UEFI
                    
        elif os_type == OSType.LINUX:
            # Check if /sys/firmware/efi exists
            if os.path.exists("/sys/firmware/efi"):
                return BootMode.UEFI
            else:
                return BootMode.LEGACY
                
    except Exception:
        pass
    
    return BootMode.UNKNOWN


def check_utility(utility_name: str) -> bool:
    """
    Check if a command-line utility is available.
    
    Args:
        utility_name: Name of the utility to check
        
    Returns:
        True if utility is found, False otherwise
    """
    return shutil.which(utility_name) is not None


def get_required_utilities() -> Dict[OSType, List[str]]:
    """
    Get list of required utilities for each operating system.
    
    Returns:
        Dictionary mapping OS types to required utilities
    """
    return {
        OSType.WINDOWS: [
            "diskpart",
            "wmic",
            "powershell",
        ],
        OSType.LINUX: [
            "lsblk",
            "fdisk",
            "parted",
            "mkfs",
            "smartctl",
            "blkid",
        ],
    }


def check_requirements() -> Tuple[bool, List[str]]:
    """
    Check if all required utilities are available.
    
    Returns:
        Tuple of (all_present, missing_utilities)
    """
    os_type = get_os_type()
    required = get_required_utilities().get(os_type, [])
    
    missing = []
    for utility in required:
        if not check_utility(utility):
            missing.append(utility)
    
    return (len(missing) == 0, missing)


def get_platform() -> PlatformInfo:
    """
    Get comprehensive platform information.
    
    Returns:
        PlatformInfo object with system details
    """
    os_type = get_os_type()
    
    return PlatformInfo(
        os_type=os_type,
        os_version=platform.version(),
        os_release=platform.release(),
        is_admin=is_admin(),
        boot_mode=detect_boot_mode(),
        python_version=platform.python_version(),
        architecture=platform.machine(),
    )


def require_admin(raise_error: bool = True) -> bool:
    """
    Check for admin privileges and optionally raise error.
    
    Args:
        raise_error: If True, raise PermissionError when not admin
        
    Returns:
        True if admin, False otherwise
        
    Raises:
        PermissionError: If not admin and raise_error is True
    """
    if not is_admin():
        if raise_error:
            os_type = get_os_type()
            if os_type == OSType.WINDOWS:
                msg = "This operation requires Administrator privileges. Please run as Administrator."
            else:
                msg = "This operation requires root privileges. Please run with sudo."
            raise PermissionError(msg)
        return False
    return True


if __name__ == "__main__":
    # Display platform information
    info = get_platform()
    print(info)
    print()
    
    # Check requirements
    all_present, missing = check_requirements()
    if all_present:
        print("✅ All required utilities are available")
    else:
        print("❌ Missing required utilities:")
        for util in missing:
            print(f"  - {util}")
