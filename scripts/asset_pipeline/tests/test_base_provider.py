"""
Tests for base provider interface and registry.
"""

import unittest
from unittest.mock import Mock, patch
from PIL import Image
import io

from scripts.asset_pipeline.providers.base import (
    AssetSpec, ProcessedAsset, AssetProvider, ProviderRegistry,
    ProviderError, AssetNotFoundError, ConfigurationError, NetworkError,
    provider_registry
)


class MockProvider(AssetProvider):
    """Mock provider for testing."""
    
    def __init__(self, config):
        super().__init__(config)
        self.assets = []
    
    def get_available_assets(self):
        return self.assets
    
    def fetch_asset(self, spec):
        # Create a simple 1x1 red pixel image
        img = Image.new('RGBA', (1, 1), (255, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    
    def configure(self, config):
        self._configured = True
        if config.get('fail_config'):
            raise ValueError("Configuration failed")


class TestAssetSpec(unittest.TestCase):
    """Test AssetSpec dataclass."""
    
    def test_valid_asset_spec(self):
        """Test creating valid asset spec."""
        spec = AssetSpec(
            name="test_tile",
            asset_type="tile",
            size=(64, 32),
            source_path="test.png"
        )
        
        self.assertEqual(spec.name, "test_tile")
        self.assertEqual(spec.asset_type, "tile")
        self.assertEqual(spec.size, (64, 32))
        self.assertEqual(spec.source_path, "test.png")
        self.assertEqual(spec.metadata, {})
    
    def test_invalid_asset_type(self):
        """Test that invalid asset type raises ValueError."""
        with self.assertRaises(ValueError):
            AssetSpec(
                name="test",
                asset_type="invalid",
                size=(64, 32)
            )
    
    def test_invalid_size(self):
        """Test that invalid size raises ValueError."""
        with self.assertRaises(ValueError):
            AssetSpec(
                name="test",
                asset_type="tile",
                size=(-1, 32)
            )
        
        with self.assertRaises(ValueError):
            AssetSpec(
                name="test",
                asset_type="tile",
                size=(64, -1)
            )


class TestProcessedAsset(unittest.TestCase):
    """Test ProcessedAsset dataclass."""
    
    def test_processed_asset_properties(self):
        """Test ProcessedAsset properties."""
        spec = AssetSpec("test", "tile", (64, 32))
        img = Image.new('RGBA', (64, 32), (255, 0, 0, 255))
        
        asset = ProcessedAsset(
            spec=spec,
            image=img,
            output_path="output/test.png"
        )
        
        self.assertEqual(asset.name, "test")
        self.assertEqual(asset.asset_type, "tile")
        self.assertEqual(asset.size, (64, 32))


class TestProviderRegistry(unittest.TestCase):
    """Test ProviderRegistry functionality."""
    
    def setUp(self):
        """Set up test registry."""
        self.registry = ProviderRegistry()
    
    def test_register_provider_class(self):
        """Test registering provider class."""
        self.registry.register_provider_class("mock", MockProvider)
        
        classes = self.registry.list_available_provider_classes()
        self.assertIn("mock", classes)
    
    def test_register_invalid_provider_class(self):
        """Test registering invalid provider class raises error."""
        class NotAProvider:
            pass
        
        with self.assertRaises(ValueError):
            self.registry.register_provider_class("invalid", NotAProvider)
    
    def test_create_provider(self):
        """Test creating provider instance."""
        self.registry.register_provider_class("mock", MockProvider)
        
        provider = self.registry.create_provider("mock", {})
        self.assertIsInstance(provider, MockProvider)
        self.assertTrue(provider.is_configured())
    
    def test_create_provider_with_config_error(self):
        """Test creating provider with configuration error."""
        self.registry.register_provider_class("mock", MockProvider)
        
        with self.assertRaises(ConfigurationError):
            self.registry.create_provider("mock", {"fail_config": True})
    
    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with self.assertRaises(ValueError):
            self.registry.create_provider("unknown", {})
    
    def test_register_and_get_provider(self):
        """Test registering and getting provider instance."""
        provider = MockProvider({})
        provider.configure({})
        
        self.registry.register_provider("test", provider)
        
        retrieved = self.registry.get_provider("test")
        self.assertIs(retrieved, provider)
    
    def test_get_unknown_provider(self):
        """Test getting unknown provider raises error."""
        with self.assertRaises(ValueError):
            self.registry.get_provider("unknown")
    
    def test_list_providers(self):
        """Test listing providers."""
        provider = MockProvider({})
        provider.configure({})
        
        self.registry.register_provider("test", provider)
        
        providers = self.registry.list_registered_providers()
        self.assertIn("test", providers)
    
    def test_remove_provider(self):
        """Test removing provider."""
        provider = MockProvider({})
        provider.configure({})
        
        self.registry.register_provider("test", provider)
        self.assertIn("test", self.registry.list_registered_providers())
        
        self.registry.remove_provider("test")
        self.assertNotIn("test", self.registry.list_registered_providers())
    
    def test_clear_providers(self):
        """Test clearing all providers."""
        provider = MockProvider({})
        provider.configure({})
        
        self.registry.register_provider("test", provider)
        self.assertEqual(len(self.registry.list_registered_providers()), 1)
        
        self.registry.clear_providers()
        self.assertEqual(len(self.registry.list_registered_providers()), 0)
    
    def test_get_all_available_assets(self):
        """Test getting all available assets from providers."""
        provider = MockProvider({})
        provider.configure({})
        provider.assets = [AssetSpec("test", "tile", (64, 32))]
        
        self.registry.register_provider("test", provider)
        
        all_assets = self.registry.get_all_available_assets()
        self.assertIn("test", all_assets)
        self.assertEqual(len(all_assets["test"]), 1)
        self.assertEqual(all_assets["test"][0].name, "test")


class TestProviderErrors(unittest.TestCase):
    """Test provider error classes."""
    
    def test_provider_error(self):
        """Test base ProviderError."""
        error = ProviderError("test message", "test_provider", recoverable=True)
        
        self.assertEqual(str(error), "test message")
        self.assertEqual(error.provider, "test_provider")
        self.assertTrue(error.recoverable)
    
    def test_asset_not_found_error(self):
        """Test AssetNotFoundError."""
        error = AssetNotFoundError("test_asset", "test_provider")
        
        self.assertIn("test_asset", str(error))
        self.assertEqual(error.provider, "test_provider")
        self.assertEqual(error.asset_name, "test_asset")
        self.assertFalse(error.recoverable)
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("invalid config", "test_provider")
        
        self.assertIn("Configuration error", str(error))
        self.assertEqual(error.provider, "test_provider")
        self.assertFalse(error.recoverable)
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("connection failed", "test_provider")
        
        self.assertIn("Network error", str(error))
        self.assertEqual(error.provider, "test_provider")
        self.assertTrue(error.recoverable)


if __name__ == '__main__':
    unittest.main()