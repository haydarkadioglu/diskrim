#!/usr/bin/env python
"""
DiskRim GUI Launcher

Run this file directly to start the DiskRim GUI application.
Requires administrator/root privileges for full functionality.

Usage:
    python run_gui.py
    
On Windows, you can also double-click this file.
"""

import sys
from partition_manager.gui.main_window import main

if __name__ == "__main__":
    main()
