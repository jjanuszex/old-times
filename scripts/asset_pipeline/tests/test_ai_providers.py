"""
Tests for AI asset providers.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from PIL import Image
import io
import requests

from scripts.asset_pipeline.providers.ai_providers import (
    PromptTemplate, AIProvider, StubAIProvider, StableDiffusionProvider,
    ReplicateProvider, OpenAIProvider, AIProviderFactory
)
from scripts.asset_pipeline.providers.base import AssetSpec, NetworkError, ConfigurationError, ProviderError


class TestPromptTemplate(unittest.TestCase):
    """Test PromptTemplate functionality."""
    
    def setUp(self):
        """Set up test template."""
        self.template = PromptTemplate("medieval")
    
    def test_init(self):
        """Test template initialization."""
        self.assertEqual(self.template.style, "medieval")
    
    def test_generate_prompt_tile(self):
        """Test prompt generation for tile."""
        spec = AssetSpec("grass", "tile", (64, 32))
        
        result = self.template.generate_prompt(spec, "green grass field")
        
        self.assertIn("prompt", result)
        self.assertIn("negative_prompt", result)
        self.assertIn("style", result)
        self.assertIn("green grass field", result["prompt"])
        self.assertIn("isometric", result["prompt"])
        self.assertIn("64x32", result["prompt"])
        self.assertIn("medieval", result["prompt"])
        self.assertIn("blurry", result["negative_prompt"])
    
    def test_generate_prompt_building(self):
        """Test prompt generation for building."""
        spec = AssetSpec("lumberjack", "building", (64, 96))
        
        result = self.template.generate_prompt(spec, "wooden lumberjack hut")
        
        self.assertIn("wooden lumberjack hut", result["prompt"])
        self.assertIn("building", result["prompt"])
        self.assertIn("64x96", result["prompt"])
        self.assertIn("medieval", result["prompt"])
    
    def test_generate_prompt_unit(self):
        """Test prompt generation for unit."""
        spec = AssetSpec("worker", "unit", (64, 64))
        
        result = self.template.generate_prompt(spec, "medieval worker character")
        
        self.assertIn("medieval worker character", result["prompt"])
        self.assertIn("character", result["prompt"])
        self.assertIn("64x64", result["prompt"])
        self.assertIn("medieval", result["prompt"])
    
    def test_different_styles(self):
        """Test different style templates."""
        spec = AssetSpec("test", "tile", (64, 32))
        
        for style in ["medieval", "modern", "fantasy", "retro"]:
            template = PromptTemplate(style)
            result = template.generate_prompt(spec, "test description")
            self.assertIn(style, result["prompt"])


class TestStubAIProvider(unittest.TestCase):
    """Test StubAIProvider functionality."""
    
    def setUp(self):
        """Set up test provider."""
        self.config = {"style": "medieval"}
        self.provider = StubAIProvider(self.config)
    
    def test_init(self):
        """Test provider initialization."""
        self.assertFalse(self.provider.is_configured())
    
    def test_configure(self):
        """Test provider configuration."""
        self.provider.configure(self.config)
        self.assertTrue(self.provider.is_configured())
    
    def test_get_available_assets(self):
        """Test getting available assets (should be empty)."""
        self.provider.configure(self.config)
        assets = self.provider.get_available_assets()
        self.assertEqual(assets, [])
    
    def test_generate_image(self):
        """Test image generation (placeholder)."""
        prompt_data = {
            "prompt": "test prompt",
            "negative_prompt": "test negative",
            "style": "medieval"
        }
        
        image_data = self.provider.generate_image(prompt_data, (64, 32))
        
        self.assertIsInstance(image_data, bytes)
        
        # Verify it's a valid PNG
        img = Image.open(io.BytesIO(image_data))
        self.assertEqual(img.size, (64, 32))
        self.assertEqual(img.mode, 'RGBA')


class TestStableDiffusionProvider(unittest.TestCase):
    """Test StableDiffusionProvider functionality."""
    
    def setUp(self):
        """Set up test provider."""
        self.config = {
            "api_url": "http://localhost:7860",
            "steps": 20,
            "cfg_scale": 7.0,
            "asset_descriptions": {"grass": "green grass tile"}
        }
        self.provider = StableDiffusionProvider(self.config)
    
    def test_init(self):
        """Test provider initialization."""
        self.assertEqual(self.provider.api_url, "http://localhost:7860")
        self.assertEqual(self.provider.steps, 20)
        self.assertEqual(self.provider.cfg_scale, 7.0)
    
    def test_validate_config_valid(self):
        """Test valid configuration validation."""
        errors = self.provider.validate_config(self.config)
        self.assertEqual(errors, [])
    
    def test_validate_config_missing_api_url(self):
        """Test validation with missing API URL."""
        config = {"steps": 20}
        errors = self.provider.validate_config(config)
        self.assertTrue(any("api_url" in error for error in errors))
    
    def test_validate_config_invalid_steps(self):
        """Test validation with invalid steps."""
        config = {"api_url": "http://localhost:7860", "steps": 0}
        errors = self.provider.validate_config(config)
        self.assertTrue(any("steps" in error for error in errors))
    
    def test_validate_config_invalid_cfg_scale(self):
        """Test validation with invalid cfg_scale."""
        config = {"api_url": "http://localhost:7860", "cfg_scale": 25}
        errors = self.provider.validate_config(config)
        self.assertTrue(any("cfg_scale" in error for error in errors))
    
    @patch('scripts.asset_pipeline.providers.ai_providers.requests.get')
    def test_configure_success(self, mock_get):
        """Test successful configuration."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        self.provider.configure(self.config)
        
        self.assertTrue(self.provider.is_configured())
        mock_get.assert_called_once()
    
    @patch('scripts.asset_pipeline.providers.ai_providers.requests.get')
    def test_configure_connection_error(self, mock_get):
        """Test configuration with connection error."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with self.assertRaises(ConfigurationError):
            self.provider.configure(self.config)
    
    @patch('scripts.asset_pipeline.providers.ai_providers.requests.post')
    def test_generate_image_success(self, mock_post):
        """Test successful image generation."""
        # Create a test image and encode it
        test_img = Image.new('RGBA', (64, 32), (255, 0, 0, 255))
        buf = io.BytesIO()
        test_img.save(buf, format='PNG')
        test_img_b64 = base64.b64encode(buf.getvalue()).decode()
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"images": [test_img_b64]}
        mock_post.return_value = mock_response
        
        prompt_data = {
            "prompt": "test prompt",
            "negative_prompt": "test negative",
            "style": "medieval"
        }
        
        result = self.provider.generate_image(prompt_data, (64, 32))
        
        self.assertIsInstance(result, bytes)
        # Verify the returned image
        img = Image.open(io.BytesIO(result))
        self.assertEqual(img.size, (64, 32))
    
    @patch('scripts.asset_pipeline.providers.ai_providers.requests.post')
    def test_generate_image_no_images(self, mock_post):
        """Test image generation with no images returned."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"images": []}
        mock_post.return_value = mock_response
        
        prompt_data = {
            "prompt": "test prompt",
            "negative_prompt": "test negative",
            "style": "medieval"
        }
        
        with self.assertRaises(ProviderError):
            self.provider.generate_image(prompt_data, (64, 32))
    
    @patch('scripts.asset_pipeline.providers.ai_providers.requests.post')
    def test_generate_image_network_error(self, mock_post):
        """Test image generation with network error."""
        mock_post.side_effect = requests.RequestException("Network error")
        
        prompt_data = {
            "prompt": "test prompt",
            "negative_prompt": "test negative",
            "style": "medieval"
        }
        
        with self.assertRaises(NetworkError):
            self.provider.generate_image(prompt_data, (64, 32))


