"""
Configuration management system for the asset pipeline.
Supports TOML and JSON configuration files with validation.
"""

import os
import json
from dataclasses import dataclass, field

# Handle tomllib import for different Python versions
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python < 3.11 with tomli package
    except ImportError:
        tomllib = None  # Fallback if no TOML support
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


@dataclass
class PipelineConfig:
    """Main configuration class for the asset pipeline."""
    
    # Asset sources
    kenney_packs: List[str] = field(default_factory=list)
    ai_provider: str = "none"
    ai_config: Dict[str, Any] = field(default_factory=dict)
    
    # Processing settings
    tile_size: tuple[int, int] = (64, 32)
    unit_frame_size: tuple[int, int] = (64, 64)
    atlas_padding: int = 0
    
    # Quality settings
    max_alpha_threshold: float = 0.01
    edge_sharpness_threshold: float = 0.5
    
    # Output settings
    output_format: str = "PNG"
    compression_level: int = 6
    
    # Paths
    assets_dir: str = "assets"
    sprites_dir: str = "assets/sprites"
    atlases_dir: str = "assets/atlases"
    data_dir: str = "assets/data"
    mods_dir: str = "mods"
    preview_dir: str = "assets/preview"
    
    # Preview settings
    generate_previews: bool = True
    preview_grid_size: tuple[int, int] = (96, 96)
    preview_show_labels: bool = True
    preview_show_grid: bool = True
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "PipelineConfig":
        """Load configuration from TOML or JSON file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if config_path.suffix.lower() == '.toml':
            return cls._from_toml(config_path)
        elif config_path.suffix.lower() == '.json':
            return cls._from_json(config_path)
        else:
            raise ValueError(f"Unsupported configuration format: {config_path.suffix}")
    
    @classmethod
    def _from_toml(cls, config_path: Path) -> "PipelineConfig":
        """Load configuration from TOML file."""
        if tomllib is None:
            raise ImportError("TOML support not available. Install tomli package for Python < 3.11")
        
        with open(config_path, 'rb') as f:
            data = tomllib.load(f)
        return cls._from_dict(data)
    
    @classmethod
    def _from_json(cls, config_path: Path) -> "PipelineConfig":
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            data = json.load(f)
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        """Create configuration from dictionary."""
        # Convert nested dictionaries to match dataclass structure
        config_data = {}
        
        # Handle asset sources
        if 'sources' in data:
            sources = data['sources']
            config_data['kenney_packs'] = sources.get('kenney_packs', [])
            config_data['ai_provider'] = sources.get('ai_provider', 'none')
            config_data['ai_config'] = sources.get('ai_config', {})
        
        # Handle processing settings
        if 'processing' in data:
            processing = data['processing']
            if 'tile_size' in processing:
                config_data['tile_size'] = tuple(processing['tile_size'])
            if 'unit_frame_size' in processing:
                config_data['unit_frame_size'] = tuple(processing['unit_frame_size'])
            config_data['atlas_padding'] = processing.get('atlas_padding', 0)
        
        # Handle quality settings
        if 'quality' in data:
            quality = data['quality']
            config_data['max_alpha_threshold'] = quality.get('max_alpha_threshold', 0.01)
            config_data['edge_sharpness_threshold'] = quality.get('edge_sharpness_threshold', 0.5)
        
        # Handle output settings
        if 'output' in data:
            output = data['output']
            config_data['output_format'] = output.get('format', 'PNG')
            config_data['compression_level'] = output.get('compression_level', 6)
        
        # Handle paths
        if 'paths' in data:
            paths = data['paths']
            config_data['assets_dir'] = paths.get('assets_dir', 'assets')
            config_data['sprites_dir'] = paths.get('sprites_dir', 'assets/sprites')
            config_data['atlases_dir'] = paths.get('atlases_dir', 'assets/atlases')
            config_data['data_dir'] = paths.get('data_dir', 'assets/data')
            config_data['mods_dir'] = paths.get('mods_dir', 'mods')
            config_data['preview_dir'] = paths.get('preview_dir', 'assets/preview')
        
        # Handle preview settings
        if 'preview' in data:
            preview = data['preview']
            config_data['generate_previews'] = preview.get('generate_previews', True)
            if 'grid_size' in preview:
                config_data['preview_grid_size'] = tuple(preview['grid_size'])
            config_data['preview_show_labels'] = preview.get('show_labels', True)
            config_data['preview_show_grid'] = preview.get('show_grid', True)
        
        return cls(**config_data)
    
    @classmethod
    def default(cls) -> "PipelineConfig":
        """Create default configuration with environment variable overrides."""
        config = cls()
        
        # Apply environment variable overrides
        config = cls._apply_env_overrides(config)
        
        return config
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Create configuration from environment variables only."""
        config = cls()
        return cls._apply_env_overrides(config)
    
    @classmethod
    def _apply_env_overrides(cls, config: "PipelineConfig") -> "PipelineConfig":
        """Apply environment variable overrides to configuration."""
        
        # Asset sources
        if os.getenv('ASSET_PIPELINE_KENNEY_PACKS'):
            config.kenney_packs = os.getenv('ASSET_PIPELINE_KENNEY_PACKS', '').split(',')
        
        if os.getenv('ASSET_PIPELINE_AI_PROVIDER'):
            config.ai_provider = os.getenv('ASSET_PIPELINE_AI_PROVIDER', 'none')
        
        # Processing settings
        if os.getenv('ASSET_PIPELINE_TILE_WIDTH') and os.getenv('ASSET_PIPELINE_TILE_HEIGHT'):
            config.tile_size = (
                int(os.getenv('ASSET_PIPELINE_TILE_WIDTH', '64')),
                int(os.getenv('ASSET_PIPELINE_TILE_HEIGHT', '32'))
            )
        
        if os.getenv('ASSET_PIPELINE_UNIT_FRAME_WIDTH') and os.getenv('ASSET_PIPELINE_UNIT_FRAME_HEIGHT'):
            config.unit_frame_size = (
                int(os.getenv('ASSET_PIPELINE_UNIT_FRAME_WIDTH', '64')),
                int(os.getenv('ASSET_PIPELINE_UNIT_FRAME_HEIGHT', '64'))
            )
        
        if os.getenv('ASSET_PIPELINE_ATLAS_PADDING'):
            config.atlas_padding = int(os.getenv('ASSET_PIPELINE_ATLAS_PADDING', '0'))
        
        # Quality settings
        if os.getenv('ASSET_PIPELINE_MAX_ALPHA_THRESHOLD'):
            config.max_alpha_threshold = float(os.getenv('ASSET_PIPELINE_MAX_ALPHA_THRESHOLD', '0.01'))
        
        if os.getenv('ASSET_PIPELINE_EDGE_SHARPNESS_THRESHOLD'):
            config.edge_sharpness_threshold = float(os.getenv('ASSET_PIPELINE_EDGE_SHARPNESS_THRESHOLD', '0.5'))
        
        # Output settings
        if os.getenv('ASSET_PIPELINE_OUTPUT_FORMAT'):
            config.output_format = os.getenv('ASSET_PIPELINE_OUTPUT_FORMAT', 'PNG')
        
        if os.getenv('ASSET_PIPELINE_COMPRESSION_LEVEL'):
            config.compression_level = int(os.getenv('ASSET_PIPELINE_COMPRESSION_LEVEL', '6'))
        
        # Paths
        if os.getenv('ASSET_PIPELINE_ASSETS_DIR'):
            config.assets_dir = os.getenv('ASSET_PIPELINE_ASSETS_DIR', 'assets')
        
        if os.getenv('ASSET_PIPELINE_SPRITES_DIR'):
            config.sprites_dir = os.getenv('ASSET_PIPELINE_SPRITES_DIR', 'assets/sprites')
        
        if os.getenv('ASSET_PIPELINE_ATLASES_DIR'):
            config.atlases_dir = os.getenv('ASSET_PIPELINE_ATLASES_DIR', 'assets/atlases')
        
        if os.getenv('ASSET_PIPELINE_DATA_DIR'):
            config.data_dir = os.getenv('ASSET_PIPELINE_DATA_DIR', 'assets/data')
        
        if os.getenv('ASSET_PIPELINE_MODS_DIR'):
            config.mods_dir = os.getenv('ASSET_PIPELINE_MODS_DIR', 'mods')
        
        if os.getenv('ASSET_PIPELINE_PREVIEW_DIR'):
            config.preview_dir = os.getenv('ASSET_PIPELINE_PREVIEW_DIR', 'assets/preview')
        
        # Preview settings
        if os.getenv('ASSET_PIPELINE_GENERATE_PREVIEWS'):
            config.generate_previews = os.getenv('ASSET_PIPELINE_GENERATE_PREVIEWS', 'true').lower() == 'true'
        
        if os.getenv('ASSET_PIPELINE_PREVIEW_GRID_WIDTH') and os.getenv('ASSET_PIPELINE_PREVIEW_GRID_HEIGHT'):
            config.preview_grid_size = (
                int(os.getenv('ASSET_PIPELINE_PREVIEW_GRID_WIDTH', '96')),
                int(os.getenv('ASSET_PIPELINE_PREVIEW_GRID_HEIGHT', '96'))
            )
        
        if os.getenv('ASSET_PIPELINE_PREVIEW_SHOW_LABELS'):
            config.preview_show_labels = os.getenv('ASSET_PIPELINE_PREVIEW_SHOW_LABELS', 'true').lower() == 'true'
        
        if os.getenv('ASSET_PIPELINE_PREVIEW_SHOW_GRID'):
            config.preview_show_grid = os.getenv('ASSET_PIPELINE_PREVIEW_SHOW_GRID', 'true').lower() == 'true'
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate tile size
        if self.tile_size[0] <= 0 or self.tile_size[1] <= 0:
            errors.append("tile_size must have positive dimensions")
        
        # Validate unit frame size
        if self.unit_frame_size[0] <= 0 or self.unit_frame_size[1] <= 0:
            errors.append("unit_frame_size must have positive dimensions")
        
        # Validate thresholds
        if not 0 <= self.max_alpha_threshold <= 1:
            errors.append("max_alpha_threshold must be between 0 and 1")
        
        if not 0 <= self.edge_sharpness_threshold <= 1:
            errors.append("edge_sharpness_threshold must be between 0 and 1")
        
        # Validate compression level
        if not 0 <= self.compression_level <= 9:
            errors.append("compression_level must be between 0 and 9")
        
        # Validate output format
        if self.output_format.upper() not in ['PNG', 'JPEG', 'WEBP']:
            errors.append("output_format must be PNG, JPEG, or WEBP")
        
        return errors


@dataclass
class ValidationConfig:
    """Configuration for quality validation."""
    strict_dimensions: bool = True
    require_transparency: bool = True
    validate_isometric: bool = True
    max_file_size: int = 50 * 1024 * 1024  # 50MB


@dataclass
class ErrorConfig:
    """Configuration for error handling."""
    ignore_categories: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class SecurityConfig:
    """Configuration for security validation."""
    allowed_extensions: List[str] = field(default_factory=lambda: ['.png', '.jpg', '.jpeg', '.webp'])
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    scan_downloads: bool = True