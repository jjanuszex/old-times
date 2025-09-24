"""
Unit tests for mod directory management functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from ..config import PipelineConfig
from ..processing.mod import (
    ModDirectoryManager,
    ModConfigManager,
    ModAssetIsolation,
    ModMetadataGenerator,
    ModConfig,
    ModAsset
)


class TestModDirectoryManager(unittest.TestCase):
    """Test mod directory creation and management."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig(mods_dir=str(self.temp_dir))
        self.manager = ModDirectoryManager(self.config)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_mod_directory(self):
        """Test creating a new mod directory."""
        mod_name = "test_mod"
        mod_dir = self.manager.create_mod_directory(mod_name)
        
        # Check that directory was created
        self.assertTrue(mod_dir.exists())
        self.assertEqual(mod_dir.name, mod_name)
        
        # Check required subdirectories
        required_dirs = ["sprites", "atlases", "data", "config"]
        for req_dir in required_dirs:
            self.assertTrue((mod_dir / req_dir).exists())
    
    def test_create_mod_directory_exists_no_force(self):
        """Test creating mod directory when it already exists without force."""
        mod_name = "existing_mod"
        mod_dir = Path(self.temp_dir) / mod_name
        mod_dir.mkdir()
        
        with self.assertRaises(FileExistsError):
            self.manager.create_mod_directory(mod_name, force=False)
    
    def test_create_mod_directory_exists_with_force(self):
        """Test creating mod directory when it already exists with force."""
        mod_name = "existing_mod"
        mod_dir = Path(self.temp_dir) / mod_name
        mod_dir.mkdir()
        
        # Create a file in the existing directory
        test_file = mod_dir / "test.txt"
        test_file.write_text("test content")
        
        # Create with force should succeed and remove existing content
        result_dir = self.manager.create_mod_directory(mod_name, force=True)
        
        self.assertTrue(result_dir.exists())
        self.assertFalse(test_file.exists())
        
        # Check required subdirectories were created
        required_dirs = ["sprites", "atlases", "data", "config"]
        for req_dir in required_dirs:
            self.assertTrue((result_dir / req_dir).exists())
    
    def test_validate_mod_directory_valid(self):
        """Test validating a properly structured mod directory."""
        mod_name = "valid_mod"
        mod_dir = self.manager.create_mod_directory(mod_name)
        
        # Create mod.toml file
        (mod_dir / "mod.toml").write_text('name = "Valid Mod"')
        
        self.assertTrue(self.manager.validate_mod_directory(mod_name))
    
    def test_validate_mod_directory_missing_dirs(self):
        """Test validating mod directory with missing required directories."""
        mod_name = "invalid_mod"
        mod_dir = Path(self.temp_dir) / mod_name
        mod_dir.mkdir()
        
        # Create mod.toml but missing required directories
        (mod_dir / "mod.toml").write_text('name = "Invalid Mod"')
        
        self.assertFalse(self.manager.validate_mod_directory(mod_name))
    
    def test_validate_mod_directory_missing_config(self):
        """Test validating mod directory without mod.toml."""
        mod_name = "no_config_mod"
        mod_dir = self.manager.create_mod_directory(mod_name)
        
        # Don't create mod.toml file
        self.assertFalse(self.manager.validate_mod_directory(mod_name))
    
    def test_validate_mod_directory_nonexistent(self):
        """Test validating non-existent mod directory."""
        self.assertFalse(self.manager.validate_mod_directory("nonexistent_mod"))
    
    def test_get_mod_paths(self):
        """Test getting various mod directory paths."""
        mod_name = "path_test_mod"
        
        config_path = self.manager.get_mod_config_path(mod_name)
        sprites_dir = self.manager.get_mod_sprites_dir(mod_name)
        atlases_dir = self.manager.get_mod_atlases_dir(mod_name)
        data_dir = self.manager.get_mod_data_dir(mod_name)
        
        expected_base = Path(self.temp_dir) / mod_name
        self.assertEqual(config_path, expected_base / "mod.toml")
        self.assertEqual(sprites_dir, expected_base / "sprites")
        self.assertEqual(atlases_dir, expected_base / "atlases")
        self.assertEqual(data_dir, expected_base / "data")
    
    def test_list_mods_empty(self):
        """Test listing mods when no mods exist."""
        mods = self.manager.list_mods()
        self.assertEqual(mods, [])
    
    def test_list_mods_with_valid_mods(self):
        """Test listing mods with valid mod directories."""
        mod_names = ["mod_a", "mod_b", "mod_c"]
        
        for mod_name in mod_names:
            mod_dir = self.manager.create_mod_directory(mod_name)
            (mod_dir / "mod.toml").write_text(f'name = "{mod_name}"')
        
        mods = self.manager.list_mods()
        self.assertEqual(sorted(mods), sorted(mod_names))
    
    def test_list_mods_with_invalid_mods(self):
        """Test listing mods ignores invalid mod directories."""
        # Create valid mod
        valid_mod = "valid_mod"
        mod_dir = self.manager.create_mod_directory(valid_mod)
        (mod_dir / "mod.toml").write_text(f'name = "{valid_mod}"')
        
        # Create invalid mod (missing mod.toml)
        invalid_mod_dir = Path(self.temp_dir) / "invalid_mod"
        invalid_mod_dir.mkdir()
        (invalid_mod_dir / "sprites").mkdir()
        (invalid_mod_dir / "data").mkdir()
        
        mods = self.manager.list_mods()
        self.assertEqual(mods, [valid_mod])
    
    def test_cleanup_mod_directory(self):
        """Test cleaning up mod directory."""
        mod_name = "cleanup_test_mod"
        mod_dir = self.manager.create_mod_directory(mod_name)
        
        # Create some temporary files and empty directories
        temp_file = mod_dir / "temp.tmp"
        temp_file.write_text("temporary")
        
        empty_dir = mod_dir / "empty_subdir"
        empty_dir.mkdir()
        
        ds_store = mod_dir / ".DS_Store"
        ds_store.write_text("system file")
        
        # Cleanup should succeed
        self.assertTrue(self.manager.cleanup_mod_directory(mod_name))
        
        # Temporary files should be removed
        self.assertFalse(temp_file.exists())
        self.assertFalse(ds_store.exists())
        
        # Empty directory should be removed
        self.assertFalse(empty_dir.exists())
        
        # Required directories should still exist
        self.assertTrue((mod_dir / "sprites").exists())
        self.assertTrue((mod_dir / "data").exists())
    
    def test_cleanup_nonexistent_mod(self):
        """Test cleaning up non-existent mod directory."""
        self.assertFalse(self.manager.cleanup_mod_directory("nonexistent_mod"))


