"""
Metadata generation for sprites.toml and other configuration files.
"""

import os
import toml
from typing import List, Dict, Any, Optional
from pathlib import Path
import jinja2
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError

from ..providers.base import ProcessedAsset
from .atlas import AtlasResult


class MetadataGenerator:
    """Handles generation of metadata files for sprites and atlases."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize metadata generator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        if template_dir is None:
            # Use templates directory relative to this file
            template_dir = Path(__file__).parent.parent / "templates"
        
        self.template_dir = Path(template_dir)
        
        # Ensure template directory exists
        self.ensure_template_directory()
        
        # Set up Jinja2 environment with enhanced configuration
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False
        )
        
        # Add custom filters for template processing
        self._setup_template_filters()
    
    def _refresh_template_environment(self) -> None:
        """Refresh the Jinja2 environment to pick up template changes."""
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False
        )
        self._setup_template_filters()
    
    def _setup_template_filters(self) -> None:
        """Set up custom Jinja2 filters for template processing."""
        
        def calculate_tile_footprint(width: int, height: int) -> List[int]:
            """Calculate tile footprint for buildings."""
            tile_width = max(1, width // 64)
            tile_height = max(1, height // 64)  # More accurate calculation
            return [tile_width, tile_height]
        
        def format_path(path: str) -> str:
            """Format file path for TOML output."""
            return path.replace('\\', '/')
        
        def safe_name(name: str) -> str:
            """Ensure name is safe for TOML keys."""
            # Replace invalid characters with underscores
            import re
            return re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Register filters
        self.env.filters['tile_footprint'] = calculate_tile_footprint
        self.env.filters['format_path'] = format_path
        self.env.filters['safe_name'] = safe_name
    
    def generate_sprites_toml(self, assets: List[ProcessedAsset], atlases: Optional[Dict[str, AtlasResult]] = None) -> str:
        """
        Generate sprites.toml metadata file.
        
        Args:
            assets: List of processed assets
            atlases: Optional dictionary of atlas results
            
        Returns:
            Generated TOML content as string
            
        Raises:
            MetadataGenerationError: If template processing fails
        """
        if not assets:
            raise MetadataGenerationError("No assets provided for sprites.toml generation")
        
        # Organize assets by type
        tiles = [a for a in assets if a.asset_type == 'tile']
        buildings = [a for a in assets if a.asset_type == 'building']
        units = [a for a in assets if a.asset_type == 'unit']
        
        # Prepare atlas data
        atlas_data = {}
        if atlases:
            for name, atlas_result in atlases.items():
                atlas_data[name] = {
                    'size': [atlas_result.atlas.width, atlas_result.atlas.height],
                    'frame_map': atlas_result.frame_map,
                    'metadata': atlas_result.metadata
                }
        
        # Prepare template variables
        template_vars = {
            'tiles': tiles,
            'buildings': buildings,
            'units': units,
            'atlases': atlas_data,
            'total_assets': len(assets),
            'generation_timestamp': self._get_timestamp()
        }
        
        try:
            template = self.env.get_template('sprites.toml.j2')
            content = template.render(**template_vars)
            
            # Validate generated content
            validation_errors = self.validate_toml_syntax(content)
            if validation_errors:
                raise MetadataGenerationError(f"Generated TOML has syntax errors: {', '.join(validation_errors)}")
            
            return content
            
        except TemplateNotFound as e:
            # Fallback to built-in template if template file not found
            try:
                return self._generate_sprites_toml_builtin(tiles, buildings, units, atlas_data)
            except Exception as fallback_error:
                raise MetadataGenerationError(f"Template not found and fallback failed: {fallback_error}")
        except TemplateSyntaxError as e:
            # Fallback to built-in template if template has syntax errors
            try:
                return self._generate_sprites_toml_builtin(tiles, buildings, units, atlas_data)
            except Exception as fallback_error:
                raise MetadataGenerationError(f"Template syntax error and fallback failed: {fallback_error}")
        except Exception as e:
            # Fallback to built-in template for other template processing errors
            try:
                return self._generate_sprites_toml_builtin(tiles, buildings, units, atlas_data)
            except Exception as fallback_error:
                raise MetadataGenerationError(f"Template processing failed: {e}, Fallback also failed: {fallback_error}")
    
    def generate_mod_toml(self, mod_name: str, assets: List[ProcessedAsset]) -> str:
        """
        Generate mod.toml metadata file.
        
        Args:
            mod_name: Name of the mod
            assets: List of processed assets for the mod
            
        Returns:
            Generated TOML content as string
            
        Raises:
            MetadataGenerationError: If template processing fails
        """
        if not mod_name or not mod_name.strip():
            raise MetadataGenerationError("Mod name cannot be empty")
        
        # Prepare template variables
        template_vars = {
            'mod_name': mod_name.strip(),
            'assets': assets,
            'asset_count': len(assets),
            'generation_timestamp': self._get_timestamp()
        }
        
        try:
            template = self.env.get_template('mod.toml.j2')
            content = template.render(**template_vars)
            
            # Validate generated content
            validation_errors = self.validate_toml_syntax(content)
            if validation_errors:
                raise MetadataGenerationError(f"Generated mod TOML has syntax errors: {', '.join(validation_errors)}")
            
            return content
            
        except TemplateNotFound as e:
            # Fallback to built-in template
            try:
                return self._generate_mod_toml_builtin(mod_name, assets)
            except Exception as fallback_error:
                raise MetadataGenerationError(f"Mod template not found and fallback failed: {fallback_error}")
        except TemplateSyntaxError as e:
            # Fallback to built-in template
            try:
                return self._generate_mod_toml_builtin(mod_name, assets)
            except Exception as fallback_error:
                raise MetadataGenerationError(f"Mod template syntax error and fallback failed: {fallback_error}")
        except Exception as e:
            # Fallback to built-in template
            try:
                return self._generate_mod_toml_builtin(mod_name, assets)
            except Exception as fallback_error:
                raise MetadataGenerationError(f"Mod template processing failed: {e}, Fallback also failed: {fallback_error}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata generation."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def validate_toml_syntax(self, content: str) -> List[str]:
        """
        Validate TOML syntax.
        
        Args:
            content: TOML content to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        try:
            toml.loads(content)
        except toml.TomlDecodeError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error during TOML validation: {e}")
        
        return errors
    
    def _generate_sprites_toml_builtin(self, tiles: List[ProcessedAsset], buildings: List[ProcessedAsset], 
                                     units: List[ProcessedAsset], atlases: Dict[str, Any]) -> str:
        """Built-in template for sprites.toml generation."""
        lines = ["# Generated sprites.toml", ""]
        
        # Tiles section
        if tiles:
            lines.append("[tiles]")
            for tile in tiles:
                lines.append(f'[tiles.{tile.name}]')
                lines.append('kind = "tile"')
                lines.append(f'size = [{tile.image.width}, {tile.image.height}]')
                lines.append(f'source = "{tile.output_path}"')
                lines.append("")
        
        # Buildings section
        if buildings:
            lines.append("[buildings]")
            for building in buildings:
                lines.append(f'[buildings.{building.name}]')
                lines.append('kind = "building"')
                lines.append(f'size = [{building.image.width}, {building.image.height}]')
                lines.append(f'source = "{building.output_path}"')
                
                # Calculate tile footprint (assuming 64x32 tiles)
                tile_width = max(1, building.image.width // 64)
                tile_height = max(1, building.image.height // 64)  # More accurate for isometric buildings
                lines.append(f'tile_footprint = [{tile_width}, {tile_height}]')
                lines.append("")
        
        # Units section
        if units:
            lines.append("[units]")
            for unit in units:
                lines.append(f'[units.{unit.name}]')
                lines.append('kind = "unit"')
                
                # Check if unit has atlas
                atlas_name = f"{unit.name}_atlas"
                if atlas_name in atlases:
                    atlas_info = atlases[atlas_name]
                    lines.append(f'source = "atlases/{atlas_name}.png"')
                    lines.append(f'frame_size = [64, 64]')
                    lines.append('directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]')
                    lines.append('anim_walk_fps = 10')
                    lines.append('anim_walk_len = 8')
                    lines.append('layout = "dirs_rows"')
                    lines.append(f'atlas_map = "atlases/{atlas_name}.json"')
                else:
                    lines.append(f'source = "{unit.output_path}"')
                    lines.append(f'frame_size = [{unit.image.width}, {unit.image.height}]')
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_mod_toml_builtin(self, mod_name: str, assets: List[ProcessedAsset]) -> str:
        """Built-in template for mod.toml generation."""
        lines = [
            f"# Mod configuration for {mod_name}",
            "",
            "[mod]",
            f'name = "{mod_name}"',
            f'version = "1.0.0"',
            f'description = "Generated mod with {len(assets)} assets"',
            "",
            "[assets]"
        ]
        
        # Group assets by type
        asset_types = {}
        for asset in assets:
            if asset.asset_type not in asset_types:
                asset_types[asset.asset_type] = []
            asset_types[asset.asset_type].append(asset.name)
        
        for asset_type, names in asset_types.items():
            # Format names with double quotes for consistency
            formatted_names = [f'"{name}"' for name in names]
            lines.append(f'{asset_type}s = [{", ".join(formatted_names)}]')
        
        return "\n".join(lines)
    
    def validate_metadata(self, metadata_content: str, schema_type: str = "sprites", 
                         base_path: Optional[str] = None, atlases: Optional[Dict[str, AtlasResult]] = None) -> List[str]:
        """
        Validate generated metadata content.
        
        Args:
            metadata_content: Generated metadata content
            schema_type: Type of schema to validate against
            base_path: Base path for file reference validation
            atlases: Atlas results for cross-reference validation
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # First validate TOML syntax
        syntax_errors = self.validate_toml_syntax(metadata_content)
        if syntax_errors:
            errors.extend([f"TOML syntax error: {err}" for err in syntax_errors])
            return errors  # Can't continue validation if syntax is invalid
        
        try:
            # Parse TOML content for detailed validation
            parsed_toml = toml.loads(metadata_content)
            
            if schema_type == "sprites":
                errors.extend(self._validate_sprites_schema(parsed_toml))
                
                if base_path:
                    errors.extend(self._validate_file_references(parsed_toml, base_path))
                
                # Always validate atlas references (will check for missing atlases)
                errors.extend(self._validate_atlas_references(parsed_toml, atlases or {}))
            
            elif schema_type == "mod":
                errors.extend(self._validate_mod_schema(parsed_toml))
                
        except Exception as e:
            errors.append(f"Failed to parse TOML for validation: {e}")
        
        return errors
    
    def _validate_sprites_schema(self, parsed_toml: Dict[str, Any]) -> List[str]:
        """Validate sprites.toml schema structure."""
        errors = []
        
        # Check for main sections
        expected_sections = ["tiles", "buildings", "units"]
        for section in expected_sections:
            if section in parsed_toml:
                section_errors = self._validate_sprite_section(parsed_toml[section], section)
                errors.extend(section_errors)
        
        return errors
    
    def _validate_sprite_section(self, section_data: Dict[str, Any], section_type: str) -> List[str]:
        """Validate individual sprite section."""
        errors = []
        
        for sprite_name, sprite_data in section_data.items():
            if not isinstance(sprite_data, dict):
                errors.append(f"{section_type}.{sprite_name}: must be a dictionary")
                continue
            
            # Validate required fields
            required_fields = ["kind", "source"]
            
            # Size is required unless it's a unit with frame_size (atlas units)
            if section_type != "units" or "frame_size" not in sprite_data:
                required_fields.append("size")
            
            for field in required_fields:
                if field not in sprite_data:
                    errors.append(f"{section_type}.{sprite_name}: missing required field '{field}'")
            
            # Validate field types and values
            if "kind" in sprite_data:
                expected_kind = section_type[:-1]  # Remove 's' from plural
                if sprite_data["kind"] != expected_kind:
                    errors.append(f"{section_type}.{sprite_name}: kind should be '{expected_kind}', got '{sprite_data['kind']}'")
            
            if "size" in sprite_data:
                size = sprite_data["size"]
                if not isinstance(size, list) or len(size) != 2:
                    errors.append(f"{section_type}.{sprite_name}: size must be [width, height]")
                elif not all(isinstance(x, int) and x > 0 for x in size):
                    errors.append(f"{section_type}.{sprite_name}: size values must be positive integers")
                else:
                    # Validate size constraints
                    width, height = size
                    if section_type == "tiles" and (width != 64 or height != 32):
                        errors.append(f"{section_type}.{sprite_name}: tiles must be 64x32 pixels, got {width}x{height}")
                    elif section_type == "units" and "frame_size" in sprite_data:
                        frame_size = sprite_data["frame_size"]
                        if isinstance(frame_size, list) and len(frame_size) == 2:
                            if frame_size[0] != 64 or frame_size[1] != 64:
                                errors.append(f"{section_type}.{sprite_name}: unit frames must be 64x64 pixels")
            
            # Additional validation for frame_size field in units
            if section_type == "units" and "frame_size" in sprite_data:
                frame_size = sprite_data["frame_size"]
                if not isinstance(frame_size, list) or len(frame_size) != 2:
                    errors.append(f"{section_type}.{sprite_name}: frame_size must be [width, height]")
                elif not all(isinstance(x, int) and x > 0 for x in frame_size):
                    errors.append(f"{section_type}.{sprite_name}: frame_size values must be positive integers")
                elif frame_size[0] != 64 or frame_size[1] != 64:
                    errors.append(f"{section_type}.{sprite_name}: unit frames must be 64x64 pixels")
            
            # Validate unit-specific fields
            if section_type == "units":
                unit_errors = self._validate_unit_fields(sprite_name, sprite_data)
                errors.extend(unit_errors)
            
            # Validate building-specific fields
            if section_type == "buildings":
                building_errors = self._validate_building_fields(sprite_name, sprite_data)
                errors.extend(building_errors)
        
        return errors
    
    def _validate_unit_fields(self, unit_name: str, unit_data: Dict[str, Any]) -> List[str]:
        """Validate unit-specific fields."""
        errors = []
        
        # Check for animation fields if atlas is used
        if "atlas_map" in unit_data:
            required_anim_fields = ["frame_size", "directions", "anim_walk_fps", "anim_walk_len", "layout"]
            for field in required_anim_fields:
                if field not in unit_data:
                    errors.append(f"units.{unit_name}: missing animation field '{field}' for atlas unit")
            
            # Validate directions
            if "directions" in unit_data:
                directions = unit_data["directions"]
                expected_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                if directions != expected_directions:
                    errors.append(f"units.{unit_name}: directions must be {expected_directions}")
            
            # Validate animation parameters
            if "anim_walk_fps" in unit_data:
                fps = unit_data["anim_walk_fps"]
                if not isinstance(fps, int) or fps <= 0:
                    errors.append(f"units.{unit_name}: anim_walk_fps must be positive integer")
            
            if "anim_walk_len" in unit_data:
                length = unit_data["anim_walk_len"]
                if not isinstance(length, int) or length <= 0:
                    errors.append(f"units.{unit_name}: anim_walk_len must be positive integer")
            
            if "layout" in unit_data:
                layout = unit_data["layout"]
                if layout != "dirs_rows":
                    errors.append(f"units.{unit_name}: layout must be 'dirs_rows'")
        
        return errors
    
    def _validate_building_fields(self, building_name: str, building_data: Dict[str, Any]) -> List[str]:
        """Validate building-specific fields."""
        errors = []
        
        # Validate tile footprint if present
        if "tile_footprint" in building_data:
            footprint = building_data["tile_footprint"]
            if not isinstance(footprint, list) or len(footprint) != 2:
                errors.append(f"buildings.{building_name}: tile_footprint must be [width, height]")
            elif not all(isinstance(x, int) and x > 0 for x in footprint):
                errors.append(f"buildings.{building_name}: tile_footprint values must be positive integers")
        
        return errors
    
    def _validate_mod_schema(self, parsed_toml: Dict[str, Any]) -> List[str]:
        """Validate mod.toml schema structure."""
        errors = []
        
        # Check for required sections
        required_sections = ["mod", "assets"]
        for section in required_sections:
            if section not in parsed_toml:
                errors.append(f"Missing required section: [{section}]")
        
        # Validate mod section
        if "mod" in parsed_toml:
            mod_section = parsed_toml["mod"]
            required_mod_fields = ["name", "version", "description"]
            for field in required_mod_fields:
                if field not in mod_section:
                    errors.append(f"mod section missing required field: {field}")
                elif not isinstance(mod_section[field], str) or not mod_section[field].strip():
                    errors.append(f"mod.{field} must be a non-empty string")
        
        # Validate assets section
        if "assets" in parsed_toml:
            assets_section = parsed_toml["assets"]
            valid_asset_types = ["tiles", "buildings", "units"]
            for asset_type, asset_list in assets_section.items():
                if asset_type not in valid_asset_types:
                    errors.append(f"Unknown asset type in assets section: {asset_type}")
                elif not isinstance(asset_list, list):
                    errors.append(f"assets.{asset_type} must be a list")
                elif not all(isinstance(name, str) for name in asset_list):
                    errors.append(f"assets.{asset_type} must contain only strings")
        
        return errors
    
    def _validate_file_references(self, parsed_toml: Dict[str, Any], base_path: str) -> List[str]:
        """Validate that all referenced files exist."""
        errors = []
        base_path = Path(base_path)
        
        # Check sprite source files
        for section_name in ["tiles", "buildings", "units"]:
            if section_name in parsed_toml:
                for sprite_name, sprite_data in parsed_toml[section_name].items():
                    if "source" in sprite_data:
                        source_path = base_path / sprite_data["source"]
                        if not source_path.exists():
                            errors.append(f"{section_name}.{sprite_name}: source file not found: {source_path}")
                    
                    # Check atlas map files for units
                    if section_name == "units" and "atlas_map" in sprite_data:
                        atlas_map_path = base_path / sprite_data["atlas_map"]
                        if not atlas_map_path.exists():
                            errors.append(f"{section_name}.{sprite_name}: atlas_map file not found: {atlas_map_path}")
        
        return errors
    
    def _validate_atlas_references(self, parsed_toml: Dict[str, Any], atlases: Dict[str, AtlasResult]) -> List[str]:
        """Validate cross-references between metadata and atlas data."""
        errors = []
        
        if "units" in parsed_toml:
            for unit_name, unit_data in parsed_toml["units"].items():
                if "atlas_map" in unit_data:
                    # Check if corresponding atlas exists
                    atlas_name = f"{unit_name}_atlas"
                    if atlas_name not in atlases:
                        errors.append(f"units.{unit_name}: references atlas '{atlas_name}' but atlas not found")
                    else:
                        # Validate atlas consistency
                        atlas_result = atlases[atlas_name]
                        atlas_errors = self._validate_atlas_consistency(unit_name, unit_data, atlas_result)
                        errors.extend(atlas_errors)
        
        return errors
    
    def _validate_atlas_consistency(self, unit_name: str, unit_data: Dict[str, Any], atlas_result: AtlasResult) -> List[str]:
        """Validate consistency between unit metadata and atlas data."""
        errors = []
        
        # Check frame count consistency
        if "directions" in unit_data and "anim_walk_len" in unit_data:
            expected_frames = len(unit_data["directions"]) * unit_data["anim_walk_len"]
            actual_frames = len(atlas_result.frame_map)
            if actual_frames != expected_frames:
                errors.append(f"units.{unit_name}: atlas has {actual_frames} frames but metadata expects {expected_frames}")
        
        # Check frame size consistency
        if "frame_size" in unit_data and atlas_result.frame_map:
            expected_frame_size = unit_data["frame_size"]
            # Check first frame size
            first_frame = next(iter(atlas_result.frame_map.values()))
            if "w" in first_frame and "h" in first_frame:
                actual_frame_size = [first_frame["w"], first_frame["h"]]
                if actual_frame_size != expected_frame_size:
                    errors.append(f"units.{unit_name}: atlas frame size {actual_frame_size} doesn't match metadata {expected_frame_size}")
        
        return errors
    
    def ensure_template_directory(self) -> None:
        """Ensure template directory exists and create default templates if needed."""
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default sprites.toml template if it doesn't exist
        sprites_template_path = self.template_dir / "sprites.toml.j2"
        if not sprites_template_path.exists():
            self._create_default_sprites_template(sprites_template_path)
        
        # Create default mod.toml template if it doesn't exist
        mod_template_path = self.template_dir / "mod.toml.j2"
        if not mod_template_path.exists():
            self._create_default_mod_template(mod_template_path)
        
        # Refresh environment if templates were created
        if hasattr(self, 'env'):
            self._refresh_template_environment()
    
    def _create_default_sprites_template(self, path: Path) -> None:
        """Create default sprites.toml template."""
        template_content = '''# Generated sprites.toml

{% if tiles %}
[tiles]
{% for tile in tiles %}
[tiles.{{ tile.name }}]
kind = "tile"
size = [{{ tile.image.width }}, {{ tile.image.height }}]
source = "{{ tile.output_path }}"

{% endfor %}
{% endif %}

{% if buildings %}
[buildings]
{% for building in buildings %}
[buildings.{{ building.name }}]
kind = "building"
size = [{{ building.image.width }}, {{ building.image.height }}]
source = "{{ building.output_path }}"
tile_footprint = [{{ (building.image.width // 64) }}, {{ max(1, (building.image.height // 32) // 2) }}]

{% endfor %}
{% endif %}

{% if units %}
[units]
{% for unit in units %}
[units.{{ unit.name }}]
kind = "unit"
{% set atlas_name = unit.name + "_atlas" %}
{% if atlas_name in atlases %}
source = "atlases/{{ atlas_name }}.png"
frame_size = [64, 64]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "dirs_rows"
atlas_map = "atlases/{{ atlas_name }}.json"
{% else %}
source = "{{ unit.output_path }}"
frame_size = [{{ unit.image.width }}, {{ unit.image.height }}]
{% endif %}

{% endfor %}
{% endif %}'''
        
        with open(path, 'w') as f:
            f.write(template_content)
    
    def _create_default_mod_template(self, path: Path) -> None:
        """Create default mod.toml template."""
        template_content = '''# Mod configuration for {{ mod_name }}
# Generated at: {{ generation_timestamp }}

[mod]
name = "{{ mod_name | safe_name }}"
version = "1.0.0"
description = "Generated mod with {{ asset_count }} assets"
author = "Asset Pipeline"

[assets]
{% set asset_types = {} %}
{% for asset in assets %}
{% set _ = asset_types.update({asset.asset_type: asset_types.get(asset.asset_type, []) + [asset.name | safe_name]}) %}
{% endfor %}
{% for asset_type, names in asset_types.items() %}
{{ asset_type }}s = [{% for name in names %}"{{ name }}"{% if not loop.last %}, {% endif %}{% endfor %}]
{% endfor %}

[dependencies]
# List any mod dependencies here
base_game = ">=1.0.0"'''
        
        with open(path, 'w') as f:
            f.write(template_content)


class MetadataGenerationError(Exception):
    """Exception raised when metadata generation fails."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message