"""
Abstract base classes for asset providers.
Defines the interface that all asset providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from PIL import Image


@dataclass
class AssetSpec:
    """Specification for an asset to be processed."""
    name: str
    asset_type: str  # 'tile', 'building', 'unit'
    size: tuple[int, int]
    source_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate asset specification after initialization."""
        valid_types = {'tile', 'building', 'unit'}
        if self.asset_type not in valid_types:
            raise ValueError(f"asset_type must be one of {valid_types}, got {self.asset_type}")
        
        # Allow (0, 0) size for auto-calculation by normalizer
        if self.size[0] < 0 or self.size[1] < 0:
            raise ValueError(f"size dimensions cannot be negative, got {self.size}")


@dataclass
class ProcessedAsset:
    """Represents a processed asset ready for output."""
    spec: AssetSpec
    image: Image.Image
    output_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """Get asset name."""
        return self.spec.name
    
    @property
    def asset_type(self) -> str:
        """Get asset type."""
        return self.spec.asset_type
    
    @property
    def size(self) -> tuple[int, int]:
        """Get asset size."""
        return self.image.size


class AssetProvider(ABC):
    """Abstract base class for asset providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration."""
        self.config = config
        self._configured = False
    
    @abstractmethod
    def get_available_assets(self) -> List[AssetSpec]:
        """
        Return list of available assets from this provider.
        
        Returns:
            List of AssetSpec objects describing available assets
        """
        pass
    
    @abstractmethod
    def fetch_asset(self, spec: AssetSpec) -> bytes:
        """
        Fetch raw asset data for the given specification.
        
        Args:
            spec: AssetSpec describing the asset to fetch
            
        Returns:
            Raw image data as bytes
            
        Raises:
            AssetNotFoundError: If the asset cannot be found
            ProviderError: If there's an error fetching the asset
        """
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure provider with settings.
        
        Args:
            config: Configuration dictionary specific to this provider
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass
    
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return self._configured
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate provider configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        return []
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dictionary with provider metadata
        """
        return {
            "name": self.__class__.__name__,
            "configured": self.is_configured(),
            "config": self.config
        }


class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, message: str, provider: str, recoverable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.recoverable = recoverable


class AssetNotFoundError(ProviderError):
    """Exception raised when an asset cannot be found."""
    
    def __init__(self, asset_name: str, provider: str):
        super().__init__(f"Asset '{asset_name}' not found", provider, recoverable=False)
        self.asset_name = asset_name


class ConfigurationError(ProviderError):
    """Exception raised when provider configuration is invalid."""
    
    def __init__(self, message: str, provider: str):
        super().__init__(f"Configuration error: {message}", provider, recoverable=False)


class NetworkError(ProviderError):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str, provider: str):
        super().__init__(f"Network error: {message}", provider, recoverable=True)


class ProviderRegistry:
    """Registry for managing multiple asset providers."""
    
    def __init__(self):
        """Initialize empty provider registry."""
        self._providers: Dict[str, AssetProvider] = {}
        self._provider_classes: Dict[str, type] = {}
    
    def register_provider_class(self, name: str, provider_class: type) -> None:
        """
        Register a provider class.
        
        Args:
            name: Name to register the provider under
            provider_class: Provider class that inherits from AssetProvider
            
        Raises:
            ValueError: If provider_class doesn't inherit from AssetProvider
        """
        if not issubclass(provider_class, AssetProvider):
            raise ValueError(f"Provider class {provider_class} must inherit from AssetProvider")
        
        self._provider_classes[name] = provider_class
    
    def create_provider(self, name: str, config: Dict[str, Any]) -> AssetProvider:
        """
        Create and configure a provider instance.
        
        Args:
            name: Name of the provider class to create
            config: Configuration for the provider
            
        Returns:
            Configured provider instance
            
        Raises:
            ValueError: If provider name is not registered
            ConfigurationError: If provider configuration fails
        """
        if name not in self._provider_classes:
            raise ValueError(f"Provider '{name}' not registered. Available: {list(self._provider_classes.keys())}")
        
        provider_class = self._provider_classes[name]
        provider = provider_class(config)
        
        try:
            provider.configure(config)
        except Exception as e:
            raise ConfigurationError(f"Failed to configure provider '{name}': {e}", name)
        
        return provider
    
    def register_provider(self, name: str, provider: AssetProvider) -> None:
        """
        Register a configured provider instance.
        
        Args:
            name: Name to register the provider under
            provider: Configured provider instance
        """
        self._providers[name] = provider
    
    def get_provider(self, name: str) -> AssetProvider:
        """
        Get a registered provider by name.
        
        Args:
            name: Name of the provider to get
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is not registered
        """
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' not registered. Available: {list(self._providers.keys())}")
        
        return self._providers[name]
    
    def get_all_providers(self) -> Dict[str, AssetProvider]:
        """
        Get all registered providers.
        
        Returns:
            Dictionary mapping provider names to provider instances
        """
        return self._providers.copy()
    
    def list_available_provider_classes(self) -> List[str]:
        """
        List all registered provider class names.
        
        Returns:
            List of provider class names
        """
        return list(self._provider_classes.keys())
    
    def list_registered_providers(self) -> List[str]:
        """
        List all registered provider instance names.
        
        Returns:
            List of provider instance names
        """
        return list(self._providers.keys())
    
    def remove_provider(self, name: str) -> None:
        """
        Remove a registered provider.
        
        Args:
            name: Name of the provider to remove
        """
        if name in self._providers:
            del self._providers[name]
    
    def clear_providers(self) -> None:
        """Remove all registered providers."""
        self._providers.clear()
    
    def get_all_available_assets(self) -> Dict[str, List[AssetSpec]]:
        """
        Get all available assets from all registered providers.
        
        Returns:
            Dictionary mapping provider names to their available assets
        """
        all_assets = {}
        for name, provider in self._providers.items():
            try:
                assets = provider.get_available_assets()
                all_assets[name] = assets
            except Exception as e:
                # Log error but continue with other providers
                print(f"Warning: Failed to get assets from provider '{name}': {e}")
                all_assets[name] = []
        
        return all_assets


# Global provider registry instance
provider_registry = ProviderRegistry()