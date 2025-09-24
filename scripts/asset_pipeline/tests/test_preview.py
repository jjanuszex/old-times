"""
Unit tests for preview generation functionality.
"""

import unittest
import tempfile
import os
from pathlib import Path
from PIL import Image
import json

from ..utils.preview import (
    PreviewGenerator, 
    AssetPreviewManager, 
    PreviewConfig, 
    AssetPreviewItem
)
from ..processing.preview import (
    PreviewProcessor,
    PreviewProcessorConfig,
    generate_asset_previews,
    generate_animation_previews
)


class TestPreviewConfig(unittest.TestCase):
    """Test preview configuration."""
    
    def test_default_config(self):
        """Test default preview configuration."""
        config = PreviewConfig()
        
        self.assertEqual(config.grid_cell_size, (96, 96))
        self.assertEqual(config.grid_padding, 4)
        self.assertTrue(config.show_isometric_grid)
        self.assertTrue(config.show_labels)
        self.assertEqual(config.max_grid_width, 10)


class TestAssetPreviewItem(unittest.TestCase):
    """Test asset preview item."""
    
    def test_create_preview_item(self):
        """Test creating asset preview item."""
        # Create test image
        image = Image.new('RGBA', (64, 32), (255, 0, 0, 255))
        
        item = AssetPreviewItem(
            name="test_tile",
            image=image,
            asset_type="tile",
            metadata={"size": [64, 32]}
        )
        
        self.assertEqual(item.name, "test_tile")
        self.assertEqual(item.asset_type, "tile")
        self.assertEqual(item.image.size, (64, 32))
        self.assertEqual(item.metadata["size"], [64, 32])