class TestReplicateProvider(unittest.TestCase):
    """Test ReplicateProvider functionality."""
    
    def setUp(self):
        """Set up test provider."""
        self.config = {
            "api_token": "test_token",
            "asset_descriptions": {"grass": "green grass tile"}
        }
        self.provider = ReplicateProvider(self.config)
    
    def test_init(self):
        """Test provider initialization."""
        self.assertEqual(self.provider.api_token, "test_token")
        self.assertIn("stability-ai", self.provider.model)
    
    def test_validate_config_valid(self):
        """Test valid configuration validation."""
        errors = self.provider.validate_config(self.config)
        self.assertEqual(errors, [])
    
    def test_validate_config_missing_token(self):
        """Test validation with missing API token."""
        config = {}
        errors = self.provider.validate_config(config)
        self.assertTrue(any("api_token" in error for error in errors))
    
    def test_configure(self):
        """Test provider configuration."""
        self.provider.configure(self.config)
        self.assertTrue(self.provider.is_configured())


class TestOpenAIProvider(unittest.TestCase):
    """Test OpenAIProvider functionality."""
    
    def setUp(self):
        """Set up test provider."""
        self.config = {
            "api_key": "test_key",
            "model": "dall-e-3",
            "asset_descriptions": {"grass": "green grass tile"}
        }
        self.provider = OpenAIProvider(self.config)
    
    def test_init(self):
        """Test provider initialization."""
        self.assertEqual(self.provider.api_key, "test_key")
        self.assertEqual(self.provider.model, "dall-e-3")
    
    def test_validate_config_valid(self):
        """Test valid configuration validation."""
        errors = self.provider.validate_config(self.config)
        self.assertEqual(errors, [])
    
    def test_validate_config_missing_key(self):
        """Test validation with missing API key."""
        config = {}
        errors = self.provider.validate_config(config)
        self.assertTrue(any("api_key" in error for error in errors))
    
    def test_validate_config_invalid_model(self):
        """Test validation with invalid model."""
        config = {"api_key": "test", "model": "invalid-model"}
        errors = self.provider.validate_config(config)
        self.assertTrue(any("model" in error for error in errors))
    
    def test_get_dalle_size_dalle3(self):
        """Test DALL-E 3 size mapping."""
        self.provider.model = "dall-e-3"
        
        # Wide aspect ratio
        size = self.provider._get_dalle_size((128, 64))
        self.assertEqual(size, "1344x768")
        
        # Medium aspect ratio
        size = self.provider._get_dalle_size((96, 64))
        self.assertEqual(size, "1152x896")
        
        # Square-ish
        size = self.provider._get_dalle_size((64, 64))
        self.assertEqual(size, "1024x1024")
    
    def test_get_dalle_size_dalle2(self):
        """Test DALL-E 2 size mapping."""
        self.provider.model = "dall-e-2"
        
        # Small size
        size = self.provider._get_dalle_size((64, 32))
        self.assertEqual(size, "256x256")
        
        # Medium size (max dimension 300 should map to 512x512)
        size = self.provider._get_dalle_size((300, 200))
        self.assertEqual(size, "512x512")
        
        # Large size
        size = self.provider._get_dalle_size((600, 600))
        self.assertEqual(size, "1024x1024")


