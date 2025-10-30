#!/bin/bash

# DDE File Manager Extra Context Menu - Cleanup Script
# This script removes build artifacts, temporary files, and debian packaging files

echo "Starting cleanup process..."

# Remove Qt compilation artifacts
echo "Removing Qt compilation artifacts..."
rm -f *.o ui_* moc_* qrc_* Makefile *.qrc .qmake.stash *.debug

# Remove any potential binary files
echo "Removing potential binary files..."
rm -f MediaDebuger media-debuger

# Remove log directories
echo "Removing log directories..."
rm -rf app_logs/ .qm/

# Clean debian packaging directories and files
echo "Cleaning debian packaging files..."
rm -rf debian/.debhelper/
rm -rf debian/dde-file-manager-extramenu-dde-dconfig-editor-plugin/
rm -rf debian/dde-file-manager-extramenu-deb-builder-plugin/
rm -rf debian/dde-file-manager-extramenu-deepin-project-downloader-plugin/
rm -rf debian/dde-file-manager-extramenu-git-cola-plugin/
rm -rf debian/dde-file-manager-extramenu-gitk-plugin/
rm -rf debian/dde-file-manager-extramenu-integration-all-plugin/
rm -rf debian/dde-file-manager-extramenu-plugins/
rm -f debian/files debian/debhelper-build-stamp
rm -f debian/*.log debian/*.substvars

# Clean build artifacts from build-deb directory
echo "Cleaning build-deb artifacts..."
rm -rf build-deb/*.deb

# Clean any temporary files in plugin directories
echo "Cleaning temporary files in plugin directories..."
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.tmp" -delete
find . -name "*.bak" -delete
find . -name "*.swp" -delete
find . -name ".*.swp" -delete

# Clear screen and show final directory listing
clear
echo "Cleanup completed!"
echo "Current directory contents:"
ls -al

echo ""
echo "Cleanup script finished successfully!"