"""
Unit tests for symlink utilities.
"""

import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from asset_pipeline.utils.symlink import (
    SymlinkManager,
    SymlinkError,
    create_asset_symlink,
    validate_asset_symlink
)


class TestSymlinkManager(unittest.TestCase):
    """Test cases for SymlinkManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = SymlinkManager()
        self.temp_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.temp_dir) / "target"
        self.link_dir = Path(self.temp_dir) / "link"
        
        # Create target directory
        self.target_dir.mkdir()
        (self.target_dir / "test_file.txt").write_text("test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_detect_platform(self):
        """Test platform detection."""
        platform_name = self.manager.detect_platform()
        self.assertIn(platform_name, ["windows", "unix", "unknown"])
        
        # Test specific platform detection
        with patch('platform.system', return_value='Windows'):
            manager = SymlinkManager()
            self.assertEqual(manager.detect_platform(), "windows")
            self.assertTrue(manager.is_windows)
            self.assertFalse(manager.is_unix)
        
        with patch('platform.system', return_value='Linux'):
            manager = SymlinkManager()
            self.assertEqual(manager.detect_platform(), "unix")
            self.assertFalse(manager.is_windows)
            self.assertTrue(manager.is_unix)
        
        with patch('platform.system', return_value='Darwin'):
            manager = SymlinkManager()
            self.assertEqual(manager.detect_platform(), "unix")
            self.assertFalse(manager.is_windows)
            self.assertTrue(manager.is_unix)
    
    def test_create_symlink_target_not_exists(self):
        """Test symlink creation fails when target doesn't exist."""
        nonexistent_target = Path(self.temp_dir) / "nonexistent"
        
        with self.assertRaises(SymlinkError) as context:
            self.manager.create_symlink(str(nonexistent_target), str(self.link_dir))
        
        self.assertIn("Target path does not exist", str(context.exception))
    
    def test_create_symlink_link_exists_no_force(self):
        """Test symlink creation fails when link exists and force=False."""
        # Create existing file at link location
        self.link_dir.touch()
        
        with self.assertRaises(SymlinkError) as context:
            self.manager.create_symlink(str(self.target_dir), str(self.link_dir), force=False)
        
        self.assertIn("Link path already exists", str(context.exception))
    
    @patch('subprocess.run')
    def test_create_unix_symlink_success(self, mock_run):
        """Test successful Unix symlink creation."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.object(self.manager, 'is_unix', True), \
             patch.object(self.manager, 'is_windows', False):
            
            result = self.manager.create_symlink(str(self.target_dir), str(self.link_dir))
            
            self.assertTrue(result)
            mock_run.assert_called_once_with(
                ["ln", "-sf", str(self.target_dir.resolve()), str(self.link_dir)],
                capture_output=True,
                text=True,
                check=True
            )
    
    @patch('subprocess.run')
    def test_create_unix_symlink_failure(self, mock_run):
        """Test Unix symlink creation failure."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'ln', stderr='Permission denied')
        
        with patch.object(self.manager, 'is_unix', True), \
             patch.object(self.manager, 'is_windows', False):
            
            with self.assertRaises(SymlinkError) as context:
                self.manager.create_symlink(str(self.target_dir), str(self.link_dir))
            
            self.assertIn("ln command failed", str(context.exception))
    
    @patch('subprocess.run')
    def test_create_windows_symlink_success(self, mock_run):
        """Test successful Windows symlink creation."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.object(self.manager, 'is_windows', True), \
             patch.object(self.manager, 'is_unix', False):
            
            result = self.manager.create_symlink(str(self.target_dir), str(self.link_dir))
            
            self.assertTrue(result)
            mock_run.assert_called_once_with(
                ["mklink", "/D", str(self.link_dir), str(self.target_dir.resolve())],
                capture_output=True,
                text=True,
                shell=True,
                check=True
            )
    
    @patch('subprocess.run')
    def test_create_windows_symlink_failure(self, mock_run):
        """Test Windows symlink creation failure."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'mklink', stderr='Access denied')
        
        with patch.object(self.manager, 'is_windows', True), \
             patch.object(self.manager, 'is_unix', False):
            
            with self.assertRaises(SymlinkError) as context:
                self.manager.create_symlink(str(self.target_dir), str(self.link_dir))
            
            self.assertIn("mklink command failed", str(context.exception))
    
    def test_validate_symlink_not_exists(self):
        """Test validation of non-existent symlink."""
        nonexistent_link = Path(self.temp_dir) / "nonexistent_link"
        
        is_valid, message = self.manager.validate_symlink(str(nonexistent_link))
        
        self.assertFalse(is_valid)
        self.assertIn("Symlink does not exist", message)
    
    def test_validate_symlink_not_symlink(self):
        """Test validation of regular file (not symlink)."""
        regular_file = Path(self.temp_dir) / "regular_file.txt"
        regular_file.write_text("content")
        
        is_valid, message = self.manager.validate_symlink(str(regular_file))
        
        self.assertFalse(is_valid)
        self.assertIn("Path is not a symlink", message)
    
    def test_remove_symlink_not_exists(self):
        """Test removal of non-existent symlink."""
        nonexistent_link = Path(self.temp_dir) / "nonexistent_link"
        
        result = self.manager.remove_symlink(str(nonexistent_link))
        
        self.assertTrue(result)  # Should succeed (nothing to remove)
    
    def test_remove_regular_file(self):
        """Test removal of regular file."""
        regular_file = Path(self.temp_dir) / "regular_file.txt"
        regular_file.write_text("content")
        
        result = self.manager.remove_symlink(str(regular_file))
        
        self.assertTrue(result)
        self.assertFalse(regular_file.exists())
    
    def test_cleanup_broken_symlinks_empty_directory(self):
        """Test cleanup in directory with no broken symlinks."""
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()
        
        count = self.manager.cleanup_broken_symlinks(str(empty_dir))
        
        self.assertEqual(count, 0)
    
    def test_cleanup_broken_symlinks_nonexistent_directory(self):
        """Test cleanup in non-existent directory."""
        nonexistent_dir = Path(self.temp_dir) / "nonexistent"
        
        count = self.manager.cleanup_broken_symlinks(str(nonexistent_dir))
        
        self.assertEqual(count, 0)


