# 💿 DiskRim - Modern Partition Manager

<div align="center">

![DiskRim Logo](resources/icons/logo.svg)

**Modern, Safe, and User-Friendly Partition Management**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/haydarkadioglu/diskrim)

</div>

## ⚠️ Important Warning

**DiskRim is a powerful disk management tool. Improper use can lead to DATA LOSS.**

- ✅ Always backup important data before performing disk operations
- ✅ Double-check disk identifiers before confirming operations
- ✅ Test on non-critical disks first
- ✅ Run with administrator/root privileges

## ✨ Features

### 🔧 Core Operations
- **Partition Management**: Create, delete, resize, move, and format partitions
- **Filesystem Support**: NTFS, exFAT, FAT32, EXT4, XFS, BTRFS
- **MBR ↔ GPT Conversion**: Bidirectional partition table conversion
- **Disk Cloning**: Full disk and partition cloning with verification
- **Image Creation**: Backup and restore disk images

### 🛡️ Safety Features
- **Double Confirmation**: Multi-level verification for destructive operations
- **Operation Logging**: Complete audit trail with timestamps
- **Automatic Snapshots**: System state backup before operations
- **Recovery System**: Power failure recovery and rollback capabilities
- **Compatibility Checking**: UEFI/Legacy, filesystem compatibility validation

### 📊 Advanced Tools
- **S.M.A.R.T. Monitoring**: Disk health status, temperature, bad sectors
- **Secure Erase**: DoD-compliant secure data wiping
- **Bad Block Testing**: Detect and mark bad sectors
- **Boot Repair**: MBR and EFI boot sector recovery
- **Benchmark Tools**: Disk read/write speed testing

### 🎨 Modern Interface
- **Beautiful GUI**: PySide6-based interface with dark mode
- **Visual Partition View**: Graphical disk layout representation
- **Real-time Progress**: Animated progress bars with ETA
- **Job Queue**: Batch operations with conflict detection
- **CLI Support**: Full-featured command-line interface

## 🚀 Installation

### Prerequisites

**Windows:**
- Python 3.8 or higher
- Administrator privileges
- Windows 10/11

**Linux:**
- Python 3.8 or higher
- Root privileges
- Required utilities: `parted`, `lsblk`, `fdisk`, `smartctl`

```bash
# Ubuntu/Debian
sudo apt-get install parted util-linux smartmontools e2fsprogs ntfs-3g

# Arch Linux
sudo pacman -S parted util-linux smartmontools e2fsprogs ntfs-3g
```

### Install DiskRim

```bash
# Clone the repository
git clone https://github.com/haydarkadioglu/diskrim.git
cd diskrim

# Install dependencies
pip install -r requirements.txt

# Install DiskRim
pip install -e .
```

## 📖 Usage

### GUI Mode

```bash
# Windows (run as Administrator)
diskrim-gui

# Linux (run as root)
sudo diskrim-gui
```

### CLI Mode

```bash
# List all disks
diskrim disk list

# Show disk details
diskrim disk info /dev/sda    # Linux
diskrim disk info \\.\PhysicalDrive0    # Windows

# List partitions
diskrim partition list /dev/sda

# Create partition (1GB NTFS)
diskrim partition create /dev/sda 1GB ntfs

# Resize partition
diskrim partition resize /dev/sda1 2GB

# Format partition
diskrim partition format /dev/sda1 ext4

# Clone disk
diskrim tools clone /dev/sda /dev/sdb

# Create disk image
diskrim tools image create /dev/sda backup.img

# Show S.M.A.R.T. data
diskrim disk smart /dev/sda
```

## 🏗️ Architecture

```
DiskRim
├── Backend Layer (Python)
│   ├── Disk Enumeration
│   ├── Partition Operations
│   ├── Filesystem Operations
│   └── Platform Abstraction
├── Security Layer
│   ├── Validation
│   ├── Confirmation System
│   └── Recovery System
├── GUI Layer (PySide6)
│   ├── Main Window
│   ├── Disk Tree View
│   └── Dialogs
└── CLI Layer (Click)
    ├── Disk Commands
    ├── Partition Commands
    └── Tool Commands
```

