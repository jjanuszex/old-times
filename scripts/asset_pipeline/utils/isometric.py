"""
Isometric projection utilities and validation helpers.
"""

import math
from typing import Tuple, List
from PIL import Image, ImageDraw
import numpy as np


class IsometricUtils:
    """Utility class for isometric projection operations."""
    
    # Standard isometric tile dimensions (2:1 ratio)
    TILE_WIDTH = 64
    TILE_HEIGHT = 32
    TILE_RATIO = TILE_WIDTH / TILE_HEIGHT  # 2.0
    
    @staticmethod
    def validate_isometric_ratio(size: Tuple[int, int], tolerance: float = 0.1) -> bool:
        """
        Validate that dimensions follow isometric 2:1 ratio.
        
        Args:
            size: (width, height) dimensions
            tolerance: Acceptable deviation from 2:1 ratio
            
        Returns:
            True if dimensions are valid isometric
        """
        width, height = size
        if height == 0:
            return False
        
        ratio = width / height
        return abs(ratio - IsometricUtils.TILE_RATIO) <= tolerance
    
    @staticmethod
    def calculate_isometric_size(tile_count: Tuple[int, int]) -> Tuple[int, int]:
        """
        Calculate pixel size for given tile count.
        
        Args:
            tile_count: (width_tiles, height_tiles)
            
        Returns:
            Pixel dimensions (width, height)
        """
        width_tiles, height_tiles = tile_count
        pixel_width = width_tiles * IsometricUtils.TILE_WIDTH
        pixel_height = height_tiles * IsometricUtils.TILE_HEIGHT
        return (pixel_width, pixel_height)
    
    @staticmethod
    def calculate_tile_count(pixel_size: Tuple[int, int]) -> Tuple[int, int]:
        """
        Calculate tile count from pixel dimensions.
        
        Args:
            pixel_size: (width, height) in pixels
            
        Returns:
            Tile count (width_tiles, height_tiles)
        """
        width, height = pixel_size
        width_tiles = width // IsometricUtils.TILE_WIDTH
        height_tiles = height // IsometricUtils.TILE_HEIGHT
        return (width_tiles, height_tiles)
    
    @staticmethod
    def create_isometric_grid_overlay(size: Tuple[int, int], 
                                    tile_size: Tuple[int, int] = None) -> Image.Image:
        """
        Create an isometric grid overlay for alignment verification.
        
        Args:
            size: Image size (width, height)
            tile_size: Tile dimensions (default: 64x32)
            
        Returns:
            Grid overlay image
        """
        if tile_size is None:
            tile_size = (IsometricUtils.TILE_WIDTH, IsometricUtils.TILE_HEIGHT)
        
        tile_width, tile_height = tile_size
        width, height = size
        
        # Create transparent image
        grid = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(grid)
        
        # Draw vertical grid lines
        for x in range(0, width + 1, tile_width):
            draw.line([(x, 0), (x, height)], fill=(255, 0, 0, 128), width=1)
        
        # Draw horizontal grid lines
        for y in range(0, height + 1, tile_height):
            draw.line([(0, y), (width, y)], fill=(255, 0, 0, 128), width=1)
        
        # Draw isometric diamond pattern
        for x in range(0, width, tile_width):
            for y in range(0, height, tile_height):
                # Draw diamond shape for each tile
                diamond_points = [
                    (x + tile_width // 2, y),  # Top
                    (x + tile_width, y + tile_height // 2),  # Right
                    (x + tile_width // 2, y + tile_height),  # Bottom
                    (x, y + tile_height // 2)  # Left
                ]
                draw.polygon(diamond_points, outline=(0, 255, 0, 128), width=1)
        
        return grid
    
    @staticmethod
    def validate_building_alignment(image: Image.Image, 
                                  tile_size: Tuple[int, int] = None) -> bool:
        """
        Validate that building is properly aligned to isometric grid.
        
        Args:
            image: Building image to validate
            tile_size: Tile dimensions (default: 64x32)
            
        Returns:
            True if building is properly aligned
        """
        if tile_size is None:
            tile_size = (IsometricUtils.TILE_WIDTH, IsometricUtils.TILE_HEIGHT)
        
        tile_width, tile_height = tile_size
        width, height = image.size
        
        # Check if width is multiple of tile width
        if width % tile_width != 0:
            return False
        
        # Buildings can have extra height for depth, so we're more lenient
        # Just check that height is at least one tile height
        return height >= tile_height
    
    @staticmethod
    def convert_to_isometric(image: Image.Image, 
                           target_size: Tuple[int, int] = None) -> Image.Image:
        """
        Convert image to isometric projection (simplified transformation).
        
        Args:
            image: Source image
            target_size: Target isometric size
            
        Returns:
            Isometric projected image
        """
        if target_size is None:
            target_size = (IsometricUtils.TILE_WIDTH, IsometricUtils.TILE_HEIGHT)
        
        # This is a simplified implementation
        # A full implementation would apply proper isometric transformation matrix
        
        # For now, just resize to target dimensions
        return image.resize(target_size, Image.Resampling.LANCZOS)
    
    @staticmethod
    def get_isometric_transform_matrix() -> np.ndarray:
        """
        Get transformation matrix for isometric projection.
        
        Returns:
            3x3 transformation matrix
        """
        # Standard isometric transformation
        # This transforms from orthogonal to isometric view
        angle = math.radians(30)  # 30 degree rotation
        
        # Isometric transformation matrix
        matrix = np.array([
            [math.cos(angle), -math.sin(angle), 0],
            [math.sin(angle) * 0.5, math.cos(angle) * 0.5, 0],
            [0, 0, 1]
        ])
        
        return matrix
    
    @staticmethod
    def calculate_building_footprint(image_size: Tuple[int, int], 
                                   tile_size: Tuple[int, int] = None) -> Tuple[int, int]:
        """
        Calculate building footprint in tiles.
        
        Args:
            image_size: Building image size (width, height)
            tile_size: Tile dimensions (default: 64x32)
            
        Returns:
            Footprint in tiles (width_tiles, height_tiles)
        """
        if tile_size is None:
            tile_size = (IsometricUtils.TILE_WIDTH, IsometricUtils.TILE_HEIGHT)
        
        tile_width, tile_height = tile_size
        width, height = image_size
        
        # Calculate footprint
        width_tiles = max(1, width // tile_width)
        
        # For buildings, height can be more than footprint due to vertical structure
        # Use a heuristic: footprint height is roughly 1/3 of image height
        height_tiles = max(1, (height // 3) // tile_height)
        
        return (width_tiles, height_tiles)
    
    @staticmethod
    def validate_unit_frame_size(size: Tuple[int, int]) -> bool:
        """
        Validate unit frame size (should be square for proper rotation).
        
        Args:
            size: Frame size (width, height)
            
        Returns:
            True if valid unit frame size
        """
        width, height = size
        
        # Unit frames should be square
        if width != height:
            return False
        
        # Should be reasonable size (typically 64x64)
        return 32 <= width <= 128
    
    @staticmethod
    def create_direction_frames(base_frame: Image.Image, directions: int = 8) -> List[Image.Image]:
        """
        Create directional frames by rotating base frame.
        
        Args:
            base_frame: Base frame image
            directions: Number of directions (typically 8)
            
        Returns:
            List of rotated frames
        """
        frames = []
        angle_step = 360 / directions
        
        for i in range(directions):
            angle = i * angle_step
            rotated = base_frame.rotate(-angle, expand=False, fillcolor=(0, 0, 0, 0))
            frames.append(rotated)
        
        return frames