class TestAssetSymlinkFunctions(unittest.TestCase):
    """Test cases for asset symlink convenience functions."""
    
    @patch('asset_pipeline.utils.symlink.SymlinkManager')
    @patch('pathlib.Path.cwd')
    def test_create_asset_symlink(self, mock_cwd, mock_manager_class):
        """Test create_asset_symlink function."""
        # Setup mocks
        mock_cwd.return_value = Path("/project/root")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.create_symlink.return_value = True
        
        # Call function
        result = create_asset_symlink(force=True)
        
        # Verify
        self.assertTrue(result)
        mock_manager.create_symlink.assert_called_once()
        args, kwargs = mock_manager.create_symlink.call_args
        self.assertTrue(args[0].endswith("assets"))  # target path
        self.assertTrue(args[1].endswith("crates/oldtimes-client/assets"))  # link path
        self.assertEqual(kwargs['force'], True)
    
    @patch('asset_pipeline.utils.symlink.SymlinkManager')
    def test_validate_asset_symlink(self, mock_manager_class):
        """Test validate_asset_symlink function."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.validate_symlink.return_value = (True, "/path/to/target")
        
        # Call function
        is_valid, target = validate_asset_symlink()
        
        # Verify
        self.assertTrue(is_valid)
        self.assertEqual(target, "/path/to/target")
        mock_manager.validate_symlink.assert_called_once_with("crates/oldtimes-client/assets")


if __name__ == '__main__':
    unittest.main()