"""
Integration tests for asset provider system.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil
from pathlib import Path

from scripts.asset_pipeline.providers import (
    provider_registry, KenneyProvider, StubAIProvider,
    AssetSpec, ProviderError, ConfigurationError
)


class TestProviderIntegration(unittest.TestCase):
    """Test provider system integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        # Clear registry for clean tests
        provider_registry.clear_providers()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        provider_registry.clear_providers()
    
    def test_provider_registry_has_classes(self):
        """Test that provider classes are registered."""
        available_classes = provider_registry.list_available_provider_classes()
        
        self.assertIn("kenney", available_classes)
        self.assertIn("ai_stub", available_classes)
        self.assertIn("stable_diffusion", available_classes)
        self.assertIn("replicate", available_classes)
        self.assertIn("openai", available_classes)
    
    def test_create_kenney_provider(self):
        """Test creating and configuring Kenney provider."""
        config = {
            "cache_dir": self.temp_dir,
            "packs": ["isometric-buildings"]
        }
        
        provider = provider_registry.create_provider("kenney", config)
        
        self.assertIsInstance(provider, KenneyProvider)
        self.assertTrue(provider.is_configured())
    
    def test_create_ai_stub_provider(self):
        """Test creating and configuring AI stub provider."""
        config = {"style": "medieval"}
        
        provider = provider_registry.create_provider("ai_stub", config)
        
        self.assertIsInstance(provider, StubAIProvider)
        self.assertTrue(provider.is_configured())
    
    def test_register_and_use_providers(self):
        """Test registering multiple providers and using them."""
        # Create and register Kenney provider
        kenney_config = {
            "cache_dir": self.temp_dir,
            "packs": ["isometric-buildings"]
        }
        kenney_provider = provider_registry.create_provider("kenney", kenney_config)
        provider_registry.register_provider("kenney_main", kenney_provider)
        
        # Create and register AI stub provider
        ai_config = {
            "style": "medieval",
            "asset_descriptions": {"custom_tile": "custom grass tile"}
        }
        ai_provider = provider_registry.create_provider("ai_stub", ai_config)
        provider_registry.register_provider("ai_main", ai_provider)
        
        # Test getting providers
        retrieved_kenney = provider_registry.get_provider("kenney_main")
        retrieved_ai = provider_registry.get_provider("ai_main")
        
        self.assertIs(retrieved_kenney, kenney_provider)
        self.assertIs(retrieved_ai, ai_provider)
        
        # Test getting all providers
        all_providers = provider_registry.get_all_providers()
        self.assertEqual(len(all_providers), 2)
        self.assertIn("kenney_main", all_providers)
        self.assertIn("ai_main", all_providers)
    
    def test_get_all_available_assets(self):
        """Test getting assets from multiple providers."""
        # Register Kenney provider
        kenney_config = {
            "cache_dir": self.temp_dir,
            "packs": ["isometric-buildings"]
        }
        kenney_provider = provider_registry.create_provider("kenney", kenney_config)
        provider_registry.register_provider("kenney", kenney_provider)
        
        # Register AI provider with custom assets
        ai_config = {
            "style": "medieval",
            "asset_descriptions": {
                "custom_grass": "custom green grass tile",
                "custom_worker": "custom medieval worker"
            }
        }
        ai_provider = provider_registry.create_provider("ai_stub", ai_config)
        provider_registry.register_provider("ai", ai_provider)
        
        # Get all available assets
        all_assets = provider_registry.get_all_available_assets()
        
        self.assertIn("kenney", all_assets)
        self.assertIn("ai", all_assets)
        
        # Kenney should have assets from the pack
        kenney_assets = all_assets["kenney"]
        self.assertGreater(len(kenney_assets), 0)
        
        # AI provider should have no assets (stub returns empty list)
        ai_assets = all_assets["ai"]
        self.assertEqual(len(ai_assets), 0)
    
    def test_provider_error_handling(self):
        """Test error handling in provider registry."""
        # Test creating unknown provider
        with self.assertRaises(ValueError):
            provider_registry.create_provider("unknown", {})
        
        # Test getting unregistered provider
        with self.assertRaises(ValueError):
            provider_registry.get_provider("unregistered")
        
        # Test configuration error
        with self.assertRaises(ConfigurationError):
            provider_registry.create_provider("kenney", {"packs": ["invalid-pack"]})
    
    def test_provider_info(self):
        """Test getting provider information."""
        config = {
            "cache_dir": self.temp_dir,
            "packs": ["isometric-buildings"]
        }
        
        provider = provider_registry.create_provider("kenney", config)
        provider_registry.register_provider("test_kenney", provider)
        
        info = provider.get_provider_info()
        
        self.assertIn("name", info)
        self.assertIn("configured", info)
        self.assertEqual(info["name"], "KenneyProvider")
        self.assertTrue(info["configured"])
    
    def test_asset_spec_validation(self):
        """Test AssetSpec validation across providers."""
        # Valid specs
        valid_specs = [
            AssetSpec("grass", "tile", (64, 32)),
            AssetSpec("lumberjack", "building", (64, 96)),
            AssetSpec("worker", "unit", (64, 64))
        ]
        
        for spec in valid_specs:
            self.assertIn(spec.asset_type, ["tile", "building", "unit"])
            self.assertEqual(len(spec.size), 2)
            self.assertGreater(spec.size[0], 0)
            self.assertGreater(spec.size[1], 0)
        
        # Invalid specs should raise errors
        with self.assertRaises(ValueError):
            AssetSpec("invalid", "invalid_type", (64, 32))
        
        with self.assertRaises(ValueError):
            AssetSpec("invalid", "tile", (0, 32))
    
    def test_provider_registry_cleanup(self):
        """Test provider registry cleanup operations."""
        # Add some providers
        config = {"style": "medieval"}
        provider1 = provider_registry.create_provider("ai_stub", config)
        provider2 = provider_registry.create_provider("ai_stub", config)
        
        provider_registry.register_provider("provider1", provider1)
        provider_registry.register_provider("provider2", provider2)
        
        self.assertEqual(len(provider_registry.list_registered_providers()), 2)
        
        # Remove one provider
        provider_registry.remove_provider("provider1")
        self.assertEqual(len(provider_registry.list_registered_providers()), 1)
        self.assertNotIn("provider1", provider_registry.list_registered_providers())
        
        # Clear all providers
        provider_registry.clear_providers()
        self.assertEqual(len(provider_registry.list_registered_providers()), 0)


if __name__ == '__main__':
    unittest.main()