"""
Preview processing module for the asset pipeline.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from PIL import Image
from dataclasses import dataclass

from ..utils.preview import PreviewGenerator, AssetPreviewManager, PreviewConfig, AssetPreviewItem
from ..utils.image import ImageUtils


logger = logging.getLogger(__name__)


@dataclass
class PreviewProcessorConfig:
    """Configuration for preview processing."""
    output_dir: str = "assets/preview"
    create_grid_preview: bool = True
    create_alignment_preview: bool = True
    create_animation_previews: bool = True
    create_type_specific_previews: bool = True
    preview_config: PreviewConfig = None
    
    def __post_init__(self):
        if self.preview_config is None:
            self.preview_config = PreviewConfig()


class PreviewProcessor:
    """Processor for generating asset previews."""
    
    def __init__(self, config: PreviewProcessorConfig = None):
        """
        Initialize preview processor.
        
        Args:
            config: Preview processor configuration
        """
        self.config = config or PreviewProcessorConfig()
        self.preview_manager = AssetPreviewManager(self.config.preview_config)
    
    def process_assets_preview(self, assets_dir: str, 
                             processed_assets: Optional[Dict] = None) -> bool:
        """
        Process and generate previews for all assets.
        
        Args:
            assets_dir: Directory containing assets
            processed_assets: Optional dictionary of processed assets
            
        Returns:
            True if preview processing was successful
        """
        try:
            logger.info("Starting asset preview generation")
            
            # Load assets for preview
            if processed_assets:
                assets_by_type = self._convert_processed_assets(processed_assets)
            else:
                assets_by_type = self.preview_manager.load_assets_from_directory(assets_dir)
            
            if not any(assets_by_type.values()):
                logger.warning("No assets found for preview generation")
                return True  # Not an error, just no assets to preview
            
            # Create comprehensive preview
            success = self.preview_manager.create_comprehensive_preview(
                assets_by_type, self.config.output_dir
            )
            
            if success:
                logger.info(f"Successfully generated asset previews in {self.config.output_dir}")
            else:
                logger.error("Failed to generate some asset previews")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process asset previews: {e}")
            return False
    
    def process_animation_previews(self, animations: Dict[str, List[Image.Image]]) -> bool:
        """
        Process and generate animation contact sheet previews.
        
        Args:
            animations: Dictionary of animation name to frames
            
        Returns:
            True if animation preview processing was successful
        """
        try:
            if not animations:
                logger.info("No animations found for preview generation")
                return True
            
            logger.info(f"Generating animation previews for {len(animations)} animations")
            
            success = self.preview_manager.create_animation_previews(
                animations, self.config.output_dir
            )
            
            if success:
                logger.info("Successfully generated animation previews")
            else:
                logger.error("Failed to generate some animation previews")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process animation previews: {e}")
            return False
    
    def create_atlas_preview(self, atlas_path: str, frame_map: Dict, 
                           animation_name: str) -> bool:
        """
        Create preview for texture atlas.
        
        Args:
            atlas_path: Path to atlas image
            frame_map: Frame mapping data
            animation_name: Name of the animation
            
        Returns:
            True if atlas preview was created successfully
        """
        try:
            if not os.path.exists(atlas_path):
                logger.error(f"Atlas file not found: {atlas_path}")
                return False
            
            # Load atlas image
            atlas_image = Image.open(atlas_path)
            
            # Extract individual frames from atlas
            frames = self._extract_frames_from_atlas(atlas_image, frame_map)
            
            # Create contact sheet preview
            output_path = os.path.join(self.config.output_dir, f"{animation_name}_atlas_preview.png")
            
            success = self.preview_manager.generator.create_animation_contact_sheet(
                frames, f"{animation_name}_atlas", output_path
            )
            
            if success:
                logger.info(f"Created atlas preview: {output_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create atlas preview for {animation_name}: {e}")
            return False
    
    def create_validation_preview(self, validation_results: Dict, 
                                assets_dir: str) -> bool:
        """
        Create preview highlighting validation issues.
        
        Args:
            validation_results: Validation results from validator
            assets_dir: Directory containing assets
            
        Returns:
            True if validation preview was created successfully
        """
        try:
            # Load assets
            assets_by_type = self.preview_manager.load_assets_from_directory(assets_dir)
            
            # Filter to only assets with validation issues
            problem_assets = []
            for asset_type, assets in assets_by_type.items():
                for asset in assets:
                    if asset.name in validation_results.get('errors', {}):
                        # Mark asset as having issues
                        asset.metadata = {'validation_issues': validation_results['errors'][asset.name]}
                        problem_assets.append(asset)
            
            if not problem_assets:
                logger.info("No validation issues found, skipping validation preview")
                return True
            
            # Create preview of problematic assets
            output_path = os.path.join(self.config.output_dir, "validation_issues_preview.png")
            success = self.preview_manager.generator.create_asset_grid_preview(
                problem_assets, output_path
            )
            
            if success:
                logger.info(f"Created validation issues preview: {output_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create validation preview: {e}")
            return False
    
    def _convert_processed_assets(self, processed_assets: Dict) -> Dict[str, List[AssetPreviewItem]]:
        """
        Convert processed assets dictionary to preview items.
        
        Args:
            processed_assets: Dictionary of processed assets
            
        Returns:
            Assets organized by type for preview
        """
        assets_by_type = {
            'tile': [],
            'building': [],
            'unit': []
        }
        
        try:
            for asset_name, asset_data in processed_assets.items():
                if 'image' not in asset_data or 'type' not in asset_data:
                    continue
                
                preview_item = AssetPreviewItem(
                    name=asset_name,
                    image=asset_data['image'],
                    asset_type=asset_data['type'],
                    metadata=asset_data.get('metadata', {})
                )
                
                asset_type = asset_data['type']
                if asset_type in assets_by_type:
                    assets_by_type[asset_type].append(preview_item)
            
            return assets_by_type
            
        except Exception as e:
            logger.error(f"Failed to convert processed assets: {e}")
            return assets_by_type
    
    def _extract_frames_from_atlas(self, atlas_image: Image.Image, 
                                 frame_map: Dict) -> List[Image.Image]:
        """
        Extract individual frames from texture atlas.
        
        Args:
            atlas_image: Atlas image
            frame_map: Frame mapping data
            
        Returns:
            List of extracted frames
        """
        frames = []
        
        try:
            # Sort frames by name to maintain order
            sorted_frames = sorted(frame_map.get('frames', {}).items())
            
            for frame_name, frame_data in sorted_frames:
                x = frame_data.get('x', 0)
                y = frame_data.get('y', 0)
                w = frame_data.get('w', 64)
                h = frame_data.get('h', 64)
                
                # Extract frame from atlas
                frame = atlas_image.crop((x, y, x + w, y + h))
                frames.append(frame)
            
            return frames
            
        except Exception as e:
            logger.error(f"Failed to extract frames from atlas: {e}")
            return []
    
    def cleanup_old_previews(self) -> bool:
        """
        Clean up old preview files.
        
        Returns:
            True if cleanup was successful
        """
        try:
            if not os.path.exists(self.config.output_dir):
                return True
            
            # Remove all PNG files in preview directory
            for filename in os.listdir(self.config.output_dir):
                if filename.lower().endswith('.png'):
                    filepath = os.path.join(self.config.output_dir, filename)
                    try:
                        os.remove(filepath)
                        logger.debug(f"Removed old preview: {filepath}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old preview {filepath}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old previews: {e}")
            return False


def create_preview_processor(config: Optional[PreviewProcessorConfig] = None) -> PreviewProcessor:
    """
    Create a preview processor with the given configuration.
    
    Args:
        config: Preview processor configuration
        
    Returns:
        Configured preview processor
    """
    return PreviewProcessor(config)


def generate_asset_previews(assets_dir: str, output_dir: str = "assets/preview", 
                          processed_assets: Optional[Dict] = None) -> bool:
    """
    Convenience function to generate asset previews.
    
    Args:
        assets_dir: Directory containing assets
        output_dir: Output directory for previews
        processed_assets: Optional dictionary of processed assets
        
    Returns:
        True if preview generation was successful
    """
    config = PreviewProcessorConfig(output_dir=output_dir)
    processor = PreviewProcessor(config)
    
    return processor.process_assets_preview(assets_dir, processed_assets)


def generate_animation_previews(animations: Dict[str, List[Image.Image]], 
                              output_dir: str = "assets/preview") -> bool:
    """
    Convenience function to generate animation previews.
    
    Args:
        animations: Dictionary of animation name to frames
        output_dir: Output directory for previews
        
    Returns:
        True if animation preview generation was successful
    """
    config = PreviewProcessorConfig(output_dir=output_dir)
    processor = PreviewProcessor(config)
    
    return processor.process_animation_previews(animations)