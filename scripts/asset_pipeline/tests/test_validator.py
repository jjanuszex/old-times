"""
Tests for the quality validation system.
"""

import unittest
from unittest.mock import Mock, patch
import numpy as np
from PIL import Image

from ..processing.validator import ValidationResult, QualityValidator, ValidationError
from ..config import ValidationConfig
from ..providers.base import AssetSpec, ProcessedAsset


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult class."""
    
    def test_init(self):
        """Test ValidationResult initialization."""
        result = ValidationResult("test_asset")
        self.assertEqual(result.asset_name, "test_asset")
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.metadata, {})
    
    def test_is_valid_no_errors(self):
        """Test is_valid property with no errors."""
        result = ValidationResult("test_asset")
        self.assertTrue(result.is_valid)
    
    def test_is_valid_with_errors(self):
        """Test is_valid property with errors."""
        result = ValidationResult("test_asset")
        result.add_error("Test error")
        self.assertFalse(result.is_valid)
    
    def test_has_warnings_no_warnings(self):
        """Test has_warnings property with no warnings."""
        result = ValidationResult("test_asset")
        self.assertFalse(result.has_warnings)
    
    def test_has_warnings_with_warnings(self):
        """Test has_warnings property with warnings."""
        result = ValidationResult("test_asset")
        result.add_warning("Test warning")
        self.assertTrue(result.has_warnings)
    
    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult("test_asset")
        result.add_error("Error 1")
        result.add_error("Error 2")
        self.assertEqual(result.errors, ["Error 1", "Error 2"])
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult("test_asset")
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")
        self.assertEqual(result.warnings, ["Warning 1", "Warning 2"])


class TestQualityValidator(unittest.TestCase):
    """Test QualityValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ValidationConfig(
            strict_dimensions=True,
            require_transparency=True,
            validate_isometric=True,
            max_file_size=50 * 1024 * 1024
        )
        self.validator = QualityValidator(self.config)
    
    def _create_test_image(self, size=(64, 32), mode='RGBA', transparent_bg=True):
        """Create a test image with specified properties."""
        image = Image.new(mode, size, (255, 255, 255, 255))
        
        if transparent_bg and mode == 'RGBA':
            # Make background transparent
            data = np.array(image)
            # Set alpha channel to 0 for background (assuming white background)
            mask = (data[:, :, 0] == 255) & (data[:, :, 1] == 255) & (data[:, :, 2] == 255)
            data[mask, 3] = 0
            image = Image.fromarray(data)
        
        return image
    
    def _create_test_asset(self, name="test_asset", asset_type="tile", size=(64, 32)):
        """Create a test ProcessedAsset."""
        spec = AssetSpec(name=name, asset_type=asset_type, size=size)
        image = self._create_test_image(size)
        return ProcessedAsset(spec=spec, image=image, output_path=f"test/{name}.png")
    
    def test_validate_tile_correct_dimensions(self):
        """Test tile validation with correct dimensions."""
        image = self._create_test_image((64, 32))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.validator.validate_tile(image, spec)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_tile_incorrect_dimensions(self):
        """Test tile validation with incorrect dimensions."""
        image = self._create_test_image((32, 32))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(32, 32))
        
        result = self.validator.validate_tile(image, spec)
        
        self.assertFalse(result.is_valid)
        self.assertIn("size (32, 32) != expected (64, 32)", result.errors[0])
    
    def test_validate_tile_no_transparency(self):
        """Test tile validation without transparency."""
        image = self._create_test_image((64, 32), transparent_bg=False)
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.validator.validate_tile(image, spec)
        
        self.assertFalse(result.is_valid)
        self.assertIn("lacks transparent background", result.errors[0])
    
    def test_validate_building_correct_dimensions(self):
        """Test building validation with correct dimensions."""
        image = self._create_test_image((128, 96))  # 2x3 tiles
        spec = AssetSpec(name="test_building", asset_type="building", size=(128, 96))
        
        result = self.validator.validate_building(image, spec)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_building_incorrect_width(self):
        """Test building validation with incorrect width."""
        image = self._create_test_image((100, 96))  # Not a multiple of 64
        spec = AssetSpec(name="test_building", asset_type="building", size=(100, 96))
        
        result = self.validator.validate_building(image, spec)
        
        self.assertFalse(result.is_valid)
        self.assertIn("width 100 is not a multiple of tile width 64", result.errors[0])
    
    def test_validate_building_too_small_height(self):
        """Test building validation with too small height."""
        image = self._create_test_image((64, 16))  # Less than tile height
        spec = AssetSpec(name="test_building", asset_type="building", size=(64, 16))
        
        result = self.validator.validate_building(image, spec)
        
        self.assertFalse(result.is_valid)
        self.assertIn("height 16 is less than minimum tile height 32", result.errors[0])
    
    def test_validate_unit_atlas_correct_layout(self):
        """Test unit atlas validation with correct layout."""
        atlas = self._create_test_image((512, 512))  # 8x8 frames of 64x64
        
        # Create frame map for 8 directions x 8 frames
        frame_map = {}
        for direction in range(8):
            for frame in range(8):
                frame_name = f"walk_{direction}_{frame}"
                frame_map[frame_name] = {
                    'x': frame * 64,
                    'y': direction * 64,
                    'w': 64,
                    'h': 64
                }
        
        result = self.validator.validate_unit_atlas(atlas, frame_map)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_unit_atlas_incorrect_size(self):
        """Test unit atlas validation with incorrect size."""
        atlas = self._create_test_image((256, 256))  # Wrong size
        frame_map = {"frame_0": {'x': 0, 'y': 0, 'w': 64, 'h': 64}}
        
        result = self.validator.validate_unit_atlas(atlas, frame_map)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Atlas size (256, 256) != expected (512, 512)", result.errors[0])
    
    def test_validate_unit_atlas_incorrect_frame_count(self):
        """Test unit atlas validation with incorrect frame count."""
        atlas = self._create_test_image((512, 512))
        frame_map = {"frame_0": {'x': 0, 'y': 0, 'w': 64, 'h': 64}}  # Only 1 frame
        
        result = self.validator.validate_unit_atlas(atlas, frame_map)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Frame count 1 != expected 64", result.errors[0])
    
    def test_validate_unit_atlas_frame_out_of_bounds(self):
        """Test unit atlas validation with frame out of bounds."""
        atlas = self._create_test_image((512, 512))
        
        # Create 64 frames with one out of bounds
        frame_map = {}
        for direction in range(8):
            for frame in range(8):
                frame_name = f"walk_{direction}_{frame}"
                if direction == 7 and frame == 7:  # Last frame out of bounds
                    frame_map[frame_name] = {'x': 500, 'y': 500, 'w': 64, 'h': 64}
                else:
                    frame_map[frame_name] = {
                        'x': frame * 64,
                        'y': direction * 64,
                        'w': 64,
                        'h': 64
                    }
        
        result = self.validator.validate_unit_atlas(atlas, frame_map)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("extends beyond atlas bounds" in error for error in result.errors))
    
    def test_validate_unit_atlas_incorrect_frame_size(self):
        """Test unit atlas validation with incorrect frame size."""
        atlas = self._create_test_image((512, 512))
        
        # Create 64 frames with one having wrong size
        frame_map = {}
        for direction in range(8):
            for frame in range(8):
                frame_name = f"walk_{direction}_{frame}"
                if direction == 0 and frame == 0:  # First frame wrong size
                    frame_map[frame_name] = {'x': 0, 'y': 0, 'w': 32, 'h': 32}
                else:
                    frame_map[frame_name] = {
                        'x': frame * 64,
                        'y': direction * 64,
                        'w': 64,
                        'h': 64
                    }
        
        result = self.validator.validate_unit_atlas(atlas, frame_map)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("size (32, 32) != expected (64, 64)" in error for error in result.errors))
    
    def test_validate_asset_tile(self):
        """Test validate_asset method with tile."""
        asset = self._create_test_asset("test_tile", "tile", (64, 32))
        
        result = self.validator.validate_asset(asset)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.asset_name, "test_tile")
    
    def test_validate_asset_building(self):
        """Test validate_asset method with building."""
        asset = self._create_test_asset("test_building", "building", (128, 96))
        
        result = self.validator.validate_asset(asset)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.asset_name, "test_building")
    
    def test_validate_asset_unit(self):
        """Test validate_asset method with unit."""
        asset = self._create_test_asset("test_unit", "unit", (64, 64))
        
        result = self.validator.validate_asset(asset)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.asset_name, "test_unit")
    
    def test_validate_batch(self):
        """Test batch validation."""
        assets = [
            self._create_test_asset("tile1", "tile", (64, 32)),
            self._create_test_asset("building1", "building", (128, 96)),
            self._create_test_asset("unit1", "unit", (64, 64))
        ]
        
        results = self.validator.validate_batch(assets)
        
        self.assertEqual(len(results), 3)
        self.assertIn("tile1", results)
        self.assertIn("building1", results)
        self.assertIn("unit1", results)
        
        for result in results.values():
            self.assertTrue(result.is_valid)
    
    def test_get_validation_summary_all_valid(self):
        """Test validation summary with all valid assets."""
        results = {
            "asset1": ValidationResult("asset1"),
            "asset2": ValidationResult("asset2"),
            "asset3": ValidationResult("asset3")
        }
        
        summary = self.validator.get_validation_summary(results)
        
        self.assertEqual(summary["total_assets"], 3)
        self.assertEqual(summary["valid_assets"], 3)
        self.assertEqual(summary["invalid_assets"], 0)
        self.assertEqual(summary["assets_with_warnings"], 0)
        self.assertEqual(summary["total_errors"], 0)
        self.assertEqual(summary["total_warnings"], 0)
        self.assertEqual(summary["success_rate"], 1.0)
    
    def test_get_validation_summary_with_errors_and_warnings(self):
        """Test validation summary with errors and warnings."""
        result1 = ValidationResult("asset1")
        result1.add_error("Error 1")
        result1.add_error("Error 2")
        
        result2 = ValidationResult("asset2")
        result2.add_warning("Warning 1")
        
        result3 = ValidationResult("asset3")  # Valid
        
        results = {
            "asset1": result1,
            "asset2": result2,
            "asset3": result3
        }
        
        summary = self.validator.get_validation_summary(results)
        
        self.assertEqual(summary["total_assets"], 3)
        self.assertEqual(summary["valid_assets"], 2)  # asset2 and asset3
        self.assertEqual(summary["invalid_assets"], 1)  # asset1
        self.assertEqual(summary["assets_with_warnings"], 1)  # asset2
        self.assertEqual(summary["total_errors"], 2)
        self.assertEqual(summary["total_warnings"], 1)
        self.assertEqual(summary["success_rate"], 2/3)
    
    def test_has_transparent_background_rgba_with_transparency(self):
        """Test transparent background detection with RGBA image."""
        image = self._create_test_image((64, 32), mode='RGBA', transparent_bg=True)
        
        result = self.validator._has_transparent_background(image)
        
        self.assertTrue(result)
    
    def test_has_transparent_background_rgba_without_transparency(self):
        """Test transparent background detection with opaque RGBA image."""
        image = self._create_test_image((64, 32), mode='RGBA', transparent_bg=False)
        
        result = self.validator._has_transparent_background(image)
        
        self.assertFalse(result)
    
    def test_has_transparent_background_rgb(self):
        """Test transparent background detection with RGB image."""
        image = self._create_test_image((64, 32), mode='RGB')
        
        result = self.validator._has_transparent_background(image)
        
        self.assertFalse(result)
    
    def test_validate_isometric_tile_correct_ratio(self):
        """Test isometric tile validation with correct 2:1 ratio."""
        image = self._create_test_image((64, 32))
        
        result = self.validator._validate_isometric_tile(image)
        
        self.assertTrue(result)
    
    def test_validate_isometric_tile_incorrect_ratio(self):
        """Test isometric tile validation with incorrect ratio."""
        image = self._create_test_image((64, 64))  # 1:1 ratio
        
        result = self.validator._validate_isometric_tile(image)
        
        self.assertFalse(result)
    
    def test_validate_isometric_building_correct_width(self):
        """Test isometric building validation with correct width."""
        image = self._create_test_image((128, 96))  # Width is multiple of 64
        
        result = self.validator._validate_isometric_building(image)
        
        self.assertTrue(result)
    
    def test_validate_isometric_building_incorrect_width(self):
        """Test isometric building validation with incorrect width."""
        image = self._create_test_image((100, 96))  # Width is not multiple of 64
        
        result = self.validator._validate_isometric_building(image)
        
        self.assertFalse(result)


