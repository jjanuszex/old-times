"""
Asset normalization engine for processing assets to meet isometric requirements.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union
from PIL import Image
import io

from ..providers.base import AssetSpec, ProcessedAsset
from ..utils.image import ImageUtils
from ..utils.isometric import IsometricUtils


@dataclass
class NormalizationConfig:
    """Configuration for asset normalization."""
    tile_size: tuple[int, int] = (64, 32)
    unit_frame_size: tuple[int, int] = (64, 64)
    preserve_aspect_ratio: bool = True
    background_color: tuple[int, int, int, int] = (0, 0, 0, 0)  # Transparent
    edge_sharpening: bool = True
    edge_sharpening_factor: float = 1.5
    anti_aliasing: bool = True
    transparency_tolerance: int = 10
    quality_method: str = 'lanczos'  # Resampling method for quality preservation


class AssetNormalizer:
    """Handles normalization of assets to meet isometric game requirements."""
    
    def __init__(self, config: NormalizationConfig):
        """Initialize normalizer with configuration."""
        self.config = config
    
    def normalize_asset(self, image_data: Union[bytes, Image.Image], spec: AssetSpec) -> ProcessedAsset:
        """
        Normalize asset based on its type.
        
        Args:
            image_data: Raw image data as bytes or PIL Image
            spec: Asset specification
            
        Returns:
            ProcessedAsset with normalized image
            
        Raises:
            NormalizationError: If normalization fails
        """
        try:
            # Load image using utility function
            image = ImageUtils.load_image(image_data)
            original_size = image.size
            
            # Normalize based on asset type
            if spec.asset_type == 'tile':
                normalized_image = self.normalize_tile(image, spec)
            elif spec.asset_type == 'building':
                normalized_image = self.normalize_building(image, spec)
            elif spec.asset_type == 'unit':
                normalized_image = self.normalize_unit(image, spec)
            else:
                raise NormalizationError(f"Unknown asset type: {spec.asset_type}")
            
            # Validate the normalized result
            self._validate_normalized_asset(normalized_image, spec)
            
            output_path = self._generate_output_path(spec)
            
            return ProcessedAsset(
                spec=spec,
                image=normalized_image,
                output_path=output_path,
                metadata={
                    "normalized": True, 
                    "original_size": original_size,
                    "final_size": normalized_image.size,
                    "asset_type": spec.asset_type
                }
            )
            
        except Exception as e:
            raise NormalizationError(f"Failed to normalize asset {spec.name}: {str(e)}")
    
    def normalize_tile(self, image: Image.Image, spec: AssetSpec) -> Image.Image:
        """
        Normalize tile to exact 64×32 pixel dimensions with isometric 2:1 aspect ratio.
        
        Args:
            image: Source image
            spec: Asset specification
            
        Returns:
            Normalized tile image
        """
        target_size = self.config.tile_size
        
        # Convert to RGBA for transparency support
        image = ImageUtils.ensure_rgba(image)
        
        # Validate and correct isometric ratio if needed
        if not IsometricUtils.validate_isometric_ratio(image.size):
            # Resize maintaining aspect ratio, then crop/pad to exact dimensions
            image = ImageUtils.resize_with_aspect(
                image, target_size, self.config.background_color, self.config.quality_method
            )
        else:
            # Direct resize with quality preservation
            image = ImageUtils.resize_with_quality(image, target_size, self.config.quality_method)
        
        # Enforce transparent background
        image = ImageUtils.enforce_transparent_background(image, self.config.transparency_tolerance)
        
        # Apply edge sharpening for pixel-perfect tiles
        if self.config.edge_sharpening:
            image = ImageUtils.sharpen_edges(image, self.config.edge_sharpening_factor)
        
        # Apply anti-aliasing if enabled
        if self.config.anti_aliasing:
            image = ImageUtils.apply_anti_aliasing(image, self.config.quality_method)
        
        return image
    
    def normalize_building(self, image: Image.Image, spec: AssetSpec) -> Image.Image:
        """
        Normalize building to tile multiples (64×96, 128×96, etc.) with proper isometric alignment.
        
        Args:
            image: Source image
            spec: Asset specification
            
        Returns:
            Normalized building image
        """
        # Convert to RGBA for transparency support
        image = ImageUtils.ensure_rgba(image)
        
        # Calculate target size based on tile multiples
        target_size = self._calculate_building_size(spec)
        
        # Validate building alignment requirements
        if not IsometricUtils.validate_building_alignment(image, self.config.tile_size):
            # Need to resize and align to grid
            if self.config.preserve_aspect_ratio:
                image = ImageUtils.resize_with_aspect(
                    image, target_size, self.config.background_color, self.config.quality_method
                )
            else:
                image = ImageUtils.resize_with_quality(image, target_size, self.config.quality_method)
        else:
            # Direct resize with quality preservation
            image = ImageUtils.resize_with_quality(image, target_size, self.config.quality_method)
        
        # Center building content within the target size
        image = ImageUtils.center_content(image, target_size)
        
        # Enforce transparent background
        image = ImageUtils.enforce_transparent_background(image, self.config.transparency_tolerance)
        
        # Apply edge sharpening for building detail preservation
        if self.config.edge_sharpening:
            image = ImageUtils.sharpen_edges(image, self.config.edge_sharpening_factor)
        
        # Apply anti-aliasing if enabled
        if self.config.anti_aliasing:
            image = ImageUtils.apply_anti_aliasing(image, self.config.quality_method)
        
        return image
    
    def normalize_unit(self, image: Image.Image, spec: AssetSpec) -> Image.Image:
        """
        Normalize unit frames to exact 64×64 pixels with proper centering and alignment.
        
        Args:
            image: Source image
            spec: Asset specification
            
        Returns:
            Normalized unit frame image
        """
        target_size = self.config.unit_frame_size
        
        # Convert to RGBA for transparency support
        image = ImageUtils.ensure_rgba(image)
        
        # Validate unit frame size requirements
        if not IsometricUtils.validate_unit_frame_size(image.size):
            # Resize maintaining aspect ratio and center content
            image = ImageUtils.resize_with_aspect(
                image, target_size, self.config.background_color, self.config.quality_method
            )
        else:
            # Direct resize with quality preservation
            image = ImageUtils.resize_with_quality(image, target_size, self.config.quality_method)
        
        # Ensure frame is properly centered
        image = ImageUtils.center_content(image, target_size)
        
        # Enforce transparent background
        image = ImageUtils.enforce_transparent_background(image, self.config.transparency_tolerance)
        
        # Apply edge sharpening for frame clarity
        if self.config.edge_sharpening:
            image = ImageUtils.sharpen_edges(image, self.config.edge_sharpening_factor)
        
        # Apply anti-aliasing if enabled
        if self.config.anti_aliasing:
            image = ImageUtils.apply_anti_aliasing(image, self.config.quality_method)
        
        return image
    
    def _calculate_building_size(self, spec: AssetSpec) -> tuple[int, int]:
        """Calculate appropriate building size based on tile multiples."""
        tile_width, tile_height = self.config.tile_size
        
        # If size is specified in spec, use it
        if spec.size and spec.size != (0, 0):
            return spec.size
        
        # Try to determine size from metadata
        if spec.metadata and 'tile_footprint' in spec.metadata:
            footprint = spec.metadata['tile_footprint']
            if isinstance(footprint, (list, tuple)) and len(footprint) == 2:
                width_tiles, height_tiles = footprint
                # Buildings need extra height for vertical structure
                return (width_tiles * tile_width, (height_tiles + 1) * tile_height)
        
        # Default to 2x2 building (128x96 for 64x32 tiles with height offset)
        return (tile_width * 2, tile_height * 3)  # Extra height for building depth
    
    def _validate_normalized_asset(self, image: Image.Image, spec: AssetSpec) -> None:
        """
        Validate that normalized asset meets requirements.
        
        Args:
            image: Normalized image
            spec: Asset specification
            
        Raises:
            NormalizationError: If validation fails
        """
        # Check basic requirements
        if image.mode != 'RGBA':
            raise NormalizationError(f"Asset {spec.name} is not in RGBA mode")
        
        # Validate dimensions based on asset type
        if spec.asset_type == 'tile':
            expected_size = self.config.tile_size
            if image.size != expected_size:
                raise NormalizationError(
                    f"Tile {spec.name} size {image.size} != expected {expected_size}"
                )
            
            # Validate isometric ratio
            if not IsometricUtils.validate_isometric_ratio(image.size):
                raise NormalizationError(f"Tile {spec.name} does not have valid isometric ratio")
        
        elif spec.asset_type == 'unit':
            expected_size = self.config.unit_frame_size
            if image.size != expected_size:
                raise NormalizationError(
                    f"Unit {spec.name} size {image.size} != expected {expected_size}"
                )
            
            # Validate square frame
            if not IsometricUtils.validate_unit_frame_size(image.size):
                raise NormalizationError(f"Unit {spec.name} does not have valid square frame size")
        
        elif spec.asset_type == 'building':
            # Validate building alignment
            if not IsometricUtils.validate_building_alignment(image, self.config.tile_size):
                raise NormalizationError(f"Building {spec.name} is not properly aligned to grid")
        
        # Validate transparency quality
        if not ImageUtils.validate_transparency_quality(image):
            raise NormalizationError(f"Asset {spec.name} has poor transparency quality")
    
    def _generate_output_path(self, spec: AssetSpec) -> str:
        """Generate output path for processed asset."""
        return f"sprites/{spec.name}.png"


class NormalizationError(Exception):
    """Exception raised when asset normalization fails."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message