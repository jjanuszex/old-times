"""
Tests for atlas generation system functionality.
"""

import unittest
import tempfile
import os
import json
from PIL import Image

from ..processing.atlas import (
    AtlasConfig, AtlasGenerator, UnitSpec, AtlasResult, AtlasGenerationError
)


class TestAtlasResult(unittest.TestCase):
    """Test AtlasResult class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.atlas = Image.new('RGBA', (100, 100), (255, 0, 0, 255))
        self.frame_map = {
            "frame1": {"x": 0, "y": 0, "w": 50, "h": 50},
            "frame2": {"x": 50, "y": 50, "w": 50, "h": 50}
        }
        self.result = AtlasResult(self.atlas, self.frame_map, {"test": "metadata"})
    
    def test_save_atlas(self):
        """Test saving atlas image."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            try:
                self.result.save_atlas(f.name)
                self.assertTrue(os.path.exists(f.name))
                
                # Verify image can be loaded
                loaded = Image.open(f.name)
                self.assertEqual(loaded.size, (100, 100))
            finally:
                os.unlink(f.name)
    
    def test_save_frame_map_json(self):
        """Test saving frame map as JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            try:
                self.result.save_frame_map(f.name, format="json")
                self.assertTrue(os.path.exists(f.name))
                
                # Verify JSON content
                with open(f.name, 'r') as rf:
                    data = json.load(rf)
                
                self.assertIn("frames", data)
                self.assertIn("meta", data)
                self.assertEqual(data["frames"], self.frame_map)
                self.assertEqual(data["meta"]["size"]["w"], 100)
                self.assertEqual(data["meta"]["size"]["h"], 100)
            finally:
                os.unlink(f.name)
    
    def test_save_frame_map_toml(self):
        """Test saving frame map as TOML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            try:
                self.result.save_frame_map(f.name, format="toml")
                self.assertTrue(os.path.exists(f.name))
                
                # Verify TOML content structure
                with open(f.name, 'r') as rf:
                    content = rf.read()
                
                self.assertIn("[meta]", content)
                self.assertIn("[frames.", content)
                self.assertIn("x = 0", content)
                self.assertIn("y = 0", content)
            finally:
                os.unlink(f.name)