class TestPreviewGenerator(unittest.TestCase):
    """Test preview generator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PreviewConfig()
        self.generator = PreviewGenerator(self.config)
        
        # Create test assets
        self.test_assets = []
        
        # Tile asset
        tile_image = Image.new('RGBA', (64, 32), (0, 255, 0, 255))
        self.test_assets.append(AssetPreviewItem(
            name="grass",
            image=tile_image,
            asset_type="tile"
        ))
        
        # Building asset
        building_image = Image.new('RGBA', (128, 96), (0, 0, 255, 255))
        self.test_assets.append(AssetPreviewItem(
            name="lumberjack",
            image=building_image,
            asset_type="building"
        ))
        
        # Unit asset
        unit_image = Image.new('RGBA', (64, 64), (255, 255, 0, 255))
        self.test_assets.append(AssetPreviewItem(
            name="worker",
            image=unit_image,
            asset_type="unit"
        ))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_asset_grid_preview(self):
        """Test creating asset grid preview."""
        output_path = os.path.join(self.temp_dir, "grid_preview.png")
        
        success = self.generator.create_asset_grid_preview(self.test_assets, output_path)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify preview image
        preview = Image.open(output_path)
        self.assertGreater(preview.width, 0)
        self.assertGreater(preview.height, 0)
    
    def test_create_animation_contact_sheet(self):
        """Test creating animation contact sheet."""
        # Create test animation frames
        frames = []
        for i in range(64):  # 8 directions × 8 frames
            frame = Image.new('RGBA', (64, 64), (i * 4, 0, 0, 255))
            frames.append(frame)
        
        output_path = os.path.join(self.temp_dir, "contact_sheet.png")
        
        success = self.generator.create_animation_contact_sheet(
            frames, "worker_walk", output_path
        )
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify contact sheet dimensions
        contact_sheet = Image.open(output_path)
        expected_width = 8 * (64 + 2) - 2  # 8 frames with padding
        expected_height = 8 * (64 + 2) - 2 + 20  # 8 directions with padding + label space
        
        self.assertEqual(contact_sheet.width, expected_width)
        self.assertEqual(contact_sheet.height, expected_height)
    
    def test_create_isometric_alignment_preview(self):
        """Test creating isometric alignment preview."""
        output_path = os.path.join(self.temp_dir, "alignment_preview.png")
        
        success = self.generator.create_isometric_alignment_preview(
            self.test_assets, output_path
        )
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify preview has grid overlay
        preview = Image.open(output_path)
        self.assertGreater(preview.width, 0)
        self.assertGreater(preview.height, 0)
    
    def test_empty_assets_list(self):
        """Test handling empty assets list."""
        output_path = os.path.join(self.temp_dir, "empty_preview.png")
        
        success = self.generator.create_asset_grid_preview([], output_path)
        
        self.assertFalse(success)
        self.assertFalse(os.path.exists(output_path))
    
    def test_missing_frames(self):
        """Test handling missing animation frames."""
        # Create incomplete frame set
        frames = []
        for i in range(32):  # Only half the expected frames
            frame = Image.new('RGBA', (64, 64), (i * 8, 0, 0, 255))
            frames.append(frame)
        
        output_path = os.path.join(self.temp_dir, "incomplete_contact_sheet.png")
        
        success = self.generator.create_animation_contact_sheet(
            frames, "incomplete_walk", output_path
        )
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        
        # Should create placeholder frames for missing ones
        contact_sheet = Image.open(output_path)
        self.assertGreater(contact_sheet.width, 0)
        self.assertGreater(contact_sheet.height, 0)


class TestAssetPreviewManager(unittest.TestCase):
    """Test asset preview manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PreviewConfig()
        self.manager = AssetPreviewManager(self.config)
        
        # Create test assets directory structure
        self.assets_dir = os.path.join(self.temp_dir, "assets")
        self.sprites_dir = os.path.join(self.assets_dir, "sprites")
        os.makedirs(self.sprites_dir)
        
        # Create test sprite files
        self._create_test_sprite("grass.png", (64, 32), (0, 255, 0, 255))
        self._create_test_sprite("lumberjack.png", (128, 96), (0, 0, 255, 255))
        self._create_test_sprite("worker.png", (64, 64), (255, 255, 0, 255))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_sprite(self, filename: str, size: tuple, color: tuple):
        """Create a test sprite file."""
        image = Image.new('RGBA', size, color)
        image.save(os.path.join(self.sprites_dir, filename))
    
    def test_load_assets_from_directory(self):
        """Test loading assets from directory."""
        assets_by_type = self.manager.load_assets_from_directory(self.assets_dir)
        
        # Should have loaded assets of each type
        self.assertIn('tile', assets_by_type)
        self.assertIn('building', assets_by_type)
        self.assertIn('unit', assets_by_type)
        
        # Check tile assets
        tiles = assets_by_type['tile']
        self.assertEqual(len(tiles), 1)
        self.assertEqual(tiles[0].name, "grass")
        self.assertEqual(tiles[0].asset_type, "tile")
        
        # Check building assets
        buildings = assets_by_type['building']
        self.assertEqual(len(buildings), 1)
        self.assertEqual(buildings[0].name, "lumberjack")
        self.assertEqual(buildings[0].asset_type, "building")
        
        # Check unit assets
        units = assets_by_type['unit']
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].name, "worker")
        self.assertEqual(units[0].asset_type, "unit")
    
    def test_create_comprehensive_preview(self):
        """Test creating comprehensive preview."""
        assets_by_type = self.manager.load_assets_from_directory(self.assets_dir)
        output_dir = os.path.join(self.temp_dir, "previews")
        
        success = self.manager.create_comprehensive_preview(assets_by_type, output_dir)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_dir))
        
        # Check that preview files were created
        expected_files = [
            "tile_preview.png",
            "building_preview.png", 
            "unit_preview.png",
            "asset_preview.png",
            "tile_alignment.png",
            "building_alignment.png"
        ]
        
        for filename in expected_files:
            filepath = os.path.join(output_dir, filename)
            self.assertTrue(os.path.exists(filepath), f"Missing preview file: {filename}")
    
    def test_create_animation_previews(self):
        """Test creating animation previews."""
        # Create test animations
        animations = {}
        
        # Worker animation
        worker_frames = []
        for i in range(64):
            frame = Image.new('RGBA', (64, 64), (i * 4, 0, 0, 255))
            worker_frames.append(frame)
        animations["worker"] = worker_frames
        
        output_dir = os.path.join(self.temp_dir, "animation_previews")
        
        success = self.manager.create_animation_previews(animations, output_dir)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_dir))
        
        # Check that contact sheet was created
        contact_sheet_path = os.path.join(output_dir, "worker_contact_sheet.png")
        self.assertTrue(os.path.exists(contact_sheet_path))
    
    def test_determine_asset_type(self):
        """Test asset type determination."""
        # Test tile size
        self.assertEqual(self.manager._determine_asset_type("grass", (64, 32)), "tile")
        
        # Test unit size (square)
        self.assertEqual(self.manager._determine_asset_type("worker", (64, 64)), "unit")
        
        # Test building by name
        self.assertEqual(self.manager._determine_asset_type("mill", (128, 96)), "building")
        
        # Test building by size
        self.assertEqual(self.manager._determine_asset_type("custom", (128, 96)), "building")