## 🔐 Security

DiskRim implements multiple safety layers:

1. **Input Validation**: All parameters are validated before operations
2. **Privilege Checking**: Ensures proper permissions before execution
3. **Disk Verification**: Prevents operations on wrong disks
4. **Snapshot System**: Creates recovery points before modifications
5. **Operation Logging**: Full audit trail for forensics

## 🔧 Troubleshooting

### Common Issues

#### ImportError: attempted relative import with no known parent package

**Error:**
```
ImportError: attempted relative import with no known parent package
```

**Cause:** Running Python files directly instead of using the launcher scripts.

**Solution:**
```bash
# ✅ CORRECT - Use launcher scripts
python run_gui.py          # For GUI
python run_cli.py          # For CLI

# ❌ WRONG - Don't run files directly
python partition_manager/gui/main_window.py
python partition_manager/cli/main.py
```

#### GUI Doesn't Start (Windows)

**Issue:** GUI window doesn't appear or closes immediately.

**Solutions:**
1. **Run as Administrator:**
   ```cmd
   # Right-click on Command Prompt → Run as Administrator
   cd C:\path\to\diskrim
   python run_gui.py
   ```

2. **Check UAC Settings:**
   - If UAC prompt is cancelled, GUI runs in limited mode
   - Some operations won't work without admin privileges

3. **Check Dependencies:**
   ```bash
   pip install --upgrade PySide6
   ```

#### Partition Creation Fails (WinError 2)

**Error:**
```
Partition created but format failed: [WinError 2] The system cannot find the file specified
```

**Cause:** Drive letter detection issue after partition creation.

**Workaround:**
1. Partition is actually created (check Disk Management)
2. Manually assign a drive letter in Windows Disk Management
3. Or: Use FAT32/exFAT for USB drives (better compatibility)

**Fix:** This is resolved in v1.5.0 by using diskpart format directly.

#### Permission Denied Errors

**Linux:**
```bash
# Run with sudo
sudo python run_gui.py
sudo diskrim disk list
```

**Windows:**
```cmd
# Run PowerShell/CMD as Administrator
diskrim-gui
```

#### Console Windows Appearing (Windows)

**Issue:** Black console windows flash during operations.

**Status:** Fixed in v1.5.0 - all subprocess calls use `CREATE_NO_WINDOW` flag.

If still appearing:
- Update to latest version
- Check if antivirus is interfering

#### USB Drive Not Detected

**Solutions:**
1. **Refresh Disk List:**
   - Click "Refresh" button in GUI
   - Or restart application

2. **Check USB Connection:**
   ```bash
   # Windows
   diskpart
   list disk
   
   # Linux
   sudo lsblk
   ```

3. **Check Disk Management (Windows):**
   - Win+X → Disk Management
   - Check if disk is "Online"

### Reporting Issues

If you encounter an issue not listed here:

1. **Check Logs:**
   ```
   Windows: C:\Users\<user>\.diskrim\diskrim.log
   Linux: ~/.diskrim/diskrim.log
   ```

2. **Collect Information:**
   - DiskRim version (check title bar or `--version`)
   - Operating system and version
   - Error message (screenshot helpful)
   - Steps to reproduce

3. **Report:**
   - [GitHub Issues](https://github.com/haydarkadioglu/diskrim/issues)
   - Include log file if possible
   - Describe what you expected vs what happened


## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by GParted and GNOME Disks
- Built with PySide6 and Qt Framework
- Uses smartmontools for S.M.A.R.T. monitoring

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/haydarkadioglu/diskrim/issues)
- **Discussions**: [GitHub Discussions](https://github.com/haydarkadioglu/diskrim/discussions)

---

