#!/usr/bin/env python
"""
DiskRim CLI Launcher

Run this file directly to start the DiskRim CLI application.
Requires administrator/root privileges for disk operations.

Usage:
    python run_cli.py disk list
    python run_cli.py partition list /dev/sda
    python run_cli.py --help
"""

import sys
from partition_manager.cli.main import main

if __name__ == "__main__":
    main()
