"""
Kenney asset pack provider for downloading and processing CC0 assets.
"""

import os
import json
import hashlib
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import requests
from PIL import Image
import io

from .base import AssetProvider, AssetSpec, ProviderError, NetworkError, ConfigurationError


class KenneyProvider(AssetProvider):
    """Provider for Kenney CC0 asset packs."""
    
    # Known Kenney asset packs that work well for isometric games
    KNOWN_PACKS = {
        "isometric-buildings": {
            "url": "https://kenney.nl/content/3-assets/16-isometric-buildings/isometricBuildings.zip",
            "description": "Isometric building sprites",
            "asset_mappings": {
                "building_lumberjack.png": "lumberjack.png",
                "building_mill.png": "mill.png",
                "building_bakery.png": "bakery.png",
                "building_sawmill.png": "sawmill.png",
                "building_quarry.png": "quarry.png",
                "building_farm.png": "farm.png"
            }
        },
        "isometric-tiles": {
            "url": "https://kenney.nl/content/3-assets/17-isometric-tiles/isometricTiles.zip", 
            "description": "Isometric tile sprites",
            "asset_mappings": {
                "tile_grass.png": "grass.png",
                "tile_stone.png": "stone.png",
                "tile_water.png": "water.png",
                "tile_forest.png": "forest.png",
                "tile_road.png": "road.png"
            }
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Kenney provider."""
        super().__init__(config)
        self.cache_dir = Path(config.get("cache_dir", "cache/kenney"))
        self.selected_packs = config.get("packs", list(self.KNOWN_PACKS.keys()))
        self.custom_mappings = config.get("asset_mappings", {})
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OldTimes-AssetPipeline/1.0'
        })
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the Kenney provider."""
        errors = self.validate_config(config)
        if errors:
            raise ConfigurationError(f"Invalid configuration: {'; '.join(errors)}", "KenneyProvider")
        
        self.cache_dir = Path(config.get("cache_dir", "cache/kenney"))
        self.selected_packs = config.get("packs", list(self.KNOWN_PACKS.keys()))
        self.custom_mappings = config.get("asset_mappings", {})
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._configured = True
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate Kenney provider configuration."""
        errors = []
        
        packs = config.get("packs", [])
        if not isinstance(packs, list):
            errors.append("'packs' must be a list")
        else:
            for pack in packs:
                if pack not in self.KNOWN_PACKS:
                    errors.append(f"Unknown pack '{pack}'. Available: {list(self.KNOWN_PACKS.keys())}")
        
        cache_dir = config.get("cache_dir")
        if cache_dir and not isinstance(cache_dir, str):
            errors.append("'cache_dir' must be a string")
        
        mappings = config.get("asset_mappings", {})
        if not isinstance(mappings, dict):
            errors.append("'asset_mappings' must be a dictionary")
        
        return errors
    
    def get_available_assets(self) -> List[AssetSpec]:
        """Get list of available assets from selected Kenney packs."""
        assets = []
        
        for pack_name in self.selected_packs:
            if pack_name not in self.KNOWN_PACKS:
                continue
            
            pack_info = self.KNOWN_PACKS[pack_name]
            mappings = pack_info.get("asset_mappings", {})
            
            # Add custom mappings
            if pack_name in self.custom_mappings:
                mappings.update(self.custom_mappings[pack_name])
            
            for kenney_name, game_name in mappings.items():
                # Determine asset type and size from filename
                asset_type, size = self._determine_asset_properties(game_name)
                
                spec = AssetSpec(
                    name=game_name.replace('.png', ''),
                    asset_type=asset_type,
                    size=size,
                    source_path=kenney_name,
                    metadata={
                        "pack": pack_name,
                        "kenney_name": kenney_name,
                        "pack_url": pack_info["url"]
                    }
                )
                assets.append(spec)
        
        return assets
    
    def fetch_asset(self, spec: AssetSpec) -> bytes:
        """Fetch asset data from Kenney pack."""
        pack_name = spec.metadata.get("pack")
        kenney_name = spec.metadata.get("kenney_name")
        
        if not pack_name or not kenney_name:
            raise ProviderError(f"Missing pack or kenney_name metadata for asset {spec.name}", "KenneyProvider")
        
        # Download and extract pack if needed
        pack_dir = self._ensure_pack_downloaded(pack_name)
        
        # Find the asset file in the extracted pack
        asset_path = self._find_asset_in_pack(pack_dir, kenney_name)
        if not asset_path:
            raise ProviderError(f"Asset {kenney_name} not found in pack {pack_name}", "KenneyProvider")
        
        # Load and return image data
        try:
            with open(asset_path, 'rb') as f:
                return f.read()
        except IOError as e:
            raise ProviderError(f"Failed to read asset {asset_path}: {e}", "KenneyProvider")
    
    def _determine_asset_properties(self, filename: str) -> tuple[str, tuple[int, int]]:
        """Determine asset type and expected size from filename."""
        name = filename.lower().replace('.png', '')
        
        # Buildings are typically larger and have specific names
        building_keywords = ['lumberjack', 'mill', 'bakery', 'sawmill', 'quarry', 'farm']
        if any(keyword in name for keyword in building_keywords):
            return "building", (64, 96)  # Default building size
        
        # Units have specific patterns
        unit_keywords = ['worker', 'unit', 'character', 'person']
        if any(keyword in name for keyword in unit_keywords):
            return "unit", (64, 64)  # Unit frame size
        
        # Everything else is considered a tile
        return "tile", (64, 32)  # Isometric tile size
    
    def _ensure_pack_downloaded(self, pack_name: str) -> Path:
        """Ensure pack is downloaded and extracted, return path to extracted directory."""
        pack_info = self.KNOWN_PACKS[pack_name]
        pack_url = pack_info["url"]
        
        # Create pack-specific cache directory
        pack_cache_dir = self.cache_dir / pack_name
        pack_cache_dir.mkdir(exist_ok=True)
        
        # Check if pack is already extracted
        extracted_marker = pack_cache_dir / ".extracted"
        if extracted_marker.exists():
            return pack_cache_dir
        
        # Download pack zip file
        zip_path = pack_cache_dir / f"{pack_name}.zip"
        if not zip_path.exists():
            self._download_pack(pack_url, zip_path)
        
        # Extract pack
        self._extract_pack(zip_path, pack_cache_dir)
        
        # Mark as extracted
        extracted_marker.touch()
        
        return pack_cache_dir
    
    def _download_pack(self, url: str, output_path: Path) -> None:
        """Download pack zip file."""
        try:
            print(f"Downloading Kenney pack from {url}...")
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded pack to {output_path}")
            
        except requests.RequestException as e:
            raise NetworkError(f"Failed to download pack from {url}: {e}", "KenneyProvider")
    
    def _extract_pack(self, zip_path: Path, extract_dir: Path) -> None:
        """Extract pack zip file."""
        try:
            print(f"Extracting pack {zip_path}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"Extracted pack to {extract_dir}")
            
        except zipfile.BadZipFile as e:
            raise ProviderError(f"Invalid zip file {zip_path}: {e}", "KenneyProvider")
    
    def _find_asset_in_pack(self, pack_dir: Path, asset_name: str) -> Optional[Path]:
        """Find asset file in extracted pack directory."""
        # Search recursively for the asset file
        for root, dirs, files in os.walk(pack_dir):
            for file in files:
                if file.lower() == asset_name.lower():
                    return Path(root) / file
        
        # Try variations of the filename
        name_variations = [
            asset_name,
            asset_name.lower(),
            asset_name.upper(),
            asset_name.replace('_', ''),
            asset_name.replace('_', '-'),
        ]
        
        for root, dirs, files in os.walk(pack_dir):
            for file in files:
                file_lower = file.lower().replace('.png', '')
                for variation in name_variations:
                    variation_lower = variation.lower().replace('.png', '')
                    if file_lower == variation_lower:
                        return Path(root) / file
        
        return None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached packs."""
        cache_info = {
            "cache_dir": str(self.cache_dir),
            "packs": {}
        }
        
        for pack_name in self.selected_packs:
            pack_cache_dir = self.cache_dir / pack_name
            cache_info["packs"][pack_name] = {
                "cached": pack_cache_dir.exists(),
                "extracted": (pack_cache_dir / ".extracted").exists(),
                "size_mb": self._get_directory_size(pack_cache_dir) / (1024 * 1024) if pack_cache_dir.exists() else 0
            }
        
        return cache_info
    
    def clear_cache(self, pack_name: Optional[str] = None) -> None:
        """Clear cached pack data."""
        if pack_name:
            pack_cache_dir = self.cache_dir / pack_name
            if pack_cache_dir.exists():
                import shutil
                shutil.rmtree(pack_cache_dir)
                print(f"Cleared cache for pack {pack_name}")
        else:
            if self.cache_dir.exists():
                import shutil
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                print("Cleared all pack cache")
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except OSError:
            pass
        return total_size
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information."""
        info = super().get_provider_info()
        info.update({
            "available_packs": list(self.KNOWN_PACKS.keys()),
            "selected_packs": self.selected_packs,
            "cache_info": self.get_cache_info()
        })
        return info