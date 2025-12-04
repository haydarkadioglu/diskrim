"""
Comprehensive logging system for DiskRim.

Provides colored console logging and persistent SQLite-based
operation logging with automatic snapshots.
"""

import logging
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import colorlog


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class OperationType(Enum):
    """Types of disk operations."""
    CREATE_PARTITION = "create_partition"
    DELETE_PARTITION = "delete_partition"
    RESIZE_PARTITION = "resize_partition"
    MOVE_PARTITION = "move_partition"
    FORMAT_PARTITION = "format_partition"
    CONVERT_MBR_GPT = "convert_mbr_gpt"
    CONVERT_GPT_MBR = "convert_gpt_mbr"
    CLONE_DISK = "clone_disk"
    CLONE_PARTITION = "clone_partition"
    CREATE_IMAGE = "create_image"
    RESTORE_IMAGE = "restore_image"
    SECURE_ERASE = "secure_erase"
    BOOT_REPAIR = "boot_repair"
    OTHER = "other"


class OperationLogger:
    """
    Persistent operation logger using SQLite.
    
    Stores detailed operation logs, snapshots, and audit trail.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize operation logger.
        
        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Store in user's data directory
            if Path.home().exists():
                app_data = Path.home() / ".diskrim"
                app_data.mkdir(exist_ok=True)
                db_path = app_data / "operations.db"
            else:
                db_path = Path("diskrim_operations.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                disk_id TEXT,
                partition_id TEXT,
                description TEXT,
                parameters TEXT,
                status TEXT DEFAULT 'started',
                error_message TEXT,
                completed_at TEXT
            )
        """)
        
        # Snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id INTEGER,
                timestamp TEXT NOT NULL,
                disk_id TEXT NOT NULL,
                partition_table TEXT,
                filesystem_info TEXT,
                FOREIGN KEY (operation_id) REFERENCES operations(id)
            )
        """)
        
        # Audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_operation_start(
        self,
        operation_type: OperationType,
        disk_id: Optional[str] = None,
        partition_id: Optional[str] = None,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log the start of an operation.
        
        Args:
            operation_type: Type of operation
            disk_id: Target disk identifier
            partition_id: Target partition identifier
            description: Human-readable description
            parameters: Operation parameters
            
        Returns:
            Operation ID for tracking
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO operations 
            (timestamp, operation_type, disk_id, partition_id, description, parameters, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            operation_type.value,
            disk_id,
            partition_id,
            description,
            json.dumps(parameters) if parameters else None,
            "started"
        ))
        
        operation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return operation_id
    
    def log_operation_complete(self, operation_id: int):
        """Mark operation as completed successfully."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE operations 
            SET status = ?, completed_at = ?
            WHERE id = ?
        """, ("completed", datetime.now().isoformat(), operation_id))
        
        conn.commit()
        conn.close()
    
    def log_operation_error(self, operation_id: int, error_message: str):
        """Mark operation as failed with error message."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE operations 
            SET status = ?, error_message = ?, completed_at = ?
            WHERE id = ?
        """, ("failed", error_message, datetime.now().isoformat(), operation_id))
        
        conn.commit()
        conn.close()
    
    def save_snapshot(
        self,
        operation_id: int,
        disk_id: str,
        partition_table: Optional[Dict] = None,
        filesystem_info: Optional[Dict] = None
    ):
        """
        Save a disk state snapshot.
        
        Args:
            operation_id: Associated operation ID
            disk_id: Disk identifier
            partition_table: Partition table data
            filesystem_info: Filesystem metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO snapshots
            (operation_id, timestamp, disk_id, partition_table, filesystem_info)
            VALUES (?, ?, ?, ?, ?)
        """, (
            operation_id,
            datetime.now().isoformat(),
            disk_id,
            json.dumps(partition_table) if partition_table else None,
            json.dumps(filesystem_info) if filesystem_info else None
        ))
        
        conn.commit()
        conn.close()
    
    def audit_log(self, level: str, message: str, context: Optional[Dict] = None):
        """Add entry to audit log."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log (timestamp, level, message, context)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            level,
            message,
            json.dumps(context) if context else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_operation_history(self, limit: int = 100) -> List[Dict]:
        """
        Get recent operation history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of operation records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM operations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return records


def setup_logger(
    name: str = "diskrim",
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up a colored console logger.
    
    Args:
        name: Logger name
        level: Minimum log level
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level.value)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(level.value)
    
    # Colored formatter
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level.value)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "diskrim") -> logging.Logger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Global operation logger instance
_operation_logger: Optional[OperationLogger] = None


def get_operation_logger() -> OperationLogger:
    """Get global operation logger instance."""
    global _operation_logger
    if _operation_logger is None:
        _operation_logger = OperationLogger()
    return _operation_logger


if __name__ == "__main__":
    # Test logging
    logger = setup_logger(level=LogLevel.DEBUG)
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Test operation logger
    op_logger = get_operation_logger()
    op_id = op_logger.log_operation_start(
        OperationType.CREATE_PARTITION,
        disk_id="/dev/sda",
        description="Creating NTFS partition",
        parameters={"size": "10GB", "filesystem": "ntfs"}
    )
    
    print(f"\nOperation ID: {op_id}")
    
    op_logger.save_snapshot(
        op_id,
        "/dev/sda",
        partition_table={"type": "gpt", "partitions": []},
    )
    
    op_logger.log_operation_complete(op_id)
    
    # Show history
    history = op_logger.get_operation_history(limit=5)
    print("\nRecent operations:")
    for record in history:
        print(f"  {record['timestamp']} - {record['operation_type']} - {record['status']}")
