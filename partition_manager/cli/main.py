"""
DiskRim CLI - Command-line interface for partition management.

Provides disk and partition management commands through an
intuitive CLI powered by Click.
"""

import click
import sys
from typing import Optional

from ..utils.platform_check import is_admin, get_platform, check_requirements
from ..utils.logger import setup_logger, LogLevel
from ..backend.disk_enumerator import DiskEnumerator
from ..utils.validators import PartitionValidator

# Setup logger
logger = setup_logger(level=LogLevel.INFO)


def require_admin_decorator(f):
    """Decorator to require admin/root privileges."""
    def wrapper(*args, **kwargs):
        if not is_admin():
            click.secho("❌ This command requires administrator/root privileges", fg="red", bold=True)
            platform = get_platform()
            if platform.os_type.value == "windows":
                click.echo("Please run this command as Administrator")
            else:
                click.echo("Please run this command with sudo")
            sys.exit(1)
        return f(*args, **kwargs)
    return wrapper


@click.group()
@click.version_option(version="1.5.0", prog_name="DiskRim")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--debug', is_flag=True, help='Enable debug output')
def cli(verbose: bool, debug: bool):
    """
    DiskRim - Modern Partition Manager
    
    Manage disks and partitions with safety and ease.
    
    \b
    Examples:
      diskrim disk list              # List all disks
      diskrim partition list /dev/sda  # List partitions
      diskrim tools clone /dev/sda /dev/sdb  # Clone disk
    
    ⚠️  Most operations require administrator/root privileges!
    """
    # Set log level based on flags
    if debug:
        setup_logger(level=LogLevel.DEBUG)
    elif verbose:
        setup_logger(level=LogLevel.DEBUG)
    
    # Check requirements
    all_present, missing = check_requirements()
    if not all_present and (verbose or debug):
        click.secho("⚠️  Some required utilities are missing:", fg="yellow")
        for util in missing:
            click.echo(f"  - {util}")
        click.echo()


@cli.group()
def disk():
    """Disk management commands."""
    pass


@cli.group()
def partition():
    """Partition management commands."""
    pass


@cli.group()
def tools():
    """Advanced tools and utilities."""
    pass


# ============================================================================
# DISK COMMANDS
# ============================================================================

@disk.command('list')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
def disk_list(output_json: bool):
    """List all physical disks."""
    try:
        enumerator = DiskEnumerator()
        disks = enumerator.list_disks()
        
        if not disks:
            click.secho("No disks found", fg="yellow")
            return
        
        if output_json:
            import json
            disk_data = []
            for disk in disks:
                disk_data.append({
                    'id': disk.id,
                    'model': disk.model,
                    'size': disk.size,
                    'type': disk.disk_type.value,
                    'connection': disk.connection_type.value,
                    'partition_table': disk.partition_table.value,
                    'partitions': len(disk.partitions),
                    'removable': disk.is_removable,
                    'system': disk.is_system_disk
                })
            click.echo(json.dumps(disk_data, indent=2))
        else:
            click.secho(f"\n{'='*70}", fg="cyan")
            click.secho(f"Found {len(disks)} disk(s)", fg="green", bold=True)
            click.secho(f"{'='*70}\n", fg="cyan")
            
            for disk in disks:
                # Disk header with status indicators
                status_icons = []
                if disk.is_system_disk:
                    status_icons.append("💻 SYSTEM")
                if disk.is_removable:
                    status_icons.append("🔌 REMOVABLE")
                
                status_str = " ".join(status_icons) if status_icons else ""
                
                click.secho(f"📀 {disk.id}", fg="cyan", bold=True, nl=False)
                if status_str:
                    click.secho(f"  {status_str}", fg="yellow", nl=False)
                click.echo()
                
                click.echo(f"   Model:      {disk.model}")
                click.echo(f"   Size:       {PartitionValidator.format_size(disk.size)}")
                click.echo(f"   Type:       {disk.disk_type.value.upper()}")
                click.echo(f"   Connection: {disk.connection_type.value.upper()}")
                click.echo(f"   PT Type:    {disk.partition_table.value.upper()}")
                click.echo(f"   Partitions: {len(disk.partitions)}")
                
                if disk.serial:
                    click.echo(f"   Serial:     {disk.serial}")
                
                click.echo()
            
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red", bold=True)
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@disk.command('info')
@click.argument('disk_id')
@click.option('--smart', is_flag=True, help='Include S.M.A.R.T. data')
def disk_info(disk_id: str, smart: bool):
    """Show detailed information for a specific disk."""
    try:
        enumerator = DiskEnumerator()
        disk = enumerator.get_disk_info(disk_id)
        
        if not disk:
            click.secho(f"❌ Disk not found: {disk_id}", fg="red", bold=True)
            sys.exit(1)
        
        click.secho(f"\n{'='*70}", fg="cyan")
        click.secho(f"Disk Information: {disk.id}", fg="green", bold=True)
        click.secho(f"{'='*70}\n", fg="cyan")
        
        # Basic info
        click.secho("Basic Information:", fg="yellow", bold=True)
        click.echo(f"  Model:          {disk.model}")
        click.echo(f"  Size:           {PartitionValidator.format_size(disk.size)}")
        click.echo(f"  Type:           {disk.disk_type.value.upper()}")
        click.echo(f"  Connection:     {disk.connection_type.value.upper()}")
        click.echo(f"  Partition Table: {disk.partition_table.value.upper()}")
        
        if disk.serial:
            click.echo(f"  Serial Number:  {disk.serial}")
        
        click.echo(f"  Removable:      {'Yes' if disk.is_removable else 'No'}")
        click.echo(f"  System Disk:    {'Yes' if disk.is_system_disk else 'No'}")
        
        # Partitions
        if disk.partitions:
            click.echo()
            click.secho(f"Partitions ({len(disk.partitions)}):", fg="yellow", bold=True)
            
            for part in disk.partitions:
                click.echo(f"\n  └─ {part.id}")
                click.echo(f"     Number:      {part.number}")
                click.echo(f"     Size:        {PartitionValidator.format_size(part.size)}")
                click.echo(f"     Filesystem:  {part.filesystem.value.upper()}")
                
                if part.label:
                    click.echo(f"     Label:       {part.label}")
                if part.mount_point:
                    click.echo(f"     Mount Point: {part.mount_point}")
                if part.uuid:
                    click.echo(f"     UUID:        {part.uuid}")
        
        click.echo()
        
        if smart:
            click.secho("\nS.M.A.R.T. Data:", fg="yellow", bold=True)
            click.secho("  (Not yet implemented)", fg="gray")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red", bold=True)
        sys.exit(1)


