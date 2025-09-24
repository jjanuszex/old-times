"""
Image processing utilities for the asset pipeline.
"""

from typing import Tuple, Optional, Union
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np
import io


class ImageUtils:
    """Utility class for common image processing operations."""
    
    @staticmethod
    def load_image(data: Union[bytes, str, Image.Image]) -> Image.Image:
        """
        Load image from various sources.
        
        Args:
            data: Image data as bytes, file path, or PIL Image
            
        Returns:
            PIL Image object
            
        Raises:
            ValueError: If data cannot be loaded as image
        """
        if isinstance(data, Image.Image):
            return data
        elif isinstance(data, bytes):
            try:
                return Image.open(io.BytesIO(data))
            except Exception as e:
                raise ValueError(f"Cannot load image from bytes: {e}")
        elif isinstance(data, str):
            try:
                return Image.open(data)
            except Exception as e:
                raise ValueError(f"Cannot load image from path '{data}': {e}")
        else:
            raise ValueError(f"Unsupported image data type: {type(data)}")
    
    @staticmethod
    def save_image(image: Image.Image, path: str, format: str = 'PNG', **kwargs) -> None:
        """
        Save image to file with quality preservation.
        
        Args:
            image: Image to save
            path: Output file path
            format: Image format (PNG, JPEG, etc.)
            **kwargs: Additional save parameters
        """
        # Set default parameters for quality preservation
        save_kwargs = {
            'optimize': True,
        }
        
        if format.upper() == 'PNG':
            save_kwargs.update({
                'compress_level': kwargs.get('compress_level', 6),
                'pnginfo': kwargs.get('pnginfo', None)
            })
        elif format.upper() in ['JPEG', 'JPG']:
            save_kwargs.update({
                'quality': kwargs.get('quality', 95),
                'progressive': kwargs.get('progressive', True)
            })
        
        # Update with any additional kwargs
        save_kwargs.update(kwargs)
        
        image.save(path, format=format, **save_kwargs)
    
    @staticmethod
    def ensure_rgba(image: Image.Image) -> Image.Image:
        """Convert image to RGBA mode if not already."""
        if image.mode != 'RGBA':
            return image.convert('RGBA')
        return image
    
    @staticmethod
    def resize_with_quality(image: Image.Image, target_size: Tuple[int, int], 
                           method: str = 'lanczos') -> Image.Image:
        """
        Resize image with quality preservation.
        
        Args:
            image: Source image
            target_size: Target (width, height)
            method: Resampling method ('lanczos', 'bicubic', 'bilinear')
            
        Returns:
            High-quality resized image
        """
        # Choose resampling method (compatible with older PIL versions)
        if method == 'lanczos':
            resample = getattr(Image, 'LANCZOS', 1)
        elif method == 'bicubic':
            resample = getattr(Image, 'BICUBIC', 3)
        elif method == 'bilinear':
            resample = getattr(Image, 'BILINEAR', 2)
        else:
            resample = getattr(Image, 'LANCZOS', 1)
        
        return image.resize(target_size, resample)
    
    @staticmethod
    def resize_with_aspect(image: Image.Image, target_size: Tuple[int, int], 
                          background_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
                          method: str = 'lanczos') -> Image.Image:
        """
        Resize image while preserving aspect ratio, centering in target size.
        
        Args:
            image: Source image
            target_size: Target (width, height)
            background_color: Background color for padding (RGBA)
            method: Resampling method
            
        Returns:
            Resized image with preserved aspect ratio
        """
        original_width, original_height = image.size
        target_width, target_height = target_size
        
        # Calculate scaling factor
        scale_x = target_width / original_width
        scale_y = target_height / original_height
        scale = min(scale_x, scale_y)
        
        # Calculate new size
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Resize image with quality preservation
        resized = ImageUtils.resize_with_quality(image, (new_width, new_height), method)
        
        # Create new image with target size and background
        result = Image.new('RGBA', target_size, background_color)
        
        # Center the resized image
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        result.paste(resized, (x_offset, y_offset), resized if resized.mode == 'RGBA' else None)
        
        return result
    
    @staticmethod
    def remove_background(image: Image.Image, tolerance: int = 10, 
                         background_color: Optional[Tuple[int, int, int]] = None) -> Image.Image:
        """
        Remove background by making similar colors transparent.
        
        Args:
            image: Source image
            tolerance: Color similarity tolerance
            background_color: Specific background color to remove (auto-detect if None)
            
        Returns:
            Image with background removed
        """
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Auto-detect background color from corners if not specified
        if background_color is None:
            width, height = image.size
            corners = [
                image.getpixel((0, 0))[:3],  # Only RGB, ignore alpha
                image.getpixel((width-1, 0))[:3],
                image.getpixel((0, height-1))[:3],
                image.getpixel((width-1, height-1))[:3]
            ]
            
            # Use most common corner color as background
            from collections import Counter
            background_color = Counter(corners).most_common(1)[0][0]
        
        # Convert to numpy for efficient processing
        img_array = np.array(image)
        
        # Calculate color distance from background
        bg_r, bg_g, bg_b = background_color[:3]
        distances = np.sqrt(
            (img_array[:, :, 0] - bg_r) ** 2 +
            (img_array[:, :, 1] - bg_g) ** 2 +
            (img_array[:, :, 2] - bg_b) ** 2
        )
        
        # Make similar colors transparent
        mask = distances <= tolerance
        img_array[mask, 3] = 0  # Set alpha to 0
        
        return Image.fromarray(img_array, 'RGBA')
    
    @staticmethod
    def enforce_transparent_background(image: Image.Image, 
                                     tolerance: int = 10) -> Image.Image:
        """
        Enforce transparent background by removing detected background colors.
        
        Args:
            image: Source image
            tolerance: Color similarity tolerance
            
        Returns:
            Image with enforced transparent background
        """
        return ImageUtils.remove_background(image, tolerance)
    
    @staticmethod
    def sharpen_edges(image: Image.Image, factor: float = 1.5, 
                     method: str = 'unsharp_mask') -> Image.Image:
        """
        Apply edge sharpening to image for pixel-perfect appearance.
        
        Args:
            image: Source image
            factor: Sharpening factor
            method: Sharpening method ('unsharp_mask', 'sharpen', 'custom')
            
        Returns:
            Sharpened image
        """
        if method == 'unsharp_mask':
            # Apply unsharp mask filter
            enhancer = ImageEnhance.Sharpness(image)
            return enhancer.enhance(factor)
        elif method == 'sharpen':
            # Apply basic sharpen filter
            return image.filter(ImageFilter.SHARPEN)
        elif method == 'custom':
            # Apply custom sharpening kernel
            kernel = ImageFilter.Kernel((3, 3), [
                -1, -1, -1,
                -1,  9, -1,
                -1, -1, -1
            ], scale=1, offset=0)
            return image.filter(kernel)
        else:
            raise ValueError(f"Unknown sharpening method: {method}")
    
    @staticmethod
    def apply_anti_aliasing(image: Image.Image, method: str = 'lanczos') -> Image.Image:
        """
        Apply anti-aliasing to smooth edges.
        
        Args:
            image: Source image
            method: Anti-aliasing method ('lanczos', 'bicubic', 'bilinear')
            
        Returns:
            Anti-aliased image
        """
        # Get current size
        size = image.size
        
        # Upscale and downscale for anti-aliasing effect
        scale_factor = 2
        upscaled_size = (size[0] * scale_factor, size[1] * scale_factor)
        
        # Choose resampling method (compatible with older PIL versions)
        if method == 'lanczos':
            resample = getattr(Image, 'LANCZOS', 1)
        elif method == 'bicubic':
            resample = getattr(Image, 'BICUBIC', 3)
        elif method == 'bilinear':
            resample = getattr(Image, 'BILINEAR', 2)
        else:
            resample = getattr(Image, 'LANCZOS', 1)
        
        # Upscale then downscale
        upscaled = image.resize(upscaled_size, resample)
        return upscaled.resize(size, resample)
    
    @staticmethod
    def detect_transparency(image: Image.Image) -> bool:
        """
        Check if image has any transparent pixels.
        
        Args:
            image: Image to check
            
        Returns:
            True if image has transparency
        """
        if image.mode != 'RGBA':
            return False
        
        # Check if alpha channel has any values < 255
        alpha_channel = image.split()[-1]
        alpha_array = np.array(alpha_channel)
        return np.any(alpha_array < 255)
    
    @staticmethod
    def get_bounding_box(image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """
        Get bounding box of non-transparent content.
        
        Args:
            image: Image to analyze
            
        Returns:
            Bounding box as (left, top, right, bottom) or None if fully transparent
        """
        if image.mode != 'RGBA':
            return None
        
        # Get alpha channel
        alpha = image.split()[-1]
        bbox = alpha.getbbox()
        
        return bbox
    
    @staticmethod
    def crop_to_content(image: Image.Image, padding: int = 0) -> Image.Image:
        """
        Crop image to non-transparent content with optional padding.
        
        Args:
            image: Source image
            padding: Padding around content
            
        Returns:
            Cropped image
        """
        bbox = ImageUtils.get_bounding_box(image)
        if bbox is None:
            return image
        
        left, top, right, bottom = bbox
        
        # Add padding
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(image.width, right + padding)
        bottom = min(image.height, bottom + padding)
        
        return image.crop((left, top, right, bottom))
    
    @staticmethod
    def create_grid_preview(images: list, grid_size: Tuple[int, int], 
                           cell_size: Tuple[int, int] = (64, 64)) -> Image.Image:
        """
        Create a grid preview of multiple images.
        
        Args:
            images: List of images to arrange
            grid_size: Grid dimensions (cols, rows)
            cell_size: Size of each cell
            
        Returns:
            Grid preview image
        """
        cols, rows = grid_size
        cell_width, cell_height = cell_size
        
        # Create preview image
        preview_width = cols * cell_width
        preview_height = rows * cell_height
        preview = Image.new('RGBA', (preview_width, preview_height), (255, 255, 255, 255))
        
        # Place images in grid
        for i, img in enumerate(images[:cols * rows]):
            row = i // cols
            col = i % cols
            
            x = col * cell_width
            y = row * cell_height
            
            # Resize image to fit cell
            if img.size != cell_size:
                img = ImageUtils.resize_with_aspect(img, cell_size)
            
            preview.paste(img, (x, y), img if img.mode == 'RGBA' else None)
        
        return preview
    
    @staticmethod
    def validate_transparency_quality(image: Image.Image, 
                                    min_alpha_threshold: int = 10) -> bool:
        """
        Validate that image has good transparency quality.
        
        Args:
            image: Image to validate
            min_alpha_threshold: Minimum alpha value to consider opaque
            
        Returns:
            True if transparency quality is good
        """
        if image.mode != 'RGBA':
            return False
        
        # Get alpha channel
        alpha_channel = image.split()[-1]
        alpha_array = np.array(alpha_channel)
        
        # Check for proper alpha distribution
        # Good transparency should have clear distinction between transparent and opaque
        transparent_pixels = np.sum(alpha_array < min_alpha_threshold)
        opaque_pixels = np.sum(alpha_array > 255 - min_alpha_threshold)
        total_pixels = alpha_array.size
        
        # At least some pixels should be fully transparent or fully opaque
        return (transparent_pixels + opaque_pixels) > (total_pixels * 0.1)
    
    @staticmethod
    def center_content(image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """
        Center image content within target size canvas.
        
        Args:
            image: Source image
            target_size: Target canvas size
            
        Returns:
            Centered image on new canvas
        """
        target_width, target_height = target_size
        
        # Create new transparent canvas
        result = Image.new('RGBA', target_size, (0, 0, 0, 0))
        
        # Calculate centering position
        img_width, img_height = image.size
        x_offset = (target_width - img_width) // 2
        y_offset = (target_height - img_height) // 2
        
        # Paste image centered
        result.paste(image, (x_offset, y_offset), image if image.mode == 'RGBA' else None)
        
        return result
    
    @staticmethod
    def ensure_minimum_size(image: Image.Image, min_size: Tuple[int, int]) -> Image.Image:
        """
        Ensure image meets minimum size requirements.
        
        Args:
            image: Source image
            min_size: Minimum (width, height)
            
        Returns:
            Image meeting minimum size requirements
        """
        current_width, current_height = image.size
        min_width, min_height = min_size
        
        if current_width >= min_width and current_height >= min_height:
            return image
        
        # Calculate new size maintaining aspect ratio
        scale_x = min_width / current_width if current_width < min_width else 1.0
        scale_y = min_height / current_height if current_height < min_height else 1.0
        scale = max(scale_x, scale_y)
        
        new_width = int(current_width * scale)
        new_height = int(current_height * scale)
        
        return ImageUtils.resize_with_quality(image, (new_width, new_height))