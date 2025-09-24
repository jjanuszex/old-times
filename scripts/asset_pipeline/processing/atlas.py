"""
Texture atlas generation for animated units and sprite collections.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
import json
import math

from ..providers.base import AssetSpec


@dataclass
class AtlasConfig:
    """Configuration for atlas generation."""
    padding: int = 0
    power_of_two: bool = True
    max_size: tuple[int, int] = (2048, 2048)
    format: str = "RGBA"


@dataclass
class AtlasResult:
    """Result of atlas generation."""
    atlas: Image.Image
    frame_map: Dict[str, Dict[str, int]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save_atlas(self, path: str) -> None:
        """Save atlas image to file."""
        self.atlas.save(path)
    
    def save_frame_map(self, path: str, format: str = "json") -> None:
        """Save frame map to JSON or TOML file."""
        atlas_data = {
            "frames": self.frame_map,
            "meta": {
                "size": {"w": self.atlas.width, "h": self.atlas.height},
                "format": self.atlas.mode,
                "scale": 1,
                **self.metadata
            }
        }
        
        if format.lower() == "toml":
            try:
                import tomli_w
                with open(path, 'wb') as f:
                    tomli_w.dump(atlas_data, f)
            except ImportError:
                # Fallback to simple TOML-like format
                self._save_simple_toml(atlas_data, path)
        else:
            with open(path, 'w') as f:
                json.dump(atlas_data, f, indent=2)
    
    def _save_simple_toml(self, data: dict, path: str) -> None:
        """Save data in simple TOML-like format without external dependencies."""
        with open(path, 'w') as f:
            # Write meta section
            f.write("[meta]\n")
            meta = data["meta"]
            f.write(f'size = {{ w = {meta["size"]["w"]}, h = {meta["size"]["h"]} }}\n')
            f.write(f'format = "{meta["format"]}"\n')
            f.write(f'scale = {meta["scale"]}\n')
            
            for key, value in meta.items():
                if key not in ["size", "format", "scale"]:
                    if isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    else:
                        f.write(f'{key} = {value}\n')
            
            f.write("\n")
            
            # Write frames section
            for frame_name, frame_data in data["frames"].items():
                f.write(f'[frames."{frame_name}"]\n')
                f.write(f'x = {frame_data["x"]}\n')
                f.write(f'y = {frame_data["y"]}\n')
                f.write(f'w = {frame_data["w"]}\n')
                f.write(f'h = {frame_data["h"]}\n')
                f.write("\n")


@dataclass
class Rectangle:
    """Rectangle for atlas layout calculations."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def right(self) -> int:
        return self.x + self.width
    
    @property
    def bottom(self) -> int:
        return self.y + self.height
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside rectangle."""
        return self.x <= x < self.right and self.y <= y < self.bottom
    
    def intersects(self, other: 'Rectangle') -> bool:
        """Check if this rectangle intersects with another."""
        return not (self.right <= other.x or other.right <= self.x or 
                   self.bottom <= other.y or other.bottom <= self.y)


@dataclass
class LayoutNode:
    """Node in the atlas layout tree for bin packing."""
    rect: Rectangle
    used: bool = False
    right: Optional['LayoutNode'] = None
    down: Optional['LayoutNode'] = None
    
    def find_node(self, width: int, height: int) -> Optional['LayoutNode']:
        """Find a node that can fit the given dimensions."""
        if self.used:
            # Try right and down nodes
            node = self.right.find_node(width, height) if self.right else None
            if node:
                return node
            return self.down.find_node(width, height) if self.down else None
        elif width <= self.rect.width and height <= self.rect.height:
            return self
        else:
            return None
    
    def split_node(self, width: int, height: int) -> 'LayoutNode':
        """Split this node to accommodate the given dimensions."""
        self.used = True
        
        # Create right and down nodes for remaining space
        if self.rect.width > width:
            self.right = LayoutNode(Rectangle(
                self.rect.x + width, self.rect.y,
                self.rect.width - width, self.rect.height
            ))
        
        if self.rect.height > height:
            self.down = LayoutNode(Rectangle(
                self.rect.x, self.rect.y + height,
                width, self.rect.height - height
            ))
        
        return self


@dataclass
class AtlasLayout:
    """Layout information for atlas generation."""
    width: int
    height: int
    positions: Dict[str, Rectangle]
    efficiency: float = 0.0
    
    def add_item(self, name: str, rect: Rectangle) -> None:
        """Add an item to the layout."""
        self.positions[name] = rect
    
    def calculate_efficiency(self, total_item_area: int) -> None:
        """Calculate layout efficiency (used area / total area)."""
        total_area = self.width * self.height
        self.efficiency = total_item_area / total_area if total_area > 0 else 0.0


@dataclass
class UnitSpec:
    """Specification for unit animation atlas."""
    name: str
    directions: int = 8
    frames_per_direction: int = 8
    frame_size: tuple[int, int] = (64, 64)
    
    @property
    def total_frames(self) -> int:
        """Get total number of frames."""
        return self.directions * self.frames_per_direction


class AtlasLayoutEngine:
    """Engine for calculating optimal atlas layouts."""
    
    def __init__(self, config: AtlasConfig):
        """Initialize layout engine with configuration."""
        self.config = config
    
    def calculate_grid_layout(self, spec: UnitSpec) -> AtlasLayout:
        """
        Calculate grid-based layout for unit animations.
        Creates 8×8 frame layout (8 directions × 8 walking frames).
        """
        frame_width, frame_height = spec.frame_size
        
        # Calculate dimensions with padding
        atlas_width = spec.frames_per_direction * frame_width
        atlas_height = spec.directions * frame_height
        
        if self.config.padding > 0:
            atlas_width += (spec.frames_per_direction - 1) * self.config.padding
            atlas_height += (spec.directions - 1) * self.config.padding
        
        # Apply power of two constraint if needed
        if self.config.power_of_two:
            atlas_width = self._next_power_of_two(atlas_width)
            atlas_height = self._next_power_of_two(atlas_height)
        
        # Create layout
        layout = AtlasLayout(atlas_width, atlas_height, {})
        
        # Calculate frame positions
        direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        
        for direction_idx in range(spec.directions):
            for frame_idx in range(spec.frames_per_direction):
                x = frame_idx * (frame_width + self.config.padding)
                y = direction_idx * (frame_height + self.config.padding)
                
                direction_name = (direction_names[direction_idx] 
                                if direction_idx < len(direction_names) 
                                else f"dir_{direction_idx}")
                frame_name = f"walk_{direction_name}_{frame_idx}"
                
                layout.add_item(frame_name, Rectangle(x, y, frame_width, frame_height))
        
        # Calculate efficiency
        total_item_area = spec.total_frames * frame_width * frame_height
        layout.calculate_efficiency(total_item_area)
        
        return layout
    
    def calculate_packed_layout(self, items: List[Tuple[str, int, int]]) -> AtlasLayout:
        """
        Calculate packed layout using bin packing algorithm.
        
        Args:
            items: List of (name, width, height) tuples
            
        Returns:
            AtlasLayout with optimized positioning
        """
        if not items:
            return AtlasLayout(0, 0, {})
        
        # Sort items by area (largest first) for better packing
        sorted_items = sorted(items, key=lambda x: x[1] * x[2], reverse=True)
        
        # Start with initial size estimate
        total_area = sum(width * height for _, width, height in sorted_items)
        initial_size = int(math.sqrt(total_area)) + max(item[1] for item in sorted_items)
        
        # Try different atlas sizes to find optimal layout
        best_layout = None
        best_efficiency = 0.0
        
        for size_multiplier in [1.0, 1.2, 1.5, 2.0]:
            atlas_size = int(initial_size * size_multiplier)
            
            if self.config.power_of_two:
                atlas_size = self._next_power_of_two(atlas_size)
            
            # Check size limits
            if atlas_size > max(self.config.max_size):
                continue
            
            layout = self._try_pack_layout(sorted_items, atlas_size, atlas_size)
            if layout and layout.efficiency > best_efficiency:
                best_layout = layout
                best_efficiency = layout.efficiency
        
        return best_layout or AtlasLayout(self.config.max_size[0], self.config.max_size[1], {})
    
    def _try_pack_layout(self, items: List[Tuple[str, int, int]], 
                        width: int, height: int) -> Optional[AtlasLayout]:
        """Try to pack items into given dimensions using bin packing."""
        root = LayoutNode(Rectangle(0, 0, width, height))
        layout = AtlasLayout(width, height, {})
        total_item_area = 0
        
        for name, item_width, item_height in items:
            # Add padding to item dimensions
            padded_width = item_width + self.config.padding
            padded_height = item_height + self.config.padding
            
            node = root.find_node(padded_width, padded_height)
            if not node:
                return None  # Couldn't fit all items
            
            # Split the node and place the item
            node.split_node(padded_width, padded_height)
            layout.add_item(name, Rectangle(
                node.rect.x, node.rect.y, item_width, item_height
            ))
            total_item_area += item_width * item_height
        
        layout.calculate_efficiency(total_item_area)
        return layout
    
    def optimize_atlas_size(self, layout: AtlasLayout) -> AtlasLayout:
        """
        Optimize atlas size by removing unused space.
        """
        if not layout.positions:
            return layout
        
        # Find actual bounds of all items
        max_x = max(rect.right for rect in layout.positions.values())
        max_y = max(rect.bottom for rect in layout.positions.values())
        
        # Apply power of two constraint if needed
        if self.config.power_of_two:
            max_x = self._next_power_of_two(max_x)
            max_y = self._next_power_of_two(max_y)
        
        # Don't make it smaller than current size if it would hurt efficiency
        optimized_width = min(max_x, layout.width)
        optimized_height = min(max_y, layout.height)
        
        # Recalculate efficiency with new dimensions
        total_item_area = sum(rect.width * rect.height for rect in layout.positions.values())
        new_layout = AtlasLayout(optimized_width, optimized_height, layout.positions.copy())
        new_layout.calculate_efficiency(total_item_area)
        
        return new_layout
    
    def _next_power_of_two(self, n: int) -> int:
        """Find the next power of two greater than or equal to n."""
        if n <= 0:
            return 1
        
        # Check if n is already a power of two
        if n & (n - 1) == 0:
            return n
        
        # Find the next power of two
        power = 1
        while power < n:
            power <<= 1
        
        return power


class AtlasGenerator:
    """Handles generation of texture atlases for sprites and animations."""
    
    def __init__(self, config: AtlasConfig):
        """Initialize atlas generator with configuration."""
        self.config = config
        self.layout_engine = AtlasLayoutEngine(config)
    
    def create_unit_atlas(self, frames: List[Image.Image], spec: UnitSpec) -> AtlasResult:
        """
        Create texture atlas for animated unit using grid-based layout.
        
        Args:
            frames: List of animation frames
            spec: Unit specification
            
        Returns:
            AtlasResult with atlas image and frame map
            
        Raises:
            AtlasGenerationError: If atlas generation fails
        """
        if len(frames) != spec.total_frames:
            raise AtlasGenerationError(
                f"Expected {spec.total_frames} frames, got {len(frames)}"
            )
        
        # Calculate optimal layout using layout engine
        layout = self.layout_engine.calculate_grid_layout(spec)
        
        # Check size limits
        if layout.width > self.config.max_size[0] or layout.height > self.config.max_size[1]:
            raise AtlasGenerationError(
                f"Atlas size {layout.width}x{layout.height} exceeds maximum {self.config.max_size}"
            )
        
        # Create atlas image
        atlas = Image.new(self.config.format, (layout.width, layout.height), (0, 0, 0, 0))
        frame_map = {}
        
        # Place frames according to layout
        direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        
        for direction_idx in range(spec.directions):
            for frame_idx in range(spec.frames_per_direction):
                frame_index = direction_idx * spec.frames_per_direction + frame_idx
                
                if frame_index >= len(frames):
                    break
                
                frame = frames[frame_index]
                
                # Get position from layout
                direction_name = (direction_names[direction_idx] 
                                if direction_idx < len(direction_names) 
                                else f"dir_{direction_idx}")
                frame_name = f"walk_{direction_name}_{frame_idx}"
                
                if frame_name in layout.positions:
                    rect = layout.positions[frame_name]
                    
                    # Paste frame into atlas
                    atlas.paste(frame, (rect.x, rect.y), frame if frame.mode == 'RGBA' else None)
                    
                    # Add to frame map
                    frame_map[frame_name] = {
                        "x": rect.x,
                        "y": rect.y,
                        "w": rect.width,
                        "h": rect.height
                    }
        
        return AtlasResult(
            atlas=atlas,
            frame_map=frame_map,
            metadata={
                "unit_name": spec.name,
                "directions": spec.directions,
                "frames_per_direction": spec.frames_per_direction,
                "frame_size": spec.frame_size,
                "layout_efficiency": layout.efficiency
            }
        )
    
    def create_sprite_atlas(self, sprites: List[tuple[str, Image.Image]]) -> AtlasResult:
        """
        Create texture atlas for a collection of sprites using bin packing.
        
        Args:
            sprites: List of (name, image) tuples
            
        Returns:
            AtlasResult with atlas image and frame map
        """
        if not sprites:
            raise AtlasGenerationError("No sprites provided for atlas generation")
        
        # Prepare items for packing algorithm
        items = [(name, sprite.width, sprite.height) for name, sprite in sprites]
        
        # Calculate optimal layout using bin packing
        layout = self.layout_engine.calculate_packed_layout(items)
        
        # Optimize atlas size
        layout = self.layout_engine.optimize_atlas_size(layout)
        
        # Check size limits
        if layout.width > self.config.max_size[0] or layout.height > self.config.max_size[1]:
            raise AtlasGenerationError(
                f"Atlas size {layout.width}x{layout.height} exceeds maximum {self.config.max_size}"
            )
        
        # Create atlas image
        atlas = Image.new(self.config.format, (layout.width, layout.height), (0, 0, 0, 0))
        frame_map = {}
        
        # Create sprite lookup for easy access
        sprite_dict = {name: sprite for name, sprite in sprites}
        
        # Place sprites according to layout
        for name, rect in layout.positions.items():
            if name in sprite_dict:
                sprite = sprite_dict[name]
                
                # Paste sprite into atlas
                atlas.paste(sprite, (rect.x, rect.y), sprite if sprite.mode == 'RGBA' else None)
                
                # Add to frame map
                frame_map[name] = {
                    "x": rect.x,
                    "y": rect.y,
                    "w": rect.width,
                    "h": rect.height
                }
        
        return AtlasResult(
            atlas=atlas,
            frame_map=frame_map,
            metadata={
                "sprite_count": len(sprites),
                "layout_efficiency": layout.efficiency
            }
        )
    
    def create_worker_atlas(self, frames: List[Image.Image], worker_name: str = "worker") -> AtlasResult:
        """
        Create 512×512 pixel texture atlas specifically for worker animations.
        
        Args:
            frames: List of 64 animation frames (8 directions × 8 walking frames)
            worker_name: Name of the worker unit
            
        Returns:
            AtlasResult with 512×512 atlas and frame map
            
        Raises:
            AtlasGenerationError: If atlas generation fails
        """
        # Create worker specification for 512x512 atlas
        spec = UnitSpec(
            name=worker_name,
            directions=8,
            frames_per_direction=8,
            frame_size=(64, 64)
        )
        
        # Validate frame count
        if len(frames) != 64:
            raise AtlasGenerationError(
                f"Worker atlas requires exactly 64 frames (8 directions × 8 frames), got {len(frames)}"
            )
        
        # Validate frame sizes
        for i, frame in enumerate(frames):
            if frame.size != (64, 64):
                raise AtlasGenerationError(
                    f"Frame {i} has size {frame.size}, expected (64, 64)"
                )
        
        # Create atlas using unit atlas method
        result = self.create_unit_atlas(frames, spec)
        
        # Ensure atlas is exactly 512×512
        if result.atlas.size != (512, 512):
            # Resize canvas to 512×512 if needed
            new_atlas = Image.new(self.config.format, (512, 512), (0, 0, 0, 0))
            new_atlas.paste(result.atlas, (0, 0))
            result.atlas = new_atlas
        
        # Update metadata for worker-specific information
        result.metadata.update({
            "atlas_type": "worker_animation",
            "target_size": (512, 512),
            "frame_layout": "8x8_grid",
            "animation_type": "walking"
        })
        
        return result
    
    def generate_placeholder_frames(self, count: int, frame_size: Tuple[int, int] = (64, 64)) -> List[Image.Image]:
        """
        Generate placeholder frames for missing animation frames.
        
        Args:
            count: Number of placeholder frames to generate
            frame_size: Size of each frame
            
        Returns:
            List of placeholder frame images
        """
        frames = []
        
        for i in range(count):
            # Create a simple placeholder with a colored rectangle and frame number
            frame = Image.new('RGBA', frame_size, (0, 0, 0, 0))
            
            # Add a colored border to indicate it's a placeholder
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(frame)
            
            # Draw border
            border_color = (255, 0, 255, 128)  # Magenta with transparency
            draw.rectangle([2, 2, frame_size[0]-3, frame_size[1]-3], 
                         outline=border_color, width=2)
            
            # Add frame number text
            try:
                # Try to use a default font
                font = ImageFont.load_default()
                text = f"F{i}"
                
                # Calculate text position (center)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (frame_size[0] - text_width) // 2
                y = (frame_size[1] - text_height) // 2
                
                draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
            except:
                # If font loading fails, just draw a simple cross
                draw.line([10, 10, frame_size[0]-10, frame_size[1]-10], 
                         fill=(255, 255, 255, 255), width=2)
                draw.line([frame_size[0]-10, 10, 10, frame_size[1]-10], 
                         fill=(255, 255, 255, 255), width=2)
            
            frames.append(frame)
        
        return frames


class AtlasValidator:
    """Validator for atlas generation results and consistency checks."""
    
    def __init__(self, config: AtlasConfig):
        """Initialize atlas validator with configuration."""
        self.config = config
    
    def validate_atlas_dimensions(self, atlas: Image.Image, expected_size: Optional[Tuple[int, int]] = None) -> List[str]:
        """
        Validate atlas dimensions meet requirements.
        
        Args:
            atlas: Atlas image to validate
            expected_size: Expected atlas size (optional)
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check if atlas exists and has valid dimensions
        if not atlas:
            errors.append("Atlas image is None or invalid")
            return errors
        
        width, height = atlas.size
        
        # Check minimum dimensions
        if width <= 0 or height <= 0:
            errors.append(f"Atlas has invalid dimensions: {width}x{height}")
        
        # Check maximum dimensions
        if width > self.config.max_size[0] or height > self.config.max_size[1]:
            errors.append(f"Atlas size {width}x{height} exceeds maximum {self.config.max_size}")
        
        # Check expected size if provided
        if expected_size:
            if (width, height) != expected_size:
                errors.append(f"Atlas size {width}x{height} does not match expected {expected_size}")
        
        # Check power of two constraint if enabled
        if self.config.power_of_two:
            if not self._is_power_of_two(width):
                errors.append(f"Atlas width {width} is not a power of two")
            if not self._is_power_of_two(height):
                errors.append(f"Atlas height {height} is not a power of two")
        
        return errors
    
    def validate_frame_boundaries(self, atlas: Image.Image, frame_map: Dict[str, Dict[str, int]]) -> List[str]:
        """
        Validate that all frame boundaries are within atlas dimensions.
        
        Args:
            atlas: Atlas image
            frame_map: Frame coordinate mapping
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not atlas or not frame_map:
            errors.append("Atlas or frame map is None")
            return errors
        
        atlas_width, atlas_height = atlas.size
        
        for frame_name, frame_data in frame_map.items():
            try:
                x = frame_data["x"]
                y = frame_data["y"]
                w = frame_data["w"]
                h = frame_data["h"]
                
                # Check frame coordinates are non-negative
                if x < 0 or y < 0:
                    errors.append(f"Frame '{frame_name}' has negative coordinates: ({x}, {y})")
                
                # Check frame dimensions are positive
                if w <= 0 or h <= 0:
                    errors.append(f"Frame '{frame_name}' has invalid dimensions: {w}x{h}")
                
                # Check frame fits within atlas
                if x + w > atlas_width:
                    errors.append(f"Frame '{frame_name}' extends beyond atlas width: {x + w} > {atlas_width}")
                
                if y + h > atlas_height:
                    errors.append(f"Frame '{frame_name}' extends beyond atlas height: {y + h} > {atlas_height}")
                
            except KeyError as e:
                errors.append(f"Frame '{frame_name}' missing required coordinate: {e}")
            except (TypeError, ValueError) as e:
                errors.append(f"Frame '{frame_name}' has invalid coordinate data: {e}")
        
        return errors
    
    def validate_frame_content(self, atlas: Image.Image, frame_map: Dict[str, Dict[str, int]]) -> List[str]:
        """
        Validate frame content for basic quality checks.
        
        Args:
            atlas: Atlas image
            frame_map: Frame coordinate mapping
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not atlas or not frame_map:
            errors.append("Atlas or frame map is None")
            return errors
        
        for frame_name, frame_data in frame_map.items():
            try:
                x = frame_data["x"]
                y = frame_data["y"]
                w = frame_data["w"]
                h = frame_data["h"]
                
                # Extract frame from atlas
                frame_region = atlas.crop((x, y, x + w, y + h))
                
                # Check if frame is completely transparent
                if self._is_completely_transparent(frame_region):
                    errors.append(f"Frame '{frame_name}' is completely transparent")
                
                # Check if frame has expected format
                if frame_region.mode != atlas.mode:
                    errors.append(f"Frame '{frame_name}' mode {frame_region.mode} differs from atlas mode {atlas.mode}")
                
            except Exception as e:
                errors.append(f"Error validating frame '{frame_name}' content: {e}")
        
        return errors
    
    def validate_atlas_metadata_consistency(self, atlas_result: AtlasResult, spec: Optional[UnitSpec] = None) -> List[str]:
        """
        Validate consistency between atlas metadata and actual content.
        
        Args:
            atlas_result: Atlas generation result
            spec: Unit specification (optional)
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Validate atlas and frame map consistency
        atlas = atlas_result.atlas
        frame_map = atlas_result.frame_map
        metadata = atlas_result.metadata
        
        # Check atlas dimensions match metadata
        if "size" in metadata:
            expected_size = metadata["size"]
            if isinstance(expected_size, (list, tuple)) and len(expected_size) == 2:
                if atlas.size != tuple(expected_size):
                    errors.append(f"Atlas size {atlas.size} does not match metadata size {expected_size}")
        
        # Check frame count consistency
        if spec:
            expected_frames = spec.total_frames
            actual_frames = len(frame_map)
            
            if actual_frames != expected_frames:
                errors.append(f"Frame count {actual_frames} does not match expected {expected_frames}")
            
            # Check frame naming consistency for unit animations
            direction_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            
            for direction_idx in range(spec.directions):
                for frame_idx in range(spec.frames_per_direction):
                    direction_name = (direction_names[direction_idx] 
                                    if direction_idx < len(direction_names) 
                                    else f"dir_{direction_idx}")
                    expected_frame_name = f"walk_{direction_name}_{frame_idx}"
                    
                    if expected_frame_name not in frame_map:
                        errors.append(f"Missing expected frame: {expected_frame_name}")
        
        # Check metadata completeness
        required_metadata = ["unit_name"] if spec else []
        for key in required_metadata:
            if key not in metadata:
                errors.append(f"Missing required metadata: {key}")
        
        return errors
    
    def validate_worker_atlas(self, atlas_result: AtlasResult) -> List[str]:
        """
        Validate worker-specific atlas requirements.
        
        Args:
            atlas_result: Atlas generation result
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check atlas is exactly 512x512
        if atlas_result.atlas.size != (512, 512):
            errors.append(f"Worker atlas size {atlas_result.atlas.size} is not 512x512")
        
        # Check frame count is exactly 64
        if len(atlas_result.frame_map) != 64:
            errors.append(f"Worker atlas has {len(atlas_result.frame_map)} frames, expected 64")
        
        # Check all frames are 64x64
        for frame_name, frame_data in atlas_result.frame_map.items():
            if frame_data["w"] != 64 or frame_data["h"] != 64:
                errors.append(f"Worker frame '{frame_name}' size {frame_data['w']}x{frame_data['h']} is not 64x64")
        
        # Check worker-specific metadata
        metadata = atlas_result.metadata
        expected_metadata = {
            "atlas_type": "worker_animation",
            "target_size": (512, 512),
            "frame_layout": "8x8_grid",
            "animation_type": "walking"
        }
        
        for key, expected_value in expected_metadata.items():
            if key not in metadata:
                errors.append(f"Missing worker metadata: {key}")
            elif metadata[key] != expected_value:
                errors.append(f"Worker metadata '{key}' is {metadata[key]}, expected {expected_value}")
        
        return errors
    
    def validate_complete_atlas_workflow(self, atlas_result: AtlasResult, spec: Optional[UnitSpec] = None) -> List[str]:
        """
        Perform complete validation of atlas generation workflow.
        
        Args:
            atlas_result: Atlas generation result
            spec: Unit specification (optional)
            
        Returns:
            List of all validation error messages
        """
        all_errors = []
        
        # Validate atlas dimensions
        expected_size = None
        if spec:
            frame_width, frame_height = spec.frame_size
            expected_width = spec.frames_per_direction * frame_width
            expected_height = spec.directions * frame_height
            
            if self.config.padding > 0:
                expected_width += (spec.frames_per_direction - 1) * self.config.padding
                expected_height += (spec.directions - 1) * self.config.padding
            
            if self.config.power_of_two:
                expected_width = self._next_power_of_two(expected_width)
                expected_height = self._next_power_of_two(expected_height)
            
            expected_size = (expected_width, expected_height)
        
        all_errors.extend(self.validate_atlas_dimensions(atlas_result.atlas, expected_size))
        
        # Validate frame boundaries
        all_errors.extend(self.validate_frame_boundaries(atlas_result.atlas, atlas_result.frame_map))
        
        # Validate frame content
        all_errors.extend(self.validate_frame_content(atlas_result.atlas, atlas_result.frame_map))
        
        # Validate metadata consistency
        all_errors.extend(self.validate_atlas_metadata_consistency(atlas_result, spec))
        
        # Special validation for worker atlases
        if (atlas_result.metadata.get("atlas_type") == "worker_animation" or 
            (spec and spec.name == "worker")):
            all_errors.extend(self.validate_worker_atlas(atlas_result))
        
        return all_errors
    
    def _is_power_of_two(self, n: int) -> bool:
        """Check if number is a power of two."""
        return n > 0 and (n & (n - 1)) == 0
    
    def _next_power_of_two(self, n: int) -> int:
        """Find the next power of two greater than or equal to n."""
        if n <= 0:
            return 1
        
        if n & (n - 1) == 0:
            return n
        
        power = 1
        while power < n:
            power <<= 1
        
        return power
    
    def _is_completely_transparent(self, image: Image.Image) -> bool:
        """Check if image is completely transparent."""
        if image.mode not in ('RGBA', 'LA'):
            return False
        
        # Check if all alpha values are 0
        if image.mode == 'RGBA':
            alpha_channel = image.split()[-1]
            return all(pixel == 0 for pixel in alpha_channel.getdata())
        elif image.mode == 'LA':
            alpha_channel = image.split()[-1]
            return all(pixel == 0 for pixel in alpha_channel.getdata())
        
        return False


class AtlasGenerationError(Exception):
    """Exception raised when atlas generation fails."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message