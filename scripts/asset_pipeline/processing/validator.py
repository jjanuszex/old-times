"""
Quality validation system for ensuring assets meet game requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np

from ..providers.base import AssetSpec, ProcessedAsset
from ..config import ValidationConfig


@dataclass
class ValidationResult:
    """Result of asset validation."""
    asset_name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0
    
    def add_error(self, message: str) -> None:
        """Add validation error."""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """Add validation warning."""
        self.warnings.append(message)


class QualityValidator:
    """Handles quality validation of processed assets."""
    
    def __init__(self, config: ValidationConfig):
        """Initialize validator with configuration."""
        self.config = config
    
    def validate_asset(self, asset: ProcessedAsset) -> ValidationResult:
        """
        Validate a processed asset based on its type.
        
        Args:
            asset: Processed asset to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(asset.name)
        
        # Common validations
        self._validate_image_format(asset.image, result)
        self._validate_file_size(asset.image, result)
        
        # Type-specific validations
        if asset.asset_type == 'tile':
            self._validate_tile(asset, result)
        elif asset.asset_type == 'building':
            self._validate_building(asset, result)
        elif asset.asset_type == 'unit':
            self._validate_unit(asset, result)
        
        return result
    
    def validate_tile(self, image: Image.Image, spec: AssetSpec) -> ValidationResult:
        """
        Validate tile meets isometric requirements.
        
        Args:
            image: Tile image to validate
            spec: Asset specification
            
        Returns:
            ValidationResult with validation results
        """
        result = ValidationResult(spec.name)
        
        # Check dimensions
        expected_size = (64, 32)  # Isometric 2:1 ratio
        if image.size != expected_size:
            result.add_error(f"Tile size {image.size} != expected {expected_size}")
        
        # Check transparency
        if self.config.require_transparency and not self._has_transparent_background(image):
            result.add_error("Tile lacks transparent background")
        
        # Check isometric compliance
        if self.config.validate_isometric and not self._validate_isometric_tile(image):
            result.add_warning("Tile may not be properly aligned to isometric grid")
        
        return result
    
    def validate_building(self, image: Image.Image, spec: AssetSpec) -> ValidationResult:
        """
        Validate building meets size and alignment requirements.
        
        Args:
            image: Building image to validate
            spec: Asset specification
            
        Returns:
            ValidationResult with validation results
        """
        result = ValidationResult(spec.name)
        
        # Check dimensions are multiples of tile size
        tile_width, tile_height = 64, 32
        width, height = image.size
        
        if width % tile_width != 0:
            result.add_error(f"Building width {width} is not a multiple of tile width {tile_width}")
        
        # Buildings can have extra height for depth, so we're more lenient
        if height < tile_height:
            result.add_error(f"Building height {height} is less than minimum tile height {tile_height}")
        
        # Check transparency
        if self.config.require_transparency and not self._has_transparent_background(image):
            result.add_error("Building lacks transparent background")
        
        # Check isometric compliance
        if self.config.validate_isometric and not self._validate_isometric_building(image):
            result.add_warning("Building may not maintain proper isometric 2:1 aspect ratio")
        
        return result
    
    def validate_unit_atlas(self, atlas: Image.Image, frame_map: Dict[str, Dict[str, int]]) -> ValidationResult:
        """
        Validate unit atlas has correct frame layout.
        
        Args:
            atlas: Atlas image to validate
            frame_map: Frame mapping data
            
        Returns:
            ValidationResult with validation results
        """
        result = ValidationResult("unit_atlas")
        
        # Check atlas dimensions
        expected_width = 8 * 64  # 8 frames
        expected_height = 8 * 64  # 8 directions
        expected_size = (expected_width, expected_height)
        
        self._validate_atlas_dimensions(atlas, expected_size, result)
        
        # Check frame count
        expected_frames = 64  # 8 directions × 8 frames
        if len(frame_map) != expected_frames:
            result.add_error(f"Frame count {len(frame_map)} != expected {expected_frames}")
        
        # Validate frame boundaries and dimensions
        for frame_name, frame_data in frame_map.items():
            x, y, w, h = frame_data['x'], frame_data['y'], frame_data['w'], frame_data['h']
            
            # Check frame is within atlas bounds
            if x + w > atlas.width or y + h > atlas.height:
                result.add_error(f"Frame {frame_name} extends beyond atlas bounds")
            
            # Check frame size
            if (w, h) != (64, 64):
                result.add_error(f"Frame {frame_name} size {(w, h)} != expected (64, 64)")
            
            # Check frame position is valid
            if x < 0 or y < 0:
                result.add_error(f"Frame {frame_name} has negative position: ({x}, {y})")
        
        return result
    
    def _validate_tile(self, asset: ProcessedAsset, result: ValidationResult) -> None:
        """Validate tile-specific requirements."""
        image = asset.image
        
        # Check exact dimensions
        self._validate_tile_dimensions(image, asset.name, result)
        
        # Check transparency
        self._validate_transparency(image, f"Tile {asset.name}", result)
        
        # Check isometric compliance
        if self.config.validate_isometric:
            self._validate_isometric_compliance(image, asset.name, asset.asset_type, result)
    
    def _validate_building(self, asset: ProcessedAsset, result: ValidationResult) -> None:
        """Validate building-specific requirements."""
        image = asset.image
        
        # Check dimensions are reasonable multiples
        self._validate_building_dimensions(image, asset.name, result)
        
        # Check transparency
        self._validate_transparency(image, f"Building {asset.name}", result)
        
        # Check isometric compliance
        if self.config.validate_isometric:
            self._validate_isometric_compliance(image, asset.name, asset.asset_type, result)
    
    def _validate_unit(self, asset: ProcessedAsset, result: ValidationResult) -> None:
        """Validate unit-specific requirements."""
        image = asset.image
        
        # Check frame dimensions
        self._validate_unit_frame_dimensions(image, asset.name, result)
        
        # Check transparency
        self._validate_transparency(image, f"Unit frame {asset.name}", result)
        
        # Check isometric compliance
        if self.config.validate_isometric:
            self._validate_isometric_compliance(image, asset.name, asset.asset_type, result)
    
    def _validate_image_format(self, image: Image.Image, result: ValidationResult) -> None:
        """Validate image format and properties."""
        # Check mode
        if image.mode not in ['RGBA', 'RGB']:
            result.add_warning(f"Image mode {image.mode} may not be optimal (prefer RGBA)")
        
        # Check for transparency support
        if image.mode != 'RGBA' and self.config.require_transparency:
            result.add_error("Image does not support transparency (not RGBA mode)")
    
    def _validate_file_size(self, image: Image.Image, result: ValidationResult) -> None:
        """Validate image file size is reasonable."""
        # Estimate file size (rough calculation)
        width, height = image.size
        channels = len(image.getbands())
        estimated_size = width * height * channels
        
        # Check if size is reasonable (this is a rough check)
        max_reasonable_size = self.config.max_file_size if hasattr(self.config, 'max_file_size') else 10 * 1024 * 1024
        if estimated_size > max_reasonable_size:
            result.add_warning(f"Image size may be too large: {estimated_size} bytes")
    
    def _has_transparent_background(self, image: Image.Image) -> bool:
        """Check if image has transparent background."""
        if image.mode != 'RGBA':
            return False
        
        # Convert to numpy array for easier processing
        img_array = np.array(image)
        alpha_channel = img_array[:, :, 3]
        
        # Check if there are any fully transparent pixels
        return np.any(alpha_channel == 0)
    
    def _validate_transparency(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Comprehensive transparency validation."""
        # Check if image supports transparency
        if image.mode != 'RGBA':
            if self.config.require_transparency:
                result.add_error(f"{asset_name} does not support transparency (mode: {image.mode})")
            else:
                result.add_warning(f"{asset_name} does not support transparency (mode: {image.mode})")
            return
        
        # Convert to numpy array for analysis
        img_array = np.array(image)
        alpha_channel = img_array[:, :, 3]
        
        # Check for transparent background
        if self.config.require_transparency and not self._has_transparent_background(image):
            result.add_error(f"{asset_name} lacks transparent background")
        
        # Validate alpha channel values
        self._validate_alpha_channel(alpha_channel, asset_name, result)
        
        # Check edge transparency
        self._validate_edge_transparency(alpha_channel, asset_name, result)
        
        # Check background color consistency
        self._validate_background_consistency(img_array, asset_name, result)
    
    def _validate_alpha_channel(self, alpha_channel: np.ndarray, asset_name: str, result: ValidationResult) -> None:
        """Validate alpha channel properties."""
        # Check for valid alpha values (0-255)
        min_alpha = np.min(alpha_channel)
        max_alpha = np.max(alpha_channel)
        
        if min_alpha < 0 or max_alpha > 255:
            result.add_error(f"{asset_name} has invalid alpha values: range [{min_alpha}, {max_alpha}]")
        
        # Check for semi-transparent pixels (may indicate anti-aliasing issues)
        semi_transparent = np.sum((alpha_channel > 0) & (alpha_channel < 255))
        total_pixels = alpha_channel.size
        semi_transparent_ratio = semi_transparent / total_pixels
        
        if semi_transparent_ratio > 0.1:  # More than 10% semi-transparent
            result.add_warning(f"{asset_name} has high semi-transparency ratio: {semi_transparent_ratio:.2%}")
        
        # Check for fully transparent pixels
        fully_transparent = np.sum(alpha_channel == 0)
        if fully_transparent == 0 and self.config.require_transparency:
            result.add_error(f"{asset_name} has no fully transparent pixels")
        
        # Check for fully opaque pixels
        fully_opaque = np.sum(alpha_channel == 255)
        if fully_opaque == 0:
            result.add_warning(f"{asset_name} has no fully opaque pixels")
    
    def _validate_edge_transparency(self, alpha_channel: np.ndarray, asset_name: str, result: ValidationResult) -> None:
        """Validate transparency at image edges."""
        height, width = alpha_channel.shape
        
        # Check edges for transparency
        top_edge = alpha_channel[0, :]
        bottom_edge = alpha_channel[-1, :]
        left_edge = alpha_channel[:, 0]
        right_edge = alpha_channel[:, -1]
        
        # Count non-transparent edge pixels
        edge_pixels = np.concatenate([top_edge, bottom_edge, left_edge, right_edge])
        non_transparent_edges = np.sum(edge_pixels > 0)
        total_edge_pixels = len(edge_pixels)
        
        if non_transparent_edges > 0:
            edge_ratio = non_transparent_edges / total_edge_pixels
            if edge_ratio > 0.5:  # More than 50% of edge pixels are non-transparent
                result.add_warning(f"{asset_name} has significant non-transparent edges: {edge_ratio:.2%}")
    
    def _validate_background_consistency(self, img_array: np.ndarray, asset_name: str, result: ValidationResult) -> None:
        """Validate background color consistency."""
        if img_array.shape[2] < 4:  # No alpha channel
            return
        
        alpha_channel = img_array[:, :, 3]
        
        # Find fully transparent pixels
        transparent_mask = alpha_channel == 0
        
        if not np.any(transparent_mask):
            return  # No transparent pixels to check
        
        # Get RGB values of transparent pixels
        transparent_pixels = img_array[transparent_mask][:, :3]  # RGB only
        
        if len(transparent_pixels) == 0:
            return
        
        # Check if transparent pixels have consistent background color
        unique_colors = np.unique(transparent_pixels.reshape(-1, 3), axis=0)
        
        if len(unique_colors) > 1:  # More than one unique color is inconsistent
            result.add_warning(f"{asset_name} has inconsistent background colors in transparent areas")
        
        # Check if transparent pixels are not black (common issue)
        non_black_transparent = np.sum(np.any(transparent_pixels != [0, 0, 0], axis=1))
        if non_black_transparent > len(transparent_pixels) * 0.1:  # More than 10%
            result.add_warning(f"{asset_name} has non-black colors in transparent areas")
    
    def _validate_isometric_tile(self, image: Image.Image) -> bool:
        """Validate tile follows isometric projection rules."""
        # This is a simplified check - in practice you'd want more sophisticated validation
        width, height = image.size
        
        # Check 2:1 aspect ratio
        expected_ratio = 2.0
        actual_ratio = width / height
        tolerance = 0.1
        
        return abs(actual_ratio - expected_ratio) <= tolerance
    
    def _validate_isometric_building(self, image: Image.Image) -> bool:
        """Validate building maintains isometric proportions."""
        # This is a simplified check
        width, height = image.size
        
        # Buildings can have extra height, but width should still follow tile multiples
        return width % 64 == 0
    
    def _validate_isometric_compliance(self, image: Image.Image, asset_name: str, asset_type: str, result: ValidationResult) -> None:
        """Comprehensive isometric compliance validation."""
        if not self.config.validate_isometric:
            return
            
        width, height = image.size
        
        if asset_type == 'tile':
            self._validate_tile_isometric_compliance(image, asset_name, result)
        elif asset_type == 'building':
            self._validate_building_isometric_compliance(image, asset_name, result)
        elif asset_type == 'unit':
            self._validate_unit_isometric_compliance(image, asset_name, result)
    
    def _validate_tile_isometric_compliance(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate tile follows isometric 2:1 aspect ratio and grid alignment."""
        width, height = image.size
        
        # Check 2:1 aspect ratio
        expected_ratio = 2.0
        if height > 0:
            actual_ratio = width / height
            tolerance = 0.05  # Stricter tolerance for tiles
            
            if abs(actual_ratio - expected_ratio) > tolerance:
                result.add_error(f"Tile {asset_name} aspect ratio {actual_ratio:.2f} != expected {expected_ratio} (tolerance: ±{tolerance})")
        
        # Check exact dimensions for standard isometric tile
        if (width, height) != (64, 32):
            result.add_warning(f"Tile {asset_name} dimensions {(width, height)} != standard isometric tile (64, 32)")
        
        # Validate grid alignment
        self._validate_grid_alignment(image, asset_name, result)
    
    def _validate_building_isometric_compliance(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate building maintains isometric proportions and grid alignment."""
        width, height = image.size
        
        # Check width is multiple of tile width (64px)
        tile_width = 64
        if width % tile_width != 0:
            result.add_error(f"Building {asset_name} width {width} is not aligned to isometric grid (not multiple of {tile_width})")
        
        # Check minimum height
        min_height = 32  # At least one tile height
        if height < min_height:
            result.add_error(f"Building {asset_name} height {height} is less than minimum isometric height {min_height}")
        
        # Validate building proportions
        tile_count_width = width // tile_width
        expected_base_height = max(32, tile_count_width * 16)  # Isometric depth for base, minimum 32
        
        if height < expected_base_height:
            result.add_warning(f"Building {asset_name} height {height} may be too short for {tile_count_width}x{tile_count_width} base (expected min: {expected_base_height})")
        
        # Check for reasonable maximum height
        max_reasonable_height = tile_count_width * 128  # Allow tall buildings
        if height > max_reasonable_height:
            result.add_warning(f"Building {asset_name} height {height} may be too tall for {tile_count_width}x{tile_count_width} base")
        
        # Validate visual consistency
        self._validate_building_visual_consistency(image, asset_name, result)
    
    def _validate_unit_isometric_compliance(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate unit frame follows isometric perspective rules."""
        width, height = image.size
        
        # Units should be square for animation frames
        if width != height:
            result.add_warning(f"Unit {asset_name} frame is not square: {(width, height)}")
        
        # Check standard unit frame size
        if (width, height) != (64, 64):
            result.add_warning(f"Unit {asset_name} frame size {(width, height)} != standard (64, 64)")
        
        # Validate unit positioning within frame
        self._validate_unit_positioning(image, asset_name, result)
    
    def _validate_grid_alignment(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate asset alignment to isometric grid."""
        if image.mode != 'RGBA':
            return  # Can't validate alignment without transparency
        
        # Convert to numpy array
        img_array = np.array(image)
        alpha_channel = img_array[:, :, 3]
        
        # Find the bounding box of non-transparent pixels
        non_transparent = np.where(alpha_channel > 0)
        
        if len(non_transparent[0]) == 0:
            result.add_warning(f"{asset_name} has no visible content for grid alignment validation")
            return
        
        min_y, max_y = np.min(non_transparent[0]), np.max(non_transparent[0])
        min_x, max_x = np.min(non_transparent[1]), np.max(non_transparent[1])
        
        content_width = max_x - min_x + 1
        content_height = max_y - min_y + 1
        
        # Check if content is centered
        image_center_x = image.width // 2
        image_center_y = image.height // 2
        content_center_x = (min_x + max_x) // 2
        content_center_y = (min_y + max_y) // 2
        
        center_offset_x = abs(content_center_x - image_center_x)
        center_offset_y = abs(content_center_y - image_center_y)
        
        # Allow some tolerance for centering
        tolerance_x = max(2, image.width // 20)  # 5% or 2px minimum
        tolerance_y = max(2, image.height // 20)
        
        if center_offset_x > tolerance_x:
            result.add_warning(f"{asset_name} content may not be horizontally centered (offset: {center_offset_x}px)")
        
        if center_offset_y > tolerance_y:
            result.add_warning(f"{asset_name} content may not be vertically centered (offset: {center_offset_y}px)")
    
    def _validate_building_visual_consistency(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate building visual consistency with isometric perspective."""
        if image.mode != 'RGBA':
            return
        
        # Convert to numpy array
        img_array = np.array(image)
        alpha_channel = img_array[:, :, 3]
        
        # Find non-transparent pixels
        non_transparent = np.where(alpha_channel > 0)
        
        if len(non_transparent[0]) == 0:
            return
        
        # Check if building has reasonable distribution of pixels
        # (not just a thin line or single point)
        min_y, max_y = np.min(non_transparent[0]), np.max(non_transparent[0])
        min_x, max_x = np.min(non_transparent[1]), np.max(non_transparent[1])
        
        content_width = max_x - min_x + 1
        content_height = max_y - min_y + 1
        
        # Check if building has reasonable proportions
        if content_width < image.width * 0.3:
            result.add_warning(f"Building {asset_name} content width {content_width} seems narrow for image width {image.width}")
        
        if content_height < image.height * 0.3:
            result.add_warning(f"Building {asset_name} content height {content_height} seems short for image height {image.height}")
    
    def _validate_unit_positioning(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate unit positioning within frame for animation consistency."""
        if image.mode != 'RGBA':
            return
        
        # Convert to numpy array
        img_array = np.array(image)
        alpha_channel = img_array[:, :, 3]
        
        # Find non-transparent pixels
        non_transparent = np.where(alpha_channel > 0)
        
        if len(non_transparent[0]) == 0:
            result.add_warning(f"Unit {asset_name} has no visible content")
            return
        
        # Check if unit is positioned in lower portion of frame (typical for isometric units)
        min_y, max_y = np.min(non_transparent[0]), np.max(non_transparent[0])
        content_center_y = (min_y + max_y) // 2
        
        # Units should typically be in the lower 2/3 of the frame
        expected_center_y = image.height * 2 // 3
        tolerance = image.height // 3  # More lenient tolerance
        
        if abs(content_center_y - expected_center_y) > tolerance:
            result.add_warning(f"Unit {asset_name} may not be positioned optimally for isometric view (center Y: {content_center_y}, expected around: {expected_center_y})")
        
        # Check if unit has reasonable size within frame
        content_height = max_y - min_y + 1
        if content_height < image.height * 0.4:
            result.add_warning(f"Unit {asset_name} content seems small for frame size")
        elif content_height > image.height * 0.9:
            result.add_warning(f"Unit {asset_name} content may be too large for frame")
    
    def _validate_tile_dimensions(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate tile has exact 64×32 pixel dimensions."""
        expected_size = (64, 32)
        actual_size = image.size
        
        if self.config.strict_dimensions and actual_size != expected_size:
            result.add_error(f"Tile {asset_name} size {actual_size} != required {expected_size}")
        elif actual_size != expected_size:
            result.add_warning(f"Tile {asset_name} size {actual_size} != recommended {expected_size}")
        
        # Additional dimension checks
        width, height = actual_size
        if width <= 0 or height <= 0:
            result.add_error(f"Tile {asset_name} has invalid dimensions: {actual_size}")
        
        # Check aspect ratio for isometric tiles (2:1)
        if height > 0:
            aspect_ratio = width / height
            expected_ratio = 2.0
            tolerance = 0.1
            if abs(aspect_ratio - expected_ratio) > tolerance:
                result.add_warning(f"Tile {asset_name} aspect ratio {aspect_ratio:.2f} != expected {expected_ratio}")
    
    def _validate_unit_frame_dimensions(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate unit frame has exact 64×64 pixel dimensions."""
        expected_size = (64, 64)
        actual_size = image.size
        
        if self.config.strict_dimensions and actual_size != expected_size:
            result.add_error(f"Unit frame {asset_name} size {actual_size} != required {expected_size}")
        elif actual_size != expected_size:
            result.add_warning(f"Unit frame {asset_name} size {actual_size} != recommended {expected_size}")
        
        # Additional dimension checks
        width, height = actual_size
        if width <= 0 or height <= 0:
            result.add_error(f"Unit frame {asset_name} has invalid dimensions: {actual_size}")
        
        # Check that frame is square
        if width != height:
            result.add_warning(f"Unit frame {asset_name} is not square: {actual_size}")
    
    def _validate_building_dimensions(self, image: Image.Image, asset_name: str, result: ValidationResult) -> None:
        """Validate building dimensions are multiples of tile size."""
        width, height = image.size
        tile_width, tile_height = 64, 32
        
        # Check width is multiple of tile width
        if width % tile_width != 0:
            result.add_error(f"Building {asset_name} width {width} is not a multiple of tile width {tile_width}")
        
        # Check minimum height
        if height < tile_height:
            result.add_error(f"Building {asset_name} height {height} is less than minimum tile height {tile_height}")
        
        # Check height is reasonable (warn if not multiple of tile height)
        if height % tile_height != 0:
            result.add_warning(f"Building {asset_name} height {height} is not a multiple of tile height {tile_height}")
        
        # Additional dimension checks
        if width <= 0 or height <= 0:
            result.add_error(f"Building {asset_name} has invalid dimensions: {image.size}")
        
        # Check reasonable size limits
        max_width = 512  # 8 tiles wide
        max_height = 512  # Reasonable building height
        if width > max_width:
            result.add_warning(f"Building {asset_name} width {width} exceeds recommended maximum {max_width}")
        if height > max_height:
            result.add_warning(f"Building {asset_name} height {height} exceeds recommended maximum {max_height}")
    
    def _validate_atlas_dimensions(self, atlas: Image.Image, expected_size: tuple[int, int], result: ValidationResult) -> None:
        """Validate atlas has expected dimensions."""
        actual_size = atlas.size
        
        if actual_size != expected_size:
            result.add_error(f"Atlas size {actual_size} != expected {expected_size}")
        
        # Check dimensions are positive
        width, height = actual_size
        if width <= 0 or height <= 0:
            result.add_error(f"Atlas has invalid dimensions: {actual_size}")
        
        # Check dimensions are reasonable multiples
        if width % 64 != 0 or height % 64 != 0:
            result.add_warning(f"Atlas dimensions {actual_size} are not multiples of 64")
    
    def validate_batch(self, assets: List[ProcessedAsset]) -> Dict[str, ValidationResult]:
        """
        Validate a batch of assets.
        
        Args:
            assets: List of processed assets to validate
            
        Returns:
            Dictionary mapping asset names to validation results
        """
        results = {}
        
        for asset in assets:
            results[asset.name] = self.validate_asset(asset)
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """
        Get summary of validation results.
        
        Args:
            results: Dictionary of validation results
            
        Returns:
            Summary statistics
        """
        total_assets = len(results)
        valid_assets = sum(1 for r in results.values() if r.is_valid)
        assets_with_warnings = sum(1 for r in results.values() if r.has_warnings)
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        
        return {
            "total_assets": total_assets,
            "valid_assets": valid_assets,
            "invalid_assets": total_assets - valid_assets,
            "assets_with_warnings": assets_with_warnings,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "success_rate": valid_assets / total_assets if total_assets > 0 else 0.0
        }


class ValidationError(Exception):
    """Exception raised when validation fails critically."""
    
    def __init__(self, message: str, results: Optional[Dict[str, ValidationResult]] = None):
        super().__init__(message)
        self.message = message
        self.results = results or {}