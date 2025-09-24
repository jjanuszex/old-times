"""
Asset providers for the pipeline.
Handles different sources of assets including CC0 packs, AI generation, and local files.
"""

from .base import (
    AssetProvider, AssetSpec, ProcessedAsset, ProviderRegistry,
    ProviderError, AssetNotFoundError, ConfigurationError, NetworkError,
    provider_registry
)
from .kenney import KenneyProvider
from .ai_providers import (
    AIProvider, StubAIProvider, StableDiffusionProvider, 
    ReplicateProvider, OpenAIProvider, AIProviderFactory,
    PromptTemplate
)

# Register provider classes with the global registry
provider_registry.register_provider_class("kenney", KenneyProvider)
provider_registry.register_provider_class("ai_stub", StubAIProvider)
provider_registry.register_provider_class("stable_diffusion", StableDiffusionProvider)
provider_registry.register_provider_class("replicate", ReplicateProvider)
provider_registry.register_provider_class("openai", OpenAIProvider)

__all__ = [
    # Base classes and registry
    "AssetProvider",
    "AssetSpec", 
    "ProcessedAsset",
    "ProviderRegistry",
    "provider_registry",
    
    # Exceptions
    "ProviderError",
    "AssetNotFoundError", 
    "ConfigurationError",
    "NetworkError",
    
    # Concrete providers
    "KenneyProvider",
    "AIProvider",
    "StubAIProvider",
    "StableDiffusionProvider",
    "ReplicateProvider", 
    "OpenAIProvider",
    
    # Utilities
    "AIProviderFactory",
    "PromptTemplate",
]