class TestPreviewProcessor(unittest.TestCase):
    """Test preview processor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "previews")
        
        self.config = PreviewProcessorConfig(output_dir=self.output_dir)
        self.processor = PreviewProcessor(self.config)
        
        # Create test assets directory
        self.assets_dir = os.path.join(self.temp_dir, "assets")
        self.sprites_dir = os.path.join(self.assets_dir, "sprites")
        os.makedirs(self.sprites_dir)
        
        # Create test sprite
        image = Image.new('RGBA', (64, 32), (0, 255, 0, 255))
        image.save(os.path.join(self.sprites_dir, "grass.png"))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_assets_preview(self):
        """Test processing assets preview."""
        success = self.processor.process_assets_preview(self.assets_dir)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.output_dir))
        
        # Check that preview was created
        preview_path = os.path.join(self.output_dir, "asset_preview.png")
        self.assertTrue(os.path.exists(preview_path))
    
    def test_process_animation_previews(self):
        """Test processing animation previews."""
        # Create test animations
        animations = {}
        frames = []
        for i in range(8):
            frame = Image.new('RGBA', (64, 64), (i * 32, 0, 0, 255))
            frames.append(frame)
        animations["test_anim"] = frames
        
        success = self.processor.process_animation_previews(animations)
        
        self.assertTrue(success)
        
        # Check that contact sheet was created
        contact_sheet_path = os.path.join(self.output_dir, "test_anim_contact_sheet.png")
        self.assertTrue(os.path.exists(contact_sheet_path))
    
    def test_create_atlas_preview(self):
        """Test creating atlas preview."""
        # Create test atlas
        atlas = Image.new('RGBA', (512, 512), (128, 128, 128, 255))
        atlas_path = os.path.join(self.temp_dir, "test_atlas.png")
        atlas.save(atlas_path)
        
        # Create test frame map
        frame_map = {
            "frames": {
                "walk_N_0": {"x": 0, "y": 0, "w": 64, "h": 64},
                "walk_N_1": {"x": 64, "y": 0, "w": 64, "h": 64},
                "walk_E_0": {"x": 0, "y": 64, "w": 64, "h": 64},
                "walk_E_1": {"x": 64, "y": 64, "w": 64, "h": 64}
            }
        }
        
        success = self.processor.create_atlas_preview(atlas_path, frame_map, "test_unit")
        
        self.assertTrue(success)
        
        # Check that atlas preview was created
        preview_path = os.path.join(self.output_dir, "test_unit_atlas_preview.png")
        self.assertTrue(os.path.exists(preview_path))
    
    def test_cleanup_old_previews(self):
        """Test cleaning up old previews."""
        # Create some old preview files
        os.makedirs(self.output_dir, exist_ok=True)
        old_preview = os.path.join(self.output_dir, "old_preview.png")
        Image.new('RGBA', (100, 100), (255, 0, 0, 255)).save(old_preview)
        
        self.assertTrue(os.path.exists(old_preview))
        
        success = self.processor.cleanup_old_previews()
        
        self.assertTrue(success)
        self.assertFalse(os.path.exists(old_preview))


class TestPreviewConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for preview generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test assets directory
        self.assets_dir = os.path.join(self.temp_dir, "assets")
        self.sprites_dir = os.path.join(self.assets_dir, "sprites")
        os.makedirs(self.sprites_dir)
        
        # Create test sprite
        image = Image.new('RGBA', (64, 32), (0, 255, 0, 255))
        image.save(os.path.join(self.sprites_dir, "grass.png"))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_asset_previews(self):
        """Test generate_asset_previews convenience function."""
        output_dir = os.path.join(self.temp_dir, "previews")
        
        success = generate_asset_previews(self.assets_dir, output_dir)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_dir))
        
        # Check that preview was created
        preview_path = os.path.join(output_dir, "asset_preview.png")
        self.assertTrue(os.path.exists(preview_path))
    
    def test_generate_animation_previews(self):
        """Test generate_animation_previews convenience function."""
        # Create test animations
        animations = {}
        frames = []
        for i in range(8):
            frame = Image.new('RGBA', (64, 64), (i * 32, 0, 0, 255))
            frames.append(frame)
        animations["test_anim"] = frames
        
        output_dir = os.path.join(self.temp_dir, "animation_previews")
        
        success = generate_animation_previews(animations, output_dir)
        
        self.assertTrue(success)
        
        # Check that contact sheet was created
        contact_sheet_path = os.path.join(output_dir, "test_anim_contact_sheet.png")
        self.assertTrue(os.path.exists(contact_sheet_path))


if __name__ == '__main__':
    unittest.main()