@disk.command('smart')
@click.argument('disk_id')
def disk_smart(disk_id: str):
    """Show S.M.A.R.T. health data for a disk."""
    click.secho("S.M.A.R.T. monitoring - Coming soon!", fg="yellow")
    click.echo("This feature will show:")
    click.echo("  • Health status")
    click.echo("  • Temperature")
    click.echo("  • Bad sectors")
    click.echo("  • Power-on hours")
    click.echo("  • SSD wear level")


# ============================================================================
# PARTITION COMMANDS
# ============================================================================

@partition.command('list')
@click.argument('disk_id')
def partition_list(disk_id: str):
    """List all partitions on a disk."""
    try:
        enumerator = DiskEnumerator()
        disk = enumerator.get_disk_info(disk_id)
        
        if not disk:
            click.secho(f"❌ Disk not found: {disk_id}", fg="red", bold=True)
            sys.exit(1)
        
        if not disk.partitions:
            click.secho(f"No partitions found on {disk_id}", fg="yellow")
            return
        
        click.secho(f"\nPartitions on {disk_id}:", fg="green", bold=True)
        click.secho(f"{'='*70}\n", fg="cyan")
        
        for part in disk.partitions:
            click.secho(f"  {part.id}", fg="cyan", bold=True)
            click.echo(f"    Size:       {PartitionValidator.format_size(part.size)}")
            click.echo(f"    Filesystem: {part.filesystem.value.upper()}")
            
            if part.label:
                click.echo(f"    Label:      {part.label}")
            if part.mount_point:
                click.echo(f"    Mounted:    {part.mount_point}")
            
            click.echo()
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red", bold=True)
        sys.exit(1)


@partition.command('create')
@click.argument('disk_id')
@click.argument('size')
@click.argument('filesystem')
@click.option('--label', '-l', help='Partition label')
@require_admin_decorator
def partition_create(disk_id: str, size: str, filesystem: str, label: Optional[str]):
    """
    Create a new partition.
    
    SIZE: Partition size (e.g., 10GB, 500M, 1.5TB)
    FILESYSTEM: Filesystem type (ntfs, ext4, fat32, exfat, xfs, btrfs)
    """
    click.secho("Partition creation - Coming soon!", fg="yellow")
    click.echo(f"Will create: {size} {filesystem} partition on {disk_id}")
    if label:
        click.echo(f"Label: {label}")


@partition.command('delete')
@click.argument('partition_id')
@click.option('--secure', is_flag=True, help='Secure wipe (3-pass)')
@click.confirmation_option(prompt='Are you sure you want to delete this partition?')
@require_admin_decorator
def partition_delete(partition_id: str, secure: bool):
    """Delete a partition."""
    click.secho("Partition deletion - Coming soon!", fg="yellow")
    if secure:
        click.echo("Will perform secure wipe")


@partition.command('resize')
@click.argument('partition_id')
@click.argument('new_size')
@require_admin_decorator
def partition_resize(partition_id: str, new_size: str):
    """Resize a partition."""
    click.secho("Partition resize - Coming soon!", fg="yellow")


@partition.command('format')
@click.argument('partition_id')
@click.argument('filesystem')
@click.option('--label', '-l', help='Volume label')
@click.option('--quick', is_flag=True, default=True, help='Quick format (default)')
@click.confirmation_option(prompt='⚠️  This will erase all data. Continue?')
@require_admin_decorator
def partition_format(partition_id: str, filesystem: str, label: Optional[str], quick: bool):
    """Format a partition."""
    click.secho("Partition format - Coming soon!", fg="yellow")


# ============================================================================
# TOOLS COMMANDS
# ============================================================================

@tools.command('clone')
@click.argument('source')
@click.argument('destination')
@click.option('--verify', is_flag=True, help='Verify after cloning')
@click.confirmation_option(prompt='⚠️  Destination will be overwritten. Continue?')
@require_admin_decorator
def tools_clone(source: str, destination: str, verify: bool):
    """Clone a disk or partition."""
    click.secho("Disk cloning - Coming soon!", fg="yellow")


@tools.command('image')
@click.argument('action', type=click.Choice(['create', 'restore']))
@click.argument('source')
@click.argument('target')
@require_admin_decorator
def tools_image(action: str, source: str, target: str):
    """Create or restore disk images."""
    click.secho(f"Image {action} - Coming soon!", fg="yellow")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
