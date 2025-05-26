#!/usr/bin/env python3
"""
Setup script for PPORTS - Port Management Tool
Поддержка упаковки в AppImage и стандартное Python окружение
"""

import sys
import os
from setuptools import setup, find_packages


def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "PPORTS - инструмент для управления сетевыми портами и процессами"

def read_requirements():
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return ["psutil>=5.9.0", "customtkinter>=5.2.0"]

setup(
    name="pports",
    version="1.0.0",
    author="vebulogmetra",
    author_email="vebulogmetra@yandex.ru",
    description="Графический инструмент для управления сетевыми портами и процессами",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/vebulogmetra/pports",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=22.0",
            "flake8>=5.0",
        ],
        "packaging": [
            "pyinstaller>=5.0",
            "cx-freeze>=6.0",
        ]
    },
    include_package_data=True,
    package_data={
        "": ["*.svg", "*.png", "*.ico"],
    },
    data_files=[
        ("share/pixmaps", ["assets/pports.svg"]),
        ("share/applications", ["assets/pports.desktop"]),
    ],
    entry_points={
        "console_scripts": [
            "pports=main:main",
            "pports-cli=cli:main",
        ],
        "gui_scripts": [
            "pports-gui=main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/vebulogmetra/pports/issues",
        "Source": "https://github.com/vebulogmetra/pports",
        "Documentation": "https://github.com/vebulogmetra/pports/wiki",
    },
    keywords="ports network processes system-administration gui",
    zip_safe=False,
) 