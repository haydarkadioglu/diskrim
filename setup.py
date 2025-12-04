#!/usr/bin/env python3
"""
DiskRim - Modern Open Source Partition Manager
"""

from setuptools import setup, find_packages
import sys
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="diskrim",
    version="0.1.0",
    description="Modern open-source partition manager with GUI and CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DiskRim Contributors",
    author_email="",
    url="https://github.com/haydarkadioglu/diskrim",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "diskrim=partition_manager.cli.main:cli",
            "diskrim-gui=partition_manager.gui.main_window:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Filesystems",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
    ],
    keywords="partition disk manager filesystem GUI CLI windows linux",
    project_urls={
        "Bug Reports": "https://github.com/haydarkadioglu/diskrim/issues",
        "Source": "https://github.com/haydarkadioglu/diskrim",
    },
)
