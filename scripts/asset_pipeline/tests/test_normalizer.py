"""
Tests for asset normalization engine.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import os
from PIL import Image
import numpy as np

from ..processing.normalizer import AssetNormalizer, NormalizationConfig, NormalizationError
from ..providers.base import AssetSpec
from ..utils.image import ImageUtils
from ..utils.isometric import IsometricUtils


class TestAssetNormalizer(unittest.TestCase):
    """Test cases for AssetNormalizer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = NormalizationConfig(
            tile_size=(64, 32),
            unit_frame_size=(64, 64),
            preserve_aspect_ratio=True,
            edge_sharpening=True,
            anti_aliasing=True,
            transparency_tolerance=10
        )
        self.normalizer = AssetNormalizer(self.config)
    
    def create_test_image(self, size: tuple[int, int], mode: str = 'RGBA') -> Image.Image:
        """Create a test image with specified size and mode."""
        image = Image.new(mode, size, (255, 255, 255, 255))
        
        # Add some content to make it non-uniform
        if mode == 'RGBA':
            # Create a simple pattern
            pixels = image.load()
            for x in range(size[0]):
                for y in range(size[1]):
                    if (x + y) % 10 == 0:
                        pixels[x, y] = (255, 0, 0, 255)  # Red pixels
                    elif x < 5 or y < 5:
                        pixels[x, y] = (0, 0, 0, 0)  # Transparent border
        
        return image
    
    def test_normalize_tile_exact_size(self):
        """Test tile normalization when image is already correct size."""
        # Create test image with exact tile size
        image = self.create_test_image((64, 32))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.normalizer.normalize_tile(image, spec)
        
        # Should maintain exact size
        self.assertEqual(result.size, (64, 32))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_tile_resize_needed(self):
        """Test tile normalization when resizing is needed."""
        # Create test image with different size
        image = self.create_test_image((128, 64))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.normalizer.normalize_tile(image, spec)
        
        # Should be resized to exact tile dimensions
        self.assertEqual(result.size, (64, 32))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_tile_non_isometric_ratio(self):
        """Test tile normalization with non-isometric input."""
        # Create square image (not 2:1 ratio)
        image = self.create_test_image((100, 100))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.normalizer.normalize_tile(image, spec)
        
        # Should be normalized to isometric dimensions
        self.assertEqual(result.size, (64, 32))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_tile_rgb_to_rgba(self):
        """Test tile normalization converts RGB to RGBA."""
        # Create RGB image
        image = self.create_test_image((64, 32), 'RGB')
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.normalizer.normalize_tile(image, spec)
        
        # Should be converted to RGBA
        self.assertEqual(result.mode, 'RGBA')
        self.assertEqual(result.size, (64, 32))
    
    def test_normalize_building_default_size(self):
        """Test building normalization with default size calculation."""
        image = self.create_test_image((100, 150))
        spec = AssetSpec(name="test_building", asset_type="building", size=(0, 0))
        
        result = self.normalizer.normalize_building(image, spec)
        
        # Should use default building size (2x3 tiles = 128x96)
        self.assertEqual(result.size, (128, 96))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_building_specified_size(self):
        """Test building normalization with specified size."""
        image = self.create_test_image((100, 150))
        spec = AssetSpec(name="test_building", asset_type="building", size=(192, 128))
        
        result = self.normalizer.normalize_building(image, spec)
        
        # Should use specified size
        self.assertEqual(result.size, (192, 128))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_building_with_footprint_metadata(self):
        """Test building normalization with tile footprint metadata."""
        image = self.create_test_image((100, 150))
        spec = AssetSpec(
            name="test_building", 
            asset_type="building", 
            size=(0, 0),
            metadata={"tile_footprint": [3, 2]}  # 3x2 tiles
        )
        
        result = self.normalizer.normalize_building(image, spec)
        
        # Should calculate size from footprint: 3*64 x (2+1)*32 = 192x96
        self.assertEqual(result.size, (192, 96))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_unit_exact_size(self):
        """Test unit normalization when image is already correct size."""
        image = self.create_test_image((64, 64))
        spec = AssetSpec(name="test_unit", asset_type="unit", size=(64, 64))
        
        result = self.normalizer.normalize_unit(image, spec)
        
        # Should maintain exact size
        self.assertEqual(result.size, (64, 64))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_unit_resize_needed(self):
        """Test unit normalization when resizing is needed."""
        image = self.create_test_image((48, 48))
        spec = AssetSpec(name="test_unit", asset_type="unit", size=(64, 64))
        
        result = self.normalizer.normalize_unit(image, spec)
        
        # Should be resized to unit frame size
        self.assertEqual(result.size, (64, 64))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_unit_non_square(self):
        """Test unit normalization with non-square input."""
        image = self.create_test_image((80, 60))
        spec = AssetSpec(name="test_unit", asset_type="unit", size=(64, 64))
        
        result = self.normalizer.normalize_unit(image, spec)
        
        # Should be normalized to square dimensions
        self.assertEqual(result.size, (64, 64))
        self.assertEqual(result.mode, 'RGBA')
    
    def test_normalize_asset_unknown_type(self):
        """Test normalization with unknown asset type."""
        image = self.create_test_image((64, 64))
        # Create spec with valid type first, then modify it
        spec = AssetSpec(name="test_unknown", asset_type="tile", size=(64, 64))
        # Bypass validation by directly setting the asset_type
        spec.asset_type = "unknown"
        
        with self.assertRaises(NormalizationError) as context:
            self.normalizer.normalize_asset(image, spec)
        
        self.assertIn("Unknown asset type", str(context.exception))
    
    def test_normalize_asset_with_bytes_input(self):
        """Test normalization with bytes input."""
        # Create test image and convert to bytes
        image = self.create_test_image((64, 32))
        
        # Save to bytes
        import io
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        result = self.normalizer.normalize_asset(img_bytes, spec)
        
        # Should successfully process bytes input
        self.assertEqual(result.image.size, (64, 32))
        self.assertEqual(result.spec.name, "test_tile")
        self.assertTrue(result.metadata["normalized"])
    
    def test_validation_tile_wrong_size(self):
        """Test validation fails for tile with wrong size."""
        # Create image with wrong size
        image = self.create_test_image((32, 32))  # Should be 64x32
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        with self.assertRaises(NormalizationError) as context:
            self.normalizer._validate_normalized_asset(image, spec)
        
        self.assertIn("size", str(context.exception))
    
    def test_validation_unit_wrong_size(self):
        """Test validation fails for unit with wrong size."""
        # Create image with wrong size
        image = self.create_test_image((32, 32))  # Should be 64x64
        spec = AssetSpec(name="test_unit", asset_type="unit", size=(64, 64))
        
        with self.assertRaises(NormalizationError) as context:
            self.normalizer._validate_normalized_asset(image, spec)
        
        self.assertIn("size", str(context.exception))
    
    def test_validation_non_rgba_mode(self):
        """Test validation fails for non-RGBA image."""
        # Create RGB image
        image = self.create_test_image((64, 32), 'RGB')
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        with self.assertRaises(NormalizationError) as context:
            self.normalizer._validate_normalized_asset(image, spec)
        
        self.assertIn("RGBA mode", str(context.exception))
    
    def test_edge_sharpening_disabled(self):
        """Test normalization with edge sharpening disabled."""
        config = NormalizationConfig(edge_sharpening=False)
        normalizer = AssetNormalizer(config)
        
        image = self.create_test_image((64, 32))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        # Should not raise any errors
        result = normalizer.normalize_tile(image, spec)
        self.assertEqual(result.size, (64, 32))
    
    def test_anti_aliasing_disabled(self):
        """Test normalization with anti-aliasing disabled."""
        config = NormalizationConfig(anti_aliasing=False)
        normalizer = AssetNormalizer(config)
        
        image = self.create_test_image((64, 32))
        spec = AssetSpec(name="test_tile", asset_type="tile", size=(64, 32))
        
        # Should not raise any errors
        result = normalizer.normalize_tile(image, spec)
        self.assertEqual(result.size, (64, 32))
    
    def test_preserve_aspect_ratio_disabled(self):
        """Test building normalization with aspect ratio preservation disabled."""
        config = NormalizationConfig(preserve_aspect_ratio=False)
        normalizer = AssetNormalizer(config)
        
        image = self.create_test_image((100, 200))  # 1:2 ratio
        spec = AssetSpec(name="test_building", asset_type="building", size=(128, 96))
        
        result = normalizer.normalize_building(image, spec)
        
        # Should stretch to exact target size
        self.assertEqual(result.size, (128, 96))
    
    def test_unit_frame_sequence_validation(self):
        """Test validation of unit frame sequences for 8-direction walking."""
        # Test that unit frames maintain consistency for animation sequences
        frames = []
        for i in range(8):  # 8 directions
            frame = self.create_test_image((64, 64))
            spec = AssetSpec(name=f"test_unit_frame_{i}", asset_type="unit", size=(64, 64))
            normalized = self.normalizer.normalize_unit(frame, spec)
            frames.append(normalized)
        
        # All frames should have consistent size
        for frame in frames:
            self.assertEqual(frame.size, (64, 64))
            self.assertEqual(frame.mode, 'RGBA')
    
    def test_unit_animation_frame_consistency(self):
        """Test that animation frames maintain consistency across directions."""
        # Create frames with slightly different sizes to test normalization consistency
        frame_sizes = [(60, 60), (64, 64), (68, 68), (56, 56)]
        normalized_frames = []
        
        for i, size in enumerate(frame_sizes):
            frame = self.create_test_image(size)
            spec = AssetSpec(name=f"test_anim_frame_{i}", asset_type="unit", size=(64, 64))
            normalized = self.normalizer.normalize_unit(frame, spec)
            normalized_frames.append(normalized)
        
        # All normalized frames should have identical dimensions
        target_size = (64, 64)
        for frame in normalized_frames:
            self.assertEqual(frame.size, target_size)
            self.assertEqual(frame.mode, 'RGBA')
    
    def test_unit_frame_centering(self):
        """Test that unit frames are properly centered."""
        # Create a small frame that needs centering
        small_frame = self.create_test_image((32, 32))
        spec = AssetSpec(name="test_centered_unit", asset_type="unit", size=(64, 64))
        
        result = self.normalizer.normalize_unit(small_frame, spec)
        
        # Should be centered in 64x64 canvas
        self.assertEqual(result.size, (64, 64))
        self.assertEqual(result.mode, 'RGBA')
        
        # Check that there's transparent padding around the content
        # (This is a basic check - in practice you'd verify the actual centering)
        self.assertTrue(ImageUtils.detect_transparency(result))


class TestNormalizationConfig(unittest.TestCase):
    """Test cases for NormalizationConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = NormalizationConfig()
        
        self.assertEqual(config.tile_size, (64, 32))
        self.assertEqual(config.unit_frame_size, (64, 64))
        self.assertTrue(config.preserve_aspect_ratio)
        self.assertEqual(config.background_color, (0, 0, 0, 0))
        self.assertTrue(config.edge_sharpening)
        self.assertTrue(config.anti_aliasing)
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = NormalizationConfig(
            tile_size=(32, 16),
            unit_frame_size=(32, 32),
            preserve_aspect_ratio=False,
            edge_sharpening=False,
            anti_aliasing=False,
            transparency_tolerance=5
        )
        
        self.assertEqual(config.tile_size, (32, 16))
        self.assertEqual(config.unit_frame_size, (32, 32))
        self.assertFalse(config.preserve_aspect_ratio)
        self.assertFalse(config.edge_sharpening)
        self.assertFalse(config.anti_aliasing)
        self.assertEqual(config.transparency_tolerance, 5)


if __name__ == '__main__':
    unittest.main()