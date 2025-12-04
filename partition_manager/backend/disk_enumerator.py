"""
Cross-platform disk enumeration module.

Discovers physical disks and partitions on Windows and Linux,
providing unified disk information API.
"""

import subprocess
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..utils.platform_check import get_os_type, OSType, is_admin
from ..utils.logger import get_logger
from ..utils.validators import FilesystemType

logger = get_logger(__name__)


class DiskType(Enum):
    """Physical disk type."""
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    USB = "usb"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """Disk connection interface."""
    SATA = "sata"
    NVME = "nvme"
    USB = "usb"
    SCSI = "scsi"
    IDE = "ide"
    UNKNOWN = "unknown"


class PartitionTableType(Enum):
    """Partition table format."""
    MBR = "mbr"
    GPT = "gpt"
    UNKNOWN = "unknown"


@dataclass
class PartitionInfo:
    """Partition information."""
    id: str  # Device path or drive letter
    number: int
    start: int  # Start sector
    end: int  # End sector
    size: int  # Size in bytes
    filesystem: FilesystemType
    label: str
    mount_point: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    uuid: Optional[str] = None


@dataclass
class DiskInfo:
    """Physical disk information."""
    id: str  # Device path
    model: str
    serial: Optional[str]
    size: int  # Size in bytes
    disk_type: DiskType
    connection_type: ConnectionType
    partition_table: PartitionTableType
    partitions: List[PartitionInfo] = field(default_factory=list)
    is_removable: bool = False
    is_system_disk: bool = False
    
    def __str__(self) -> str:
        """String representation."""
        from ..utils.validators import PartitionValidator
        
        return (
            f"Disk: {self.id}\n"
            f"  Model: {self.model}\n"
            f"  Size: {PartitionValidator.format_size(self.size)}\n"
            f"  Type: {self.disk_type.value.upper()}\n"
            f"  Connection: {self.connection_type.value.upper()}\n"
            f"  Partition Table: {self.partition_table.value.upper()}\n"
            f"  Partitions: {len(self.partitions)}\n"
            f"  Removable: {self.is_removable}\n"
            f"  System: {self.is_system_disk}"
        )


