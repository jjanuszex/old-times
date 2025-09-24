"""
AI-based asset providers for generating custom game assets.
"""

import os
import json
import base64
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import requests
from PIL import Image
import io

from .base import AssetProvider, AssetSpec, ProviderError, NetworkError, ConfigurationError


class PromptTemplate:
    """Template system for consistent AI asset generation prompts."""
    
    # Base prompts for different asset types
    BASE_PROMPTS = {
        "tile": "isometric 2D game tile, {description}, pixel art style, transparent background, 64x32 pixels, top-down isometric view, clean edges, game asset",
        "building": "isometric 2D game building, {description}, pixel art style, transparent background, isometric view, detailed architecture, game asset, {size_hint}",
        "unit": "isometric 2D game character, {description}, pixel art style, transparent background, 64x64 pixels, character sprite, game asset, animation frame"
    }
    
    # Style modifiers
    STYLE_MODIFIERS = {
        "medieval": "medieval fantasy style, stone and wood materials, rustic appearance",
        "modern": "modern style, clean lines, contemporary materials",
        "fantasy": "fantasy style, magical elements, vibrant colors",
        "retro": "retro pixel art style, 16-bit era graphics, nostalgic feel"
    }
    
    # Quality modifiers
    QUALITY_MODIFIERS = [
        "high quality",
        "detailed",
        "sharp edges",
        "clean pixel art",
        "professional game asset",
        "consistent lighting"
    ]
    
    def __init__(self, style: str = "medieval"):
        """Initialize prompt template with style."""
        self.style = style
    
    def generate_prompt(self, asset_spec: AssetSpec, description: str) -> str:
        """Generate AI prompt for asset specification."""
        base_prompt = self.BASE_PROMPTS.get(asset_spec.asset_type, self.BASE_PROMPTS["tile"])
        
        # Add size hint for buildings
        size_hint = ""
        if asset_spec.asset_type == "building":
            width, height = asset_spec.size
            if width > 64 or height > 64:
                size_hint = f"large building {width}x{height} pixels"
            else:
                size_hint = f"small building {width}x{height} pixels"
        
        # Build full prompt
        prompt_parts = [
            base_prompt.format(description=description, size_hint=size_hint),
            self.STYLE_MODIFIERS.get(self.style, ""),
            ", ".join(self.QUALITY_MODIFIERS)
        ]
        
        # Add negative prompt elements
        negative_elements = [
            "blurry",
            "low quality",
            "distorted",
            "3D",
            "realistic",
            "photographic",
            "background",
            "text",
            "watermark"
        ]
        
        full_prompt = ", ".join(filter(None, prompt_parts))
        negative_prompt = ", ".join(negative_elements)
        
        return {
            "prompt": full_prompt,
            "negative_prompt": negative_prompt,
            "style": self.style
        }


class AIProvider(AssetProvider):
    """Base class for AI asset providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize AI provider."""
        super().__init__(config)
        self.prompt_template = PromptTemplate(config.get("style", "medieval"))
        self.asset_descriptions = config.get("asset_descriptions", {})
        self.generation_params = config.get("generation_params", {})
    
    @abstractmethod
    def generate_image(self, prompt_data: Dict[str, str], size: tuple[int, int]) -> bytes:
        """
        Generate image using AI provider.
        
        Args:
            prompt_data: Dictionary with 'prompt', 'negative_prompt', 'style'
            size: Target image size (width, height)
            
        Returns:
            Generated image data as bytes
        """
        pass
    
    def get_available_assets(self) -> List[AssetSpec]:
        """Get list of assets that can be generated."""
        assets = []
        
        for asset_name, description in self.asset_descriptions.items():
            # Determine asset type and size from name
            asset_type, size = self._determine_asset_properties(asset_name)
            
            spec = AssetSpec(
                name=asset_name,
                asset_type=asset_type,
                size=size,
                metadata={
                    "description": description,
                    "provider": self.__class__.__name__,
                    "style": self.prompt_template.style
                }
            )
            assets.append(spec)
        
        return assets
    
    def fetch_asset(self, spec: AssetSpec) -> bytes:
        """Generate and fetch AI asset."""
        description = spec.metadata.get("description", spec.name)
        
        # Generate prompt
        prompt_data = self.prompt_template.generate_prompt(spec, description)
        
        # Generate image
        try:
            image_data = self.generate_image(prompt_data, spec.size)
            return image_data
        except Exception as e:
            raise ProviderError(f"Failed to generate asset {spec.name}: {e}", self.__class__.__name__)
    
    def _determine_asset_properties(self, asset_name: str) -> tuple[str, tuple[int, int]]:
        """Determine asset type and size from name."""
        name_lower = asset_name.lower()
        
        # Buildings
        building_keywords = ['lumberjack', 'mill', 'bakery', 'sawmill', 'quarry', 'farm', 'house', 'tower', 'castle']
        if any(keyword in name_lower for keyword in building_keywords):
            return "building", (64, 96)
        
        # Units
        unit_keywords = ['worker', 'unit', 'character', 'person', 'soldier', 'mage', 'archer']
        if any(keyword in name_lower for keyword in unit_keywords):
            return "unit", (64, 64)
        
        # Default to tile
        return "tile", (64, 32)