class TestModConfigManager(unittest.TestCase):
    """Test mod configuration management."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig(mods_dir=str(self.temp_dir))
        self.dir_manager = ModDirectoryManager(self.config)
        self.config_manager = ModConfigManager(self.dir_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_mod_config(self):
        """Test creating mod configuration file."""
        mod_name = "config_test_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        mod_config = ModConfig(
            name="Test Mod",
            version="2.0.0",
            description="A test mod",
            author="Test Author",
            priority=200
        )
        
        config_path = self.config_manager.create_mod_config(mod_name, mod_config)
        
        # Check that file was created
        self.assertTrue(config_path.exists())
        
        # Check content
        content = config_path.read_text()
        self.assertIn('name = "Test Mod"', content)
        self.assertIn('version = "2.0.0"', content)
        self.assertIn('description = "A test mod"', content)
        self.assertIn('author = "Test Author"', content)
        self.assertIn('priority = 200', content)
    
    def test_load_mod_config_success(self):
        """Test loading mod configuration successfully."""
        mod_name = "load_test_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        # Create a real TOML config file
        config_path = self.dir_manager.get_mod_config_path(mod_name)
        toml_content = '''name = "Loaded Mod"
version = "1.5.0"
description = "A loaded mod"
author = "Loaded Author"
priority = 150

[dependencies]
base_game = ">=1.0.0"
other_mod = ">=2.0.0"
'''
        config_path.write_text(toml_content)
        
        loaded_config = self.config_manager.load_mod_config(mod_name)
        
        self.assertIsNotNone(loaded_config)
        self.assertEqual(loaded_config.name, 'Loaded Mod')
        self.assertEqual(loaded_config.version, '1.5.0')
        self.assertEqual(loaded_config.description, 'A loaded mod')
        self.assertEqual(loaded_config.author, 'Loaded Author')
        self.assertEqual(loaded_config.priority, 150)
        self.assertEqual(loaded_config.dependencies, {'base_game': '>=1.0.0', 'other_mod': '>=2.0.0'})
    
    def test_load_mod_config_missing_file(self):
        """Test loading mod configuration when file doesn't exist."""
        loaded_config = self.config_manager.load_mod_config("nonexistent_mod")
        self.assertIsNone(loaded_config)
    
    @patch('scripts.asset_pipeline.processing.mod.tomllib', None)
    def test_load_mod_config_no_tomllib(self):
        """Test loading mod configuration when tomllib is not available."""
        mod_name = "no_tomllib_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        # Create a dummy config file
        config_path = self.dir_manager.get_mod_config_path(mod_name)
        config_path.write_text("dummy content")
        
        loaded_config = self.config_manager.load_mod_config(mod_name)
        self.assertIsNone(loaded_config)
    
    def test_update_mod_config_new_config(self):
        """Test updating mod configuration when no existing config."""
        mod_name = "update_test_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        assets = [
            ModAsset("tile1", "tile", "sprites/tile1.png"),
            ModAsset("building1", "building", "sprites/building1.png")
        ]
        
        success = self.config_manager.update_mod_config(mod_name, assets)
        self.assertTrue(success)
        
        # Check that config file was created
        config_path = self.dir_manager.get_mod_config_path(mod_name)
        self.assertTrue(config_path.exists())
        
        content = config_path.read_text()
        self.assertIn(f'name = "{mod_name}"', content)
        self.assertIn('Generated mod with 2 assets', content)
    
    def test_generate_mod_toml(self):
        """Test generating TOML content."""
        config = ModConfig(
            name="TOML Test Mod",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            priority=100,
            dependencies={"base_game": ">=1.0.0", "dep_mod": ">=2.0.0"}
        )
        
        toml_content = self.config_manager._generate_mod_toml(config)
        
        expected_lines = [
            'name = "TOML Test Mod"',
            'version = "1.0.0"',
            'description = "Test description"',
            'author = "Test Author"',
            'priority = 100',
            '[dependencies]',
            'base_game = ">=1.0.0"',
            'dep_mod = ">=2.0.0"'
        ]
        
        for line in expected_lines:
            self.assertIn(line, toml_content)


