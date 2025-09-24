"""
Cross-platform symlink utilities for the asset pipeline.

Provides platform-specific symlink creation, validation, and cleanup functionality
for managing asset directory links between the main assets directory and client assets.
"""

import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SymlinkError(Exception):
    """Exception raised for symlink operation errors."""
    pass


class SymlinkManager:
    """Cross-platform symlink management utilities."""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_unix = platform.system() in ("Linux", "Darwin")
    
    def detect_platform(self) -> str:
        """
        Detect the current platform for symlink operations.
        
        Returns:
            str: Platform identifier ('windows', 'unix', or 'unknown')
        """
        system = platform.system()
        if system == "Windows":
            return "windows"
        elif system in ("Linux", "Darwin"):
            return "unix"
        else:
            return "unknown"
    
    def create_symlink(self, target: str, link_path: str, force: bool = True) -> bool:
        """
        Create a symlink from link_path to target using platform-appropriate commands.
        
        Args:
            target: Path to the target directory/file
            link_path: Path where the symlink should be created
            force: Whether to remove existing symlinks before creating new ones
            
        Returns:
            bool: True if symlink was created successfully
            
        Raises:
            SymlinkError: If symlink creation fails
        """
        target_path = Path(target).resolve()
        link_path_obj = Path(link_path)
        
        # Validate target exists
        if not target_path.exists():
            raise SymlinkError(f"Target path does not exist: {target_path}")
        
        # Handle existing symlink/directory
        if link_path_obj.exists() or link_path_obj.is_symlink():
            if force:
                self.remove_symlink(str(link_path_obj))
            else:
                raise SymlinkError(f"Link path already exists: {link_path}")
        
        # Create parent directories if needed
        link_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if self.is_windows:
                return self._create_windows_symlink(str(target_path), str(link_path_obj))
            elif self.is_unix:
                return self._create_unix_symlink(str(target_path), str(link_path_obj))
            else:
                raise SymlinkError(f"Unsupported platform: {platform.system()}")
        except Exception as e:
            raise SymlinkError(f"Failed to create symlink: {e}")
    
    def _create_unix_symlink(self, target: str, link_path: str) -> bool:
        """Create symlink on Unix systems using ln -sf."""
        try:
            result = subprocess.run(
                ["ln", "-sf", target, link_path],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Created Unix symlink: {link_path} -> {target}")
            return True
        except subprocess.CalledProcessError as e:
            raise SymlinkError(f"ln command failed: {e.stderr}")
    
    def _create_windows_symlink(self, target: str, link_path: str) -> bool:
        """Create symlink on Windows using mklink /D."""
        try:
            # Use mklink /D for directory symlinks
            result = subprocess.run(
                ["mklink", "/D", link_path, target],
                capture_output=True,
                text=True,
                shell=True,
                check=True
            )
            logger.info(f"Created Windows symlink: {link_path} -> {target}")
            return True
        except subprocess.CalledProcessError as e:
            raise SymlinkError(f"mklink command failed: {e.stderr}")
    
    def validate_symlink(self, link_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a symlink exists and points to a valid target.
        
        Args:
            link_path: Path to the symlink to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, target_path or error_message)
        """
        link_path_obj = Path(link_path)
        
        # Check if path exists and is a symlink
        if not link_path_obj.exists():
            return False, f"Symlink does not exist: {link_path}"
        
        if not link_path_obj.is_symlink():
            return False, f"Path is not a symlink: {link_path}"
        
        try:
            # Get the target path
            target = link_path_obj.resolve()
            
            # Check if target exists
            if not target.exists():
                return False, f"Symlink target does not exist: {target}"
            
            return True, str(target)
        except Exception as e:
            return False, f"Error validating symlink: {e}"
    
    def remove_symlink(self, link_path: str) -> bool:
        """
        Remove a symlink or directory safely.
        
        Args:
            link_path: Path to the symlink to remove
            
        Returns:
            bool: True if removal was successful
        """
        link_path_obj = Path(link_path)
        
        try:
            if link_path_obj.is_symlink():
                link_path_obj.unlink()
                logger.info(f"Removed symlink: {link_path}")
                return True
            elif link_path_obj.is_dir():
                # Remove directory (including non-empty directories)
                if self.is_windows:
                    # On Windows, use rmdir /S for recursive removal
                    subprocess.run(["rmdir", "/S", "/Q", str(link_path_obj)], shell=True, check=True)
                else:
                    # On Unix, use rm -rf for recursive removal
                    subprocess.run(["rm", "-rf", str(link_path_obj)], check=True)
                logger.info(f"Removed directory: {link_path}")
                return True
            elif link_path_obj.exists():
                link_path_obj.unlink()
                logger.info(f"Removed file: {link_path}")
                return True
            else:
                logger.debug(f"Path does not exist, nothing to remove: {link_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove {link_path}: {e}")
            return False
    
    def cleanup_broken_symlinks(self, directory: str) -> int:
        """
        Clean up broken symlinks in a directory.
        
        Args:
            directory: Directory to scan for broken symlinks
            
        Returns:
            int: Number of broken symlinks removed
        """
        directory_path = Path(directory)
        if not directory_path.exists():
            return 0
        
        removed_count = 0
        for item in directory_path.iterdir():
            if item.is_symlink() and not item.exists():
                try:
                    item.unlink()
                    logger.info(f"Removed broken symlink: {item}")
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Failed to remove broken symlink {item}: {e}")
        
        return removed_count


def create_asset_symlink(force: bool = True) -> bool:
    """
    Create the main asset symlink from crates/oldtimes-client/assets to ../../assets.
    
    Args:
        force: Whether to remove existing symlinks before creating new ones
        
    Returns:
        bool: True if symlink was created successfully
        
    Raises:
        SymlinkError: If symlink creation fails
    """
    manager = SymlinkManager()
    
    # Define paths relative to project root
    link_path = "crates/oldtimes-client/assets"
    
    # Resolve absolute paths for validation
    project_root = Path.cwd()
    abs_target = (project_root / "assets").resolve()
    abs_link = (project_root / link_path).resolve()
    
    logger.info(f"Creating asset symlink: {abs_link} -> {abs_target}")
    
    return manager.create_symlink(str(abs_target), link_path, force=force)


def validate_asset_symlink() -> Tuple[bool, Optional[str]]:
    """
    Validate the main asset symlink.
    
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, target_path or error_message)
    """
    manager = SymlinkManager()
    link_path = "crates/oldtimes-client/assets"
    
    return manager.validate_symlink(link_path)