class StubAIProvider(AIProvider):
    """Stub AI provider that does nothing when no AI provider is configured."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize stub provider."""
        super().__init__(config)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure stub provider (always succeeds)."""
        self._configured = True
    
    def generate_image(self, prompt_data: Dict[str, str], size: tuple[int, int]) -> bytes:
        """Generate placeholder image."""
        # Create a simple colored rectangle as placeholder
        color = (128, 128, 128, 255)  # Gray
        img = Image.new('RGBA', size, color)
        
        # Add some basic pattern to indicate it's a placeholder
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Draw diagonal lines
        for i in range(0, size[0] + size[1], 10):
            draw.line([(i, 0), (0, i)], fill=(100, 100, 100, 255), width=1)
        
        # Save to bytes
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    
    def get_available_assets(self) -> List[AssetSpec]:
        """Return empty list for stub provider."""
        return []


class StableDiffusionProvider(AIProvider):
    """Provider for local Stable Diffusion API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Stable Diffusion provider."""
        super().__init__(config)
        self.api_url = config.get("api_url", "http://localhost:7860")
        self.model = config.get("model", "")
        self.steps = config.get("steps", 20)
        self.cfg_scale = config.get("cfg_scale", 7.0)
        self.sampler = config.get("sampler", "Euler a")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure Stable Diffusion provider."""
        errors = self.validate_config(config)
        if errors:
            raise ConfigurationError(f"Invalid configuration: {'; '.join(errors)}", "StableDiffusionProvider")
        
        self.api_url = config.get("api_url", "http://localhost:7860")
        self.model = config.get("model", "")
        self.steps = config.get("steps", 20)
        self.cfg_scale = config.get("cfg_scale", 7.0)
        self.sampler = config.get("sampler", "Euler a")
        
        # Test connection
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/options", timeout=5)
            response.raise_for_status()
            self._configured = True
        except requests.RequestException as e:
            raise ConfigurationError(f"Cannot connect to Stable Diffusion API: {e}", "StableDiffusionProvider")
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate Stable Diffusion configuration."""
        errors = []
        
        api_url = config.get("api_url")
        if not api_url or not isinstance(api_url, str):
            errors.append("'api_url' is required and must be a string")
        
        steps = config.get("steps", 20)
        if not isinstance(steps, int) or steps < 1 or steps > 100:
            errors.append("'steps' must be an integer between 1 and 100")
        
        cfg_scale = config.get("cfg_scale", 7.0)
        if not isinstance(cfg_scale, (int, float)) or cfg_scale < 1 or cfg_scale > 20:
            errors.append("'cfg_scale' must be a number between 1 and 20")
        
        return errors
    
    def generate_image(self, prompt_data: Dict[str, str], size: tuple[int, int]) -> bytes:
        """Generate image using Stable Diffusion API."""
        payload = {
            "prompt": prompt_data["prompt"],
            "negative_prompt": prompt_data["negative_prompt"],
            "width": size[0],
            "height": size[1],
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "sampler_name": self.sampler,
            "batch_size": 1,
            "n_iter": 1,
            "seed": -1,
            "restore_faces": False,
            "tiling": False
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            if "images" not in result or not result["images"]:
                raise ProviderError("No images generated", "StableDiffusionProvider")
            
            # Decode base64 image
            image_b64 = result["images"][0]
            image_data = base64.b64decode(image_b64)
            
            return image_data
            
        except requests.RequestException as e:
            raise NetworkError(f"Stable Diffusion API error: {e}", "StableDiffusionProvider")


class ReplicateProvider(AIProvider):
    """Provider for Replicate AI API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Replicate provider."""
        super().__init__(config)
        self.api_token = config.get("api_token", "")
        self.model = config.get("model", "stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478")
        self.api_url = "https://api.replicate.com/v1/predictions"
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure Replicate provider."""
        errors = self.validate_config(config)
        if errors:
            raise ConfigurationError(f"Invalid configuration: {'; '.join(errors)}", "ReplicateProvider")
        
        self.api_token = config.get("api_token", "")
        self.model = config.get("model", "stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478")
        
        self._configured = True
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate Replicate configuration."""
        errors = []
        
        api_token = config.get("api_token")
        if not api_token or not isinstance(api_token, str):
            errors.append("'api_token' is required and must be a string")
        
        return errors
    
    def generate_image(self, prompt_data: Dict[str, str], size: tuple[int, int]) -> bytes:
        """Generate image using Replicate API."""
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": self.model.split(":")[-1],
            "input": {
                "prompt": prompt_data["prompt"],
                "negative_prompt": prompt_data["negative_prompt"],
                "width": size[0],
                "height": size[1],
                "num_inference_steps": 20,
                "guidance_scale": 7.5
            }
        }
        
        try:
            # Start prediction
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            prediction = response.json()
            prediction_id = prediction["id"]
            
            # Poll for completion
            import time
            max_wait = 300  # 5 minutes
            wait_time = 0
            
            while wait_time < max_wait:
                response = requests.get(
                    f"{self.api_url}/{prediction_id}",
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                
                result = response.json()
                status = result["status"]
                
                if status == "succeeded":
                    if result["output"] and len(result["output"]) > 0:
                        image_url = result["output"][0]
                        # Download the generated image
                        img_response = requests.get(image_url, timeout=30)
                        img_response.raise_for_status()
                        return img_response.content
                    else:
                        raise ProviderError("No output generated", "ReplicateProvider")
                
                elif status == "failed":
                    error_msg = result.get("error", "Unknown error")
                    raise ProviderError(f"Generation failed: {error_msg}", "ReplicateProvider")
                
                elif status in ["starting", "processing"]:
                    time.sleep(2)
                    wait_time += 2
                else:
                    raise ProviderError(f"Unknown status: {status}", "ReplicateProvider")
            
            raise ProviderError("Generation timed out", "ReplicateProvider")
            
        except requests.RequestException as e:
            raise NetworkError(f"Replicate API error: {e}", "ReplicateProvider")


class OpenAIProvider(AIProvider):
    """Provider for OpenAI DALL-E API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider."""
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "dall-e-3")
        self.api_url = "https://api.openai.com/v1/images/generations"
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure OpenAI provider."""
        errors = self.validate_config(config)
        if errors:
            raise ConfigurationError(f"Invalid configuration: {'; '.join(errors)}", "OpenAIProvider")
        
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "dall-e-3")
        
        self._configured = True
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate OpenAI configuration."""
        errors = []
        
        api_key = config.get("api_key")
        if not api_key or not isinstance(api_key, str):
            errors.append("'api_key' is required and must be a string")
        
        model = config.get("model", "dall-e-3")
        if model not in ["dall-e-2", "dall-e-3"]:
            errors.append("'model' must be 'dall-e-2' or 'dall-e-3'")
        
        return errors
    
    def generate_image(self, prompt_data: Dict[str, str], size: tuple[int, int]) -> bytes:
        """Generate image using OpenAI DALL-E API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # DALL-E has specific size requirements
        dalle_size = self._get_dalle_size(size)
        
        payload = {
            "model": self.model,
            "prompt": prompt_data["prompt"],
            "size": dalle_size,
            "quality": "standard",
            "n": 1
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if "data" not in result or not result["data"]:
                raise ProviderError("No images generated", "OpenAIProvider")
            
            image_url = result["data"][0]["url"]
            
            # Download the generated image
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            # Resize to target size if needed
            if dalle_size != f"{size[0]}x{size[1]}":
                img = Image.open(io.BytesIO(img_response.content))
                img = img.resize(size, Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                return buf.getvalue()
            
            return img_response.content
            
        except requests.RequestException as e:
            raise NetworkError(f"OpenAI API error: {e}", "OpenAIProvider")
    
    def _get_dalle_size(self, target_size: tuple[int, int]) -> str:
        """Get closest DALL-E supported size."""
        width, height = target_size
        
        if self.model == "dall-e-3":
            # DALL-E 3 supports: 1024x1024, 1152x896, 1344x768
            if width >= height:
                if width / height > 1.5:
                    return "1344x768"
                elif width / height > 1.2:
                    return "1152x896"
                else:
                    return "1024x1024"
            else:
                return "1024x1024"
        else:
            # DALL-E 2 supports: 256x256, 512x512, 1024x1024
            max_dimension = max(width, height)
            if max_dimension <= 256:
                return "256x256"
            elif max_dimension <= 512:
                return "512x512"
            else:
                return "1024x1024"


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    PROVIDERS = {
        "stub": StubAIProvider,
        "stable_diffusion": StableDiffusionProvider,
        "replicate": ReplicateProvider,
        "openai": OpenAIProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> AIProvider:
        """Create AI provider instance."""
        if provider_type not in cls.PROVIDERS:
            raise ValueError(f"Unknown AI provider type: {provider_type}. Available: {list(cls.PROVIDERS.keys())}")
        
        provider_class = cls.PROVIDERS[provider_type]
        return provider_class(config)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List available AI provider types."""
        return list(cls.PROVIDERS.keys())