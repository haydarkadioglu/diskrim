"""
Input validation and safety checks for disk operations.

Provides validators for disk identifiers, partition sizes,
filesystem compatibility, and operation safety.
"""

import re
from typing import Optional, Tuple, List
from enum import Enum
from pathlib import Path

from .platform_check import get_os_type, OSType


class FilesystemType(Enum):
    """Supported filesystem types."""
    NTFS = "ntfs"
    EXFAT = "exfat"
    FAT32 = "fat32"
    EXT4 = "ext4"
    EXT3 = "ext3"
    EXT2 = "ext2"
    XFS = "xfs"
    BTRFS = "btrfs"
    SWAP = "swap"
    UNKNOWN = "unknown"


class DiskValidator:
    """Validator for disk identifiers and properties."""
    
    # Regex patterns for disk identifiers
    LINUX_DISK_PATTERN = re.compile(r'^/dev/(sd[a-z]|nvme\d+n\d+|hd[a-z]|vd[a-z]|mmcblk\d+)$')
    WINDOWS_DISK_PATTERN = re.compile(r'^\\\\\.\\PhysicalDrive\d+$')
    
    @staticmethod
    def is_valid_disk_id(disk_id: str) -> bool:
        """
        Validate disk identifier format.
        
        Args:
            disk_id: Disk identifier string
            
        Returns:
            True if valid format, False otherwise
        """
        os_type = get_os_type()
        
        if os_type == OSType.LINUX:
            return bool(DiskValidator.LINUX_DISK_PATTERN.match(disk_id))
        elif os_type == OSType.WINDOWS:
            return bool(DiskValidator.WINDOWS_DISK_PATTERN.match(disk_id))
        
        return False
    
    @staticmethod
    def is_valid_partition_id(partition_id: str) -> bool:
        """
        Validate partition identifier format.
        
        Args:
            partition_id: Partition identifier string
            
        Returns:
            True if valid format, False otherwise
        """
        os_type = get_os_type()
        
        if os_type == OSType.LINUX:
            # Matches /dev/sda1, /dev/nvme0n1p1, etc.
            pattern = re.compile(r'^/dev/(sd[a-z]\d+|nvme\d+n\d+p\d+|hd[a-z]\d+|vd[a-z]\d+|mmcblk\d+p\d+)$')
            return bool(pattern.match(partition_id))
        elif os_type == OSType.WINDOWS:
            # Matches C:, D:, etc.
            pattern = re.compile(r'^[A-Z]:$')
            return bool(pattern.match(partition_id))
        
        return False
    
    @staticmethod
    def is_system_disk(disk_id: str) -> bool:
        """
        Check if disk is likely a system disk.
        
        Args:
            disk_id: Disk identifier
            
        Returns:
            True if appears to be system disk
        """
        os_type = get_os_type()
        
        # Simple heuristic: first disk is usually system disk
        if os_type == OSType.LINUX:
            return disk_id in ['/dev/sda', '/dev/nvme0n1', '/dev/hda']
        elif os_type == OSType.WINDOWS:
            return disk_id == r'\\.\PhysicalDrive0'
        
        return False
    
    @staticmethod
    def is_removable_media(disk_id: str) -> bool:
        """
        Check if disk identifier suggests removable media.
        
        Note: This is a heuristic check. Use proper system APIs for accurate detection.
        
        Args:
            disk_id: Disk identifier
            
        Returns:
            True if appears to be removable
        """
        # USB devices often have specific patterns
        # This is just a heuristic; actual implementation should use system APIs
        os_type = get_os_type()
        
        if os_type == OSType.LINUX:
            # MMC/SD cards
            if 'mmcblk' in disk_id:
                return True
        
        return False


class PartitionValidator:
    """Validator for partition operations and parameters."""
    
    # Size multipliers
    SIZE_UNITS = {
        'B': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
    }
    
    @staticmethod
    def parse_size(size_str: str) -> Optional[int]:
        """
        Parse size string to bytes.
        
        Args:
            size_str: Size string (e.g., "10GB", "500M", "1T")
            
        Returns:
            Size in bytes, or None if invalid
        """
        size_str = size_str.strip().upper()
        
        # Extract number and unit
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]B?)$', size_str)
        if not match:
            # Try without unit (assume bytes)
            if size_str.isdigit():
                return int(size_str)
            return None
        
        number, unit = match.groups()
        number = float(number)
        
        if unit not in PartitionValidator.SIZE_UNITS:
            return None
        
        return int(number * PartitionValidator.SIZE_UNITS[unit])
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """
        Format bytes to human-readable size.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted string (e.g., "10.5 GB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / (1024 ** 2):.2f} MB"
        elif size_bytes < 1024 ** 4:
            return f"{size_bytes / (1024 ** 3):.2f} GB"
        else:
            return f"{size_bytes / (1024 ** 4):.2f} TB"
    
    @staticmethod
    def validate_size_range(
        size: int,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate size is within acceptable range.
        
        Args:
            size: Size in bytes
            min_size: Minimum allowed size
            max_size: Maximum allowed size
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if min_size and size < min_size:
            return False, f"Size too small. Minimum: {PartitionValidator.format_size(min_size)}"
        
        if max_size and size > max_size:
            return False, f"Size too large. Maximum: {PartitionValidator.format_size(max_size)}"
        
        # Check alignment (should be multiple of 1MB for best performance)
        if size % (1024 * 1024) != 0:
            # This is a warning, not an error
            pass
        
        return True, None
    
    @staticmethod
    def validate_label(label: str, filesystem: FilesystemType) -> Tuple[bool, Optional[str]]:
        """
        Validate partition label based on filesystem constraints.
        
        Args:
            label: Proposed label
            filesystem: Filesystem type
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not label:
            return True, None  # Empty label is allowed
        
        # Filesystem-specific constraints
        if filesystem == FilesystemType.NTFS:
            if len(label) > 32:
                return False, "NTFS labels must be 32 characters or less"
        elif filesystem == FilesystemType.FAT32:
            if len(label) > 11:
                return False, "FAT32 labels must be 11 characters or less"
            # FAT32 labels should be uppercase
            if label != label.upper():
                return False, "FAT32 labels should be uppercase"
        elif filesystem in [FilesystemType.EXT4, FilesystemType.EXT3, FilesystemType.EXT2]:
            if len(label) > 16:
                return False, "EXT labels must be 16 characters or less"
        
        # Check for invalid characters
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            if char in label:
                return False, f"Label contains invalid character: '{char}'"
        
        return True, None


