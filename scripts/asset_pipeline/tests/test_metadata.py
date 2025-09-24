"""
Tests for metadata generation system.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image

from ..processing.metadata import MetadataGenerator, MetadataGenerationError
from ..providers.base import ProcessedAsset, AssetSpec
from ..processing.atlas import AtlasResult


class TestMetadataGenerator(unittest.TestCase):
    """Test cases for MetadataGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.temp_dir) / "templates"
        self.generator = MetadataGenerator(str(self.template_dir))
        
        # Create mock assets
        self.mock_tile = self._create_mock_asset("grass", "tile", 64, 32)
        self.mock_building = self._create_mock_asset("lumberjack", "building", 128, 96)
        self.mock_unit = self._create_mock_asset("worker", "unit", 64, 64)
        
        # Create mock atlas
        self.mock_atlas = self._create_mock_atlas()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_mock_asset(self, name: str, asset_type: str, width: int, height: int) -> ProcessedAsset:
        """Create a mock ProcessedAsset."""
        mock_image = Mock(spec=Image.Image)
        mock_image.width = width
        mock_image.height = height
        mock_image.size = (width, height)
        
        # Create AssetSpec first
        spec = AssetSpec(
            name=name,
            asset_type=asset_type,
            size=(width, height)
        )
        
        return ProcessedAsset(
            spec=spec,
            image=mock_image,
            output_path=f"sprites/{name}.png"
        )
    
    def _create_mock_atlas(self) -> AtlasResult:
        """Create a mock AtlasResult."""
        mock_atlas_image = Mock(spec=Image.Image)
        mock_atlas_image.width = 512
        mock_atlas_image.height = 512
        
        frame_map = {
            "walk_N_0": {"x": 0, "y": 0, "w": 64, "h": 64},
            "walk_N_1": {"x": 64, "y": 0, "w": 64, "h": 64}
        }
        
        return AtlasResult(
            atlas=mock_atlas_image,
            frame_map=frame_map,
            metadata={"directions": 8, "frames_per_direction": 8}
        )
    
    def test_init_creates_template_directory(self):
        """Test that initialization creates template directory."""
        self.assertTrue(self.template_dir.exists())
        self.assertTrue((self.template_dir / "sprites.toml.j2").exists())
        self.assertTrue((self.template_dir / "mod.toml.j2").exists())
    
    def test_template_filters_setup(self):
        """Test that custom template filters are properly set up."""
        # Test tile_footprint filter
        self.assertIn('tile_footprint', self.generator.env.filters)
        self.assertIn('format_path', self.generator.env.filters)
        self.assertIn('safe_name', self.generator.env.filters)
        
        # Test filter functionality
        tile_footprint_filter = self.generator.env.filters['tile_footprint']
        self.assertEqual(tile_footprint_filter(128, 96), [2, 1])
        
        format_path_filter = self.generator.env.filters['format_path']
        self.assertEqual(format_path_filter("path\\to\\file.png"), "path/to/file.png")
        
        safe_name_filter = self.generator.env.filters['safe_name']
        self.assertEqual(safe_name_filter("test-name!"), "test_name_")
    
    def test_generate_sprites_toml_success(self):
        """Test successful sprites.toml generation."""
        assets = [self.mock_tile, self.mock_building, self.mock_unit]
        atlases = {"worker_atlas": self.mock_atlas}
        
        result = self.generator.generate_sprites_toml(assets, atlases)
        
        # Verify content structure
        self.assertIn("[tiles]", result)
        self.assertIn("[tiles.grass]", result)
        self.assertIn('kind = "tile"', result)
        self.assertIn("size = [64, 32]", result)
        
        self.assertIn("[buildings]", result)
        self.assertIn("[buildings.lumberjack]", result)
        self.assertIn('kind = "building"', result)
        self.assertIn("size = [128, 96]", result)
        
        self.assertIn("[units]", result)
        self.assertIn("[units.worker]", result)
        self.assertIn('kind = "unit"', result)
    
    def test_generate_sprites_toml_empty_assets(self):
        """Test sprites.toml generation with empty assets list."""
        with self.assertRaises(MetadataGenerationError) as context:
            self.generator.generate_sprites_toml([])
        
        self.assertIn("No assets provided", str(context.exception))
    
    def test_generate_sprites_toml_with_atlas(self):
        """Test sprites.toml generation with atlas data."""
        assets = [self.mock_unit]
        atlases = {"worker_atlas": self.mock_atlas}
        
        result = self.generator.generate_sprites_toml(assets, atlases)
        
        # Verify atlas-specific content
        self.assertIn("source = \"atlases/worker_atlas.png\"", result)
        self.assertIn("frame_size = [64, 64]", result)
        self.assertIn("directions = [\"N\", \"NE\", \"E\", \"SE\", \"S\", \"SW\", \"W\", \"NW\"]", result)
        self.assertIn("anim_walk_fps = 10", result)
        self.assertIn("anim_walk_len = 8", result)
        self.assertIn("layout = \"dirs_rows\"", result)
        self.assertIn("atlas_map = \"atlases/worker_atlas.json\"", result)
    
    def test_generate_sprites_toml_without_atlas(self):
        """Test sprites.toml generation without atlas data."""
        assets = [self.mock_unit]
        
        result = self.generator.generate_sprites_toml(assets)
        
        # Verify non-atlas content
        self.assertIn("source = \"sprites/worker.png\"", result)
        self.assertIn("frame_size = [64, 64]", result)
        self.assertNotIn("atlas_map", result)
    
    def test_generate_mod_toml_success(self):
        """Test successful mod.toml generation."""
        assets = [self.mock_tile, self.mock_building]
        
        result = self.generator.generate_mod_toml("test_mod", assets)
        
        # Verify content structure
        self.assertIn("[mod]", result)
        self.assertIn('name = "test_mod"', result)
        self.assertIn('version = "1.0.0"', result)
        self.assertIn("Generated mod with 2 assets", result)
        
        self.assertIn("[assets]", result)
        # Check for tiles and buildings arrays (flexible with quote style)
        self.assertTrue('tiles = ["grass"]' in result or "tiles = ['grass']" in result)
        self.assertTrue('buildings = ["lumberjack"]' in result or "buildings = ['lumberjack']" in result)
        
        self.assertIn("[dependencies]", result)
        self.assertIn('base_game = ">=1.0.0"', result)
    
    def test_generate_mod_toml_empty_name(self):
        """Test mod.toml generation with empty mod name."""
        with self.assertRaises(MetadataGenerationError) as context:
            self.generator.generate_mod_toml("", [self.mock_tile])
        
        self.assertIn("Mod name cannot be empty", str(context.exception))
    
    def test_generate_mod_toml_whitespace_name(self):
        """Test mod.toml generation with whitespace-only mod name."""
        with self.assertRaises(MetadataGenerationError) as context:
            self.generator.generate_mod_toml("   ", [self.mock_tile])
        
        self.assertIn("Mod name cannot be empty", str(context.exception))
    
    def test_validate_toml_syntax_valid(self):
        """Test TOML syntax validation with valid content."""
        valid_toml = """
[section]
key = "value"
number = 42
array = ["item1", "item2"]
        """
        
        errors = self.generator.validate_toml_syntax(valid_toml)
        self.assertEqual(errors, [])
    
    def test_validate_toml_syntax_invalid(self):
        """Test TOML syntax validation with invalid content."""
        invalid_toml = """
[section
key = "unclosed string
invalid_syntax
        """
        
        errors = self.generator.validate_toml_syntax(invalid_toml)
        self.assertGreater(len(errors), 0)
    
    def test_template_not_found_fallback(self):
        """Test fallback to built-in template when template file not found."""
        # Remove template files
        (self.template_dir / "sprites.toml.j2").unlink()
        
        assets = [self.mock_tile]
        result = self.generator.generate_sprites_toml(assets)
        
        # Should still generate valid content using built-in template
        self.assertIn("[tiles]", result)
        self.assertIn("[tiles.grass]", result)
    
    def test_template_syntax_error_fallback(self):
        """Test fallback when template has syntax errors."""
        # Create template with syntax error
        bad_template = "{% invalid syntax %}"
        with open(self.template_dir / "sprites.toml.j2", 'w') as f:
            f.write(bad_template)
        
        assets = [self.mock_tile]
        result = self.generator.generate_sprites_toml(assets)
        
        # Should fallback to built-in template
        self.assertIn("[tiles]", result)
        self.assertIn("[tiles.grass]", result)
    
    def test_builtin_template_tile_footprint_calculation(self):
        """Test tile footprint calculation in built-in template."""
        # Remove template to force built-in usage
        (self.template_dir / "sprites.toml.j2").unlink()
        
        # Create building with specific dimensions
        building = self._create_mock_asset("big_building", "building", 192, 128)
        assets = [building]
        
        result = self.generator.generate_sprites_toml(assets)
        
        # Verify tile footprint calculation (192/64 = 3, 128/64 = 2)
        self.assertIn("tile_footprint = [3, 2]", result)
    
    def test_timestamp_generation(self):
        """Test timestamp generation for metadata."""
        timestamp = self.generator._get_timestamp()
        
        # Should be ISO format
        self.assertRegex(timestamp, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    
    def test_validate_metadata_sprites_schema_valid(self):
        """Test metadata validation with valid sprites.toml content."""
        valid_sprites_toml = """
[tiles]
[tiles.grass]
kind = "tile"
size = [64, 32]
source = "sprites/grass.png"

[buildings]
[buildings.lumberjack]
kind = "building"
size = [128, 96]
source = "sprites/lumberjack.png"
tile_footprint = [2, 1]

[units]
[units.worker]
kind = "unit"
source = "atlases/worker_atlas.png"
frame_size = [64, 64]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "dirs_rows"
atlas_map = "atlases/worker_atlas.json"
        """
        
        # Provide atlas data for validation
        mock_atlas_image = Mock(spec=Image.Image)
        mock_atlas_image.width, mock_atlas_image.height = 512, 512
        
        # Create atlas with correct number of frames (8 directions * 8 frames = 64)
        frame_map = {}
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        for dir_idx, direction in enumerate(directions):
            for frame_idx in range(8):
                frame_map[f"walk_{direction}_{frame_idx}"] = {
                    "x": frame_idx * 64, "y": dir_idx * 64, "w": 64, "h": 64
                }
        
        valid_atlas = AtlasResult(
            atlas=mock_atlas_image,
            frame_map=frame_map,
            metadata={"directions": 8, "frames_per_direction": 8}
        )
        
        errors = self.generator.validate_metadata(
            valid_sprites_toml, "sprites", None, {"worker_atlas": valid_atlas}
        )
        self.assertEqual(errors, [])
    
    def test_validate_metadata_sprites_schema_invalid(self):
        """Test metadata validation with invalid sprites.toml content."""
        invalid_sprites_toml = """
[tiles]
[tiles.grass]
kind = "wrong_kind"
size = [32, 64]
# missing source field

[buildings]
[buildings.lumberjack]
kind = "building"
size = "invalid_size"
source = "sprites/lumberjack.png"

[units]
[units.worker]
kind = "unit"
source = "atlases/worker_atlas.png"
frame_size = [32, 32]
directions = ["N", "S"]
anim_walk_fps = -5
atlas_map = "atlases/worker_atlas.json"
        """
        
        errors = self.generator.validate_metadata(invalid_sprites_toml, "sprites")
        
        # Should have multiple validation errors
        self.assertGreater(len(errors), 0)
        
        # Check for specific error types
        error_text = " ".join(errors)
        self.assertIn("kind should be 'tile'", error_text)
        self.assertIn("tiles must be 64x32 pixels", error_text)
        self.assertIn("missing required field 'source'", error_text)
        self.assertIn("size must be [width, height]", error_text)
        self.assertIn("unit frames must be 64x64 pixels", error_text)
        self.assertIn("anim_walk_fps must be positive integer", error_text)
    
    def test_validate_metadata_mod_schema_valid(self):
        """Test metadata validation with valid mod.toml content."""
        valid_mod_toml = """
[mod]
name = "test_mod"
version = "1.0.0"
description = "Test mod"

[assets]
tiles = ["grass", "stone"]
buildings = ["lumberjack"]
units = ["worker"]

[dependencies]
base_game = ">=1.0.0"
        """
        
        errors = self.generator.validate_metadata(valid_mod_toml, "mod")
        self.assertEqual(errors, [])
    
    def test_validate_metadata_mod_schema_invalid(self):
        """Test metadata validation with invalid mod.toml content."""
        invalid_mod_toml = """
[mod]
# missing name field
version = "1.0.0"
description = ""

[assets]
invalid_type = ["item1"]
tiles = "not_a_list"
        """
        
        errors = self.generator.validate_metadata(invalid_mod_toml, "mod")
        
        # Should have multiple validation errors
        self.assertGreater(len(errors), 0)
        
        error_text = " ".join(errors)
        self.assertIn("missing required field: name", error_text)
        self.assertIn("must be a non-empty string", error_text)
        self.assertIn("Unknown asset type", error_text)
        self.assertIn("must be a list", error_text)
    
    def test_validate_file_references(self):
        """Test file reference validation."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            sprites_dir = Path(temp_dir) / "sprites"
            sprites_dir.mkdir()
            (sprites_dir / "grass.png").touch()
            # Don't create lumberjack.png to test missing file
            
            sprites_toml = """
[tiles]
[tiles.grass]
kind = "tile"
size = [64, 32]
source = "sprites/grass.png"

[buildings]
[buildings.lumberjack]
kind = "building"
size = [128, 96]
source = "sprites/lumberjack.png"
            """
            
            errors = self.generator.validate_metadata(sprites_toml, "sprites", temp_dir)
            
            # Should find missing file
            self.assertGreater(len(errors), 0)
            self.assertTrue(any("lumberjack.png" in error and "not found" in error for error in errors))
            self.assertFalse(any("grass.png" in error and "not found" in error for error in errors))
    
    def test_validate_atlas_references(self):
        """Test atlas cross-reference validation."""
        # Create mock atlas with inconsistent data
        mock_atlas_image = Mock(spec=Image.Image)
        mock_atlas_image.width, mock_atlas_image.height = 512, 512
        
        # Atlas with wrong number of frames (should be 8 directions * 8 frames = 64)
        inconsistent_atlas = AtlasResult(
            atlas=mock_atlas_image,
            frame_map={
                "walk_N_0": {"x": 0, "y": 0, "w": 64, "h": 64},
                "walk_N_1": {"x": 64, "y": 0, "w": 64, "h": 64}
                # Missing other frames
            },
            metadata={"directions": 8, "frames_per_direction": 8}
        )
        
        sprites_toml = """
[units]
[units.worker]
kind = "unit"
source = "atlases/worker_atlas.png"
frame_size = [64, 64]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "dirs_rows"
atlas_map = "atlases/worker_atlas.json"
        """
        
        errors = self.generator.validate_metadata(
            sprites_toml, "sprites", None, {"worker_atlas": inconsistent_atlas}
        )
        
        # Should find frame count mismatch
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("atlas has 2 frames but metadata expects 64" in error for error in errors))
    
    def test_validate_atlas_references_missing_atlas(self):
        """Test validation when referenced atlas is missing."""
        sprites_toml = """
[units]
[units.worker]
kind = "unit"
source = "atlases/worker_atlas.png"
frame_size = [64, 64]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "dirs_rows"
atlas_map = "atlases/worker_atlas.json"
        """
        
        errors = self.generator.validate_metadata(sprites_toml, "sprites", None, {})
        
        # Should find missing atlas
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("atlas not found" in error for error in errors))
    
    def test_validate_metadata_syntax_error_first(self):
        """Test that syntax errors are caught before schema validation."""
        invalid_toml = """
[section
invalid syntax
        """
        
        errors = self.generator.validate_metadata(invalid_toml, "sprites")
        
        # Should only have syntax errors, not schema errors
        self.assertGreater(len(errors), 0)
        self.assertTrue(all("TOML syntax error" in error for error in errors))
    
    def test_ensure_template_directory_creates_defaults(self):
        """Test that ensure_template_directory creates default templates."""
        # Remove existing templates
        import shutil
        shutil.rmtree(self.template_dir)
        
        # Recreate generator (should create templates)
        generator = MetadataGenerator(str(self.template_dir))
        
        # Verify templates were created
        self.assertTrue((self.template_dir / "sprites.toml.j2").exists())
        self.assertTrue((self.template_dir / "mod.toml.j2").exists())
        
        # Verify templates have content
        sprites_template = (self.template_dir / "sprites.toml.j2").read_text()
        self.assertIn("{% if tiles %}", sprites_template)
        self.assertIn("{% if buildings %}", sprites_template)
        self.assertIn("{% if units %}", sprites_template)
        
        mod_template = (self.template_dir / "mod.toml.j2").read_text()
        self.assertIn("[mod]", mod_template)
        self.assertIn("{{ mod_name }}", mod_template)


class TestMetadataGenerationError(unittest.TestCase):
    """Test cases for MetadataGenerationError exception."""
    
    def test_error_creation(self):
        """Test MetadataGenerationError creation."""
        error = MetadataGenerationError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.message, "Test error message")


if __name__ == '__main__':
    unittest.main()