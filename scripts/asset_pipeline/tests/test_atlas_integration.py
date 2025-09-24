"""
Integration tests for complete atlas workflow.
"""

import unittest
import tempfile
import os
import json
from PIL import Image

from ..processing.atlas import (
    AtlasConfig, AtlasGenerator, AtlasValidator, UnitSpec, AtlasGenerationError
)


class TestAtlasIntegration(unittest.TestCase):
    """Integration tests for complete atlas workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(padding=0, power_of_two=False)
        self.generator = AtlasGenerator(self.config)
        self.validator = AtlasValidator(self.config)
    
    def test_complete_worker_atlas_workflow(self):
        """Test complete workflow for worker atlas generation and validation."""
        # Step 1: Create test frames
        frames = []
        for direction in range(8):
            for frame in range(8):
                # Create unique colored frame for each position
                color = (direction * 32, frame * 32, 100, 255)
                image = Image.new('RGBA', (64, 64), color)
                frames.append(image)
        
        # Step 2: Generate worker atlas
        atlas_result = self.generator.create_worker_atlas(frames, "integration_worker")
        
        # Step 3: Validate atlas
        errors = self.validator.validate_worker_atlas(atlas_result)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
        
        # Step 4: Verify atlas properties
        self.assertEqual(atlas_result.atlas.size, (512, 512))
        self.assertEqual(len(atlas_result.frame_map), 64)
        self.assertEqual(atlas_result.metadata["atlas_type"], "worker_animation")
        
        # Step 5: Verify frame layout
        direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        for direction_idx in range(8):
            for frame_idx in range(8):
                direction_name = direction_names[direction_idx]
                frame_name = f"walk_{direction_name}_{frame_idx}"
                
                self.assertIn(frame_name, atlas_result.frame_map)
                
                frame_data = atlas_result.frame_map[frame_name]
                expected_x = frame_idx * 64
                expected_y = direction_idx * 64
                
                self.assertEqual(frame_data["x"], expected_x)
                self.assertEqual(frame_data["y"], expected_y)
                self.assertEqual(frame_data["w"], 64)
                self.assertEqual(frame_data["h"], 64)
    
    def test_complete_unit_atlas_workflow_with_validation(self):
        """Test complete workflow for unit atlas with comprehensive validation."""
        # Step 1: Create test frames for smaller unit (4 directions, 4 frames each)
        frames = []
        for i in range(16):  # 4 * 4
            color = (i * 16, 100, 200, 255)
            image = Image.new('RGBA', (32, 32), color)
            frames.append(image)
        
        spec = UnitSpec("integration_unit", directions=4, frames_per_direction=4, frame_size=(32, 32))
        
        # Step 2: Generate unit atlas
        atlas_result = self.generator.create_unit_atlas(frames, spec)
        
        # Step 3: Comprehensive validation
        errors = self.validator.validate_complete_atlas_workflow(atlas_result, spec)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
        
        # Step 4: Verify atlas properties
        self.assertEqual(atlas_result.atlas.size, (128, 128))  # 4 * 32 = 128
        self.assertEqual(len(atlas_result.frame_map), 16)
        self.assertEqual(atlas_result.metadata["unit_name"], "integration_unit")
        
        # Step 5: Verify layout efficiency is calculated
        self.assertIn("layout_efficiency", atlas_result.metadata)
        self.assertGreater(atlas_result.metadata["layout_efficiency"], 0)
    
    def test_atlas_with_padding_workflow(self):
        """Test atlas generation with padding configuration."""
        config = AtlasConfig(padding=2, power_of_two=False)
        generator = AtlasGenerator(config)
        validator = AtlasValidator(config)
        
        # Create test frames
        frames = []
        for i in range(4):  # 2 directions, 2 frames each
            color = (i * 64, 128, 64, 255)
            image = Image.new('RGBA', (64, 64), color)
            frames.append(image)
        
        spec = UnitSpec("padded_unit", directions=2, frames_per_direction=2, frame_size=(64, 64))
        
        # Generate atlas with padding
        atlas_result = generator.create_unit_atlas(frames, spec)
        
        # Validate with padding-aware validator
        errors = validator.validate_complete_atlas_workflow(atlas_result, spec)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
        
        # Verify padding is applied
        # Expected size: 2 frames * 64px + 1 padding = 130px
        self.assertEqual(atlas_result.atlas.size, (130, 130))
        
        # Verify frame positions account for padding
        frame_1_0 = atlas_result.frame_map["walk_N_1"]
        self.assertEqual(frame_1_0["x"], 66)  # 64 + 2 padding
        self.assertEqual(frame_1_0["y"], 0)
    
    def test_atlas_with_power_of_two_workflow(self):
        """Test atlas generation with power of two constraint."""
        config = AtlasConfig(padding=0, power_of_two=True)
        generator = AtlasGenerator(config)
        validator = AtlasValidator(config)
        
        # Create test frames that will result in non-power-of-two size
        frames = []
        for i in range(9):  # 3 directions, 3 frames each
            color = (i * 28, 200, 100, 255)
            image = Image.new('RGBA', (50, 50), color)
            frames.append(image)
        
        spec = UnitSpec("power_unit", directions=3, frames_per_direction=3, frame_size=(50, 50))
        
        # Generate atlas with power of two constraint
        atlas_result = generator.create_unit_atlas(frames, spec)
        
        # Validate with power of two validator
        errors = validator.validate_complete_atlas_workflow(atlas_result, spec)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
        
        # Verify size is power of two
        # Original would be 150x150, next power of two is 256x256
        self.assertEqual(atlas_result.atlas.size, (256, 256))
        
        # Verify dimensions are power of two
        width, height = atlas_result.atlas.size
        self.assertTrue(validator._is_power_of_two(width))
        self.assertTrue(validator._is_power_of_two(height))
    
    def test_atlas_save_and_load_workflow(self):
        """Test complete workflow including saving and loading atlas files."""
        # Create test frames
        frames = []
        for i in range(8):  # 2 directions, 4 frames each
            color = (i * 32, 150, 75, 255)
            image = Image.new('RGBA', (64, 64), color)
            frames.append(image)
        
        spec = UnitSpec("save_test_unit", directions=2, frames_per_direction=4)
        
        # Generate atlas
        atlas_result = self.generator.create_unit_atlas(frames, spec)
        
        # Validate before saving
        errors = self.validator.validate_complete_atlas_workflow(atlas_result, spec)
        self.assertEqual(len(errors), 0)
        
        # Test saving to temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            atlas_path = os.path.join(temp_dir, "test_atlas.png")
            json_path = os.path.join(temp_dir, "test_atlas.json")
            toml_path = os.path.join(temp_dir, "test_atlas.toml")
            
            # Save atlas and frame maps
            atlas_result.save_atlas(atlas_path)
            atlas_result.save_frame_map(json_path, format="json")
            atlas_result.save_frame_map(toml_path, format="toml")
            
            # Verify files exist
            self.assertTrue(os.path.exists(atlas_path))
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(toml_path))
            
            # Verify atlas can be loaded
            loaded_atlas = Image.open(atlas_path)
            self.assertEqual(loaded_atlas.size, atlas_result.atlas.size)
            
            # Verify JSON frame map can be loaded
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            self.assertIn("frames", json_data)
            self.assertIn("meta", json_data)
            self.assertEqual(len(json_data["frames"]), len(atlas_result.frame_map))
            
            # Verify TOML frame map exists and has content
            with open(toml_path, 'r') as f:
                toml_content = f.read()
            
            self.assertIn("[meta]", toml_content)
            self.assertIn("[frames.", toml_content)
    
    def test_placeholder_frame_generation_workflow(self):
        """Test workflow with placeholder frame generation."""
        # Generate placeholder frames
        placeholder_frames = self.generator.generate_placeholder_frames(16, (64, 64))
        
        self.assertEqual(len(placeholder_frames), 16)
        
        # Use placeholder frames in atlas generation
        spec = UnitSpec("placeholder_unit", directions=4, frames_per_direction=4)
        atlas_result = self.generator.create_unit_atlas(placeholder_frames, spec)
        
        # Validate atlas with placeholder frames
        errors = self.validator.validate_complete_atlas_workflow(atlas_result, spec)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
        
        # Verify atlas properties
        self.assertEqual(atlas_result.atlas.size, (256, 256))  # 4 * 64 = 256
        self.assertEqual(len(atlas_result.frame_map), 16)
    
    def test_sprite_atlas_workflow(self):
        """Test complete workflow for sprite atlas generation."""
        # Create test sprites of different sizes
        sprites = [
            ("small_sprite", Image.new('RGBA', (32, 32), (255, 0, 0, 255))),
            ("medium_sprite", Image.new('RGBA', (64, 48), (0, 255, 0, 255))),
            ("large_sprite", Image.new('RGBA', (96, 64), (0, 0, 255, 255))),
            ("tall_sprite", Image.new('RGBA', (32, 96), (255, 255, 0, 255))),
        ]
        
        # Generate sprite atlas
        atlas_result = self.generator.create_sprite_atlas(sprites)
        
        # Basic validation
        self.assertGreater(atlas_result.atlas.width, 0)
        self.assertGreater(atlas_result.atlas.height, 0)
        self.assertEqual(len(atlas_result.frame_map), 4)
        
        # Verify all sprites are in frame map
        for name, _ in sprites:
            self.assertIn(name, atlas_result.frame_map)
        
        # Verify layout efficiency is calculated
        self.assertIn("layout_efficiency", atlas_result.metadata)
        self.assertGreater(atlas_result.metadata["layout_efficiency"], 0)
    
    def test_error_handling_workflow(self):
        """Test error handling in complete workflow."""
        # Test with wrong frame count
        frames = [Image.new('RGBA', (64, 64), (255, 0, 0, 255)) for _ in range(10)]
        spec = UnitSpec("error_unit", directions=4, frames_per_direction=4)  # Expects 16 frames
        
        with self.assertRaises(AtlasGenerationError) as context:
            self.generator.create_unit_atlas(frames, spec)
        
        self.assertIn("Expected 16 frames, got 10", str(context.exception))
        
        # Test with size limit exceeded
        config = AtlasConfig(max_size=(128, 128))
        generator = AtlasGenerator(config)
        
        large_frames = [Image.new('RGBA', (64, 64), (255, 0, 0, 255)) for _ in range(16)]
        large_spec = UnitSpec("large_unit", directions=4, frames_per_direction=4)
        
        with self.assertRaises(AtlasGenerationError) as context:
            generator.create_unit_atlas(large_frames, large_spec)
        
        self.assertIn("exceeds maximum", str(context.exception))


if __name__ == '__main__':
    unittest.main()