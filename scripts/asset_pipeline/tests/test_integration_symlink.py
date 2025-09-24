"""
Integration tests for symlink functionality.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from asset_pipeline.utils.symlink import create_asset_symlink, validate_asset_symlink


class TestSymlinkIntegration(unittest.TestCase):
    """Integration tests for symlink functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        
        # Create mock project structure
        self.assets_dir = Path("assets")
        self.client_dir = Path("crates/oldtimes-client")
        self.client_assets_dir = self.client_dir / "assets"
        
        # Create directories
        self.assets_dir.mkdir()
        self.client_dir.mkdir(parents=True)
        
        # Create some test files in assets
        (self.assets_dir / "test_sprite.png").write_text("fake image data")
        (self.assets_dir / "sprites").mkdir()
        (self.assets_dir / "sprites" / "grass.png").write_text("grass sprite")
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_and_validate_symlink(self):
        """Test creating and validating asset symlink."""
        # Create symlink
        result = create_asset_symlink(force=True)
        self.assertTrue(result)
        
        # Verify symlink exists
        self.assertTrue(self.client_assets_dir.is_symlink())
        
        # Validate symlink
        is_valid, target = validate_asset_symlink()
        self.assertTrue(is_valid)
        self.assertTrue(target.endswith("assets"))
        
        # Verify we can access files through symlink
        symlink_sprite = self.client_assets_dir / "sprites" / "grass.png"
        self.assertTrue(symlink_sprite.exists())
        self.assertEqual(symlink_sprite.read_text(), "grass sprite")
    
    def test_create_symlink_with_existing_directory(self):
        """Test creating symlink when target directory already exists."""
        # Create existing directory with content
        self.client_assets_dir.mkdir()
        (self.client_assets_dir / "existing_file.txt").write_text("existing content")
        
        # Create symlink with force=True (should succeed)
        result = create_asset_symlink(force=True)
        self.assertTrue(result)
        
        # Verify symlink was created
        self.assertTrue(self.client_assets_dir.is_symlink())
        
        # Verify old content is gone and new content is accessible
        self.assertFalse((self.client_assets_dir / "existing_file.txt").exists())
        self.assertTrue((self.client_assets_dir / "test_sprite.png").exists())
    
    def test_create_symlink_no_force_with_existing(self):
        """Test creating symlink fails when target exists and force=False."""
        # Create existing directory
        self.client_assets_dir.mkdir()
        
        # Try to create symlink with force=False (should fail)
        with self.assertRaises(Exception):
            create_asset_symlink(force=False)
        
        # Verify directory still exists and is not a symlink
        self.assertTrue(self.client_assets_dir.exists())
        self.assertFalse(self.client_assets_dir.is_symlink())


if __name__ == '__main__':
    unittest.main()