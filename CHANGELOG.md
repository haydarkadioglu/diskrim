# DiskRim - Version History

All notable changes to DiskRim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.5.0] - 2026-01-02

### 🎉 Major Features Added

#### Partition Operations
- ✅ **Create Partition**: Full-featured dialog with slider, filesystem selection, and size calculator
  - Real-time GB/MB conversion
  - Smart available space detection
  - Slider with visual feedback
  - Primary/Logical partition type selection
  - Filesystem support: NTFS, FAT32, exFAT, EXT4, EXT3
  
- ✅ **Delete Partition**: Secure deletion with DoD 5220.22-M compliance
  - Normal deletion mode
  - Secure wipe mode (3-pass, 7-pass configurable)
  - Confirmation dialogs with partition info
  - Progress tracking
  
- ✅ **Resize Partition**: Intelligent partition resizing
  - Input in MB with real-time GB display
  - Filesystem-aware resizing (NTFS, EXT4, XFS support)
  - Automatic filesystem resize after partition resize
  - Safety confirmations

#### Backend Improvements
- ✅ **Partition Operations Module** (`partition_ops.py`)
  - Cross-platform implementation (Windows/Linux)
  - Windows: diskpart integration
  - Linux: parted integration
  - Operation logging to SQLite database
  - Progress callback system for UI updates

- ✅ **Filesystem Operations Module** (`filesystem_ops.py`)
  - Format: NTFS, EXT4, EXT3, XFS, BTRFS, FAT32, exFAT
  - Resize: NTFS (ntfsresize), EXT4 (resize2fs), XFS (grow only)
  - Repair: chkdsk (Windows), e2fsck, ntfsfix, xfs_repair (Linux)
  - Quick and full format modes
  - Cluster size customization

#### GUI Enhancements
- ✅ **Enhanced Create Dialog**
  - 💾 Available space indicator
  - 📊 Interactive slider (100 MB - max available)
  - 🔄 Real-time size conversion (MB ↔ GB)
  - 🎨 Modern styled widgets
  - ✅ Input validation

- ✅ **No Console Windows**
  - Fixed ALL subprocess calls to prevent CMD popups
  - CREATE_NO_WINDOW flag on all Windows operations
  - Silent background execution
  - Files affected:
    - `platform_check.py` (bcdedit)
    - `disk_enumerator.py` (diskpart, wmic)
    - `partition_ops.py` (diskpart)
    - `filesystem_ops.py` (format, chkdsk)

### 🔧 Technical Improvements

#### Code Quality
- Comprehensive error handling
- Input validation for all operations
- Safe subprocess execution
- Proper timeout handling (5s-1800s based on operation)

#### Operation Logging
- All operations logged to `~/.diskrim/operations.db`
- Timestamps, parameters, and results tracked
- Error messages preserved for debugging
- Operation history for auditing

#### Progress Tracking
- Callback system for long operations
- Real-time progress updates in GUI log panel
- Percentage completion display
- Status messages for each operation step

### 🐛 Bug Fixes
- Fixed console window flashing during operations
- Fixed UAC elevation using pythonw.exe
- Fixed partition selection tracking
- Fixed size calculations and conversions
- Fixed subprocess timeout issues

### 📚 Documentation
- Updated README with v1.5.0 features
- Added inline code documentation
- Improved docstrings for all new modules
- Created comprehensive walkthrough

### 🎨 UI/UX Improvements
- Slider for intuitive size selection
- Real-time value updates
- Color-coded info messages (green = available space)
- Comma separators for large numbers (15,360 MB)
- Improved confirmation dialogs with detailed info

---

## [1.0.0] - 2025-12-04

### 🎉 Initial Release

#### Core Features
- ✅ **Cross-Platform Support**: Windows and Linux
- ✅ **Dual Interface**: GUI (PySide6) and CLI (Click)
- ✅ **Automatic UAC Elevation** (Windows)
- ✅ **Modern Dark Theme** GUI
- ✅ **Disk Enumeration**
  - Physical disk discovery
  - Partition detection
  - Disk type classification (HDD/SSD/NVMe/USB)
  - Connection type detection (SATA/NVMe/USB)
  - MBR/GPT detection

#### GUI Features
- Main window with tree view
- Disk details panel (HTML formatted)
- Real-time log panel
- Menu bar and toolbar
- Status bar with admin status
- Automatic admin privilege request

#### CLI Features
- `diskrim disk list` - List all disks
- `diskrim disk info <disk>` - Detailed disk information
- `diskrim partition list <disk>` - List partitions
- JSON output support
- Colored, formatted output

#### Backend
- Platform detection (Windows/Linux/macOS)
- Admin/root privilege checking
- UEFI/Legacy boot mode detection
- Disk validation and formatting utilities
- Comprehensive logging system (console + SQLite)

#### Security
- Admin privilege enforcement
- Operation logging
- Safe subprocess execution
- Input validation

---

## Release Notes Format

Each version includes:
- 🎉 **Major Features**: New functionality
- 🔧 **Technical Improvements**: Code quality, performance
- 🐛 **Bug Fixes**: Issues resolved
- 📚 **Documentation**: Docs and guides
- 🎨 **UI/UX**: Interface improvements
- ⚠️ **Breaking Changes**: Compatibility notes (if any)

---

## Legend

- ✅ Completed
- 🚧 In Progress
- 📝 Planned
- ❌ Deprecated
- ⚠️ Breaking Change
