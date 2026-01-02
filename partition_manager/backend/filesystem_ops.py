"""
Filesystem-specific operations module.

Handles filesystem creation, resizing, and repair operations
with support for NTFS, EXT4, XFS, BTRFS, FAT32, and exFAT.
"""

import subprocess
import sys
import shutil
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from enum import Enum

from ..utils.platform_check import get_os_type, OSType, is_admin
from ..utils.logger import get_logger
from ..utils.validators import FilesystemType, PartitionValidator

logger = get_logger(__name__)

# Windows-specific flag to prevent console window popup
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0


class FilesystemCapability(Enum):
    """Filesystem operation capabilities."""
    CREATE = "create"
    RESIZE = "resize"
    SHRINK = "shrink"
    GROW = "grow"
    REPAIR = "repair"
    LABEL = "label"


class FilesystemOperations:
    """
    Cross-platform filesystem operations.
    
    Provides methods to create, resize, and repair filesystems.
    """
    
    # Filesystem tools mapping
    TOOLS = {
        FilesystemType.NTFS: {
            OSType.WINDOWS: {
                'format': 'format',
                'resize': None,  # Windows has no built-in NTFS resize
                'repair': 'chkdsk',
            },
            OSType.LINUX: {
                'format': 'mkfs.ntfs',
                'resize': 'ntfsresize',
                'repair': 'ntfsfix',
            }
        },
        FilesystemType.EXT4: {
            OSType.LINUX: {
                'format': 'mkfs.ext4',
                'resize': 'resize2fs',
                'repair': 'e2fsck',
            }
        },
        FilesystemType.EXT3: {
            OSType.LINUX: {
                'format': 'mkfs.ext3',
                'resize': 'resize2fs',
                'repair': 'e2fsck',
            }
        },
        FilesystemType.XFS: {
            OSType.LINUX: {
                'format': 'mkfs.xfs',
                'resize': 'xfs_growfs',  # XFS can only grow
                'repair': 'xfs_repair',
            }
        },
        FilesystemType.BTRFS: {
            OSType.LINUX: {
                'format': 'mkfs.btrfs',
                'resize': 'btrfs',  # Special: btrfs filesystem resize
                'repair': 'btrfs',
            }
        },
        FilesystemType.FAT32: {
            OSType.WINDOWS: {
                'format': 'format',
            },
            OSType.LINUX: {
                'format': 'mkfs.vfat',
                'repair': 'fsck.vfat',
            }
        },
        FilesystemType.EXFAT: {
            OSType.WINDOWS: {
                'format': 'format',
            },
            OSType.LINUX: {
                'format': 'mkfs.exfat',
                'repair': 'fsck.exfat',
            }
        },
    }
    
    def __init__(self):
        """Initialize filesystem operations."""
        self.os_type = get_os_type()
        logger.debug(f"Initialized FilesystemOperations for {self.os_type.value}")
    
    def check_tool_availability(self, filesystem: FilesystemType, operation: str) -> bool:
        """
        Check if required tool is available for operation.
        
        Args:
            filesystem: Filesystem type
            operation: Operation name (format, resize, repair)
            
        Returns:
            True if tool is available
        """
        tools = self.TOOLS.get(filesystem, {}).get(self.os_type, {})
        tool = tools.get(operation)
        
        if not tool:
            return False
        
        return shutil.which(tool) is not None
    
    def format_partition(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        label: Optional[str] = None,
        quick: bool = True,
        cluster_size: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Format a partition with specified filesystem.
        
        Args:
            partition_id: Partition identifier
            filesystem: Filesystem type
            label: Optional volume label
            quick: Quick format (vs full format)
            cluster_size: Optional cluster size in bytes
            
        Returns:
            Tuple of (success, error_message)
        """
        if not is_admin():
            return False, "Administrator/root privileges required"
        
        logger.info(f"Formatting {partition_id} as {filesystem.value}")
        
        if self.os_type == OSType.WINDOWS:
            return self._format_windows(partition_id, filesystem, label, quick, cluster_size)
        elif self.os_type == OSType.LINUX:
            return self._format_linux(partition_id, filesystem, label)
        
        return False, f"Unsupported OS: {self.os_type}"
    
    def _format_windows(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        label: Optional[str],
        quick: bool,
        cluster_size: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Format partition on Windows."""
        try:
            # Windows format command
            # Example: format D: /FS:NTFS /Q /V:MyLabel
            
            cmd = ['format', partition_id]
            
            # Filesystem type
            fs_map = {
                FilesystemType.NTFS: 'NTFS',
                FilesystemType.FAT32: 'FAT32',
                FilesystemType.EXFAT: 'EXFAT',
            }
            
            fs_name = fs_map.get(filesystem)
            if not fs_name:
                return False, f"Filesystem {filesystem.value} not supported on Windows"
            
            cmd.extend(['/FS:' + fs_name])
            
            # Quick format
            if quick:
                cmd.append('/Q')
            
            # Label
            if label:
                cmd.extend(['/V:' + label])
            
            # Cluster size
            if cluster_size:
                cmd.extend(['/A:' + str(cluster_size)])
            
            # Auto-confirm
            cmd.append('/Y')
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully formatted {partition_id}")
                return True, None
            else:
                error = result.stderr or result.stdout
                logger.error(f"Format failed: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Format operation timed out"
        except Exception as e:
            logger.error(f"Error formatting partition: {e}")
            return False, str(e)
    
    def _format_linux(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        label: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Format partition on Linux."""
        try:
            # Get format tool
            tools = self.TOOLS.get(filesystem, {}).get(OSType.LINUX, {})
            tool = tools.get('format')
            
            if not tool:
                return False, f"No format tool for {filesystem.value} on Linux"
            
            # Check if tool exists
            if not shutil.which(tool):
                return False, f"Tool '{tool}' not found. Please install it."
            
            # Build command based on filesystem
            if filesystem == FilesystemType.NTFS:
                cmd = ['mkfs.ntfs', '-f', partition_id]  # -f = fast format
                if label:
                    cmd.extend(['-L', label])
                    
            elif filesystem in [FilesystemType.EXT4, FilesystemType.EXT3, FilesystemType.EXT2]:
                cmd = [f'mkfs.{filesystem.value}', partition_id]
                if label:
                    cmd.extend(['-L', label])
                    
            elif filesystem == FilesystemType.XFS:
                cmd = ['mkfs.xfs', '-f', partition_id]  # -f = force
                if label:
                    cmd.extend(['-L', label])
                    
            elif filesystem == FilesystemType.BTRFS:
                cmd = ['mkfs.btrfs', '-f', partition_id]
                if label:
                    cmd.extend(['-L', label])
                    
            elif filesystem == FilesystemType.FAT32:
                cmd = ['mkfs.vfat', '-F', '32', partition_id]
                if label:
                    cmd.extend(['-n', label])
                    
            elif filesystem == FilesystemType.EXFAT:
                cmd = ['mkfs.exfat', partition_id]
                if label:
                    cmd.extend(['-n', label])
            else:
                return False, f"Unsupported filesystem: {filesystem.value}"
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully formatted {partition_id}")
                return True, None
            else:
                error = result.stderr or result.stdout
                logger.error(f"Format failed: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Format operation timed out"
        except Exception as e:
            logger.error(f"Error formatting partition: {e}")
            return False, str(e)
    
    def resize_filesystem(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        new_size: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Resize filesystem.
        
        Args:
            partition_id: Partition identifier
            filesystem: Filesystem type
            new_size: New size in bytes
            
        Returns:
            Tuple of (success, error_message)
        """
        if not is_admin():
            return False, "Administrator/root privileges required"
        
        logger.info(f"Resizing {partition_id} ({filesystem.value}) to {PartitionValidator.format_size(new_size)}")
        
        if self.os_type == OSType.LINUX:
            return self._resize_linux(partition_id, filesystem, new_size)
        elif self.os_type == OSType.WINDOWS:
            # Windows doesn't have built-in filesystem resize tools
            return False, "Filesystem resize not supported on Windows (use diskpart for partition resize)"
        
        return False, f"Unsupported OS: {self.os_type}"
    
    def _resize_linux(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        new_size: int
    ) -> Tuple[bool, Optional[str]]:
        """Resize filesystem on Linux."""
        try:
            if filesystem == FilesystemType.NTFS:
                # ntfsresize
                if not shutil.which('ntfsresize'):
                    return False, "ntfsresize not found. Install ntfs-3g package."
                
                # Convert size to MB
                size_mb = new_size // (1024 * 1024)
                
                cmd = ['ntfsresize', '-s', f'{size_mb}M', partition_id]
                
            elif filesystem in [FilesystemType.EXT4, FilesystemType.EXT3, FilesystemType.EXT2]:
                # resize2fs
                if not shutil.which('resize2fs'):
                    return False, "resize2fs not found. Install e2fsprogs package."
                
                # resize2fs can work with mounted fs, but safer unmounted
                # Size in K
                size_k = new_size // 1024
                
                cmd = ['resize2fs', partition_id, f'{size_k}K']
                
            elif filesystem == FilesystemType.XFS:
                # XFS can only grow, not shrink
                # Must be mounted
                return False, "XFS resize requires mount point and can only grow. Use 'xfs_growfs /mount/point'"
                
            elif filesystem == FilesystemType.BTRFS:
                # BTRFS resize requires mount point
                return False, "BTRFS resize requires mount point. Use 'btrfs filesystem resize'"
                
            else:
                return False, f"Resize not supported for {filesystem.value}"
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # Resize can take longer
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully resized {partition_id}")
                return True, None
            else:
                error = result.stderr or result.stdout
                logger.error(f"Resize failed: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Resize operation timed out"
        except Exception as e:
            logger.error(f"Error resizing filesystem: {e}")
            return False, str(e)
    
    def repair_filesystem(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        auto_fix: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Repair/check filesystem.
        
        Args:
            partition_id: Partition identifier
            filesystem: Filesystem type
            auto_fix: Automatically fix errors
            
        Returns:
            Tuple of (success, error_message)
        """
        if not is_admin():
            return False, "Administrator/root privileges required"
        
        logger.info(f"Checking/repairing {partition_id} ({filesystem.value})")
        
        if self.os_type == OSType.WINDOWS:
            return self._repair_windows(partition_id, auto_fix)
        elif self.os_type == OSType.LINUX:
            return self._repair_linux(partition_id, filesystem, auto_fix)
        
        return False, f"Unsupported OS: {self.os_type}"
    
    def _repair_windows(
        self,
        partition_id: str,
        auto_fix: bool
    ) -> Tuple[bool, Optional[str]]:
        """Repair filesystem on Windows using chkdsk."""
        try:
            cmd = ['chkdsk', partition_id]
            
            if auto_fix:
                cmd.append('/F')  # Fix errors
                cmd.append('/R')  # Locate bad sectors and recover readable information
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes
                creationflags=CREATE_NO_WINDOW
            )
            
            # chkdsk returns different codes
            # 0 = no errors, 2 = disk cleanup performed, 3 = errors but not fixed
            if result.returncode in [0, 2]:
                logger.info(f"Filesystem check completed on {partition_id}")
                return True, None
            else:
                error = result.stderr or result.stdout
                logger.warning(f"Filesystem check found issues: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Filesystem check timed out"
        except Exception as e:
            logger.error(f"Error checking filesystem: {e}")
            return False, str(e)
    
    def _repair_linux(
        self,
        partition_id: str,
        filesystem: FilesystemType,
        auto_fix: bool
    ) -> Tuple[bool, Optional[str]]:
        """Repair filesystem on Linux."""
        try:
            tools = self.TOOLS.get(filesystem, {}).get(OSType.LINUX, {})
            tool = tools.get('repair')
            
            if not tool:
                return False, f"No repair tool for {filesystem.value}"
            
            if not shutil.which(tool):
                return False, f"Tool '{tool}' not found"
            
            # Build command based on filesystem
            if filesystem in [FilesystemType.EXT4, FilesystemType.EXT3, FilesystemType.EXT2]:
                cmd = ['e2fsck']
                if auto_fix:
                    cmd.append('-y')  # Auto yes to prompts
                else:
                    cmd.append('-n')  # No changes, just check
                cmd.append(partition_id)
                
            elif filesystem == FilesystemType.NTFS:
                cmd = ['ntfsfix', partition_id]
                
            elif filesystem == FilesystemType.XFS:
                cmd = ['xfs_repair']
                if not auto_fix:
                    cmd.append('-n')  # No-modify mode
                cmd.append(partition_id)
                
            elif filesystem == FilesystemType.FAT32:
                cmd = ['fsck.vfat']
                if auto_fix:
                    cmd.append('-a')  # Auto repair
                cmd.append(partition_id)
                
            else:
                return False, f"Repair not supported for {filesystem.value}"
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            # Most fsck tools return 0 for no errors, 1 for errors corrected
            if result.returncode in [0, 1]:
                logger.info(f"Filesystem check completed on {partition_id}")
                return True, None
            else:
                error = result.stderr or result.stdout
                logger.warning(f"Filesystem check found issues: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Filesystem check timed out"
        except Exception as e:
            logger.error(f"Error checking filesystem: {e}")
            return False, str(e)


if __name__ == "__main__":
    # Test filesystem operations
    from ..utils.logger import setup_logger, LogLevel
    
    setup_logger(level=LogLevel.DEBUG)
    
    fs_ops = FilesystemOperations()
    
    print("=== Filesystem Operations Tools ===\n")
    
    for fs_type in [FilesystemType.NTFS, FilesystemType.EXT4, FilesystemType.XFS]:
        print(f"{fs_type.value.upper()}:")
        for op in ['format', 'resize', 'repair']:
            available = fs_ops.check_tool_availability(fs_type, op)
            print(f"  {op}: {'✓' if available else '✗'}")
        print()