class TestAtlasGenerator(unittest.TestCase):
    """Test AtlasGenerator class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(padding=0, power_of_two=False)
        self.generator = AtlasGenerator(self.config)
    
    def test_create_unit_atlas_success(self):
        """Test successful unit atlas creation."""
        # Create test frames
        frames = []
        for i in range(64):  # 8 directions * 8 frames
            frame = Image.new('RGBA', (64, 64), (i * 4, 0, 0, 255))
            frames.append(frame)
        
        spec = UnitSpec("test_unit", directions=8, frames_per_direction=8)
        
        result = self.generator.create_unit_atlas(frames, spec)
        
        self.assertIsInstance(result, AtlasResult)
        self.assertEqual(result.atlas.size, (512, 512))
        self.assertEqual(len(result.frame_map), 64)
        
        # Check metadata
        self.assertEqual(result.metadata["unit_name"], "test_unit")
        self.assertEqual(result.metadata["directions"], 8)
        self.assertEqual(result.metadata["frames_per_direction"], 8)
        self.assertIn("layout_efficiency", result.metadata)
        
        # Check frame map structure
        self.assertIn("walk_N_0", result.frame_map)
        self.assertIn("walk_S_7", result.frame_map)
        
        # Verify frame positions
        first_frame = result.frame_map["walk_N_0"]
        self.assertEqual(first_frame["x"], 0)
        self.assertEqual(first_frame["y"], 0)
        self.assertEqual(first_frame["w"], 64)
        self.assertEqual(first_frame["h"], 64)
        
        last_frame = result.frame_map["walk_NW_7"]
        self.assertEqual(last_frame["x"], 7 * 64)  # 7th frame
        self.assertEqual(last_frame["y"], 7 * 64)  # 7th direction (NW)
    
    def test_create_unit_atlas_wrong_frame_count(self):
        """Test unit atlas creation with wrong frame count."""
        frames = [Image.new('RGBA', (64, 64), (255, 0, 0, 255)) for _ in range(32)]
        spec = UnitSpec("test_unit", directions=8, frames_per_direction=8)
        
        with self.assertRaises(AtlasGenerationError) as context:
            self.generator.create_unit_atlas(frames, spec)
        
        self.assertIn("Expected 64 frames, got 32", str(context.exception))
    
    def test_create_unit_atlas_size_limit_exceeded(self):
        """Test unit atlas creation exceeding size limits."""
        config = AtlasConfig(max_size=(256, 256))
        generator = AtlasGenerator(config)
        
        frames = [Image.new('RGBA', (64, 64), (255, 0, 0, 255)) for _ in range(64)]
        spec = UnitSpec("test_unit", directions=8, frames_per_direction=8)
        
        with self.assertRaises(AtlasGenerationError) as context:
            generator.create_unit_atlas(frames, spec)
        
        self.assertIn("exceeds maximum", str(context.exception))
    
    def test_create_worker_atlas_success(self):
        """Test successful worker atlas creation."""
        # Create test frames
        frames = []
        for i in range(64):
            frame = Image.new('RGBA', (64, 64), (i * 4, 100, 0, 255))
            frames.append(frame)
        
        result = self.generator.create_worker_atlas(frames, "test_worker")
        
        self.assertIsInstance(result, AtlasResult)
        self.assertEqual(result.atlas.size, (512, 512))
        self.assertEqual(len(result.frame_map), 64)
        
        # Check worker-specific metadata
        self.assertEqual(result.metadata["unit_name"], "test_worker")
        self.assertEqual(result.metadata["atlas_type"], "worker_animation")
        self.assertEqual(result.metadata["target_size"], (512, 512))
        self.assertEqual(result.metadata["frame_layout"], "8x8_grid")
        self.assertEqual(result.metadata["animation_type"], "walking")
    
    def test_create_worker_atlas_wrong_frame_count(self):
        """Test worker atlas creation with wrong frame count."""
        frames = [Image.new('RGBA', (64, 64), (255, 0, 0, 255)) for _ in range(32)]
        
        with self.assertRaises(AtlasGenerationError) as context:
            self.generator.create_worker_atlas(frames)
        
        self.assertIn("requires exactly 64 frames", str(context.exception))
    
    def test_create_worker_atlas_wrong_frame_size(self):
        """Test worker atlas creation with wrong frame size."""
        frames = [Image.new('RGBA', (32, 32), (255, 0, 0, 255)) for _ in range(64)]
        
        with self.assertRaises(AtlasGenerationError) as context:
            self.generator.create_worker_atlas(frames)
        
        self.assertIn("expected (64, 64)", str(context.exception))
    
    def test_create_sprite_atlas_success(self):
        """Test successful sprite atlas creation."""
        sprites = [
            ("sprite1", Image.new('RGBA', (32, 32), (255, 0, 0, 255))),
            ("sprite2", Image.new('RGBA', (64, 32), (0, 255, 0, 255))),
            ("sprite3", Image.new('RGBA', (32, 64), (0, 0, 255, 255))),
        ]
        
        result = self.generator.create_sprite_atlas(sprites)
        
        self.assertIsInstance(result, AtlasResult)
        self.assertGreater(result.atlas.width, 0)
        self.assertGreater(result.atlas.height, 0)
        self.assertEqual(len(result.frame_map), 3)
        
        # Check all sprites are in frame map
        for name, _ in sprites:
            self.assertIn(name, result.frame_map)
        
        # Check metadata
        self.assertEqual(result.metadata["sprite_count"], 3)
        self.assertIn("layout_efficiency", result.metadata)
    
    def test_create_sprite_atlas_empty(self):
        """Test sprite atlas creation with no sprites."""
        with self.assertRaises(AtlasGenerationError) as context:
            self.generator.create_sprite_atlas([])
        
        self.assertIn("No sprites provided", str(context.exception))
    
    def test_generate_placeholder_frames(self):
        """Test placeholder frame generation."""
        frames = self.generator.generate_placeholder_frames(5, (32, 32))
        
        self.assertEqual(len(frames), 5)
        
        for frame in frames:
            self.assertEqual(frame.size, (32, 32))
            self.assertEqual(frame.mode, 'RGBA')
            
            # Check that frame has some content (not completely transparent)
            pixels = list(frame.getdata())
            non_transparent = [p for p in pixels if p[3] > 0]
            self.assertGreater(len(non_transparent), 0)
    
    def test_generate_placeholder_frames_default_size(self):
        """Test placeholder frame generation with default size."""
        frames = self.generator.generate_placeholder_frames(3)
        
        self.assertEqual(len(frames), 3)
        
        for frame in frames:
            self.assertEqual(frame.size, (64, 64))


class TestAtlasGeneratorWithPadding(unittest.TestCase):
    """Test AtlasGenerator with padding configuration."""
    
    def setUp(self):
        """Set up test fixtures with padding."""
        self.config = AtlasConfig(padding=2, power_of_two=False)
        self.generator = AtlasGenerator(self.config)
    
    def test_create_unit_atlas_with_padding(self):
        """Test unit atlas creation with padding."""
        frames = [Image.new('RGBA', (32, 32), (255, 0, 0, 255)) for _ in range(4)]
        spec = UnitSpec("test_unit", directions=2, frames_per_direction=2, frame_size=(32, 32))
        
        result = self.generator.create_unit_atlas(frames, spec)
        
        # With padding: 2 frames * 32px + 1 padding = 66px
        self.assertEqual(result.atlas.size, (66, 66))
        
        # Check frame positions account for padding
        frame_1_0 = result.frame_map["walk_N_1"]
        self.assertEqual(frame_1_0["x"], 34)  # 32 + 2 padding
        self.assertEqual(frame_1_0["y"], 0)


class TestAtlasGeneratorPowerOfTwo(unittest.TestCase):
    """Test AtlasGenerator with power of two configuration."""
    
    def setUp(self):
        """Set up test fixtures with power of two."""
        self.config = AtlasConfig(padding=0, power_of_two=True)
        self.generator = AtlasGenerator(self.config)
    
    def test_create_unit_atlas_power_of_two(self):
        """Test unit atlas creation with power of two constraint."""
        frames = [Image.new('RGBA', (50, 50), (255, 0, 0, 255)) for _ in range(9)]
        spec = UnitSpec("test_unit", directions=3, frames_per_direction=3, frame_size=(50, 50))
        
        result = self.generator.create_unit_atlas(frames, spec)
        
        # Original would be 150x150, next power of two is 256x256
        self.assertEqual(result.atlas.size, (256, 256))


if __name__ == '__main__':
    unittest.main()