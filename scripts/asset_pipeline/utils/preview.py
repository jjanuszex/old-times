"""
Preview generation utilities for the asset pipeline.
"""

import os
from typing import List, Dict, Tuple, Optional, Union
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
import logging

from .image import ImageUtils
from .isometric import IsometricUtils


logger = logging.getLogger(__name__)


@dataclass
class PreviewConfig:
    """Configuration for preview generation."""
    grid_cell_size: Tuple[int, int] = (96, 96)  # Larger cells for better visibility
    grid_padding: int = 4
    grid_background_color: Tuple[int, int, int, int] = (240, 240, 240, 255)
    grid_border_color: Tuple[int, int, int, int] = (200, 200, 200, 255)
    show_isometric_grid: bool = True
    show_labels: bool = True
    max_grid_width: int = 10  # Maximum columns in grid
    contact_sheet_frame_size: Tuple[int, int] = (64, 64)
    contact_sheet_padding: int = 2


@dataclass
class AssetPreviewItem:
    """Item for preview generation."""
    name: str
    image: Image.Image
    asset_type: str  # 'tile', 'building', 'unit'
    metadata: Optional[Dict] = None


class PreviewGenerator:
    """Generator for asset preview images."""
    
    def __init__(self, config: PreviewConfig = None):
        """
        Initialize preview generator.
        
        Args:
            config: Preview configuration
        """
        self.config = config or PreviewConfig()
    
    def create_asset_grid_preview(self, assets: List[AssetPreviewItem], 
                                output_path: str) -> bool:
        """
        Create a grid preview showing all assets.
        
        Args:
            assets: List of assets to preview
            output_path: Output file path
            
        Returns:
            True if preview was created successfully
        """
        try:
            if not assets:
                logger.warning("No assets provided for preview generation")
                return False
            
            # Calculate grid dimensions
            total_assets = len(assets)
            grid_cols = min(self.config.max_grid_width, total_assets)
            grid_rows = (total_assets + grid_cols - 1) // grid_cols
            
            # Calculate preview dimensions
            cell_width, cell_height = self.config.grid_cell_size
            padding = self.config.grid_padding
            
            preview_width = grid_cols * (cell_width + padding) - padding
            preview_height = grid_rows * (cell_height + padding) - padding
            
            # Create preview image
            preview = Image.new('RGBA', (preview_width, preview_height), 
                              self.config.grid_background_color)
            
            # Place assets in grid
            for i, asset in enumerate(assets):
                row = i // grid_cols
                col = i % grid_cols
                
                x = col * (cell_width + padding)
                y = row * (cell_height + padding)
                
                # Create cell
                cell = self._create_asset_cell(asset, (cell_width, cell_height))
                preview.paste(cell, (x, y), cell if cell.mode == 'RGBA' else None)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save preview
            ImageUtils.save_image(preview, output_path)
            logger.info(f"Created asset grid preview: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create asset grid preview: {e}")
            return False
    
    def create_animation_contact_sheet(self, frames: List[Image.Image], 
                                     animation_name: str, 
                                     output_path: str,
                                     directions: int = 8,
                                     frames_per_direction: int = 8) -> bool:
        """
        Create a contact sheet showing all animation frames.
        
        Args:
            frames: List of animation frames
            animation_name: Name of the animation
            output_path: Output file path
            directions: Number of directions
            frames_per_direction: Number of frames per direction
            
        Returns:
            True if contact sheet was created successfully
        """
        try:
            if not frames:
                logger.warning(f"No frames provided for animation contact sheet: {animation_name}")
                return False
            
            frame_width, frame_height = self.config.contact_sheet_frame_size
            padding = self.config.contact_sheet_padding
            
            # Calculate contact sheet dimensions
            sheet_width = frames_per_direction * (frame_width + padding) - padding
            sheet_height = directions * (frame_height + padding) - padding
            
            # Add space for labels
            label_height = 20 if self.config.show_labels else 0
            total_height = sheet_height + label_height
            
            # Create contact sheet
            contact_sheet = Image.new('RGBA', (sheet_width, total_height), 
                                    self.config.grid_background_color)
            
            # Place frames in grid (directions as rows, frames as columns)
            for direction in range(directions):
                for frame_idx in range(frames_per_direction):
                    frame_index = direction * frames_per_direction + frame_idx
                    
                    if frame_index >= len(frames):
                        # Create placeholder frame if missing
                        frame = Image.new('RGBA', (frame_width, frame_height), (255, 0, 0, 128))
                    else:
                        frame = frames[frame_index]
                        # Resize frame to contact sheet size
                        if frame.size != (frame_width, frame_height):
                            frame = ImageUtils.resize_with_aspect(frame, (frame_width, frame_height))
                    
                    x = frame_idx * (frame_width + padding)
                    y = direction * (frame_height + padding)
                    
                    # Add border around frame
                    cell = Image.new('RGBA', (frame_width, frame_height), 
                                   self.config.grid_border_color)
                    cell.paste(frame, (0, 0), frame if frame.mode == 'RGBA' else None)
                    
                    contact_sheet.paste(cell, (x, y), cell if cell.mode == 'RGBA' else None)
            
            # Add labels if enabled
            if self.config.show_labels:
                self._add_animation_labels(contact_sheet, directions, frames_per_direction, 
                                         frame_width, frame_height, padding)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save contact sheet
            ImageUtils.save_image(contact_sheet, output_path)
            logger.info(f"Created animation contact sheet: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create animation contact sheet for {animation_name}: {e}")
            return False
    
    def create_isometric_alignment_preview(self, assets: List[AssetPreviewItem], 
                                         output_path: str) -> bool:
        """
        Create a preview with isometric grid overlay for alignment verification.
        
        Args:
            assets: List of assets to preview
            output_path: Output file path
            
        Returns:
            True if preview was created successfully
        """
        try:
            # Create base grid preview
            base_preview_path = output_path.replace('.png', '_base.png')
            if not self.create_asset_grid_preview(assets, base_preview_path):
                return False
            
            # Load base preview
            base_preview = Image.open(base_preview_path)
            
            # Create isometric grid overlay
            grid_overlay = IsometricUtils.create_isometric_grid_overlay(
                base_preview.size, 
                (IsometricUtils.TILE_WIDTH, IsometricUtils.TILE_HEIGHT)
            )
            
            # Composite base preview with grid overlay
            result = Image.alpha_composite(base_preview, grid_overlay)
            
            # Save result
            ImageUtils.save_image(result, output_path)
            
            # Clean up temporary base preview
            os.remove(base_preview_path)
            
            logger.info(f"Created isometric alignment preview: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create isometric alignment preview: {e}")
            return False
    
    def _create_asset_cell(self, asset: AssetPreviewItem, 
                          cell_size: Tuple[int, int]) -> Image.Image:
        """
        Create a preview cell for a single asset.
        
        Args:
            asset: Asset to create cell for
            cell_size: Size of the cell
            
        Returns:
            Cell image
        """
        cell_width, cell_height = cell_size
        
        # Create cell background
        cell = Image.new('RGBA', cell_size, (255, 255, 255, 255))
        
        # Add border
        draw = ImageDraw.Draw(cell)
        draw.rectangle([0, 0, cell_width-1, cell_height-1], 
                      outline=self.config.grid_border_color, width=1)
        
        # Resize and center asset image
        asset_image = asset.image
        if asset_image.size != cell_size:
            # Leave some padding around the asset
            padding = 8
            target_size = (cell_width - padding * 2, cell_height - padding * 2)
            asset_image = ImageUtils.resize_with_aspect(asset_image, target_size)
        
        # Center asset in cell
        asset_x = (cell_width - asset_image.width) // 2
        asset_y = (cell_height - asset_image.height) // 2
        
        cell.paste(asset_image, (asset_x, asset_y), 
                  asset_image if asset_image.mode == 'RGBA' else None)
        
        # Add label if enabled
        if self.config.show_labels:
            self._add_asset_label(cell, asset.name, asset.asset_type)
        
        # Add isometric grid overlay for individual assets if enabled
        if self.config.show_isometric_grid and asset.asset_type in ['tile', 'building']:
            grid_overlay = IsometricUtils.create_isometric_grid_overlay(
                cell_size, 
                (IsometricUtils.TILE_WIDTH // 2, IsometricUtils.TILE_HEIGHT // 2)
            )
            # Make grid more subtle for individual cells
            grid_overlay = self._adjust_overlay_opacity(grid_overlay, 0.3)
            cell = Image.alpha_composite(cell, grid_overlay)
        
        return cell
    
    def _add_asset_label(self, cell: Image.Image, name: str, asset_type: str):
        """
        Add label to asset cell.
        
        Args:
            cell: Cell image to add label to
            name: Asset name
            asset_type: Asset type
        """
        draw = ImageDraw.Draw(cell)
        
        # Try to use a small font, fall back to default if not available
        font = None
        font_size = 10
        
        # Try different font paths
        font_paths = [
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/Windows/Fonts/arial.ttf"
        ]
        
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except (OSError, IOError):
                continue
        
        # Fall back to default font if no TrueType font found
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                # If even default font fails, skip labeling
                return
        
        # Create label text
        label_text = f"{name} ({asset_type})"
        
        # Calculate text position (bottom of cell)
        try:
            text_bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except Exception:
            # Fallback for older PIL versions
            text_width, text_height = draw.textsize(label_text, font=font)
        
        text_x = (cell.width - text_width) // 2
        text_y = cell.height - text_height - 2
        
        # Draw text background
        draw.rectangle([text_x - 2, text_y - 1, text_x + text_width + 2, text_y + text_height + 1],
                      fill=(255, 255, 255, 200))
        
        # Draw text
        draw.text((text_x, text_y), label_text, fill=(0, 0, 0, 255), font=font)
    
    def _add_animation_labels(self, contact_sheet: Image.Image, 
                            directions: int, frames_per_direction: int,
                            frame_width: int, frame_height: int, padding: int):
        """
        Add direction and frame labels to animation contact sheet.
        
        Args:
            contact_sheet: Contact sheet image
            directions: Number of directions
            frames_per_direction: Number of frames per direction
            frame_width: Width of each frame
            frame_height: Height of each frame
            padding: Padding between frames
        """
        draw = ImageDraw.Draw(contact_sheet)
        
        # Try to use a small font, fall back to default if not available
        font = None
        font_size = 10
        
        # Try different font paths
        font_paths = [
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/Windows/Fonts/arial.ttf"
        ]
        
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except (OSError, IOError):
                continue
        
        # Fall back to default font if no TrueType font found
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                # If even default font fails, skip labeling
                return
        
        # Direction labels (8-direction compass)
        direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        
        for direction in range(min(directions, len(direction_names))):
            y = direction * (frame_height + padding)
            label = direction_names[direction]
            
            # Draw direction label on the left
            draw.text((2, y + frame_height // 2), label, fill=(0, 0, 0, 255), font=font)
        
        # Frame number labels at the top
        for frame_idx in range(frames_per_direction):
            x = frame_idx * (frame_width + padding)
            label = str(frame_idx)
            
            # Draw frame number at the top
            draw.text((x + frame_width // 2, 2), label, fill=(0, 0, 0, 255), font=font)
    
    def _adjust_overlay_opacity(self, overlay: Image.Image, opacity: float) -> Image.Image:
        """
        Adjust opacity of overlay image.
        
        Args:
            overlay: Overlay image
            opacity: Opacity factor (0.0 to 1.0)
            
        Returns:
            Overlay with adjusted opacity
        """
        if overlay.mode != 'RGBA':
            overlay = overlay.convert('RGBA')
        
        # Adjust alpha channel
        alpha = overlay.split()[-1]
        alpha = alpha.point(lambda p: int(p * opacity))
        
        # Reconstruct image with new alpha
        r, g, b, _ = overlay.split()
        return Image.merge('RGBA', (r, g, b, alpha))


class AssetPreviewManager:
    """Manager for creating various types of asset previews."""
    
    def __init__(self, config: PreviewConfig = None):
        """
        Initialize preview manager.
        
        Args:
            config: Preview configuration
        """
        self.config = config or PreviewConfig()
        self.generator = PreviewGenerator(self.config)
    
    def create_comprehensive_preview(self, assets_by_type: Dict[str, List[AssetPreviewItem]], 
                                   output_dir: str) -> bool:
        """
        Create comprehensive preview including all asset types.
        
        Args:
            assets_by_type: Assets organized by type
            output_dir: Output directory for previews
            
        Returns:
            True if all previews were created successfully
        """
        success = True
        
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Create preview for each asset type
            for asset_type, assets in assets_by_type.items():
                if not assets:
                    continue
                
                # Create type-specific preview
                type_preview_path = os.path.join(output_dir, f"{asset_type}_preview.png")
                if not self.generator.create_asset_grid_preview(assets, type_preview_path):
                    success = False
                
                # Create isometric alignment preview for tiles and buildings
                if asset_type in ['tile', 'building']:
                    alignment_preview_path = os.path.join(output_dir, f"{asset_type}_alignment.png")
                    if not self.generator.create_isometric_alignment_preview(assets, alignment_preview_path):
                        success = False
            
            # Create combined preview with all assets
            all_assets = []
            for assets in assets_by_type.values():
                all_assets.extend(assets)
            
            if all_assets:
                combined_preview_path = os.path.join(output_dir, "asset_preview.png")
                if not self.generator.create_asset_grid_preview(all_assets, combined_preview_path):
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create comprehensive preview: {e}")
            return False
    
    def create_animation_previews(self, animations: Dict[str, List[Image.Image]], 
                                output_dir: str) -> bool:
        """
        Create contact sheet previews for all animations.
        
        Args:
            animations: Dictionary of animation name to frames
            output_dir: Output directory for previews
            
        Returns:
            True if all animation previews were created successfully
        """
        success = True
        
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            for animation_name, frames in animations.items():
                contact_sheet_path = os.path.join(output_dir, f"{animation_name}_contact_sheet.png")
                if not self.generator.create_animation_contact_sheet(frames, animation_name, contact_sheet_path):
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create animation previews: {e}")
            return False
    
    def load_assets_from_directory(self, assets_dir: str) -> Dict[str, List[AssetPreviewItem]]:
        """
        Load assets from directory for preview generation.
        
        Args:
            assets_dir: Directory containing assets
            
        Returns:
            Assets organized by type
        """
        assets_by_type = {
            'tile': [],
            'building': [],
            'unit': []
        }
        
        try:
            sprites_dir = os.path.join(assets_dir, 'sprites')
            if not os.path.exists(sprites_dir):
                logger.warning(f"Sprites directory not found: {sprites_dir}")
                return assets_by_type
            
            # Load sprite files
            for filename in os.listdir(sprites_dir):
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                
                filepath = os.path.join(sprites_dir, filename)
                try:
                    image = Image.open(filepath)
                    name = os.path.splitext(filename)[0]
                    
                    # Determine asset type based on filename or size
                    asset_type = self._determine_asset_type(name, image.size)
                    
                    preview_item = AssetPreviewItem(
                        name=name,
                        image=image,
                        asset_type=asset_type
                    )
                    
                    assets_by_type[asset_type].append(preview_item)
                    
                except Exception as e:
                    logger.warning(f"Failed to load asset {filepath}: {e}")
            
            return assets_by_type
            
        except Exception as e:
            logger.error(f"Failed to load assets from directory {assets_dir}: {e}")
            return assets_by_type
    
    def _determine_asset_type(self, name: str, size: Tuple[int, int]) -> str:
        """
        Determine asset type based on name and size.
        
        Args:
            name: Asset name
            size: Image size
            
        Returns:
            Asset type ('tile', 'building', 'unit')
        """
        width, height = size
        
        # Check for unit indicators
        if 'worker' in name.lower() or 'unit' in name.lower():
            return 'unit'
        
        # Check for tile size (64x32)
        if width == 64 and height == 32:
            return 'tile'
        
        # Check for building indicators
        if any(keyword in name.lower() for keyword in ['mill', 'bakery', 'lumberjack', 'quarry', 'sawmill']):
            return 'building'
        
        # Default based on size
        if width == height:  # Square images are likely units
            return 'unit'
        elif IsometricUtils.validate_isometric_ratio(size):
            return 'tile'
        else:
            return 'building'