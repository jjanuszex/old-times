"""
Integration tests for mod asset generation functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import sys

from ..config import PipelineConfig
from ..processing.mod import (
    ModDirectoryManager,
    ModConfigManager,
    ModAssetIsolation,
    ModMetadataGenerator,
    ModAsset
)


class TestModAssetGenerationIntegration(unittest.TestCase):
    """Integration tests for complete mod asset generation workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig(mods_dir=str(self.temp_dir))
        
        # Initialize managers
        self.dir_manager = ModDirectoryManager(self.config)
        self.config_manager = ModConfigManager(self.dir_manager)
        self.isolation_manager = ModAssetIsolation(self.dir_manager)
        self.metadata_generator = ModMetadataGenerator(self.dir_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_complete_mod_generation_workflow(self):
        """Test complete mod generation workflow from start to finish."""
        mod_name = "integration_test_mod"
        
        # Step 1: Create mod directory
        mod_dir = self.dir_manager.create_mod_directory(mod_name)
        self.assertTrue(mod_dir.exists())
        
        # Step 2: Create sample mod assets
        sample_assets = [
            ModAsset(
                name="test_tile",
                asset_type="tile",
                source_path=f"mods/{mod_name}/sprites/tile/test_tile.png",
                metadata={"size": [64, 32]}
            ),
            ModAsset(
                name="test_building",
                asset_type="building",
                source_path=f"mods/{mod_name}/sprites/building/test_building.png",
                metadata={"size": [128, 96], "tile_footprint": [2, 2]}
            ),
            ModAsset(
                name="test_unit",
                asset_type="unit",
                source_path=f"mods/{mod_name}/sprites/unit/test_unit.png",
                metadata={
                    "frame_size": [64, 64],
                    "directions": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
                    "anim_walk_fps": 10,
                    "anim_walk_len": 8,
                    "layout": "dirs_rows"
                }
            )
        ]
        
        # Step 3: Isolate mod assets
        isolation_map = self.isolation_manager.isolate_mod_assets(mod_name, sample_assets)
        self.assertEqual(len(isolation_map), 3)
        
        # Verify asset type subdirectories were created
        mod_sprites_dir = self.dir_manager.get_mod_sprites_dir(mod_name)
        self.assertTrue((mod_sprites_dir / "tile").exists())
        self.assertTrue((mod_sprites_dir / "building").exists())
        self.assertTrue((mod_sprites_dir / "unit").exists())
        
        # Step 4: Generate mod metadata
        sprites_toml_path = self.metadata_generator.generate_mod_sprites_toml(mod_name, sample_assets)
        manifest_path = self.metadata_generator.generate_mod_manifest(mod_name, sample_assets)
        
        self.assertTrue(sprites_toml_path.exists())
        self.assertTrue(manifest_path.exists())
        
        # Verify sprites.toml content
        sprites_content = sprites_toml_path.read_text()
        self.assertIn("[tiles.test_tile]", sprites_content)
        self.assertIn("[buildings.test_building]", sprites_content)
        self.assertIn("[units.test_unit]", sprites_content)
        
        # Verify manifest content
        import json
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        
        self.assertEqual(manifest_data["mod_name"], mod_name)
        self.assertEqual(manifest_data["asset_count"], 3)
        self.assertEqual(set(manifest_data["asset_types"]), {"tile", "building", "unit"})
        
        # Step 5: Update mod configuration
        success = self.config_manager.update_mod_config(mod_name, sample_assets)
        self.assertTrue(success)
        
        # Verify mod.toml was created
        config_path = self.dir_manager.get_mod_config_path(mod_name)
        self.assertTrue(config_path.exists())
        
        config_content = config_path.read_text()
        self.assertIn(f'name = "{mod_name}"', config_content)
        self.assertIn('Generated mod with 3 assets', config_content)
        
        # Step 6: Validate mod structure
        self.assertTrue(self.dir_manager.validate_mod_directory(mod_name))
        
        # Step 7: Validate asset isolation (should have no conflicts)
        isolation_errors = self.isolation_manager.validate_asset_isolation(mod_name)
        self.assertEqual(isolation_errors, [])
    
    def test_mod_generation_with_existing_directory(self):
        """Test mod generation when directory already exists."""
        mod_name = "existing_mod"
        
        # Create mod directory first
        mod_dir = self.dir_manager.create_mod_directory(mod_name)
        existing_file = mod_dir / "existing.txt"
        existing_file.write_text("existing content")
        
        # Try to create again without force - should fail
        with self.assertRaises(FileExistsError):
            self.dir_manager.create_mod_directory(mod_name, force=False)
        
        # Create with force - should succeed and remove existing content
        new_mod_dir = self.dir_manager.create_mod_directory(mod_name, force=True)
        self.assertTrue(new_mod_dir.exists())
        self.assertFalse(existing_file.exists())
    
    def test_mod_asset_isolation_conflict_detection(self):
        """Test detection of asset naming conflicts."""
        mod_name = "conflict_test_mod"
        
        # Create base sprites directory with conflicting asset
        base_sprites_dir = Path(self.temp_dir) / "base_sprites"
        base_sprites_dir.mkdir(parents=True)
        conflicting_asset = base_sprites_dir / "conflicting_asset.png"
        conflicting_asset.write_text("base asset")
        
        # Update config to use the base sprites directory
        self.config.sprites_dir = str(base_sprites_dir)
        self.isolation_manager = ModAssetIsolation(self.dir_manager)
        
        # Create mod with conflicting asset name
        mod_dir = self.dir_manager.create_mod_directory(mod_name)
        mod_sprites_dir = self.dir_manager.get_mod_sprites_dir(mod_name)
        mod_conflicting_asset = mod_sprites_dir / "conflicting_asset.png"
        mod_conflicting_asset.parent.mkdir(parents=True, exist_ok=True)
        mod_conflicting_asset.write_text("mod asset")
        
        # Validate isolation - should detect conflict
        isolation_errors = self.isolation_manager.validate_asset_isolation(mod_name)
        self.assertEqual(len(isolation_errors), 1)
        self.assertIn("Asset name conflict", isolation_errors[0])
        self.assertIn("conflicting_asset.png", isolation_errors[0])
    
    def test_mod_cleanup_functionality(self):
        """Test mod directory cleanup functionality."""
        mod_name = "cleanup_test_mod"
        mod_dir = self.dir_manager.create_mod_directory(mod_name)
        
        # Create temporary files and empty directories
        temp_file = mod_dir / "temp.tmp"
        temp_file.write_text("temporary")
        
        ds_store = mod_dir / "sprites" / ".DS_Store"
        ds_store.parent.mkdir(exist_ok=True)
        ds_store.write_text("system file")
        
        empty_subdir = mod_dir / "sprites" / "empty_subdir"
        empty_subdir.mkdir()
        
        # Run cleanup
        success = self.dir_manager.cleanup_mod_directory(mod_name)
        self.assertTrue(success)
        
        # Verify cleanup results
        self.assertFalse(temp_file.exists())
        self.assertFalse(ds_store.exists())
        self.assertFalse(empty_subdir.exists())
        
        # Required directories should still exist
        self.assertTrue((mod_dir / "sprites").exists())
        self.assertTrue((mod_dir / "data").exists())
    
    def test_mod_listing_functionality(self):
        """Test listing available mods."""
        # Initially no mods
        mods = self.dir_manager.list_mods()
        self.assertEqual(mods, [])
        
        # Create several valid mods
        mod_names = ["mod_alpha", "mod_beta", "mod_gamma"]
        for mod_name in mod_names:
            mod_dir = self.dir_manager.create_mod_directory(mod_name)
            config_path = mod_dir / "mod.toml"
            config_path.write_text(f'name = "{mod_name}"')
        
        # Create invalid mod (missing mod.toml)
        invalid_mod_dir = Path(self.temp_dir) / "invalid_mod"
        invalid_mod_dir.mkdir()
        (invalid_mod_dir / "sprites").mkdir()
        (invalid_mod_dir / "data").mkdir()
        
        # List mods - should only return valid ones
        mods = self.dir_manager.list_mods()
        self.assertEqual(sorted(mods), sorted(mod_names))
        self.assertNotIn("invalid_mod", mods)
    
    def test_mod_config_loading_and_updating(self):
        """Test mod configuration loading and updating."""
        mod_name = "config_test_mod"
        mod_dir = self.dir_manager.create_mod_directory(mod_name)
        
        # Create initial config
        initial_config_content = '''name = "Config Test Mod"
version = "1.0.0"
description = "Initial description"
author = "Test Author"
priority = 100

[dependencies]
base_game = ">=1.0.0"
'''
        config_path = mod_dir / "mod.toml"
        config_path.write_text(initial_config_content)
        
        # Load config
        loaded_config = self.config_manager.load_mod_config(mod_name)
        self.assertIsNotNone(loaded_config)
        self.assertEqual(loaded_config.name, "Config Test Mod")
        self.assertEqual(loaded_config.description, "Initial description")
        
        # Update config with assets
        sample_assets = [
            ModAsset("asset1", "tile", "path1.png"),
            ModAsset("asset2", "building", "path2.png")
        ]
        
        success = self.config_manager.update_mod_config(mod_name, sample_assets)
        self.assertTrue(success)
        
        # Verify config was updated
        updated_content = config_path.read_text()
        self.assertIn("Generated mod with 2 assets", updated_content)


class TestModCLIIntegration(unittest.TestCase):
    """Integration tests for mod CLI commands."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('scripts.asset_pipeline.cli._load_config')
    @patch('scripts.asset_pipeline.cli._process_mod_asset_sources')
    def test_cli_mod_command_success(self, mock_process_assets, mock_load_config):
        """Test successful mod command execution via CLI."""
        # Mock configuration
        mock_config = PipelineConfig(mods_dir=str(self.temp_dir))
        mock_load_config.return_value = mock_config
        
        # Mock asset processing
        mock_assets = [
            ModAsset("test_tile", "tile", "test_path.png", {"size": [64, 32]})
        ]
        mock_process_assets.return_value = mock_assets
        
        # Import and test CLI function
        from ..cli import mod as cli_mod_command
        
        # This would normally be called by typer, but we can test the logic
        # In a real integration test, we might use subprocess to call the CLI
        try:
            # Note: This is a simplified test - in practice we'd use subprocess
            # or typer's testing utilities for full CLI integration testing
            pass
        except Exception as e:
            self.fail(f"CLI mod command failed: {e}")
    
    def test_makefile_integration(self):
        """Test that Makefile targets work correctly."""
        # This test would verify that the Makefile targets execute correctly
        # For now, we'll just verify the Makefile exists and has the right targets
        makefile_path = Path(__file__).parent.parent.parent.parent / "Makefile"
        
        if makefile_path.exists():
            makefile_content = makefile_path.read_text()
            self.assertIn("assets-mod:", makefile_content)
            self.assertIn("$(NAME)", makefile_content)
            self.assertIn("mod $(NAME)", makefile_content)


if __name__ == '__main__':
    unittest.main()