class TestAIProviderFactory(unittest.TestCase):
    """Test AIProviderFactory functionality."""
    
    def test_list_providers(self):
        """Test listing available providers."""
        providers = AIProviderFactory.list_providers()
        
        self.assertIn("stub", providers)
        self.assertIn("stable_diffusion", providers)
        self.assertIn("replicate", providers)
        self.assertIn("openai", providers)
    
    def test_create_stub_provider(self):
        """Test creating stub provider."""
        config = {"style": "medieval"}
        provider = AIProviderFactory.create_provider("stub", config)
        
        self.assertIsInstance(provider, StubAIProvider)
    
    def test_create_stable_diffusion_provider(self):
        """Test creating Stable Diffusion provider."""
        config = {"api_url": "http://localhost:7860"}
        provider = AIProviderFactory.create_provider("stable_diffusion", config)
        
        self.assertIsInstance(provider, StableDiffusionProvider)
    
    def test_create_replicate_provider(self):
        """Test creating Replicate provider."""
        config = {"api_token": "test_token"}
        provider = AIProviderFactory.create_provider("replicate", config)
        
        self.assertIsInstance(provider, ReplicateProvider)
    
    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        config = {"api_key": "test_key"}
        provider = AIProviderFactory.create_provider("openai", config)
        
        self.assertIsInstance(provider, OpenAIProvider)
    
    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with self.assertRaises(ValueError):
            AIProviderFactory.create_provider("unknown", {})


class TestAIProviderBase(unittest.TestCase):
    """Test base AIProvider functionality."""
    
    def setUp(self):
        """Set up test provider."""
        self.config = {
            "style": "medieval",
            "asset_descriptions": {
                "grass": "green grass field",
                "lumberjack": "wooden lumberjack hut",
                "worker": "medieval worker character"
            }
        }
        self.provider = StubAIProvider(self.config)
        self.provider.configure(self.config)
    
    def test_determine_asset_properties_building(self):
        """Test asset property determination for buildings."""
        asset_type, size = self.provider._determine_asset_properties("lumberjack_hut")
        self.assertEqual(asset_type, "building")
        self.assertEqual(size, (64, 96))
    
    def test_determine_asset_properties_unit(self):
        """Test asset property determination for units."""
        asset_type, size = self.provider._determine_asset_properties("worker_character")
        self.assertEqual(asset_type, "unit")
        self.assertEqual(size, (64, 64))
    
    def test_determine_asset_properties_tile(self):
        """Test asset property determination for tiles."""
        asset_type, size = self.provider._determine_asset_properties("grass_tile")
        self.assertEqual(asset_type, "tile")
        self.assertEqual(size, (64, 32))


if __name__ == '__main__':
    unittest.main()