class TestModAssetIsolation(unittest.TestCase):
    """Test mod asset isolation functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig(
            mods_dir=str(self.temp_dir),
            sprites_dir=str(Path(self.temp_dir) / "base_sprites")
        )
        self.dir_manager = ModDirectoryManager(self.config)
        self.isolation = ModAssetIsolation(self.dir_manager)
        
        # Create base sprites directory
        Path(self.config.sprites_dir).mkdir(parents=True)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_isolate_mod_assets(self):
        """Test isolating mod assets."""
        mod_name = "isolation_test_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        assets = [
            ModAsset("tile1", "tile", "original/tile1.png"),
            ModAsset("building1", "building", "original/building1.png"),
            ModAsset("unit1", "unit", "original/unit1.png")
        ]
        
        isolation_map = self.isolation.isolate_mod_assets(mod_name, assets)
        
        # Check that isolation map was created
        self.assertEqual(len(isolation_map), 3)
        
        # Check that paths are properly isolated
        for original_path, isolated_path in isolation_map.items():
            self.assertIn(mod_name, isolated_path)
            self.assertIn("sprites", isolated_path)
        
        # Check that asset type subdirectories were created
        mod_sprites_dir = self.dir_manager.get_mod_sprites_dir(mod_name)
        self.assertTrue((mod_sprites_dir / "tile").exists())
        self.assertTrue((mod_sprites_dir / "building").exists())
        self.assertTrue((mod_sprites_dir / "unit").exists())
    
    def test_validate_asset_isolation_no_conflicts(self):
        """Test validating asset isolation with no conflicts."""
        mod_name = "no_conflict_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        # Create mod asset that doesn't conflict
        mod_sprites_dir = self.dir_manager.get_mod_sprites_dir(mod_name)
        mod_asset = mod_sprites_dir / "unique_asset.png"
        mod_asset.parent.mkdir(parents=True, exist_ok=True)
        mod_asset.write_text("mod asset")
        
        errors = self.isolation.validate_asset_isolation(mod_name)
        self.assertEqual(errors, [])
    
    def test_validate_asset_isolation_with_conflicts(self):
        """Test validating asset isolation with naming conflicts."""
        mod_name = "conflict_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        # Create conflicting assets
        base_sprites_dir = Path(self.config.sprites_dir)
        base_asset = base_sprites_dir / "conflicting_asset.png"
        base_asset.write_text("base asset")
        
        mod_sprites_dir = self.dir_manager.get_mod_sprites_dir(mod_name)
        mod_asset = mod_sprites_dir / "conflicting_asset.png"
        mod_asset.parent.mkdir(parents=True, exist_ok=True)
        mod_asset.write_text("mod asset")
        
        errors = self.isolation.validate_asset_isolation(mod_name)
        self.assertEqual(len(errors), 1)
        self.assertIn("Asset name conflict", errors[0])
        self.assertIn("conflicting_asset.png", errors[0])
    
    def test_validate_asset_isolation_missing_directory(self):
        """Test validating asset isolation when mod sprites directory doesn't exist."""
        mod_name = "missing_dir_mod"
        # Don't create mod directory
        
        errors = self.isolation.validate_asset_isolation(mod_name)
        self.assertEqual(len(errors), 1)
        self.assertIn("Mod sprites directory does not exist", errors[0])


