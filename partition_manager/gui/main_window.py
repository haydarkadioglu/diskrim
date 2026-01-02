"""
DiskRim Main Window - Modern GUI for partition management.

Provides an intuitive interface for managing disks and partitions
with real-time visualization and safety features.
"""

import sys
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QLabel, QTextEdit,
    QMenuBar, QMenu, QToolBar, QStatusBar, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QFont

from ..utils.platform_check import is_admin, get_platform, OSType
from ..utils.logger import setup_logger, get_logger, LogLevel
from ..backend.disk_enumerator import DiskEnumerator, DiskInfo, PartitionInfo
from ..backend.partition_ops import PartitionOperations
from ..backend.filesystem_ops import FilesystemOperations
from ..utils.validators import PartitionValidator, FilesystemType

logger = get_logger(__name__)


def request_admin_restart():
    """
    Request administrator/root privileges and restart the application.
    
    On Windows: Uses ShellExecuteW with 'runas' verb to trigger UAC prompt
    On Linux: Shows instructions for using sudo
    
    Returns:
        True if restart was initiated, False otherwise
    """
    os_platform = get_platform()
    
    if os_platform.os_type == OSType.WINDOWS:
        try:
            import ctypes
            
            # Determine how to restart the application
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                script = sys.executable
                params = ''
            else:
                # Running as Python script
                # Use pythonw.exe instead of python.exe to avoid console window
                python_dir = os.path.dirname(sys.executable)
                pythonw = os.path.join(python_dir, 'pythonw.exe')
                
                # Fallback to python.exe if pythonw.exe doesn't exist
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                
                script = pythonw
                
                # Check if we're running via entry point (diskrim-gui) or direct python
                if 'diskrim-gui' in sys.argv[0] or 'main_window' in sys.argv[0]:
                    # Running via entry point, use -m to run the module
                    params = '-m partition_manager.gui.main_window'
                else:
                    # Direct python execution
                    params = ' '.join([f'"{arg}"' for arg in sys.argv])
            
            logger.info(f"Requesting elevation: {script} {params}")
            
            # Show UAC prompt and restart as admin
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,                    # hwnd
                "runas",                 # operation (runas = run as administrator)
                script,                  # file
                params,                  # parameters
                None,                    # directory
                1                        # show command (SW_SHOW)
            )
            
            # If successful (ret > 32), the new instance was launched
            if ret > 32:
                logger.info(f"Elevation request successful (code: {ret})")
                return True
            else:
                logger.error(f"Failed to elevate privileges. Error code: {ret}")
                return False
                
        except Exception as e:
            logger.error(f"Error requesting admin privileges: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    elif os_platform.os_type == OSType.LINUX:
        # On Linux, we can't auto-restart with sudo from GUI
        # User needs to run from terminal with sudo
        return False
    
    return False


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.os_platform = get_platform()
        self.disk_enumerator = DiskEnumerator()
        self.partition_ops = PartitionOperations()
        self.filesystem_ops = FilesystemOperations()
        self.current_disk: Optional[DiskInfo] = None
        self.current_partition: Optional[PartitionInfo] = None
        
        self.init_ui()
        self.check_permissions()
        self.load_disks()
    
    def init_ui(self):
        """Initialize the user interface."""
        from .. import __version__
        self.setWindowTitle(f"DiskRim v{__version__} - Partition Manager")
        self.setMinimumSize(1200, 700)
        
        # Load stylesheet
        self.load_stylesheet()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create splitter for disk list and details
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Disk tree view
        self.disk_tree = QTreeWidget()
        self.disk_tree.setHeaderLabels(["Device", "Size", "Type"])
        self.disk_tree.setColumnWidth(0, 250)
        self.disk_tree.setColumnWidth(1, 100)
        self.disk_tree.itemSelectionChanged.connect(self.on_disk_selected)
        main_splitter.addWidget(self.disk_tree)
        
        # Right panel: Details view
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Details header
        self.details_header = QLabel("Select a disk to view details")
        self.details_header.setProperty("class", "header")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.details_header.setFont(font)
        right_layout.addWidget(self.details_header)
        
        # Details content
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        right_layout.addWidget(self.details_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.btn_create = QPushButton("Create Partition")
        self.btn_create.setEnabled(False)
        self.btn_create.clicked.connect(self.create_partition)
        button_layout.addWidget(self.btn_create)
        
        self.btn_delete = QPushButton("Delete Partition")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_partition)
        button_layout.addWidget(self.btn_delete)
        
        self.btn_resize = QPushButton("Resize Partition")
        self.btn_resize.setEnabled(False)
        self.btn_resize.clicked.connect(self.resize_partition)
        button_layout.addWidget(self.btn_resize)
        
        right_layout.addLayout(button_layout)
        
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(main_splitter)
        
        # Bottom panel: Log view
        log_splitter = QSplitter(Qt.Vertical)
        log_splitter.addWidget(main_splitter)
        
        log_widget = QWidget()
        log_layout = QVBoxLayout()
        log_widget.setLayout(log_layout)
        
        log_label = QLabel("Log")
        log_label.setProperty("class", "subheader")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        log_label.setFont(font)
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        log_splitter.addWidget(log_widget)
        log_splitter.setStretchFactor(0, 4)
        log_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(log_splitter)
        
        # Create status bar
        self.create_status_bar()
    
    def load_stylesheet(self):
        """Load and apply the dark theme stylesheet."""
        try:
            style_path = Path(__file__).parent / "styles.qss"
            if style_path.exists():
                with open(style_path, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                logger.debug("Stylesheet loaded successfully")
            else:
                logger.warning(f"Stylesheet not found: {style_path}")
        except Exception as e:
            logger.error(f"Error loading stylesheet: {e}")
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_disks)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Disk menu
        disk_menu = menubar.addMenu("Disk")
        
        info_action = QAction("Disk Information", self)
        info_action.triggered.connect(self.show_disk_info)
        disk_menu.addAction(info_action)
        
        smart_action = QAction("S.M.A.R.T. Data", self)
        smart_action.triggered.connect(self.show_smart_data)
        disk_menu.addAction(smart_action)
        
        # Partition menu
        partition_menu = menubar.addMenu("Partition")
        
        create_action = QAction("Create Partition", self)
        create_action.triggered.connect(self.create_partition)
        partition_menu.addAction(create_action)
        
        delete_action = QAction("Delete Partition", self)
        delete_action.triggered.connect(self.delete_partition)
        partition_menu.addAction(delete_action)
        
        resize_action = QAction("Resize Partition", self)
        resize_action.triggered.connect(self.resize_partition)
        partition_menu.addAction(resize_action)
        
        format_action = QAction("Format Partition", self)
        format_action.triggered.connect(self.format_partition)
        partition_menu.addAction(format_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        clone_action = QAction("Clone Disk", self)
        clone_action.triggered.connect(self.clone_disk)
        tools_menu.addAction(clone_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About DiskRim", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the toolbar."""
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.load_disks)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        create_action = QAction("Create", self)
        create_action.triggered.connect(self.create_partition)
        toolbar.addAction(create_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_partition)
        toolbar.addAction(delete_action)
        
        resize_action = QAction("Resize", self)
        resize_action.triggered.connect(self.resize_partition)
        toolbar.addAction(resize_action)
    
    def create_status_bar(self):
        """Create the status bar."""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Permission status
        if is_admin():
            self.statusBar.showMessage("✓ Running with Administrator/Root privileges")
        else:
            self.statusBar.showMessage("⚠ Limited mode - Administrator/Root privileges required for operations")
    
    def check_permissions(self):
        """Check permissions and automatically request admin elevation if needed."""
        if not is_admin():
            if self.os_platform.os_type == OSType.WINDOWS:
                # Directly request UAC elevation without showing dialog first
                logger.info("Not running as admin, requesting elevation...")
                
                if request_admin_restart():
                    # Successfully launched elevated instance, close this one
                    logger.info("Elevated instance launched, closing current instance")
                    QApplication.quit()
                    sys.exit(0)
                else:
                    # User cancelled UAC or elevation failed
                    logger.warning("Admin elevation cancelled or failed, running in limited mode")
                    
                    # Show limited mode warning
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Running in Limited Mode")
                    msg.setText("DiskRim is running without Administrator privileges.")
                    msg.setInformativeText(
                        "You cancelled the UAC prompt or elevation failed.\n\n"
                        "The application will run in limited mode - you can view disks "
                        "but cannot perform partition operations.\n\n"
                        "To enable full functionality, restart the application and "
                        "accept the UAC prompt."
                    )
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec()
                
            else:
                # Linux - can't auto-restart with sudo from GUI
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Root Privileges Required")
                msg.setText("DiskRim is not running with root privileges.")
                msg.setInformativeText(
                    "Many disk operations require root privileges.\n\n"
                    "Please close this window and run from terminal:\n"
                    "sudo diskrim-gui"
                )
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
    
    def load_disks(self):
        """Load and display all disks."""
        try:
            self.log_text.append("Loading disks...")
            self.disk_tree.clear()
            
            disks = self.disk_enumerator.list_disks()
            
            if not disks:
                self.log_text.append("No disks found")
                return
            
            for disk in disks:
                # Create disk item
                disk_item = QTreeWidgetItem(self.disk_tree)
                
                # Add status indicators
                status_text = disk.id
                if disk.is_system_disk:
                    status_text += " [SYSTEM]"
                if disk.is_removable:
                    status_text += " [REMOVABLE]"
                
                disk_item.setText(0, status_text)
                disk_item.setText(1, PartitionValidator.format_size(disk.size))
                disk_item.setText(2, f"{disk.disk_type.value.upper()} ({disk.partition_table.value.upper()})")
                disk_item.setData(0, Qt.UserRole, disk)
                
                # Add partitions as children
                for partition in disk.partitions:
                    part_item = QTreeWidgetItem(disk_item)
                    part_label = partition.label if partition.label else "Unlabeled"
                    part_item.setText(0, f"{partition.id} - {part_label}")
                    part_item.setText(1, PartitionValidator.format_size(partition.size))
                    part_item.setText(2, partition.filesystem.value.upper())
                    part_item.setData(0, Qt.UserRole, partition)
                
                # Expand disk items
                disk_item.setExpanded(True)
            
            self.log_text.append(f"✓ Loaded {len(disks)} disk(s)")
            
        except Exception as e:
            logger.error(f"Error loading disks: {e}")
            self.log_text.append(f"❌ Error loading disks: {e}")
    
    def on_disk_selected(self):
        """Handle disk/partition selection."""
        selected_items = self.disk_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        data = item.data(0, Qt.UserRole)
        
        if isinstance(data, DiskInfo):
            self.current_disk = data
            self.show_disk_details(data)
            self.btn_create.setEnabled(is_admin())
            self.btn_delete.setEnabled(False)
            self.btn_resize.setEnabled(False)
        else:
            # Partition selected
            self.current_partition = data
            parent_item = item.parent()
            if parent_item:
                self.current_disk = parent_item.data(0, Qt.UserRole)
            self.btn_create.setEnabled(False)
            self.btn_delete.setEnabled(is_admin())
            self.btn_resize.setEnabled(is_admin())
    
    def show_disk_details(self, disk: DiskInfo):
        """Display detailed disk information."""
        self.details_header.setText(f"Disk: {disk.id}")
        
        details = f"""
<h2>Disk Information</h2>

<table style="width: 100%; border-collapse: collapse;">
<tr>
    <td style="padding: 8px; font-weight: bold; width: 40%;">Model:</td>
    <td style="padding: 8px;">{disk.model}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold;">Size:</td>
    <td style="padding: 8px;">{PartitionValidator.format_size(disk.size)}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold;">Type:</td>
    <td style="padding: 8px;">{disk.disk_type.value.upper()}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold;">Connection:</td>
    <td style="padding: 8px;">{disk.connection_type.value.upper()}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold;">Partition Table:</td>
    <td style="padding: 8px;">{disk.partition_table.value.upper()}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold;">Partitions:</td>
    <td style="padding: 8px;">{len(disk.partitions)}</td>
</tr>
"""
        
        if disk.serial:
            details += f"""
<tr>
    <td style="padding: 8px; font-weight: bold;">Serial Number:</td>
    <td style="padding: 8px;">{disk.serial}</td>
</tr>
"""
        
        details += f"""
<tr>
    <td style="padding: 8px; font-weight: bold;">Removable:</td>
    <td style="padding: 8px;">{'Yes' if disk.is_removable else 'No'}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold;">System Disk:</td>
    <td style="padding: 8px;">{'Yes' if disk.is_system_disk else 'No'}</td>
</tr>
</table>
"""
        
        if disk.partitions:
            details += """
<h3>Partitions</h3>
<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
<tr style="background-color: rgba(58, 123, 213, 0.2);">
    <th style="padding: 8px; text-align: left;">ID</th>
    <th style="padding: 8px; text-align: left;">Size</th>
    <th style="padding: 8px; text-align: left;">Filesystem</th>
    <th style="padding: 8px; text-align: left;">Label</th>
</tr>
"""
            for part in disk.partitions:
                details += f"""
<tr>
    <td style="padding: 8px;">{part.id}</td>
    <td style="padding: 8px;">{PartitionValidator.format_size(part.size)}</td>
    <td style="padding: 8px;">{part.filesystem.value.upper()}</td>
    <td style="padding: 8px;">{part.label if part.label else '-'}</td>
</tr>
"""
            details += "</table>"
        
        self.details_text.setHtml(details)
    
    # Operation methods
    def create_partition(self):
        """Create a new partition with dialog."""
        if not self.current_disk:
            QMessageBox.warning(self, "No Selection", "Please select a disk to create a partition on.")
            return
        
        if not is_admin():
            QMessageBox.warning(self, "Permission Denied", "Administrator/root privileges required for this operation.")
            return
        
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QSpinBox, QSlider, QLabel, QHBoxLayout
        
        # Calculate available space
        used_space = sum(p.size for p in self.current_disk.partitions)
        available_space = self.current_disk.size - used_space
        available_mb = int(available_space / (1024 * 1024))
        available_gb = available_space / (1024**3)
        
        if available_mb < 100:
            QMessageBox.warning(self, "No Space", f"Not enough free space on disk.\n\nAvailable: {available_mb} MB")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Partition")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Available space info
        info_label = QLabel(f"💾 Available Space: {available_mb:,} MB ({available_gb:.2f} GB)")
        info_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)
        
        form = QFormLayout()
        
        # Size with slider
        size_layout = QVBoxLayout()
        
        # SpinBox and GB label in horizontal layout
        size_input_layout = QHBoxLayout()
        size_input = QSpinBox()
        size_input.setRange(100, available_mb)
        size_input.setValue(min(10240, available_mb))  # Default 10 GB or max
        size_input.setSuffix(" MB")
        size_input.setMaximumWidth(150)
        
        size_gb_label = QLabel()
        size_gb_label.setStyleSheet("color: #888; margin-left: 10px;")
        
        def update_gb_label():
            gb = size_input.value() / 1024
            size_gb_label.setText(f"≈ {gb:.2f} GB")
        
        update_gb_label()
        
        size_input_layout.addWidget(size_input)
        size_input_layout.addWidget(size_gb_label)
        size_input_layout.addStretch()
        
        # Slider
        size_slider = QSlider(Qt.Horizontal)
        size_slider.setRange(100, available_mb)
        size_slider.setValue(size_input.value())
        size_slider.setTickPosition(QSlider.TicksBelow)
        size_slider.setTickInterval(available_mb // 10)
        
        # Sync slider and spinbox
        def on_slider_change(value):
            size_input.setValue(value)
            update_gb_label()
        
        def on_spinbox_change(value):
            size_slider.setValue(value)
            update_gb_label()
        
        size_slider.valueChanged.connect(on_slider_change)
        size_input.valueChanged.connect(on_spinbox_change)
        
        size_layout.addLayout(size_input_layout)
        size_layout.addWidget(size_slider)
        
        form.addRow("Size:", size_layout)
        
        # Filesystem type
        fs_combo = QComboBox()
        fs_combo.addItems(["NTFS", "FAT32", "exFAT", "EXT4", "EXT3"])
        form.addRow("Filesystem:", fs_combo)
        
        # Label
        label_input = QLineEdit()
        label_input.setPlaceholderText("Partition Label (optional)")
        form.addRow("Label:", label_input)
        
        # Partition type
        type_combo = QComboBox()
        type_combo.addItems(["primary", "logical"])
        form.addRow("Type:", type_combo)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        # Show dialog
        if dialog.exec() != QDialog.Accepted:
            return
        
        # Get values
        size_mb = size_input.value()
        size_bytes = size_mb * 1024 * 1024
        
        fs_str = fs_combo.currentText().lower()
        fs_map = {
            'ntfs': FilesystemType.NTFS,
            'fat32': FilesystemType.FAT32,
            'exfat': FilesystemType.EXFAT,
            'ext4': FilesystemType.EXT4,
            'ext3': FilesystemType.EXT3,
        }
        filesystem = fs_map.get(fs_str, FilesystemType.NTFS)
        
        label = label_input.text().strip() or None
        partition_type = type_combo.currentText()
        
        # Confirm
        size_gb = size_bytes / (1024**3)
        reply = QMessageBox.question(
            self,
            "Confirm Creation",
            f"Create partition on {self.current_disk.id}:\n\n"
            f"Size: {size_mb:,} MB ({size_gb:.2f} GB)\n"
            f"Filesystem: {fs_combo.currentText()}\n"
            f"Label: {label or 'None'}\n"
            f"Type: {partition_type}\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Perform creation
        self.log_text.append(f"Creating partition on {self.current_disk.id}...")
        
        success, error, part_id = self.partition_ops.create_partition(
            disk_id=self.current_disk.id,
            size=size_bytes,
            filesystem=filesystem,
            label=label,
            partition_type=partition_type,
            progress_callback=lambda pct, msg: self.log_text.append(f"[{pct}%] {msg}")
        )
        
        if success:
            QMessageBox.information(self, "Success", f"Partition created successfully: {part_id}")
            self.log_text.append("✓ Partition created successfully")
            self.load_disks()  # Refresh
        else:
            QMessageBox.critical(self, "Error", f"Failed to create partition:\n\n{error}")
            self.log_text.append(f"❌ Error: {error}")
    
    def delete_partition(self):
        """Delete selected partition with confirmation."""
        if not self.current_partition:
            QMessageBox.warning(self, "No Selection", "Please select a partition to delete.")
            return
        
        if not is_admin():
            QMessageBox.warning(self, "Permission Denied", "Administrator/root privileges required for this operation.")
            return
        
        # Confirmation dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Deletion")
        msg.setText(f"Are you sure you want to delete partition:\n\n{self.current_partition.id}")
        msg.setInformativeText(
            f"Filesystem: {self.current_partition.filesystem.value}\n"
            f"Size: {PartitionValidator.format_size(self.current_partition.size)}\n\n"
            "⚠ This action cannot be undone!\n\n"
            "All data on this partition will be lost."
        )
        
        # Add secure wipe option
        secure_btn = msg.addButton("Secure Delete (3-pass wipe)", QMessageBox.DestructiveRole)
        normal_btn = msg.addButton("Delete", QMessageBox.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)
        
        msg.exec()
        
        if msg.clickedButton() == cancel_btn:
            return
        
        secure_wipe = (msg.clickedButton() == secure_btn)
        
        # Perform deletion
        self.log_text.append(f"Deleting partition {self.current_partition.id}...")
        
        success, error = self.partition_ops.delete_partition(
            partition_id=self.current_partition.id,
            secure_wipe=secure_wipe,
            wipe_passes=3 if secure_wipe else 0,
            progress_callback=lambda pct, msg: self.log_text.append(f"[{pct}%] {msg}")
        )
        
        if success:
            QMessageBox.information(self, "Success", f"Partition {self.current_partition.id} deleted successfully.")
            self.log_text.append("✓ Partition deleted successfully")
            self.load_disks()  # Refresh
        else:
            QMessageBox.critical(self, "Error", f"Failed to delete partition:\n\n{error}")
            self.log_text.append(f"❌ Error: {error}")
    
    def resize_partition(self):
        """Resize selected partition with simple dialog."""
        if not self.current_partition:
            QMessageBox.warning(self, "No Selection", "Please select a partition to resize.")
            return
        
        if not is_admin():
            QMessageBox.warning(self, "Permission Denied", "Administrator/root privileges required for this operation.")
            return
        
        from PySide6.QtWidgets import QInputDialog
        
        # Calculate current size in MB and GB
        current_size_mb = self.current_partition.size / (1024**2)
        current_size_gb = self.current_partition.size / (1024**3)
        
        # Show input dialog for new size in MB
        new_size_mb, ok = QInputDialog.getDouble(
            self,
            "Resize Partition",
            f"Current size: {current_size_mb:.0f} MB ({current_size_gb:.2f} GB)\n\nEnter new size (MB):",
            value=current_size_mb,
            min=1.0,
            max=10000000.0,  # ~10TB
            decimals=0
        )
        
        if not ok:
            return
        
        new_size_bytes = int(new_size_mb * (1024**2))
        new_size_gb = new_size_bytes / (1024**3)
        
        # Confirm with both MB and GB display
        reply = QMessageBox.question(
            self,
            "Confirm Resize",
            f"Resize partition {self.current_partition.id}:\n\n"
            f"From: {current_size_mb:.0f} MB ({current_size_gb:.2f} GB)\n"
            f"To: {new_size_mb:.0f} MB ({new_size_gb:.2f} GB)\n\n"
            "This operation may take several minutes.\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Perform resize
        self.log_text.append(f"Resizing partition {self.current_partition.id}...")
        
        success, error = self.partition_ops.resize_partition(
            partition_id=self.current_partition.id,
            new_size=new_size_bytes,
            filesystem=self.current_partition.filesystem,
            progress_callback=lambda pct, msg: self.log_text.append(f"[{pct}%] {msg}")
        )
        
        if success:
            QMessageBox.information(self, "Success", f"Partition resized successfully to {new_size_mb:.0f} MB ({new_size_gb:.2f} GB).")
            self.log_text.append("✓ Partition resized successfully")
            self.load_disks()  # Refresh
        else:
            QMessageBox.critical(self, "Error", f"Failed to resize partition:\n\n{error}")
            self.log_text.append(f"❌ Error: {error}")
    
    def format_partition(self):
        QMessageBox.information(self, "Coming Soon", "Partition format will be implemented soon!")
    
    def clone_disk(self):
        QMessageBox.information(self, "Coming Soon", "Disk cloning will be implemented soon!")
    
    def show_disk_info(self):
        if self.current_disk:
            self.show_disk_details(self.current_disk)
    
    def show_smart_data(self):
        QMessageBox.information(self, "Coming Soon", "S.M.A.R.T. monitoring will be implemented soon!")
    
    def show_about(self):
        """Show about dialog."""
        from .. import __version__
        QMessageBox.about(
            self,
            "About DiskRim",
            f"<h2>DiskRim - Partition Manager</h2>"
            f"<p>Version {__version__}</p>"
            "<p>Modern, safe, and user-friendly partition management.</p>"
            "<p>Built with Python and PySide6</p>"
            "<p>© 2025 DiskRim Contributors</p>"
            "<p>Licensed under MIT License</p>"
        )


def main():
    """Entry point for GUI application."""
    # Setup logging
    setup_logger(level=LogLevel.INFO)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("DiskRim")
    app.setOrganizationName("DiskRim")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
