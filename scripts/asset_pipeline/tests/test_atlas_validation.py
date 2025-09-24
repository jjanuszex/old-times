"""
Tests for atlas validation functionality.
"""

import unittest
from PIL import Image

from ..processing.atlas import (
    AtlasConfig, AtlasValidator, AtlasResult, UnitSpec, AtlasGenerator
)


class TestAtlasValidator(unittest.TestCase):
    """Test AtlasValidator class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(padding=0, power_of_two=False, max_size=(1024, 1024))
        self.validator = AtlasValidator(self.config)
    
    def test_validate_atlas_dimensions_valid(self):
        """Test validation of valid atlas dimensions."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        errors = self.validator.validate_atlas_dimensions(atlas)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_atlas_dimensions_none(self):
        """Test validation of None atlas."""
        errors = self.validator.validate_atlas_dimensions(None)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("Atlas image is None", errors[0])
    
    def test_validate_atlas_dimensions_invalid_size(self):
        """Test validation of invalid atlas dimensions."""
        atlas = Image.new('RGBA', (0, 0), (0, 0, 0, 0))
        
        errors = self.validator.validate_atlas_dimensions(atlas)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid dimensions", errors[0])
    
    def test_validate_atlas_dimensions_exceeds_max(self):
        """Test validation of atlas exceeding maximum size."""
        atlas = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))
        
        errors = self.validator.validate_atlas_dimensions(atlas)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("exceeds maximum", errors[0])
    
    def test_validate_atlas_dimensions_expected_size_mismatch(self):
        """Test validation with expected size mismatch."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        errors = self.validator.validate_atlas_dimensions(atlas, expected_size=(256, 256))
        
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match expected", errors[0])
    
    def test_validate_atlas_dimensions_power_of_two(self):
        """Test validation with power of two constraint."""
        config = AtlasConfig(power_of_two=True)
        validator = AtlasValidator(config)
        atlas = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
        
        errors = validator.validate_atlas_dimensions(atlas)
        
        self.assertEqual(len(errors), 2)  # Both width and height not power of two
        self.assertTrue(any("not a power of two" in error for error in errors))
    
    def test_validate_frame_boundaries_valid(self):
        """Test validation of valid frame boundaries."""
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        frame_map = {
            "frame1": {"x": 0, "y": 0, "w": 64, "h": 64},
            "frame2": {"x": 64, "y": 64, "w": 64, "h": 64}
        }
        
        errors = self.validator.validate_frame_boundaries(atlas, frame_map)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_frame_boundaries_none_inputs(self):
        """Test validation with None inputs."""
        errors = self.validator.validate_frame_boundaries(None, {})
        
        self.assertEqual(len(errors), 1)
        self.assertIn("Atlas or frame map is None", errors[0])
    
    def test_validate_frame_boundaries_negative_coordinates(self):
        """Test validation of negative frame coordinates."""
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        frame_map = {
            "frame1": {"x": -10, "y": 0, "w": 64, "h": 64}
        }
        
        errors = self.validator.validate_frame_boundaries(atlas, frame_map)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("negative coordinates", errors[0])
    
    def test_validate_frame_boundaries_invalid_dimensions(self):
        """Test validation of invalid frame dimensions."""
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        frame_map = {
            "frame1": {"x": 0, "y": 0, "w": 0, "h": 64}
        }
        
        errors = self.validator.validate_frame_boundaries(atlas, frame_map)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid dimensions", errors[0])
    
    def test_validate_frame_boundaries_extends_beyond_atlas(self):
        """Test validation of frames extending beyond atlas."""
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        frame_map = {
            "frame1": {"x": 100, "y": 100, "w": 64, "h": 64}
        }
        
        errors = self.validator.validate_frame_boundaries(atlas, frame_map)
        
        self.assertEqual(len(errors), 2)  # Both width and height extend beyond
        self.assertTrue(any("extends beyond atlas width" in error for error in errors))
        self.assertTrue(any("extends beyond atlas height" in error for error in errors))
    
    def test_validate_frame_boundaries_missing_coordinates(self):
        """Test validation with missing frame coordinates."""
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        frame_map = {
            "frame1": {"x": 0, "y": 0, "w": 64}  # Missing 'h'
        }
        
        errors = self.validator.validate_frame_boundaries(atlas, frame_map)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("missing required coordinate", errors[0])
    
    def test_validate_frame_content_valid(self):
        """Test validation of valid frame content."""
        # Create atlas with some content
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        # Add some non-transparent content
        for x in range(32):
            for y in range(32):
                atlas.putpixel((x, y), (255, 0, 0, 255))
        
        frame_map = {
            "frame1": {"x": 0, "y": 0, "w": 64, "h": 64}
        }
        
        errors = self.validator.validate_frame_content(atlas, frame_map)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_frame_content_completely_transparent(self):
        """Test validation of completely transparent frame."""
        atlas = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        frame_map = {
            "frame1": {"x": 0, "y": 0, "w": 64, "h": 64}
        }
        
        errors = self.validator.validate_frame_content(atlas, frame_map)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("completely transparent", errors[0])
    
    def test_validate_atlas_metadata_consistency_valid(self):
        """Test validation of consistent atlas metadata."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        # Create complete frame map for 2 directions, 8 frames each
        frame_map = {}
        direction_names = ["N", "NE"]  # First 2 directions
        for direction_idx, direction_name in enumerate(direction_names):
            for frame_idx in range(8):
                frame_name = f"walk_{direction_name}_{frame_idx}"
                frame_map[frame_name] = {
                    "x": frame_idx * 64,
                    "y": direction_idx * 64,
                    "w": 64,
                    "h": 64
                }
        
        metadata = {
            "unit_name": "test_unit",
            "size": [512, 512]
        }
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        spec = UnitSpec("test_unit", directions=2, frames_per_direction=8)
        
        errors = self.validator.validate_atlas_metadata_consistency(atlas_result, spec)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_atlas_metadata_consistency_size_mismatch(self):
        """Test validation with atlas size mismatch."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {}
        metadata = {"size": [256, 256]}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        
        errors = self.validator.validate_atlas_metadata_consistency(atlas_result)
        
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match metadata size", errors[0])
    
    def test_validate_atlas_metadata_consistency_frame_count_mismatch(self):
        """Test validation with frame count mismatch."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {"frame1": {"x": 0, "y": 0, "w": 64, "h": 64}}
        metadata = {"unit_name": "test_unit"}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        spec = UnitSpec("test_unit", directions=8, frames_per_direction=8)
        
        errors = self.validator.validate_atlas_metadata_consistency(atlas_result, spec)
        
        # Should have frame count error plus missing frame errors
        self.assertGreater(len(errors), 1)
        frame_count_errors = [e for e in errors if "Frame count 1 does not match expected 64" in e]
        self.assertEqual(len(frame_count_errors), 1)
    
    def test_validate_atlas_metadata_consistency_missing_frames(self):
        """Test validation with missing expected frames."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {"walk_N_0": {"x": 0, "y": 0, "w": 64, "h": 64}}
        metadata = {"unit_name": "test_unit"}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        spec = UnitSpec("test_unit", directions=2, frames_per_direction=2)
        
        errors = self.validator.validate_atlas_metadata_consistency(atlas_result, spec)
        
        # Should have errors for missing frames
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Missing expected frame" in error for error in errors))
    
    def test_validate_worker_atlas_valid(self):
        """Test validation of valid worker atlas."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {}
        
        # Create 64 frames (8x8)
        direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        for direction_idx in range(8):
            for frame_idx in range(8):
                direction_name = direction_names[direction_idx]
                frame_name = f"walk_{direction_name}_{frame_idx}"
                frame_map[frame_name] = {
                    "x": frame_idx * 64,
                    "y": direction_idx * 64,
                    "w": 64,
                    "h": 64
                }
        
        metadata = {
            "atlas_type": "worker_animation",
            "target_size": (512, 512),
            "frame_layout": "8x8_grid",
            "animation_type": "walking"
        }
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        
        errors = self.validator.validate_worker_atlas(atlas_result)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_worker_atlas_wrong_size(self):
        """Test validation of worker atlas with wrong size."""
        atlas = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        frame_map = {}
        metadata = {}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        
        errors = self.validator.validate_worker_atlas(atlas_result)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("is not 512x512" in error for error in errors))
    
    def test_validate_worker_atlas_wrong_frame_count(self):
        """Test validation of worker atlas with wrong frame count."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {"frame1": {"x": 0, "y": 0, "w": 64, "h": 64}}
        metadata = {}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        
        errors = self.validator.validate_worker_atlas(atlas_result)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("expected 64" in error for error in errors))
    
    def test_validate_worker_atlas_wrong_frame_size(self):
        """Test validation of worker atlas with wrong frame size."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {"frame1": {"x": 0, "y": 0, "w": 32, "h": 32}}
        metadata = {}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        
        errors = self.validator.validate_worker_atlas(atlas_result)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("is not 64x64" in error for error in errors))
    
    def test_validate_worker_atlas_missing_metadata(self):
        """Test validation of worker atlas with missing metadata."""
        atlas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        frame_map = {}
        metadata = {}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        
        errors = self.validator.validate_worker_atlas(atlas_result)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Missing worker metadata" in error for error in errors))
    
    def test_validate_complete_atlas_workflow_success(self):
        """Test complete atlas workflow validation with success."""
        # Create a valid atlas using the generator
        config = AtlasConfig(padding=0, power_of_two=False)
        generator = AtlasGenerator(config)
        validator = AtlasValidator(config)
        
        # Create test frames
        frames = []
        for i in range(16):  # 2 directions * 8 frames
            frame = Image.new('RGBA', (64, 64), (i * 16, 0, 0, 255))
            frames.append(frame)
        
        spec = UnitSpec("test_unit", directions=2, frames_per_direction=8)
        atlas_result = generator.create_unit_atlas(frames, spec)
        
        errors = validator.validate_complete_atlas_workflow(atlas_result, spec)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_complete_atlas_workflow_with_errors(self):
        """Test complete atlas workflow validation with errors."""
        # Create an invalid atlas
        atlas = Image.new('RGBA', (100, 100), (0, 0, 0, 0))  # Wrong size
        frame_map = {
            "walk_N_0": {"x": 0, "y": 0, "w": 64, "h": 64},
            "walk_N_1": {"x": 150, "y": 0, "w": 64, "h": 64}  # Extends beyond atlas
        }
        metadata = {"unit_name": "test_unit"}
        
        atlas_result = AtlasResult(atlas, frame_map, metadata)
        spec = UnitSpec("test_unit", directions=2, frames_per_direction=8)
        
        errors = self.validator.validate_complete_atlas_workflow(atlas_result, spec)
        
        self.assertGreater(len(errors), 0)
        # Should have multiple types of errors
        error_text = " ".join(errors)
        self.assertIn("extends beyond", error_text)
        self.assertIn("Frame count", error_text)
    
    def test_is_power_of_two(self):
        """Test power of two checking."""
        self.assertTrue(self.validator._is_power_of_two(1))
        self.assertTrue(self.validator._is_power_of_two(2))
        self.assertTrue(self.validator._is_power_of_two(4))
        self.assertTrue(self.validator._is_power_of_two(8))
        self.assertTrue(self.validator._is_power_of_two(256))
        self.assertTrue(self.validator._is_power_of_two(1024))
        
        self.assertFalse(self.validator._is_power_of_two(0))
        self.assertFalse(self.validator._is_power_of_two(3))
        self.assertFalse(self.validator._is_power_of_two(5))
        self.assertFalse(self.validator._is_power_of_two(100))
    
    def test_is_completely_transparent(self):
        """Test transparent image detection."""
        # Completely transparent image
        transparent = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        self.assertTrue(self.validator._is_completely_transparent(transparent))
        
        # Image with some opaque pixels
        semi_transparent = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        semi_transparent.putpixel((10, 10), (255, 0, 0, 255))
        self.assertFalse(self.validator._is_completely_transparent(semi_transparent))
        
        # RGB image (no alpha channel)
        rgb_image = Image.new('RGB', (64, 64), (255, 0, 0))
        self.assertFalse(self.validator._is_completely_transparent(rgb_image))