class DiskEnumerator:
    """Cross-platform disk enumeration."""
    
    def __init__(self):
        """Initialize disk enumerator."""
        self.os_type = get_os_type()
        logger.debug(f"Initialized DiskEnumerator for {self.os_type.value}")
    
    def list_disks(self) -> List[DiskInfo]:
        """
        List all physical disks.
        
        Returns:
            List of DiskInfo objects
        """
        if not is_admin():
            logger.warning("Not running with administrator/root privileges - disk enumeration may be incomplete")
        
        if self.os_type == OSType.WINDOWS:
            return self._list_disks_windows()
        elif self.os_type == OSType.LINUX:
            return self._list_disks_linux()
        else:
            logger.error(f"Unsupported OS: {self.os_type}")
            return []
    
    def get_disk_info(self, disk_id: str) -> Optional[DiskInfo]:
        """
        Get information for a specific disk.
        
        Args:
            disk_id: Disk identifier
            
        Returns:
            DiskInfo or None if not found
        """
        disks = self.list_disks()
        for disk in disks:
            if disk.id == disk_id:
                return disk
        return None
    
    def _list_disks_linux(self) -> List[DiskInfo]:
        """List disks on Linux using lsblk."""
        try:
            # Use lsblk with JSON output
            result = subprocess.run(
                ["lsblk", "-b", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL,UUID,PTTYPE,MODEL,SERIAL,ROTA,TRAN"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"lsblk failed: {result.stderr}")
                return []
            
            data = json.loads(result.stdout)
            disks = []
            
            for device in data.get("blockdevices", []):
                # Only process physical disks
                if device.get("type") != "disk":
                    continue
                
                disk_info = self._parse_linux_disk(device)
                if disk_info:
                    disks.append(disk_info)
            
            return disks
            
        except FileNotFoundError:
            logger.error("lsblk not found - please install util-linux")
            return []
        except subprocess.TimeoutExpired:
            logger.error("lsblk command timed out")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse lsblk JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing disks: {e}")
            return []
    
    def _parse_linux_disk(self, device: Dict) -> Optional[DiskInfo]:
        """Parse Linux disk information from lsblk output."""
        try:
            disk_id = f"/dev/{device['name']}"
            size = int(device.get("size", 0))
            model = device.get("model", "Unknown").strip()
            serial = device.get("serial")
            pttype = device.get("pttype", "").lower()
            
            # Determine partition table type
            if pttype == "gpt":
                partition_table = PartitionTableType.GPT
            elif pttype in ["dos", "msdos"]:
                partition_table = PartitionTableType.MBR
            else:
                partition_table = PartitionTableType.UNKNOWN
            
            # Determine disk type
            rota = device.get("rota")
            tran = device.get("tran", "").lower()
            
            if "nvme" in disk_id:
                disk_type = DiskType.NVME
                connection_type = ConnectionType.NVME
            elif tran == "usb":
                disk_type = DiskType.USB
                connection_type = ConnectionType.USB
            elif rota == "1":
                disk_type = DiskType.HDD
                connection_type = ConnectionType.SATA if tran == "sata" else ConnectionType.UNKNOWN
            elif rota == "0":
                disk_type = DiskType.SSD
                connection_type = ConnectionType.SATA if tran == "sata" else ConnectionType.UNKNOWN
            else:
                disk_type = DiskType.UNKNOWN
                connection_type = ConnectionType.UNKNOWN
            
            # Check if removable
            is_removable = connection_type == ConnectionType.USB
            
            # Check if system disk (heuristic: has root partition)
            is_system_disk = False
            
            # Parse partitions
            partitions = []
            for idx, child in enumerate(device.get("children", []), 1):
                if child.get("type") == "part":
                    partition = self._parse_linux_partition(child, idx)
                    if partition:
                        partitions.append(partition)
                        if partition.mount_point == "/":
                            is_system_disk = True
            
            return DiskInfo(
                id=disk_id,
                model=model,
                serial=serial,
                size=size,
                disk_type=disk_type,
                connection_type=connection_type,
                partition_table=partition_table,
                partitions=partitions,
                is_removable=is_removable,
                is_system_disk=is_system_disk
            )
            
        except Exception as e:
            logger.error(f"Error parsing disk {device.get('name')}: {e}")
            return None
    
    def _parse_linux_partition(self, partition: Dict, number: int) -> Optional[PartitionInfo]:
        """Parse Linux partition information."""
        try:
            partition_id = f"/dev/{partition['name']}"
            size = int(partition.get("size", 0))
            fstype = partition.get("fstype", "").lower()
            label = partition.get("label", "")
            mount_point = partition.get("mountpoint")
            uuid = partition.get("uuid")
            
            # Map filesystem type
            from ..utils.validators import FilesystemValidator
            filesystem = FilesystemValidator.get_filesystem_from_string(fstype)
            
            # Get partition boundaries (requires more detailed parsing)
            # For now, we'll use approximate values
            start = 0
            end = 0
            
            return PartitionInfo(
                id=partition_id,
                number=number,
                start=start,
                end=end,
                size=size,
                filesystem=filesystem,
                label=label,
                mount_point=mount_point,
                uuid=uuid
            )
            
        except Exception as e:
            logger.error(f"Error parsing partition {partition.get('name')}: {e}")
            return None
    
    def _list_disks_windows(self) -> List[DiskInfo]:
        """List disks on Windows using WMI."""
        try:
            import wmi
            
            c = wmi.WMI()
            disks = []
            
            # Get physical disks
            for disk in c.Win32_DiskDrive():
                disk_info = self._parse_windows_disk(disk, c)
                if disk_info:
                    disks.append(disk_info)
            
            return disks
            
        except ImportError:
            logger.error("WMI module not available - please install wmi package")
            return self._list_disks_windows_fallback()
        except Exception as e:
            logger.error(f"Error listing disks with WMI: {e}")
            return self._list_disks_windows_fallback()
    
    def _parse_windows_disk(self, disk, wmi_connection) -> Optional[DiskInfo]:
        """Parse Windows disk information from WMI."""
        try:
            # Get disk properties
            disk_id = f"\\\\.\\PhysicalDrive{disk.Index}"
            model = disk.Model.strip() if disk.Model else "Unknown"
            serial = disk.SerialNumber.strip() if disk.SerialNumber else None
            size = int(disk.Size) if disk.Size else 0
            
            # Determine disk type
            media_type = disk.MediaType.lower() if disk.MediaType else ""
            interface_type = disk.InterfaceType.lower() if disk.InterfaceType else ""
            
            if "usb" in interface_type or "usb" in media_type:
                disk_type = DiskType.USB
                connection_type = ConnectionType.USB
            elif "nvme" in model.lower() or "nvme" in interface_type:
                disk_type = DiskType.NVME
                connection_type = ConnectionType.NVME
            elif "ssd" in media_type or "solid state" in media_type:
                disk_type = DiskType.SSD
                connection_type = ConnectionType.SATA if "sata" in interface_type else ConnectionType.UNKNOWN
            else:
                disk_type = DiskType.HDD
                connection_type = ConnectionType.SATA if "sata" in interface_type else ConnectionType.SCSI
            
            # Get partition table type
            partition_table = self._detect_windows_partition_table(disk_id)
            
            # Get partitions
            partitions = self._get_windows_partitions(disk.Index, wmi_connection)
            
            # Check if system disk
            is_system_disk = (disk.Index == 0)
            
            # Check if removable
            is_removable = (connection_type == ConnectionType.USB)
            
            return DiskInfo(
                id=disk_id,
                model=model,
                serial=serial,
                size=size,
                disk_type=disk_type,
                connection_type=connection_type,
                partition_table=partition_table,
                partitions=partitions,
                is_removable=is_removable,
                is_system_disk=is_system_disk
            )
            
        except Exception as e:
            logger.error(f"Error parsing Windows disk: {e}")
            return None
    
    def _detect_windows_partition_table(self, disk_id: str) -> PartitionTableType:
        """Detect partition table type on Windows."""
        try:
            # Use diskpart to check partition style
            script = f"select disk {disk_id.split('PhysicalDrive')[1]}\ndetail disk\n"
            
            result = subprocess.run(
                ["diskpart"],
                input=script,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.lower()
            if "gpt" in output:
                return PartitionTableType.GPT
            elif "mbr" in output or "master boot record" in output:
                return PartitionTableType.MBR
                
        except Exception as e:
            logger.debug(f"Could not detect partition table type: {e}")
        
        return PartitionTableType.UNKNOWN
    
    def _get_windows_partitions(self, disk_index: int, wmi_connection) -> List[PartitionInfo]:
        """Get partitions for a Windows disk."""
        partitions = []
        
        try:
            # Get partitions associated with this disk
            for partition in wmi_connection.Win32_DiskPartition():
                if partition.DiskIndex != disk_index:
                    continue
                
                partition_info = self._parse_windows_partition(partition, wmi_connection)
                if partition_info:
                    partitions.append(partition_info)
            
        except Exception as e:
            logger.error(f"Error getting Windows partitions: {e}")
        
        return partitions
    
    def _parse_windows_partition(self, partition, wmi_connection) -> Optional[PartitionInfo]:
        """Parse Windows partition information."""
        try:
            # Get logical disk (drive letter) associated with this partition
            drive_letter = None
            label = ""
            filesystem = FilesystemType.UNKNOWN
            mount_point = None
            
            for logical_disk in wmi_connection.Win32_LogicalDisk():
                # Match partition to logical disk
                query = f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} WHERE AssocClass=Win32_LogicalDiskToPartition"
                associated = wmi_connection.query(query)
                
                for disk in associated:
                    if disk.DeviceID:
                        drive_letter = disk.DeviceID
                        mount_point = disk.DeviceID + "\\"
                        label = disk.VolumeName if disk.VolumeName else ""
                        
                        # Get filesystem
                        fs_str = disk.FileSystem.lower() if disk.FileSystem else ""
                        from ..utils.validators import FilesystemValidator
                        filesystem = FilesystemValidator.get_filesystem_from_string(fs_str)
                        break
            
            if drive_letter is None:
                drive_letter = f"Partition{partition.Index}"
            
            size = int(partition.Size) if partition.Size else 0
            start = int(partition.StartingOffset) if partition.StartingOffset else 0
            end = start + size
            
            return PartitionInfo(
                id=drive_letter,
                number=partition.Index,
                start=start,
                end=end,
                size=size,
                filesystem=filesystem,
                label=label,
                mount_point=mount_point
            )
            
        except Exception as e:
            logger.error(f"Error parsing Windows partition: {e}")
            return None
    
    def _list_disks_windows_fallback(self) -> List[DiskInfo]:
        """Fallback method for Windows using diskpart."""
        logger.warning("Using fallback diskpart method - limited information available")
        
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "index,model,size", "/format:csv"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            # Parse CSV output
            lines = result.stdout.strip().split('\n')
            disks = []
            
            for line in lines[2:]:  # Skip header rows
                if not line.strip():
                    continue
                
                parts = line.split(',')
                if len(parts) >= 4:
                    try:
                        index = int(parts[1])
                        model = parts[2].strip()
                        size = int(parts[3]) if parts[3] else 0
                        
                        disk_info = DiskInfo(
                            id=f"\\\\.\\PhysicalDrive{index}",
                            model=model,
                            serial=None,
                            size=size,
                            disk_type=DiskType.UNKNOWN,
                            connection_type=ConnectionType.UNKNOWN,
                            partition_table=PartitionTableType.UNKNOWN,
                            partitions=[],
                            is_removable=False,
                            is_system_disk=(index == 0)
                        )
                        disks.append(disk_info)
                        
                    except (ValueError, IndexError):
                        continue
            
            return disks
            
        except Exception as e:
            logger.error(f"Fallback disk enumeration failed: {e}")
            return []


if __name__ == "__main__":
    # Test disk enumeration
    from ..utils.logger import setup_logger, LogLevel
    
    setup_logger(level=LogLevel.DEBUG)
    
    enumerator = DiskEnumerator()
    disks = enumerator.list_disks()
    
    print(f"\nFound {len(disks)} disk(s):\n")
    
    for disk in disks:
        print("=" * 60)
        print(disk)
        print()
        
        if disk.partitions:
            print("  Partitions:")
            for part in disk.partitions:
                from ..utils.validators import PartitionValidator
                print(f"    {part.id}: {PartitionValidator.format_size(part.size)} "
                      f"({part.filesystem.value}) {part.label}")
        print()
