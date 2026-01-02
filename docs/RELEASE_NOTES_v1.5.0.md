# Release Notes - DiskRim v1.5.0

**Release Date**: January 2, 2026  
**Type**: Major Feature Release  
**Status**: Stable

---

## 🎯 What's New in v1.5.0

This release brings **complete partition management functionality** to DiskRim with an intuitive GUI and powerful backend operations.

### ⭐ Headline Features

#### 1. 📊 Smart Partition Creation
Create partitions with an intelligent, user-friendly dialog:
- **Interactive Slider**: Drag to select size with visual feedback
- **Real-time Conversion**: See MB and GB values simultaneously
- **Smart Space Detection**: Automatically calculates available free space
- **Multiple Filesystems**: NTFS, FAT32, exFAT, EXT4, EXT3
- **Primary/Logical**: Choose partition type

![Create Dialog](https://via.placeholder.com/600x400?text=Create+Partition+Dialog)

#### 2. 🗑️ Secure Partition Deletion
Delete partitions safely with optional secure data wiping:
- **DoD 5220.22-M Compliant**: Military-grade data erasure
- **Configurable Passes**: 3-pass or 7-pass secure wipe
- **Confirmation Dialogs**: Prevent accidental deletion
- **Progress Tracking**: Real-time status updates

#### 3. 📏 Intelligent Partition Resizing
Resize partitions with automatic filesystem handling:
- **MB Input with GB Display**: Precise size control
- **Filesystem-Aware**: Automatically resizes NTFS, EXT4, XFS
- **Safety Checks**: Validates size constraints
- **Progress Updates**: Track resize operation

---

## 🔧 Technical Highlights

### Backend Architecture

#### New Modules
1. **`partition_ops.py`** - Core partition operations
   - Create, Delete, Resize partitions
   - Cross-platform (Windows diskpart, Linux parted)
   - Operation logging and history
   - Progress callback system

2. **`filesystem_ops.py`** - Filesystem management
   - Format: 7 filesystem types supported
   - Resize: NTFS, EXT4, XFS
   - Repair: chkdsk, e2fsck, ntfsfix, xfs_repair

### Windows Integration
- **No Console Windows**: All operations run silently
- **CREATE_NO_WINDOW flag**: Applied to all subprocess calls
- **Files updated**: 4 backend modules fixed
- **UAC Elevation**: Uses pythonw.exe for GUI-friendly elevation

### Operation Logging
- **SQLite Database**: All operations logged to `~/.diskrim/operations.db`
- **Audit Trail**: Timestamps, parameters, results
- **Error Tracking**: Full error messages preserved
- **Query Support**: For operation history review

---

## 📊 Feature Comparison

| Feature | v1.0.0 | v1.5.0 |
|---------|--------|--------|
| View Disks | ✅ | ✅ |
| View Partitions | ✅ | ✅ |
| Create Partition | ❌ | ✅ |
| Delete Partition | ❌ | ✅ |
| Resize Partition | ❌ | ✅ |
| Secure Wipe | ❌ | ✅ |
| Format Filesystem | ❌ | ✅ |
| Repair Filesystem | ❌ | ✅ |
| Operation Logging | ⚠️ Basic | ✅ Full |
| Console Windows | ⚠️ Visible | ✅ Hidden |
| Progress Tracking | ❌ | ✅ |

---

## 🚀 Getting Started

### Installation

```bash
# Install from source
git clone https://github.com/haydarkadioglu/diskrim.git
cd diskrim
pip install -e .
```

### Quick Start

#### GUI Mode
```bash
# Windows
python run_gui.py

# Linux
sudo python run_gui.py
```

#### CLI Mode
```bash
# List disks
diskrim disk list

# View disk info
diskrim disk info /dev/sda

# Create partition (coming in CLI)
diskrim partition create /dev/sda 10GB ntfs
```

---

## 📝 Usage Examples

### Create a 50GB NTFS Partition
1. Launch DiskRim GUI
2. Select target disk (not partition!)
3. Click **"Create Partition"**
4. Use slider or type **51200 MB**
5. Select **NTFS** filesystem
6. Enter label (optional): "Data"
7. Click **OK** → **Confirm**

### Securely Delete a Partition
1. Select partition in tree view
2. Click **"Delete Partition"**
3. Choose **"Secure Delete (3-pass wipe)"**
4. Confirm deletion
5. Wait for completion

### Resize a Partition to 100GB
1. Select partition
2. Click **"Resize Partition"**
3. Enter **102400 MB**
4. Confirm resize
5. Filesystem auto-resized

---

## ⚠️ Important Notes

### Safety
- ⚠️ **Always backup important data** before partition operations
- ⚠️ **Secure wipe is permanent** - data cannot be recovered
- ⚠️ **Admin/root required** for all operations
- ⚠️ **System disk operations** require extra caution

### Platform Differences
- **Windows**: Uses diskpart for partition operations
- **Linux**: Uses parted for partition operations
- **XFS**: Can only grow, cannot shrink
- **Windows FS Resize**: Limited (manual diskpart needed)

### Known Limitations
- Move partition: Not yet implemented
- Clone disk: Not yet implemented
- S.M.A.R.T. monitoring: Not yet implemented
- MBR ↔ GPT conversion: Not yet implemented

---

## 🐛 Bug Fixes

### From v1.0.0
- ✅ Fixed console window popups during all operations
- ✅ Fixed UAC elevation to use pythonw.exe
- ✅ Fixed partition selection not tracking correctly
- ✅ Fixed size calculation overflow for large disks
- ✅ Fixed subprocess timeout on slow operations

---

## 🔮 What's Next (v2.0.0 Roadmap)

### Planned Features
- 📝 **Move Partition**: Relocate partitions on disk
- 📝 **Clone Disk**: Full disk-to-disk cloning
- 📝 **Disk Imaging**: Create/restore .img files
- 📝 **S.M.A.R.T. Monitoring**: Health status, temperature
- 📝 **MBR ↔ GPT Conversion**: Non-destructive conversion
- 📝 **Partition Visualization**: Graphical disk layout
- 📝 **Batch Operations**: Queue multiple operations
- 📝 **CLI Operations**: Full CLI implementation

---

## 📞 Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/haydarkadioglu/diskrim/issues)
- **Discussions**: [GitHub Discussions](https://github.com/haydarkadioglu/diskrim/discussions)
- **Documentation**: [README.md](README.md)

---

## 🙏 Acknowledgments

Thanks to all contributors and the open-source community for tools and libraries that made DiskRim possible:
- PySide6 (GUI framework)
- Click (CLI framework)
- Python community

---

## 📜 License

DiskRim is released under the MIT License. See [LICENSE](LICENSE) file for details.

---

**Enjoy DiskRim v1.5.0! 🎉**