class TestModMetadataGenerator(unittest.TestCase):
    """Test mod metadata generation."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig(mods_dir=str(self.temp_dir))
        self.dir_manager = ModDirectoryManager(self.config)
        self.metadata_gen = ModMetadataGenerator(self.dir_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_mod_sprites_toml(self):
        """Test generating mod sprites.toml file."""
        mod_name = "metadata_test_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        assets = [
            ModAsset("tile1", "tile", "sprites/tile1.png", {"size": [64, 32]}),
            ModAsset("building1", "building", "sprites/building1.png", {"size": [128, 96], "tile_footprint": [2, 2]})
        ]
        
        sprites_toml_path = self.metadata_gen.generate_mod_sprites_toml(mod_name, assets)
        
        # Check that file was created in correct location
        expected_path = self.dir_manager.get_mod_data_dir(mod_name) / "sprites.toml"
        self.assertEqual(sprites_toml_path, expected_path)
        self.assertTrue(sprites_toml_path.exists())
        
        # Check that content was written correctly
        content = sprites_toml_path.read_text()
        
        # Verify content contains expected sections
        self.assertIn("[tiles]", content)
        self.assertIn("[tiles.tile1]", content)
        self.assertIn('kind = "tile"', content)
        self.assertIn('size = [64, 32]', content)
        self.assertIn('source = "sprites/tile1.png"', content)
        
        self.assertIn("[buildings]", content)
        self.assertIn("[buildings.building1]", content)
        self.assertIn('kind = "building"', content)
        self.assertIn('size = [128, 96]', content)
        self.assertIn('source = "sprites/building1.png"', content)
        self.assertIn('tile_footprint = [2, 2]', content)
    
    def test_generate_mod_manifest(self):
        """Test generating mod manifest.json file."""
        mod_name = "manifest_test_mod"
        self.dir_manager.create_mod_directory(mod_name)
        
        assets = [
            ModAsset("tile1", "tile", "sprites/tile1.png", {"size": [64, 32]}),
            ModAsset("tile2", "tile", "sprites/tile2.png", {"size": [64, 32]}),
            ModAsset("building1", "building", "sprites/building1.png", {"size": [128, 96]})
        ]
        
        manifest_path = self.metadata_gen.generate_mod_manifest(mod_name, assets)
        
        # Check that file was created in correct location
        expected_path = self.dir_manager.get_mod_data_dir(mod_name) / "manifest.json"
        self.assertEqual(manifest_path, expected_path)
        self.assertTrue(manifest_path.exists())
        
        # Check manifest content
        import json
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        
        self.assertEqual(manifest_data["mod_name"], mod_name)
        self.assertEqual(manifest_data["asset_count"], 3)
        self.assertEqual(set(manifest_data["asset_types"]), {"tile", "building"})
        self.assertEqual(manifest_data["version"], "1.0.0")
        
        # Check asset grouping
        self.assertEqual(len(manifest_data["assets"]["tile"]), 2)
        self.assertEqual(len(manifest_data["assets"]["building"]), 1)


if __name__ == '__main__':
    unittest.main()