class TestAtlasValidatorIntegration(unittest.TestCase):
    """Integration tests for atlas validator with generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(padding=0, power_of_two=False)
        self.generator = AtlasGenerator(self.config)
        self.validator = AtlasValidator(self.config)
    
    def test_validate_generated_worker_atlas(self):
        """Test validation of generated worker atlas."""
        # Create frames for worker
        frames = []
        for i in range(64):
            frame = Image.new('RGBA', (64, 64), (i * 4, 100, 0, 255))
            frames.append(frame)
        
        # Generate worker atlas
        atlas_result = self.generator.create_worker_atlas(frames, "test_worker")
        
        # Validate the generated atlas
        errors = self.validator.validate_worker_atlas(atlas_result)
        
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
    
    def test_validate_generated_unit_atlas(self):
        """Test validation of generated unit atlas."""
        # Create frames for unit
        frames = []
        for i in range(32):  # 4 directions * 8 frames
            frame = Image.new('RGBA', (64, 64), (i * 8, 50, 100, 255))
            frames.append(frame)
        
        spec = UnitSpec("test_unit", directions=4, frames_per_direction=8)
        
        # Generate unit atlas
        atlas_result = self.generator.create_unit_atlas(frames, spec)
        
        # Validate the generated atlas
        errors = self.validator.validate_complete_atlas_workflow(atlas_result, spec)
        
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")


if __name__ == '__main__':
    unittest.main()