class TestValidationError(unittest.TestCase):
    """Test ValidationError exception."""
    
    def test_init_with_message_only(self):
        """Test ValidationError initialization with message only."""
        error = ValidationError("Test error")
        
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.results, {})
    
    def test_init_with_results(self):
        """Test ValidationError initialization with results."""
        results = {"asset1": ValidationResult("asset1")}
        error = ValidationError("Test error", results)
        
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.results, results)


class TestDimensionValidation(unittest.TestCase):
    """Test dimension validation methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ValidationConfig(
            strict_dimensions=True,
            require_transparency=True,
            validate_isometric=True,
            max_file_size=50 * 1024 * 1024
        )
        self.validator = QualityValidator(self.config)
    
    def _create_test_image(self, size=(64, 32), mode='RGBA'):
        """Create a test image with specified properties."""
        return Image.new(mode, size, (255, 255, 255, 255))
    
    def test_validate_tile_dimensions_correct(self):
        """Test tile dimension validation with correct 64x32 size."""
        image = self._create_test_image((64, 32))
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_dimensions(image, "test_tile", result)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_tile_dimensions_incorrect_size(self):
        """Test tile dimension validation with incorrect size."""
        image = self._create_test_image((32, 16))
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_dimensions(image, "test_tile", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("size (32, 16) != required (64, 32)", result.errors[0])
    
    def test_validate_tile_dimensions_zero_size(self):
        """Test tile dimension validation with zero dimensions."""
        image = self._create_test_image((0, 32))
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_dimensions(image, "test_tile", result)
        
        self.assertFalse(result.is_valid)
        # Should have both size mismatch and invalid dimensions errors
        self.assertTrue(any("invalid dimensions" in error for error in result.errors))
    
    def test_validate_tile_dimensions_wrong_aspect_ratio(self):
        """Test tile dimension validation with wrong aspect ratio."""
        image = self._create_test_image((64, 64))  # 1:1 instead of 2:1
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_dimensions(image, "test_tile", result)
        
        self.assertTrue(any("aspect ratio" in warning for warning in result.warnings))
    
    def test_validate_unit_frame_dimensions_correct(self):
        """Test unit frame dimension validation with correct 64x64 size."""
        image = self._create_test_image((64, 64))
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_frame_dimensions(image, "test_unit", result)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_unit_frame_dimensions_incorrect_size(self):
        """Test unit frame dimension validation with incorrect size."""
        image = self._create_test_image((32, 32))
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_frame_dimensions(image, "test_unit", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("size (32, 32) != required (64, 64)", result.errors[0])
    
    def test_validate_unit_frame_dimensions_not_square(self):
        """Test unit frame dimension validation with non-square dimensions."""
        image = self._create_test_image((64, 32))
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_frame_dimensions(image, "test_unit", result)
        
        self.assertTrue(any("not square" in warning for warning in result.warnings))
    
    def test_validate_unit_frame_dimensions_zero_size(self):
        """Test unit frame dimension validation with zero dimensions."""
        image = self._create_test_image((0, 64))
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_frame_dimensions(image, "test_unit", result)
        
        self.assertFalse(result.is_valid)
        # Should have both size mismatch and invalid dimensions errors
        self.assertTrue(any("invalid dimensions" in error for error in result.errors))
    
    def test_validate_building_dimensions_correct(self):
        """Test building dimension validation with correct multiples."""
        image = self._create_test_image((128, 96))  # 2x3 tiles
        result = ValidationResult("test_building")
        
        self.validator._validate_building_dimensions(image, "test_building", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_building_dimensions_width_not_multiple(self):
        """Test building dimension validation with width not multiple of 64."""
        image = self._create_test_image((100, 96))
        result = ValidationResult("test_building")
        
        self.validator._validate_building_dimensions(image, "test_building", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("width 100 is not a multiple of tile width 64", result.errors[0])
    
    def test_validate_building_dimensions_height_too_small(self):
        """Test building dimension validation with height too small."""
        image = self._create_test_image((64, 16))
        result = ValidationResult("test_building")
        
        self.validator._validate_building_dimensions(image, "test_building", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("height 16 is less than minimum tile height 32", result.errors[0])
    
    def test_validate_building_dimensions_height_not_multiple(self):
        """Test building dimension validation with height not multiple of 32."""
        image = self._create_test_image((64, 50))
        result = ValidationResult("test_building")
        
        self.validator._validate_building_dimensions(image, "test_building", result)
        
        self.assertTrue(any("height 50 is not a multiple of tile height 32" in warning for warning in result.warnings))
    
    def test_validate_building_dimensions_too_large(self):
        """Test building dimension validation with excessive size."""
        image = self._create_test_image((1024, 1024))  # Very large
        result = ValidationResult("test_building")
        
        self.validator._validate_building_dimensions(image, "test_building", result)
        
        self.assertTrue(any("exceeds recommended maximum" in warning for warning in result.warnings))
    
    def test_validate_building_dimensions_zero_size(self):
        """Test building dimension validation with zero dimensions."""
        image = self._create_test_image((0, 96))
        result = ValidationResult("test_building")
        
        self.validator._validate_building_dimensions(image, "test_building", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("invalid dimensions", result.errors[0])
    
    def test_validate_atlas_dimensions_correct(self):
        """Test atlas dimension validation with correct size."""
        atlas = self._create_test_image((512, 512))
        result = ValidationResult("test_atlas")
        
        self.validator._validate_atlas_dimensions(atlas, (512, 512), result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_atlas_dimensions_incorrect_size(self):
        """Test atlas dimension validation with incorrect size."""
        atlas = self._create_test_image((256, 256))
        result = ValidationResult("test_atlas")
        
        self.validator._validate_atlas_dimensions(atlas, (512, 512), result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Atlas size (256, 256) != expected (512, 512)", result.errors[0])
    
    def test_validate_atlas_dimensions_zero_size(self):
        """Test atlas dimension validation with zero dimensions."""
        atlas = self._create_test_image((0, 512))
        result = ValidationResult("test_atlas")
        
        self.validator._validate_atlas_dimensions(atlas, (512, 512), result)
        
        self.assertFalse(result.is_valid)
        # Should have both size mismatch and invalid dimensions errors
        self.assertTrue(any("invalid dimensions" in error for error in result.errors))
    
    def test_validate_atlas_dimensions_not_multiple_of_64(self):
        """Test atlas dimension validation with dimensions not multiple of 64."""
        atlas = self._create_test_image((500, 500))
        result = ValidationResult("test_atlas")
        
        self.validator._validate_atlas_dimensions(atlas, (500, 500), result)
        
        self.assertTrue(any("not multiples of 64" in warning for warning in result.warnings))
    
    def test_strict_dimensions_disabled(self):
        """Test dimension validation with strict_dimensions disabled."""
        config = ValidationConfig(strict_dimensions=False)
        validator = QualityValidator(config)
        
        image = self._create_test_image((32, 16))
        result = ValidationResult("test_tile")
        
        validator._validate_tile_dimensions(image, "test_tile", result)
        
        # Should have warnings but no errors when strict_dimensions is False
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)


class TestTransparencyValidation(unittest.TestCase):
    """Test transparency validation methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ValidationConfig(
            strict_dimensions=True,
            require_transparency=True,
            validate_isometric=True,
            max_file_size=50 * 1024 * 1024
        )
        self.validator = QualityValidator(self.config)
    
    def _create_test_image_with_alpha(self, size=(64, 32), transparent_bg=True, mode='RGBA'):
        """Create a test image with specific alpha properties."""
        image = Image.new(mode, size, (255, 255, 255, 255))
        
        if transparent_bg and mode == 'RGBA':
            # Make background transparent
            data = np.array(image)
            # Set alpha channel to 0 for background (assuming white background)
            mask = (data[:, :, 0] == 255) & (data[:, :, 1] == 255) & (data[:, :, 2] == 255)
            data[mask, 3] = 0
            image = Image.fromarray(data)
        
        return image
    
    def _create_image_with_custom_alpha(self, size=(64, 32), alpha_pattern='transparent_bg'):
        """Create image with specific alpha patterns."""
        image = Image.new('RGBA', size, (255, 255, 255, 255))
        data = np.array(image)
        
        if alpha_pattern == 'transparent_bg':
            # Transparent background, opaque center
            center_x, center_y = size[0] // 2, size[1] // 2
            data[:, :, 3] = 0  # All transparent
            data[center_y-5:center_y+5, center_x-5:center_x+5, 3] = 255  # Opaque center
        elif alpha_pattern == 'no_transparency':
            # All opaque
            data[:, :, 3] = 255
        elif alpha_pattern == 'all_transparent':
            # All transparent
            data[:, :, 3] = 0
        elif alpha_pattern == 'semi_transparent':
            # Mix of semi-transparent pixels
            data[:, :, 3] = 128  # All semi-transparent
        elif alpha_pattern == 'edge_opaque':
            # Transparent center, opaque edges
            data[:, :, 3] = 0  # All transparent
            data[0, :, 3] = 255  # Top edge opaque
            data[-1, :, 3] = 255  # Bottom edge opaque
            data[:, 0, 3] = 255  # Left edge opaque
            data[:, -1, 3] = 255  # Right edge opaque
        elif alpha_pattern == 'inconsistent_bg':
            # Transparent pixels with different background colors
            data[:, :, 3] = 0  # All transparent
            data[:size[1]//2, :, :3] = [255, 0, 0]  # Red background top half
            data[size[1]//2:, :, :3] = [0, 255, 0]  # Green background bottom half
        
        return Image.fromarray(data)
    
    def test_validate_transparency_rgba_with_transparency(self):
        """Test transparency validation with proper RGBA image."""
        image = self._create_image_with_custom_alpha(alpha_pattern='transparent_bg')
        result = ValidationResult("test_asset")
        
        self.validator._validate_transparency(image, "test_asset", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_transparency_rgb_mode(self):
        """Test transparency validation with RGB image."""
        image = Image.new('RGB', (64, 32), (255, 255, 255))
        result = ValidationResult("test_asset")
        
        self.validator._validate_transparency(image, "test_asset", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("does not support transparency", result.errors[0])
    
    def test_validate_transparency_no_transparent_pixels(self):
        """Test transparency validation with no transparent pixels."""
        image = self._create_image_with_custom_alpha(alpha_pattern='no_transparency')
        result = ValidationResult("test_asset")
        
        self.validator._validate_transparency(image, "test_asset", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("lacks transparent background", result.errors[0])
    
    def test_validate_transparency_all_transparent(self):
        """Test transparency validation with all transparent pixels."""
        image = self._create_image_with_custom_alpha(alpha_pattern='all_transparent')
        result = ValidationResult("test_asset")
        
        self.validator._validate_transparency(image, "test_asset", result)
        
        self.assertTrue(any("no fully opaque pixels" in warning for warning in result.warnings))
    
    def test_validate_transparency_high_semi_transparency(self):
        """Test transparency validation with high semi-transparency ratio."""
        image = self._create_image_with_custom_alpha(alpha_pattern='semi_transparent')
        result = ValidationResult("test_asset")
        
        self.validator._validate_transparency(image, "test_asset", result)
        
        self.assertTrue(any("high semi-transparency ratio" in warning for warning in result.warnings))
    
    def test_validate_alpha_channel_valid_range(self):
        """Test alpha channel validation with valid values."""
        alpha_channel = np.array([[0, 128, 255], [64, 192, 255]], dtype=np.uint8)
        result = ValidationResult("test_asset")
        
        self.validator._validate_alpha_channel(alpha_channel, "test_asset", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_alpha_channel_no_transparent_pixels(self):
        """Test alpha channel validation with no transparent pixels."""
        alpha_channel = np.full((32, 64), 255, dtype=np.uint8)  # All opaque
        result = ValidationResult("test_asset")
        
        self.validator._validate_alpha_channel(alpha_channel, "test_asset", result)
        
        self.assertFalse(result.is_valid)
        self.assertIn("no fully transparent pixels", result.errors[0])
    
    def test_validate_alpha_channel_no_opaque_pixels(self):
        """Test alpha channel validation with no opaque pixels."""
        alpha_channel = np.full((32, 64), 128, dtype=np.uint8)  # All semi-transparent
        result = ValidationResult("test_asset")
        
        self.validator._validate_alpha_channel(alpha_channel, "test_asset", result)
        
        self.assertTrue(any("no fully opaque pixels" in warning for warning in result.warnings))
    
    def test_validate_edge_transparency_clean_edges(self):
        """Test edge transparency validation with clean transparent edges."""
        alpha_channel = np.full((32, 64), 255, dtype=np.uint8)
        alpha_channel[0, :] = 0  # Top edge transparent
        alpha_channel[-1, :] = 0  # Bottom edge transparent
        alpha_channel[:, 0] = 0  # Left edge transparent
        alpha_channel[:, -1] = 0  # Right edge transparent
        alpha_channel[1:-1, 1:-1] = 255  # Interior opaque
        result = ValidationResult("test_asset")
        
        self.validator._validate_edge_transparency(alpha_channel, "test_asset", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_edge_transparency_opaque_edges(self):
        """Test edge transparency validation with opaque edges."""
        image = self._create_image_with_custom_alpha(alpha_pattern='edge_opaque')
        data = np.array(image)
        alpha_channel = data[:, :, 3]
        result = ValidationResult("test_asset")
        
        self.validator._validate_edge_transparency(alpha_channel, "test_asset", result)
        
        self.assertTrue(any("significant non-transparent edges" in warning for warning in result.warnings))
    
    def test_validate_background_consistency_consistent(self):
        """Test background consistency validation with consistent background."""
        image = self._create_image_with_custom_alpha(alpha_pattern='transparent_bg')
        data = np.array(image)
        result = ValidationResult("test_asset")
        
        self.validator._validate_background_consistency(data, "test_asset", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_background_consistency_inconsistent(self):
        """Test background consistency validation with inconsistent background."""
        image = self._create_image_with_custom_alpha(alpha_pattern='inconsistent_bg')
        data = np.array(image)
        result = ValidationResult("test_asset")
        
        self.validator._validate_background_consistency(data, "test_asset", result)
        
        self.assertTrue(any("inconsistent background colors" in warning for warning in result.warnings))
    
    def test_validate_background_consistency_non_black_transparent(self):
        """Test background consistency validation with non-black transparent pixels."""
        image = Image.new('RGBA', (64, 32), (255, 255, 255, 0))  # White transparent background
        data = np.array(image)
        result = ValidationResult("test_asset")
        
        self.validator._validate_background_consistency(data, "test_asset", result)
        
        self.assertTrue(any("non-black colors in transparent areas" in warning for warning in result.warnings))
    
    def test_has_transparent_background_rgba_with_transparency(self):
        """Test transparent background detection with RGBA image."""
        image = self._create_image_with_custom_alpha(alpha_pattern='transparent_bg')
        
        result = self.validator._has_transparent_background(image)
        
        self.assertTrue(result)
    
    def test_has_transparent_background_rgba_without_transparency(self):
        """Test transparent background detection with opaque RGBA image."""
        image = self._create_image_with_custom_alpha(alpha_pattern='no_transparency')
        
        result = self.validator._has_transparent_background(image)
        
        self.assertFalse(result)
    
    def test_has_transparent_background_rgb(self):
        """Test transparent background detection with RGB image."""
        image = Image.new('RGB', (64, 32), (255, 255, 255))
        
        result = self.validator._has_transparent_background(image)
        
        self.assertFalse(result)
    
    def test_transparency_validation_disabled(self):
        """Test transparency validation when require_transparency is disabled."""
        config = ValidationConfig(require_transparency=False)
        validator = QualityValidator(config)
        
        image = Image.new('RGB', (64, 32), (255, 255, 255))
        result = ValidationResult("test_asset")
        
        validator._validate_transparency(image, "test_asset", result)
        
        # Should have warnings but no errors when require_transparency is False
        self.assertTrue(result.is_valid)
        self.assertTrue(any("does not support transparency" in warning for warning in result.warnings))


class TestIsometricComplianceValidation(unittest.TestCase):
    """Test isometric compliance validation methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ValidationConfig(
            strict_dimensions=True,
            require_transparency=True,
            validate_isometric=True,
            max_file_size=50 * 1024 * 1024
        )
        self.validator = QualityValidator(self.config)
    
    def _create_test_image_with_content(self, size=(64, 32), content_pattern='centered'):
        """Create test image with specific content patterns."""
        image = Image.new('RGBA', size, (0, 0, 0, 0))  # Transparent background
        data = np.array(image)
        
        if content_pattern == 'centered':
            # Create centered content
            center_x, center_y = size[0] // 2, size[1] // 2
            content_size = min(size[0] // 3, size[1] // 3)
            x1, x2 = center_x - content_size, center_x + content_size
            y1, y2 = center_y - content_size, center_y + content_size
            data[y1:y2, x1:x2] = [255, 255, 255, 255]  # White opaque content
        elif content_pattern == 'off_center':
            # Create off-center content
            x1, x2 = 5, 15
            y1, y2 = 5, 15
            data[y1:y2, x1:x2] = [255, 255, 255, 255]
        elif content_pattern == 'bottom_positioned':
            # Create content in bottom portion (good for units)
            bottom_y = int(size[1] * 0.7)
            center_x = size[0] // 2
            content_size = min(size[0] // 4, size[1] // 4)
            x1, x2 = center_x - content_size, center_x + content_size
            y1, y2 = bottom_y - content_size, bottom_y + content_size
            data[y1:y2, x1:x2] = [255, 255, 255, 255]
        elif content_pattern == 'top_positioned':
            # Create content in top portion (bad for units)
            top_y = int(size[1] * 0.15)  # Very top
            center_x = size[0] // 2
            content_size = min(size[0] // 6, size[1] // 6)
            x1, x2 = center_x - content_size, center_x + content_size
            y1, y2 = max(0, top_y - content_size), top_y + content_size
            data[y1:y2, x1:x2] = [255, 255, 255, 255]
        elif content_pattern == 'narrow':
            # Create narrow content
            center_x, center_y = size[0] // 2, size[1] // 2
            x1, x2 = center_x - 2, center_x + 2
            y1, y2 = center_y - size[1] // 4, center_y + size[1] // 4
            data[y1:y2, x1:x2] = [255, 255, 255, 255]
        elif content_pattern == 'small':
            # Create very small content
            center_x, center_y = size[0] // 2, size[1] // 2
            data[center_y-2:center_y+2, center_x-2:center_x+2] = [255, 255, 255, 255]
        elif content_pattern == 'large':
            # Create large content (90% of image)
            margin = max(1, min(size) // 20)
            data[margin:-margin, margin:-margin] = [255, 255, 255, 255]
        
        return Image.fromarray(data)
    
    def test_validate_tile_isometric_compliance_correct_ratio(self):
        """Test tile isometric compliance with correct 2:1 ratio."""
        image = self._create_test_image_with_content((64, 32), 'centered')
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_isometric_compliance(image, "test_tile", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_tile_isometric_compliance_wrong_ratio(self):
        """Test tile isometric compliance with wrong aspect ratio."""
        image = self._create_test_image_with_content((64, 64), 'centered')  # 1:1 ratio
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_isometric_compliance(image, "test_tile", result)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("aspect ratio" in error for error in result.errors))
    
    def test_validate_tile_isometric_compliance_non_standard_size(self):
        """Test tile isometric compliance with non-standard size."""
        image = self._create_test_image_with_content((128, 64), 'centered')  # 2:1 ratio but not standard
        result = ValidationResult("test_tile")
        
        self.validator._validate_tile_isometric_compliance(image, "test_tile", result)
        
        self.assertTrue(result.is_valid)  # No errors, just warnings
        self.assertTrue(any("!= standard isometric tile" in warning for warning in result.warnings))
    
    def test_validate_building_isometric_compliance_correct_alignment(self):
        """Test building isometric compliance with correct grid alignment."""
        image = self._create_test_image_with_content((128, 96), 'centered')  # 2x tile width
        result = ValidationResult("test_building")
        
        self.validator._validate_building_isometric_compliance(image, "test_building", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_building_isometric_compliance_wrong_alignment(self):
        """Test building isometric compliance with wrong grid alignment."""
        image = self._create_test_image_with_content((100, 96), 'centered')  # Not multiple of 64
        result = ValidationResult("test_building")
        
        self.validator._validate_building_isometric_compliance(image, "test_building", result)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("not aligned to isometric grid" in error for error in result.errors))
    
    def test_validate_building_isometric_compliance_too_short(self):
        """Test building isometric compliance with insufficient height."""
        image = self._create_test_image_with_content((128, 16), 'centered')  # Too short
        result = ValidationResult("test_building")
        
        self.validator._validate_building_isometric_compliance(image, "test_building", result)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("less than minimum isometric height" in error for error in result.errors))
    
    def test_validate_building_isometric_compliance_proportions(self):
        """Test building isometric compliance proportions."""
        image = self._create_test_image_with_content((128, 30), 'centered')  # Definitely too short for 2x2 base
        result = ValidationResult("test_building")
        
        self.validator._validate_building_isometric_compliance(image, "test_building", result)
        
        # Should have warnings about proportions
        self.assertTrue(any("may be too short" in warning for warning in result.warnings))
    
    def test_validate_unit_isometric_compliance_square_frame(self):
        """Test unit isometric compliance with square frame."""
        image = self._create_test_image_with_content((64, 64), 'bottom_positioned')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_isometric_compliance(image, "test_unit", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_unit_isometric_compliance_non_square_frame(self):
        """Test unit isometric compliance with non-square frame."""
        image = self._create_test_image_with_content((64, 32), 'centered')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_isometric_compliance(image, "test_unit", result)
        
        self.assertTrue(any("not square" in warning for warning in result.warnings))
    
    def test_validate_unit_isometric_compliance_non_standard_size(self):
        """Test unit isometric compliance with non-standard size."""
        image = self._create_test_image_with_content((32, 32), 'bottom_positioned')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_isometric_compliance(image, "test_unit", result)
        
        self.assertTrue(any("!= standard (64, 64)" in warning for warning in result.warnings))
    
    def test_validate_grid_alignment_centered_content(self):
        """Test grid alignment validation with centered content."""
        image = self._create_test_image_with_content((64, 32), 'centered')
        result = ValidationResult("test_asset")
        
        self.validator._validate_grid_alignment(image, "test_asset", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_grid_alignment_off_center_content(self):
        """Test grid alignment validation with off-center content."""
        image = self._create_test_image_with_content((64, 32), 'off_center')
        result = ValidationResult("test_asset")
        
        self.validator._validate_grid_alignment(image, "test_asset", result)
        
        self.assertTrue(any("not be horizontally centered" in warning or "not be vertically centered" in warning 
                          for warning in result.warnings))
    
    def test_validate_grid_alignment_no_content(self):
        """Test grid alignment validation with no visible content."""
        image = Image.new('RGBA', (64, 32), (0, 0, 0, 0))  # All transparent
        result = ValidationResult("test_asset")
        
        self.validator._validate_grid_alignment(image, "test_asset", result)
        
        self.assertTrue(any("no visible content" in warning for warning in result.warnings))
    
    def test_validate_building_visual_consistency_narrow_content(self):
        """Test building visual consistency with narrow content."""
        image = self._create_test_image_with_content((128, 96), 'narrow')
        result = ValidationResult("test_building")
        
        self.validator._validate_building_visual_consistency(image, "test_building", result)
        
        self.assertTrue(any("seems narrow" in warning for warning in result.warnings))
    
    def test_validate_building_visual_consistency_small_content(self):
        """Test building visual consistency with small content."""
        image = self._create_test_image_with_content((128, 96), 'small')
        result = ValidationResult("test_building")
        
        self.validator._validate_building_visual_consistency(image, "test_building", result)
        
        self.assertTrue(any("seems narrow" in warning or "seems short" in warning 
                          for warning in result.warnings))
    
    def test_validate_unit_positioning_good_position(self):
        """Test unit positioning validation with good bottom positioning."""
        image = self._create_test_image_with_content((64, 64), 'bottom_positioned')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_positioning(image, "test_unit", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_unit_positioning_bad_position(self):
        """Test unit positioning validation with bad top positioning."""
        image = self._create_test_image_with_content((64, 64), 'top_positioned')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_positioning(image, "test_unit", result)
        
        self.assertTrue(any("not be positioned optimally" in warning for warning in result.warnings))
    
    def test_validate_unit_positioning_small_content(self):
        """Test unit positioning validation with small content."""
        image = self._create_test_image_with_content((64, 64), 'small')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_positioning(image, "test_unit", result)
        
        self.assertTrue(any("seems small" in warning for warning in result.warnings))
    
    def test_validate_unit_positioning_large_content(self):
        """Test unit positioning validation with large content."""
        image = self._create_test_image_with_content((64, 64), 'large')
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_positioning(image, "test_unit", result)
        
        self.assertTrue(any("too large" in warning for warning in result.warnings))
    
    def test_validate_unit_positioning_no_content(self):
        """Test unit positioning validation with no content."""
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))  # All transparent
        result = ValidationResult("test_unit")
        
        self.validator._validate_unit_positioning(image, "test_unit", result)
        
        self.assertTrue(any("no visible content" in warning for warning in result.warnings))
    
    def test_validate_isometric_compliance_tile(self):
        """Test comprehensive isometric compliance for tile."""
        image = self._create_test_image_with_content((64, 32), 'centered')
        result = ValidationResult("test_tile")
        
        self.validator._validate_isometric_compliance(image, "test_tile", "tile", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_isometric_compliance_building(self):
        """Test comprehensive isometric compliance for building."""
        image = self._create_test_image_with_content((128, 96), 'centered')
        result = ValidationResult("test_building")
        
        self.validator._validate_isometric_compliance(image, "test_building", "building", result)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_isometric_compliance_unit(self):
        """Test comprehensive isometric compliance for unit."""
        image = self._create_test_image_with_content((64, 64), 'bottom_positioned')
        result = ValidationResult("test_unit")
        
        self.validator._validate_isometric_compliance(image, "test_unit", "unit", result)
        
        self.assertTrue(result.is_valid)
    
    def test_isometric_validation_disabled(self):
        """Test isometric validation when validate_isometric is disabled."""
        config = ValidationConfig(validate_isometric=False)
        validator = QualityValidator(config)
        
        # Create image with bad aspect ratio
        image = self._create_test_image_with_content((64, 64), 'centered')  # 1:1 instead of 2:1
        result = ValidationResult("test_tile")
        
        validator._validate_isometric_compliance(image, "test_tile", "tile", result)
        
        # Should not validate isometric compliance when disabled
        self.assertTrue(result.is_valid)


if __name__ == '__main__':
    unittest.main()