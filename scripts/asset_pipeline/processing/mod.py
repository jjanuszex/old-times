"""
Mod directory management and asset generation system.
Handles creation of mod directory structures and mod-specific asset processing.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python < 3.11 with tomli package
    except ImportError:
        tomllib = None

from ..config import PipelineConfig
from .metadata import MetadataGenerator
from ..providers.base import AssetSpec


@dataclass
class ModConfig:
    """Configuration for a mod."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "Asset Pipeline"
    priority: int = 100
    dependencies: Dict[str, str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = {"base_game": ">=1.0.0"}


@dataclass
class ModAsset:
    """Represents an asset within a mod."""
    name: str
    asset_type: str  # 'tile', 'building', 'unit'
    source_path: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ModDirectoryManager:
    """Manages mod directory structure creation and maintenance."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.mods_base_dir = Path(config.mods_dir)
    
    def create_mod_directory(self, mod_name: str, force: bool = False) -> Path:
        """
        Create a complete mod directory structure.
        
        Args:
            mod_name: Name of the mod
            force: Whether to overwrite existing mod directory
            
        Returns:
            Path to the created mod directory
            
        Raises:
            FileExistsError: If mod directory exists and force=False
            OSError: If directory creation fails
        """
        mod_dir = self.mods_base_dir / mod_name
        
        # Check if mod directory already exists
        if mod_dir.exists() and not force:
            raise FileExistsError(f"Mod directory already exists: {mod_dir}")
        
        # Remove existing directory if force is True
        if mod_dir.exists() and force:
            shutil.rmtree(mod_dir)
        
        # Create mod directory structure
        directories = [
            mod_dir,
            mod_dir / "sprites",
            mod_dir / "atlases", 
            mod_dir / "data",
            mod_dir / "config"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        return mod_dir
    
    def validate_mod_directory(self, mod_name: str) -> bool:
        """
        Validate that a mod directory has the correct structure.
        
        Args:
            mod_name: Name of the mod to validate
            
        Returns:
            True if directory structure is valid
        """
        mod_dir = self.mods_base_dir / mod_name
        
        if not mod_dir.exists():
            return False
        
        required_dirs = ["sprites", "data"]
        for req_dir in required_dirs:
            if not (mod_dir / req_dir).exists():
                return False
        
        # Check for mod.toml file
        if not (mod_dir / "mod.toml").exists():
            return False
        
        return True
    
    def get_mod_config_path(self, mod_name: str) -> Path:
        """Get path to mod configuration file."""
        return self.mods_base_dir / mod_name / "mod.toml"
    
    def get_mod_sprites_dir(self, mod_name: str) -> Path:
        """Get path to mod sprites directory."""
        return self.mods_base_dir / mod_name / "sprites"
    
    def get_mod_atlases_dir(self, mod_name: str) -> Path:
        """Get path to mod atlases directory."""
        return self.mods_base_dir / mod_name / "atlases"
    
    def get_mod_data_dir(self, mod_name: str) -> Path:
        """Get path to mod data directory."""
        return self.mods_base_dir / mod_name / "data"
    
    def list_mods(self) -> List[str]:
        """List all available mods."""
        if not self.mods_base_dir.exists():
            return []
        
        mods = []
        for item in self.mods_base_dir.iterdir():
            if item.is_dir() and self.validate_mod_directory(item.name):
                mods.append(item.name)
        
        return sorted(mods)
    
    def cleanup_mod_directory(self, mod_name: str) -> bool:
        """
        Clean up empty directories and temporary files in mod directory.
        
        Args:
            mod_name: Name of the mod to clean up
            
        Returns:
            True if cleanup was successful
        """
        mod_dir = self.mods_base_dir / mod_name
        
        if not mod_dir.exists():
            return False
        
        try:
            # Remove temporary files first
            temp_patterns = ["*.tmp", "*.temp", "*~", ".DS_Store"]
            for pattern in temp_patterns:
                for temp_file in mod_dir.rglob(pattern):
                    try:
                        temp_file.unlink()
                    except OSError:
                        pass  # File in use or other error
            
            # Remove empty directories (but preserve required structure)
            required_dirs = {"sprites", "atlases", "data", "config"}
            for root, dirs, files in os.walk(mod_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    # Skip required directories at the mod root level
                    if dir_path.parent == mod_dir and dir_name in required_dirs:
                        continue
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except OSError:
                        pass  # Directory not empty or other error
            
            return True
        except Exception:
            return False


class ModConfigManager:
    """Manages mod configuration files and metadata."""
    
    def __init__(self, directory_manager: ModDirectoryManager):
        self.directory_manager = directory_manager
    
    def create_mod_config(self, mod_name: str, config: ModConfig) -> Path:
        """
        Create mod.toml configuration file.
        
        Args:
            mod_name: Name of the mod
            config: Mod configuration
            
        Returns:
            Path to created configuration file
        """
        config_path = self.directory_manager.get_mod_config_path(mod_name)
        
        # Generate TOML content
        toml_content = self._generate_mod_toml(config)
        
        # Write configuration file
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        return config_path
    
    def load_mod_config(self, mod_name: str) -> Optional[ModConfig]:
        """
        Load mod configuration from mod.toml file.
        
        Args:
            mod_name: Name of the mod
            
        Returns:
            ModConfig object or None if loading fails
        """
        config_path = self.directory_manager.get_mod_config_path(mod_name)
        
        if not config_path.exists():
            return None
        
        try:
            if tomllib is None:
                raise ImportError("TOML support not available")
            
            with open(config_path, 'rb') as f:
                data = tomllib.load(f)
            
            return ModConfig(
                name=data.get('name', mod_name),
                version=data.get('version', '1.0.0'),
                description=data.get('description', ''),
                author=data.get('author', 'Asset Pipeline'),
                priority=data.get('priority', 100),
                dependencies=data.get('dependencies', {"base_game": ">=1.0.0"})
            )
        except Exception:
            return None
    
    def update_mod_config(self, mod_name: str, assets: List[ModAsset]) -> bool:
        """
        Update mod configuration with asset information.
        
        Args:
            mod_name: Name of the mod
            assets: List of assets in the mod
            
        Returns:
            True if update was successful
        """
        try:
            # Load existing config or create default
            config = self.load_mod_config(mod_name)
            if config is None:
                config = ModConfig(
                    name=mod_name,
                    description=f"Generated mod with {len(assets)} assets"
                )
            
            # Update description with asset count
            config.description = f"Generated mod with {len(assets)} assets"
            
            # Create updated configuration
            self.create_mod_config(mod_name, config)
            
            return True
        except Exception:
            return False
    
    def _generate_mod_toml(self, config: ModConfig) -> str:
        """Generate TOML content for mod configuration."""
        lines = [
            f'name = "{config.name}"',
            f'version = "{config.version}"',
            f'description = "{config.description}"',
            f'author = "{config.author}"',
            f'priority = {config.priority}',
            ''
        ]
        
        # Add dependencies section
        if config.dependencies:
            lines.append('[dependencies]')
            for dep_name, dep_version in config.dependencies.items():
                lines.append(f'{dep_name} = "{dep_version}"')
        
        return '\n'.join(lines)


class ModAssetIsolation:
    """Handles asset isolation for mods to prevent conflicts with base game."""
    
    def __init__(self, directory_manager: ModDirectoryManager):
        self.directory_manager = directory_manager
    
    def isolate_mod_assets(self, mod_name: str, assets: List[ModAsset]) -> Dict[str, str]:
        """
        Ensure mod assets are properly isolated from base game assets.
        
        Args:
            mod_name: Name of the mod
            assets: List of assets to isolate
            
        Returns:
            Dictionary mapping original paths to isolated paths
        """
        isolation_map = {}
        mod_sprites_dir = self.directory_manager.get_mod_sprites_dir(mod_name)
        
        for asset in assets:
            # Generate isolated path within mod directory
            original_path = asset.source_path
            filename = Path(original_path).name
            
            # Create subdirectory based on asset type
            asset_subdir = mod_sprites_dir / asset.asset_type
            asset_subdir.mkdir(exist_ok=True)
            
            isolated_path = asset_subdir / filename
            isolation_map[original_path] = str(isolated_path)
        
        return isolation_map
    
    def validate_asset_isolation(self, mod_name: str) -> List[str]:
        """
        Validate that mod assets don't conflict with base game assets.
        
        Args:
            mod_name: Name of the mod to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        mod_sprites_dir = self.directory_manager.get_mod_sprites_dir(mod_name)
        base_sprites_dir = Path(self.directory_manager.config.sprites_dir)
        
        if not mod_sprites_dir.exists():
            errors.append(f"Mod sprites directory does not exist: {mod_sprites_dir}")
            return errors
        
        # Check for naming conflicts
        for mod_sprite in mod_sprites_dir.rglob("*"):
            if mod_sprite.is_file():
                relative_path = mod_sprite.relative_to(mod_sprites_dir)
                base_sprite_path = base_sprites_dir / relative_path
                
                if base_sprite_path.exists():
                    errors.append(f"Asset name conflict: {relative_path}")
        
        return errors


class ModMetadataGenerator:
    """Generates mod-specific metadata files."""
    
    def __init__(self, directory_manager: ModDirectoryManager):
        self.directory_manager = directory_manager
        self.metadata_generator = MetadataGenerator(
            Path(__file__).parent.parent / "templates"
        )
    
    def generate_mod_sprites_toml(self, mod_name: str, assets: List[ModAsset]) -> Path:
        """
        Generate sprites.toml file for mod.
        
        Args:
            mod_name: Name of the mod
            assets: List of assets in the mod
            
        Returns:
            Path to generated sprites.toml file
        """
        mod_data_dir = self.directory_manager.get_mod_data_dir(mod_name)
        sprites_toml_path = mod_data_dir / "sprites.toml"
        
        # Generate sprites.toml content directly for mod assets
        toml_content = self._generate_mod_sprites_toml_content(assets)
        
        # Write to mod data directory
        with open(sprites_toml_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        
        return sprites_toml_path
    
    def _generate_mod_sprites_toml_content(self, assets: List[ModAsset]) -> str:
        """Generate sprites.toml content for mod assets."""
        lines = ["# Generated sprites.toml for mod", ""]
        
        # Group assets by type
        tiles = [a for a in assets if a.asset_type == 'tile']
        buildings = [a for a in assets if a.asset_type == 'building']
        units = [a for a in assets if a.asset_type == 'unit']
        
        # Generate tiles section
        if tiles:
            lines.append("[tiles]")
            for tile in tiles:
                lines.append(f'[tiles.{tile.name}]')
                lines.append('kind = "tile"')
                size = tile.metadata.get('size', [64, 32])
                lines.append(f'size = {size}')
                lines.append(f'source = "{tile.source_path}"')
                lines.append("")
        
        # Generate buildings section
        if buildings:
            lines.append("[buildings]")
            for building in buildings:
                lines.append(f'[buildings.{building.name}]')
                lines.append('kind = "building"')
                size = building.metadata.get('size', [64, 96])
                lines.append(f'size = {size}')
                lines.append(f'source = "{building.source_path}"')
                
                # Add tile footprint if available
                if 'tile_footprint' in building.metadata:
                    footprint = building.metadata['tile_footprint']
                    lines.append(f'tile_footprint = {footprint}')
                
                lines.append("")
        
        # Generate units section
        if units:
            lines.append("[units]")
            for unit in units:
                lines.append(f'[units.{unit.name}]')
                lines.append('kind = "unit"')
                lines.append(f'source = "{unit.source_path}"')
                
                # Add unit-specific metadata
                frame_size = unit.metadata.get('frame_size', [64, 64])
                lines.append(f'frame_size = {frame_size}')
                
                directions = unit.metadata.get('directions', ["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
                lines.append(f'directions = {directions}')
                
                anim_walk_fps = unit.metadata.get('anim_walk_fps', 10)
                lines.append(f'anim_walk_fps = {anim_walk_fps}')
                
                anim_walk_len = unit.metadata.get('anim_walk_len', 8)
                lines.append(f'anim_walk_len = {anim_walk_len}')
                
                layout = unit.metadata.get('layout', 'dirs_rows')
                lines.append(f'layout = "{layout}"')
                
                if 'atlas_map' in unit.metadata:
                    lines.append(f'atlas_map = "{unit.metadata["atlas_map"]}"')
                
                lines.append("")
        
        return '\n'.join(lines)
    
    def generate_mod_manifest(self, mod_name: str, assets: List[ModAsset]) -> Path:
        """
        Generate manifest.json file with detailed mod information.
        
        Args:
            mod_name: Name of the mod
            assets: List of assets in the mod
            
        Returns:
            Path to generated manifest.json file
        """
        mod_data_dir = self.directory_manager.get_mod_data_dir(mod_name)
        manifest_path = mod_data_dir / "manifest.json"
        
        # Group assets by type
        asset_groups = {}
        for asset in assets:
            if asset.asset_type not in asset_groups:
                asset_groups[asset.asset_type] = []
            asset_groups[asset.asset_type].append({
                "name": asset.name,
                "source_path": asset.source_path,
                "metadata": asset.metadata
            })
        
        # Create manifest data
        manifest_data = {
            "mod_name": mod_name,
            "generated_at": datetime.now().isoformat(),
            "asset_count": len(assets),
            "asset_types": list(asset_groups.keys()),
            "assets": asset_groups,
            "version": "1.0.0"
        }
        
        # Write manifest file
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2)
        
        return manifest_path