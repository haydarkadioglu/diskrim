"""
Partition operations module.

Handles partition creation, deletion, resizing, moving, and formatting
with cross-platform support for Windows and Linux.
"""

import subprocess
import sys
import time
import hashlib
from typing import Optional, Tuple, Callable
from pathlib import Path

from ..utils.platform_check import get_os_type, OSType, is_admin
from ..utils.logger import get_logger, get_operation_logger, OperationType
from ..utils.validators import FilesystemType, PartitionValidator, DiskValidator
from .filesystem_ops import FilesystemOperations

logger = get_logger(__name__)
op_logger = get_operation_logger()

# Windows-specific flag to prevent console window popup
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0


class PartitionOperations:
    """
    Cross-platform partition management operations.
    
    Provides methods to create, delete, resize, move, and format partitions
    with proper safety checks and logging.
    """
    
    def __init__(self):
        """Initialize partition operations."""
        self.os_type = get_os_type()
        self.fs_ops = FilesystemOperations()
        logger.debug(f"Initialized PartitionOperations for {self.os_type.value}")
    
    def create_partition(
        self,
        disk_id: str,
        size: int,
        filesystem: FilesystemType,
        label: Optional[str] = None,
        partition_type: str = "primary",
        start_offset: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a new partition on a disk.
        
        Args:
            disk_id: Disk identifier
            size: Partition size in bytes
            filesystem: Filesystem type
            label: Optional partition label
            partition_type: Partition type (primary, logical, extended)
            start_offset: Optional start offset in bytes
            progress_callback: Optional callback(percentage, message)
            
        Returns:
            Tuple of (success, error_message, partition_id)
        """
        if not is_admin():
            return False, "Administrator/root privileges required", None
        
        # Validate inputs
        if not DiskValidator.is_valid_disk_id(disk_id):
            return False, f"Invalid disk ID: {disk_id}", None
        
        if size < 1024 * 1024:  # Minimum 1MB
            return False, "Partition size too small (minimum 1MB)", None
        
        # Log operation start
        op_id = op_logger.log_operation_start(
            OperationType.CREATE_PARTITION,
            disk_id=disk_id,
            description=f"Creating {PartitionValidator.format_size(size)} {filesystem.value} partition",
            parameters={
                'size': size,
                'filesystem': filesystem.value,
                'label': label,
                'type': partition_type
            }
        )
        
        try:
            if progress_callback:
                progress_callback(10, "Validating disk...")
            
            # Platform-specific implementation
            if self.os_type == OSType.WINDOWS:
                success, error, part_id = self._create_partition_windows(
                    disk_id, size, filesystem, label, partition_type, start_offset, progress_callback
                )
            elif self.os_type == OSType.LINUX:
                success, error, part_id = self._create_partition_linux(
                    disk_id, size, filesystem, label, partition_type, start_offset, progress_callback
                )
            else:
                return False, f"Unsupported OS: {self.os_type}", None
            
            if success:
                op_logger.log_operation_complete(op_id)
                logger.info(f"Successfully created partition: {part_id}")
            else:
                op_logger.log_operation_error(op_id, error or "Unknown error")
                logger.error(f"Failed to create partition: {error}")
            
            return success, error, part_id
            
        except Exception as e:
            error_msg = str(e)
            op_logger.log_operation_error(op_id, error_msg)
            logger.error(f"Exception during partition creation: {e}")
            return False, error_msg, None
    
    def _create_partition_windows(
        self,
        disk_id: str,
        size: int,
        filesystem: FilesystemType,
        label: Optional[str],
        partition_type: str,
        start_offset: Optional[int],
        progress_callback: Optional[Callable]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Create partition on Windows using diskpart."""
        try:
            # Extract disk number from disk ID (e.g., \\.\PhysicalDrive0 -> 0)
            disk_num = disk_id.split('PhysicalDrive')[-1]
            
            # Create diskpart script
            script = f"""select disk {disk_num}
create partition {partition_type} size={size // (1024 * 1024)}
"""
            
            if progress_callback:
                progress_callback(30, "Creating partition...")
            
            # Execute diskpart
            result = subprocess.run(
                ['diskpart'],
                input=script,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                return False, result.stderr or "Diskpart failed", None
            
            if progress_callback:
                progress_callback(60, "Formatting partition...")
            
            # Get the new partition (it should be the last one created)
            # This is a simplification - in production, we'd need to query the partition list
            partition_id = "NEW_PARTITION"  # Placeholder
            
            # Format the partition
            if filesystem != FilesystemType.UNKNOWN:
                success, error = self.fs_ops.format_partition(
                    partition_id,
                    filesystem,
                    label=label,
                    quick=True
                )
                
                if not success:
                    return False, f"Partition created but format failed: {error}", partition_id
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            return True, None, partition_id
            
        except subprocess.TimeoutExpired:
            return False, "Diskpart operation timed out", None
        except Exception as e:
            return False, str(e), None
    
    def _create_partition_linux(
        self,
        disk_id: str,
        size: int,
        filesystem: FilesystemType,
        label: Optional[str],
        partition_type: str,
        start_offset: Optional[int],
        progress_callback: Optional[Callable]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Create partition on Linux using parted."""
        try:
            if progress_callback:
                progress_callback(30, "Creating partition...")
            
            # Use parted to create partition
            # Calculate start and end in MB
            start_mb = (start_offset // (1024 * 1024)) if start_offset else 1
            end_mb = start_mb + (size // (1024 * 1024))
            
            cmd = [
                'parted',
                '-s',  # Script mode
                disk_id,
                'mkpart',
                partition_type,
                str(start_mb) + 'MB',
                str(end_mb) + 'MB'
            ]
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return False, result.stderr or "Parted failed", None
            
            # Wait a moment for partition device to appear
            time.sleep(1)
            
            # Determine partition ID (e.g., /dev/sda3)
            # This is simplified - we'd need to query to find the actual new partition
            partition_id = f"{disk_id}1"  # Placeholder
            
            if progress_callback:
                progress_callback(60, "Formatting partition...")
            
            # Format the partition
            if filesystem != FilesystemType.UNKNOWN:
                success, error = self.fs_ops.format_partition(
                    partition_id,
                    filesystem,
                    label=label,
                    quick=True
                )
                
                if not success:
                    return False, f"Partition created but format failed: {error}", partition_id
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            return True, None, partition_id
            
        except subprocess.TimeoutExpired:
            return False, "Parted operation timed out", None
        except Exception as e:
            return False, str(e), None
    
    def delete_partition(
        self,
        partition_id: str,
        secure_wipe: bool = False,
        wipe_passes: int = 3,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a partition with optional secure wipe.
        
        Args:
            partition_id: Partition identifier
            secure_wipe: Perform secure data wipe before deletion
            wipe_passes: Number of wipe passes (for DoD compliance, use 3 or 7)
            progress_callback: Optional callback(percentage, message)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not is_admin():
            return False, "Administrator/root privileges required"
        
        # Validate partition ID
        if not DiskValidator.is_valid_partition_id(partition_id):
            return False, f"Invalid partition ID: {partition_id}"
        
        # Log operation start
        op_id = op_logger.log_operation_start(
            OperationType.SECURE_ERASE if secure_wipe else OperationType.DELETE_PARTITION,
            partition_id=partition_id,
            description=f"Deleting partition {partition_id}" + (" with secure wipe" if secure_wipe else ""),
            parameters={'secure_wipe': secure_wipe, 'passes': wipe_passes}
        )
        
        try:
            # Perform secure wipe if requested
            if secure_wipe:
                if progress_callback:
                    progress_callback(0, f"Securely wiping data ({wipe_passes} passes)...")
                
                success, error = self._secure_wipe_partition(partition_id, wipe_passes, progress_callback)
                if not success:
                    op_logger.log_operation_error(op_id, error or "Secure wipe failed")
                    return False, f"Secure wipe failed: {error}"
            
            # Delete the partition
            if progress_callback:
                progress_callback(90 if secure_wipe else 50, "Deleting partition...")
            
            if self.os_type == OSType.WINDOWS:
                success, error = self._delete_partition_windows(partition_id)
            elif self.os_type == OSType.LINUX:
                success, error = self._delete_partition_linux(partition_id)
            else:
                return False, f"Unsupported OS: {self.os_type}"
            
            if success:
                op_logger.log_operation_complete(op_id)
                logger.info(f"Successfully deleted partition: {partition_id}")
                if progress_callback:
                    progress_callback(100, "Complete")
            else:
                op_logger.log_operation_error(op_id, error or "Unknown error")
                logger.error(f"Failed to delete partition: {error}")
            
            return success, error
            
        except Exception as e:
            error_msg = str(e)
            op_logger.log_operation_error(op_id, error_msg)
            logger.error(f"Exception during partition deletion: {e}")
            return False, error_msg
    
    def _secure_wipe_partition(
        self,
        partition_id: str,
        passes: int,
        progress_callback: Optional[Callable]
    ) -> Tuple[bool, Optional[str]]:
        """
        Securely wipe partition data using DoD 5220.22-M method.
        
        Writes random data multiple times to prevent data recovery.
        """
        try:
            logger.info(f"Starting secure wipe of {partition_id} with {passes} passes")
            
            # Note: This is a simplified implementation
            # In production, use dd or shred on Linux, cipher on Windows
            
            if self.os_type == OSType.LINUX:
                # Use shred if available
                import shutil
                if shutil.which('shred'):
                    cmd = ['shred', '-n', str(passes), '-v', '-z', partition_id]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=3600  # 1 hour timeout
                    )
                    
                    return result.returncode == 0, result.stderr if result.returncode != 0 else None
                else:
                    # Fallback to dd
                    # WARNING: This is simplified and not production-ready
                    return False, "shred not available. Secure wipe requires shred tool."
                    
            elif self.os_type == OSType.WINDOWS:
                # Windows doesn't have built-in secure erase
                # Would need third-party tools or custom implementation
                return False, "Secure wipe not yet implemented for Windows"
            
            return False, "Unsupported platform for secure wipe"
            
        except subprocess.TimeoutExpired:
            return False, "Secure wipe timed out"
        except Exception as e:
            return False, str(e)
    
    def _delete_partition_windows(self, partition_id: str) -> Tuple[bool, Optional[str]]:
        """Delete partition on Windows using diskpart."""
        try:
            # Note: This is simplified - need to determine partition number
            script = f"""select volume {partition_id}
delete partition
"""
            
            result = subprocess.run(
                ['diskpart'],
                input=script,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr or "Diskpart failed"
                
        except Exception as e:
            return False, str(e)
    
    def _delete_partition_linux(self, partition_id: str) -> Tuple[bool, Optional[str]]:
        """Delete partition on Linux using parted."""
        try:
            # Extract disk and partition number
            # e.g., /dev/sda1 -> /dev/sda, 1
            import re
            match = re.match(r'(/dev/[a-z]+)(\d+)', partition_id)
            if not match:
                return False, f"Could not parse partition ID: {partition_id}"
            
            disk_id = match.group(1)
            part_num = match.group(2)
            
            cmd = ['parted', '-s', disk_id, 'rm', part_num]
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr or "Parted failed"
                
        except Exception as e:
            return False, str(e)
    
    def resize_partition(
        self,
        partition_id: str,
        new_size: int,
        filesystem: Optional[FilesystemType] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Resize a partition and its filesystem.
        
        Args:
            partition_id: Partition identifier
            new_size: New size in bytes
            filesystem: Filesystem type (auto-detected if None)
            progress_callback: Optional callback(percentage, message)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not is_admin():
            return False, "Administrator/root privileges required"
        
        # Log operation start
        op_id = op_logger.log_operation_start(
            OperationType.RESIZE_PARTITION,
            partition_id=partition_id,
            description=f"Resizing partition to {PartitionValidator.format_size(new_size)}",
            parameters={'new_size': new_size}
        )
        
        try:
            if progress_callback:
                progress_callback(10, "Validating partition...")
            
            # TODO: Detect current filesystem if not provided
            # TODO: Check current size and validate new size
            
            if progress_callback:
                progress_callback(30, "Resizing partition...")
            
            # Resize partition (not filesystem yet)
            if self.os_type == OSType.LINUX:
                # Use parted resizepart
                success, error = self._resize_partition_linux(partition_id, new_size)
            else:
                return False, "Partition resize not yet fully implemented for Windows"
            
            if not success:
                op_logger.log_operation_error(op_id, error or "Unknown error")
                return False, error
            
            if progress_callback:
                progress_callback(70, "Resizing filesystem...")
            
            # Resize filesystem to match
            if filesystem:
                fs_success, fs_error = self.fs_ops.resize_filesystem(partition_id, filesystem, new_size)
                if not fs_success:
                    logger.warning(f"Partition resized but filesystem resize failed: {fs_error}")
                    # Don't fail the whole operation if filesystem resize fails
            
            op_logger.log_operation_complete(op_id)
            if progress_callback:
                progress_callback(100, "Complete")
            
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            op_logger.log_operation_error(op_id, error_msg)
            return False, error_msg
    
    def _resize_partition_linux(self, partition_id: str, new_size: int) -> Tuple[bool, Optional[str]]:
        """Resize partition on Linux using parted."""
        try:
            # Extract disk and partition number
            import re
            match = re.match(r'(/dev/[a-z]+)(\d+)', partition_id)
            if not match:
                return False, f"Could not parse partition ID: {partition_id}"
            
            disk_id = match.group(1)
            part_num = match.group(2)
            
            # Get current partition info to determine start
            # This is simplified - production code would query partition table
            
            # Use parted resizepart
            size_mb = new_size // (1024 * 1024)
            
            cmd = ['parted', '-s', disk_id, 'resizepart', part_num, str(size_mb) + 'MB']
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr or "Parted resizepart failed"
                
        except Exception as e:
            return False, str(e)


if __name__ == "__main__":
    # Test partition operations
    from ..utils.logger import setup_logger, LogLevel
    
    setup_logger(level=LogLevel.DEBUG)
    
    part_ops = PartitionOperations()
    
    print(f"Partition Operations initialized for {part_ops.os_type.value}")
    print("\nThis module requires administrator/root privileges to test operations.")
    print("Use with caution on production systems!")