class FilesystemValidator:
    """Validator for filesystem operations and compatibility."""
    
    # Filesystem support matrix: {filesystem: {os_type: (read, write, format)}}
    FILESYSTEM_SUPPORT = {
        FilesystemType.NTFS: {
            OSType.WINDOWS: (True, True, True),
            OSType.LINUX: (True, True, True),  # With ntfs-3g
        },
        FilesystemType.EXFAT: {
            OSType.WINDOWS: (True, True, True),
            OSType.LINUX: (True, True, True),
        },
        FilesystemType.FAT32: {
            OSType.WINDOWS: (True, True, True),
            OSType.LINUX: (True, True, True),
        },
        FilesystemType.EXT4: {
            OSType.WINDOWS: (True, False, False),  # Read-only on Windows
            OSType.LINUX: (True, True, True),
        },
        FilesystemType.EXT3: {
            OSType.WINDOWS: (True, False, False),
            OSType.LINUX: (True, True, True),
        },
        FilesystemType.XFS: {
            OSType.WINDOWS: (False, False, False),
            OSType.LINUX: (True, True, True),
        },
        FilesystemType.BTRFS: {
            OSType.WINDOWS: (False, False, False),
            OSType.LINUX: (True, True, True),
        },
    }
    
    @staticmethod
    def get_filesystem_from_string(fs_str: str) -> FilesystemType:
        """Convert string to FilesystemType enum."""
        fs_str = fs_str.lower().strip()
        
        for fs_type in FilesystemType:
            if fs_type.value == fs_str:
                return fs_type
        
        return FilesystemType.UNKNOWN
    
    @staticmethod
    def can_format_filesystem(filesystem: FilesystemType, os_type: Optional[OSType] = None) -> bool:
        """
        Check if filesystem can be formatted on current OS.
        
        Args:
            filesystem: Filesystem type
            os_type: OS type (uses current if None)
            
        Returns:
            True if formatting is supported
        """
        if os_type is None:
            os_type = get_os_type()
        
        support = FilesystemValidator.FILESYSTEM_SUPPORT.get(filesystem, {}).get(os_type)
        if support is None:
            return False
        
        return support[2]  # format capability
    
    @staticmethod
    def get_supported_filesystems(os_type: Optional[OSType] = None) -> List[FilesystemType]:
        """
        Get list of filesystems that can be formatted on current OS.
        
        Args:
            os_type: OS type (uses current if None)
            
        Returns:
            List of supported filesystem types
        """
        if os_type is None:
            os_type = get_os_type()
        
        supported = []
        for fs_type, support_matrix in FilesystemValidator.FILESYSTEM_SUPPORT.items():
            if os_type in support_matrix and support_matrix[os_type][2]:
                supported.append(fs_type)
        
        return supported
    
    @staticmethod
    def validate_filesystem_for_size(filesystem: FilesystemType, size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate filesystem is appropriate for partition size.
        
        Args:
            filesystem: Filesystem type
            size: Partition size in bytes
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        # FAT32 has a 4GB file size limit
        if filesystem == FilesystemType.FAT32:
            if size > 2 * (1024 ** 4):  # 2TB
                return False, "FAT32 partitions should not exceed 2TB"
        
        # Minimum sizes
        min_sizes = {
            FilesystemType.NTFS: 16 * (1024 ** 2),  # 16MB
            FilesystemType.EXT4: 16 * (1024 ** 2),  # 16MB
            FilesystemType.XFS: 300 * (1024 ** 2),  # 300MB
            FilesystemType.BTRFS: 256 * (1024 ** 2),  # 256MB
        }
        
        min_size = min_sizes.get(filesystem)
        if min_size and size < min_size:
            return False, f"{filesystem.value.upper()} requires at least {PartitionValidator.format_size(min_size)}"
        
        return True, None


if __name__ == "__main__":
    # Test validators
    print("=== Disk Validator Tests ===")
    
    test_disks = [
        "/dev/sda",
        "/dev/nvme0n1",
        r"\\.\PhysicalDrive0",
        "/invalid/disk",
    ]
    
    for disk in test_disks:
        valid = DiskValidator.is_valid_disk_id(disk)
        system = DiskValidator.is_system_disk(disk)
        print(f"{disk}: valid={valid}, system={system}")
    
    print("\n=== Partition Validator Tests ===")
    
    test_sizes = ["10GB", "500M", "1.5TB", "invalid"]
    for size_str in test_sizes:
        size_bytes = PartitionValidator.parse_size(size_str)
        if size_bytes:
            formatted = PartitionValidator.format_size(size_bytes)
            print(f"{size_str} -> {size_bytes} bytes ({formatted})")
        else:
            print(f"{size_str} -> Invalid")
    
    print("\n=== Filesystem Validator Tests ===")
    
    os_type = get_os_type()
    print(f"Current OS: {os_type.value}")
    print(f"Supported filesystems: {[fs.value for fs in FilesystemValidator.get_supported_filesystems()]}")
