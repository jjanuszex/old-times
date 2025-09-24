"""
Tests for Kenney asset pack provider.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import zipfile
import json
from pathlib import Path
from PIL import Image
import io
import requests

from scripts.asset_pipeline.providers.kenney import KenneyProvider
from scripts.asset_pipeline.providers.base import AssetSpec, NetworkError, ConfigurationError, ProviderError


class TestKenneyProvider(unittest.TestCase):
    """Test KenneyProvider functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "cache_dir": self.temp_dir,
            "packs": ["isometric-buildings", "isometric-tiles"]
        }
        self.provider = KenneyProvider(self.config)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test provider initialization."""
        self.assertEqual(str(self.provider.cache_dir), self.temp_dir)
        self.assertEqual(self.provider.selected_packs, ["isometric-buildings", "isometric-tiles"])
        self.assertFalse(self.provider.is_configured())
    
    def test_configure_valid(self):
        """Test valid configuration."""
        config = {
            "cache_dir": self.temp_dir,
            "packs": ["isometric-buildings"]
        }
        
        self.provider.configure(config)
        
        self.assertTrue(self.provider.is_configured())
        self.assertEqual(self.provider.selected_packs, ["isometric-buildings"])
    
    def test_configure_invalid_packs(self):
        """Test configuration with invalid packs."""
        config = {
            "packs": ["invalid-pack"]
        }
        
        with self.assertRaises(ConfigurationError):
            self.provider.configure(config)
    
    def test_validate_config_valid(self):
        """Test config validation with valid config."""
        config = {
            "cache_dir": "/tmp/test",
            "packs": ["isometric-buildings"],
            "asset_mappings": {"pack1": {"old.png": "new.png"}}
        }
        
        errors = self.provider.validate_config(config)
        self.assertEqual(errors, [])
    
    def test_validate_config_invalid_packs_type(self):
        """Test config validation with invalid packs type."""
        config = {"packs": "not-a-list"}
        
        errors = self.provider.validate_config(config)
        self.assertIn("'packs' must be a list", errors)
    
    def test_validate_config_unknown_pack(self):
        """Test config validation with unknown pack."""
        config = {"packs": ["unknown-pack"]}
        
        errors = self.provider.validate_config(config)
        self.assertTrue(any("Unknown pack" in error for error in errors))
    
    def test_validate_config_invalid_cache_dir(self):
        """Test config validation with invalid cache_dir."""
        config = {"cache_dir": 123}
        
        errors = self.provider.validate_config(config)
        self.assertIn("'cache_dir' must be a string", errors)
    
    def test_validate_config_invalid_mappings(self):
        """Test config validation with invalid asset_mappings."""
        config = {"asset_mappings": "not-a-dict"}
        
        errors = self.provider.validate_config(config)
        self.assertIn("'asset_mappings' must be a dictionary", errors)
    
    def test_get_available_assets(self):
        """Test getting available assets."""
        self.provider.configure(self.config)
        
        assets = self.provider.get_available_assets()
        
        self.assertGreater(len(assets), 0)
        
        # Check that we have assets from both packs
        pack_names = {asset.metadata["pack"] for asset in assets}
        self.assertIn("isometric-buildings", pack_names)
        self.assertIn("isometric-tiles", pack_names)
        
        # Check asset properties
        for asset in assets:
            self.assertIsInstance(asset, AssetSpec)
            self.assertIn(asset.asset_type, ["tile", "building", "unit"])
            self.assertIsInstance(asset.size, tuple)
            self.assertEqual(len(asset.size), 2)
            self.assertIn("pack", asset.metadata)
            self.assertIn("kenney_name", asset.metadata)
    
    def test_determine_asset_properties_building(self):
        """Test asset property determination for buildings."""
        asset_type, size = self.provider._determine_asset_properties("lumberjack.png")
        self.assertEqual(asset_type, "building")
        self.assertEqual(size, (64, 96))
    
    def test_determine_asset_properties_unit(self):
        """Test asset property determination for units."""
        asset_type, size = self.provider._determine_asset_properties("worker.png")
        self.assertEqual(asset_type, "unit")
        self.assertEqual(size, (64, 64))
    
    def test_determine_asset_properties_tile(self):
        """Test asset property determination for tiles."""
        asset_type, size = self.provider._determine_asset_properties("grass.png")
        self.assertEqual(asset_type, "tile")
        self.assertEqual(size, (64, 32))
    
    def test_get_cache_info(self):
        """Test getting cache information."""
        self.provider.configure(self.config)
        
        cache_info = self.provider.get_cache_info()
        
        self.assertIn("cache_dir", cache_info)
        self.assertIn("packs", cache_info)
        self.assertEqual(cache_info["cache_dir"], self.temp_dir)
        
        for pack_name in self.provider.selected_packs:
            self.assertIn(pack_name, cache_info["packs"])
            pack_info = cache_info["packs"][pack_name]
            self.assertIn("cached", pack_info)
            self.assertIn("extracted", pack_info)
            self.assertIn("size_mb", pack_info)
    
    def test_clear_cache_specific_pack(self):
        """Test clearing cache for specific pack."""
        self.provider.configure(self.config)
        
        # Create fake cache directory
        pack_dir = Path(self.temp_dir) / "isometric-buildings"
        pack_dir.mkdir(parents=True)
        (pack_dir / "test.txt").write_text("test")
        
        self.assertTrue(pack_dir.exists())
        
        self.provider.clear_cache("isometric-buildings")
        
        self.assertFalse(pack_dir.exists())
    
    def test_clear_cache_all(self):
        """Test clearing all cache."""
        self.provider.configure(self.config)
        
        # Create fake cache directories
        for pack_name in ["isometric-buildings", "isometric-tiles"]:
            pack_dir = Path(self.temp_dir) / pack_name
            pack_dir.mkdir(parents=True)
            (pack_dir / "test.txt").write_text("test")
        
        self.provider.clear_cache()
        
        # Cache dir should exist but be empty
        cache_dir = Path(self.temp_dir)
        self.assertTrue(cache_dir.exists())
        self.assertEqual(len(list(cache_dir.iterdir())), 0)
    
    def test_get_provider_info(self):
        """Test getting provider information."""
        self.provider.configure(self.config)
        
        info = self.provider.get_provider_info()
        
        self.assertIn("name", info)
        self.assertIn("configured", info)
        self.assertIn("available_packs", info)
        self.assertIn("selected_packs", info)
        self.assertIn("cache_info", info)
        
        self.assertEqual(info["name"], "KenneyProvider")
        self.assertTrue(info["configured"])
        self.assertEqual(info["selected_packs"], ["isometric-buildings", "isometric-tiles"])
    
    @patch('scripts.asset_pipeline.providers.kenney.requests.Session.get')
    def test_download_pack_success(self, mock_get):
        """Test successful pack download."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b'fake zip data']
        mock_get.return_value = mock_response
        
        output_path = Path(self.temp_dir) / "test.zip"
        
        self.provider._download_pack("http://example.com/test.zip", output_path)
        
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.read_bytes(), b'fake zip data')
    
    @patch('scripts.asset_pipeline.providers.kenney.requests.Session.get')
    def test_download_pack_network_error(self, mock_get):
        """Test pack download with network error."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        output_path = Path(self.temp_dir) / "test.zip"
        
        with self.assertRaises(NetworkError):
            self.provider._download_pack("http://example.com/test.zip", output_path)
    
    def test_extract_pack_success(self):
        """Test successful pack extraction."""
        # Create a test zip file
        zip_path = Path(self.temp_dir) / "test.zip"
        extract_dir = Path(self.temp_dir) / "extracted"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test.txt", "test content")
            zf.writestr("subdir/test2.txt", "test content 2")
        
        self.provider._extract_pack(zip_path, extract_dir)
        
        self.assertTrue((extract_dir / "test.txt").exists())
        self.assertTrue((extract_dir / "subdir" / "test2.txt").exists())
        self.assertEqual((extract_dir / "test.txt").read_text(), "test content")
    
    def test_extract_pack_bad_zip(self):
        """Test pack extraction with bad zip file."""
        zip_path = Path(self.temp_dir) / "bad.zip"
        extract_dir = Path(self.temp_dir) / "extracted"
        
        # Create invalid zip file
        zip_path.write_text("not a zip file")
        
        with self.assertRaises(ProviderError):
            self.provider._extract_pack(zip_path, extract_dir)
    
    def test_find_asset_in_pack_exact_match(self):
        """Test finding asset with exact filename match."""
        pack_dir = Path(self.temp_dir) / "pack"
        pack_dir.mkdir()
        
        # Create test asset file
        asset_file = pack_dir / "test_asset.png"
        asset_file.write_text("fake image")
        
        found_path = self.provider._find_asset_in_pack(pack_dir, "test_asset.png")
        
        self.assertEqual(found_path, asset_file)
    
    def test_find_asset_in_pack_case_insensitive(self):
        """Test finding asset with case-insensitive match."""
        pack_dir = Path(self.temp_dir) / "pack"
        pack_dir.mkdir()
        
        # Create test asset file with different case
        asset_file = pack_dir / "TEST_ASSET.PNG"
        asset_file.write_text("fake image")
        
        found_path = self.provider._find_asset_in_pack(pack_dir, "test_asset.png")
        
        self.assertEqual(found_path, asset_file)
    
    def test_find_asset_in_pack_not_found(self):
        """Test finding asset that doesn't exist."""
        pack_dir = Path(self.temp_dir) / "pack"
        pack_dir.mkdir()
        
        found_path = self.provider._find_asset_in_pack(pack_dir, "nonexistent.png")
        
        self.assertIsNone(found_path)
    
    def test_find_asset_in_pack_subdirectory(self):
        """Test finding asset in subdirectory."""
        pack_dir = Path(self.temp_dir) / "pack"
        subdir = pack_dir / "sprites"
        subdir.mkdir(parents=True)
        
        # Create test asset file in subdirectory
        asset_file = subdir / "test_asset.png"
        asset_file.write_text("fake image")
        
        found_path = self.provider._find_asset_in_pack(pack_dir, "test_asset.png")
        
        self.assertEqual(found_path, asset_file)
    
    def test_fetch_asset_missing_metadata(self):
        """Test fetching asset with missing metadata."""
        spec = AssetSpec("test", "tile", (64, 32))
        
        with self.assertRaises(ProviderError):
            self.provider.fetch_asset(spec)
    
    def test_fetch_asset_file_not_found(self):
        """Test fetching asset when file not found in pack."""
        self.provider.configure(self.config)
        
        spec = AssetSpec(
            "test", "tile", (64, 32),
            metadata={"pack": "isometric-tiles", "kenney_name": "nonexistent.png"}
        )
        
        with patch.object(self.provider, '_ensure_pack_downloaded') as mock_ensure:
            mock_ensure.return_value = Path(self.temp_dir)
            
            with self.assertRaises(ProviderError):
                self.provider.fetch_asset(spec)


if __name__ == '__main__':
    unittest.main()