"""
Tests for atlas layout engine functionality.
"""

import unittest
from PIL import Image

from ..processing.atlas import (
    AtlasConfig, AtlasLayoutEngine, UnitSpec, Rectangle, 
    LayoutNode, AtlasLayout, AtlasGenerator
)


class TestRectangle(unittest.TestCase):
    """Test Rectangle class functionality."""
    
    def test_rectangle_properties(self):
        """Test rectangle property calculations."""
        rect = Rectangle(10, 20, 30, 40)
        
        self.assertEqual(rect.right, 40)
        self.assertEqual(rect.bottom, 60)
    
    def test_contains_point(self):
        """Test point containment."""
        rect = Rectangle(10, 20, 30, 40)
        
        self.assertTrue(rect.contains_point(15, 25))
        self.assertTrue(rect.contains_point(10, 20))  # Edge case
        self.assertFalse(rect.contains_point(40, 60))  # Right/bottom edges
        self.assertFalse(rect.contains_point(5, 15))
    
    def test_intersects(self):
        """Test rectangle intersection."""
        rect1 = Rectangle(10, 10, 20, 20)
        rect2 = Rectangle(31, 31, 20, 20)  # Separate
        rect3 = Rectangle(15, 15, 10, 10)  # Overlapping
        rect4 = Rectangle(50, 50, 10, 10)  # Separate
        
        self.assertFalse(rect1.intersects(rect2))  # Separate
        self.assertTrue(rect1.intersects(rect3))   # Overlapping
        self.assertFalse(rect1.intersects(rect4))  # Separate


class TestLayoutNode(unittest.TestCase):
    """Test LayoutNode class functionality."""
    
    def test_find_node_unused(self):
        """Test finding node in unused space."""
        node = LayoutNode(Rectangle(0, 0, 100, 100))
        
        found = node.find_node(50, 50)
        self.assertIsNotNone(found)
        self.assertEqual(found, node)
    
    def test_find_node_too_large(self):
        """Test finding node when space is too small."""
        node = LayoutNode(Rectangle(0, 0, 100, 100))
        
        found = node.find_node(150, 50)
        self.assertIsNone(found)
    
    def test_split_node(self):
        """Test node splitting functionality."""
        node = LayoutNode(Rectangle(0, 0, 100, 100))
        
        result = node.split_node(40, 30)
        
        self.assertTrue(node.used)
        self.assertEqual(result, node)
        self.assertIsNotNone(node.right)
        self.assertIsNotNone(node.down)
        
        # Check right node
        self.assertEqual(node.right.rect.x, 40)
        self.assertEqual(node.right.rect.y, 0)
        self.assertEqual(node.right.rect.width, 60)
        self.assertEqual(node.right.rect.height, 100)
        
        # Check down node
        self.assertEqual(node.down.rect.x, 0)
        self.assertEqual(node.down.rect.y, 30)
        self.assertEqual(node.down.rect.width, 40)
        self.assertEqual(node.down.rect.height, 70)


class TestAtlasLayout(unittest.TestCase):
    """Test AtlasLayout class functionality."""
    
    def test_add_item(self):
        """Test adding items to layout."""
        layout = AtlasLayout(100, 100, {})
        rect = Rectangle(10, 10, 20, 20)
        
        layout.add_item("test", rect)
        
        self.assertIn("test", layout.positions)
        self.assertEqual(layout.positions["test"], rect)
    
    def test_calculate_efficiency(self):
        """Test efficiency calculation."""
        layout = AtlasLayout(100, 100, {})
        
        layout.calculate_efficiency(2500)  # 25% efficiency
        
        self.assertAlmostEqual(layout.efficiency, 0.25, places=2)


class TestAtlasLayoutEngine(unittest.TestCase):
    """Test AtlasLayoutEngine class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(padding=0, power_of_two=False)
        self.engine = AtlasLayoutEngine(self.config)
    
    def test_calculate_grid_layout(self):
        """Test grid layout calculation for unit animations."""
        spec = UnitSpec("worker", directions=8, frames_per_direction=8, frame_size=(64, 64))
        
        layout = self.engine.calculate_grid_layout(spec)
        
        self.assertEqual(layout.width, 512)  # 8 * 64
        self.assertEqual(layout.height, 512)  # 8 * 64
        self.assertEqual(len(layout.positions), 64)  # 8 * 8 frames
        
        # Check specific frame positions
        self.assertIn("walk_N_0", layout.positions)
        self.assertIn("walk_S_7", layout.positions)
        
        # Check first frame position
        first_frame = layout.positions["walk_N_0"]
        self.assertEqual(first_frame.x, 0)
        self.assertEqual(first_frame.y, 0)
        self.assertEqual(first_frame.width, 64)
        self.assertEqual(first_frame.height, 64)
    
    def test_calculate_grid_layout_with_padding(self):
        """Test grid layout with padding."""
        config = AtlasConfig(padding=2, power_of_two=False)
        engine = AtlasLayoutEngine(config)
        spec = UnitSpec("worker", directions=2, frames_per_direction=2, frame_size=(32, 32))
        
        layout = engine.calculate_grid_layout(spec)
        
        # Width: 2 frames * 32px + 1 padding = 66px
        # Height: 2 directions * 32px + 1 padding = 66px
        self.assertEqual(layout.width, 66)
        self.assertEqual(layout.height, 66)
        
        # Check frame positions account for padding
        frame_1_0 = layout.positions["walk_N_1"]
        self.assertEqual(frame_1_0.x, 34)  # 32 + 2 padding
        self.assertEqual(frame_1_0.y, 0)
    
    def test_calculate_grid_layout_power_of_two(self):
        """Test grid layout with power of two constraint."""
        config = AtlasConfig(padding=0, power_of_two=True)
        engine = AtlasLayoutEngine(config)
        spec = UnitSpec("worker", directions=3, frames_per_direction=3, frame_size=(50, 50))
        
        layout = engine.calculate_grid_layout(spec)
        
        # Original would be 150x150, next power of two is 256x256
        self.assertEqual(layout.width, 256)
        self.assertEqual(layout.height, 256)
    
    def test_calculate_packed_layout(self):
        """Test packed layout calculation."""
        items = [
            ("sprite1", 32, 32),
            ("sprite2", 64, 32),
            ("sprite3", 32, 64),
        ]
        
        layout = self.engine.calculate_packed_layout(items)
        
        self.assertGreater(layout.width, 0)
        self.assertGreater(layout.height, 0)
        self.assertEqual(len(layout.positions), 3)
        
        # Check all items are positioned
        for name, _, _ in items:
            self.assertIn(name, layout.positions)
    
    def test_calculate_packed_layout_empty(self):
        """Test packed layout with no items."""
        layout = self.engine.calculate_packed_layout([])
        
        self.assertEqual(layout.width, 0)
        self.assertEqual(layout.height, 0)
        self.assertEqual(len(layout.positions), 0)
    
    def test_optimize_atlas_size(self):
        """Test atlas size optimization."""
        layout = AtlasLayout(200, 200, {
            "item1": Rectangle(10, 10, 30, 30),
            "item2": Rectangle(50, 50, 20, 20),
        })
        
        optimized = self.engine.optimize_atlas_size(layout)
        
        # Should be optimized to fit actual content (70x70)
        self.assertLessEqual(optimized.width, 200)
        self.assertLessEqual(optimized.height, 200)
        self.assertGreaterEqual(optimized.width, 70)
        self.assertGreaterEqual(optimized.height, 70)
    
    def test_next_power_of_two(self):
        """Test power of two calculation."""
        self.assertEqual(self.engine._next_power_of_two(1), 1)
        self.assertEqual(self.engine._next_power_of_two(2), 2)
        self.assertEqual(self.engine._next_power_of_two(3), 4)
        self.assertEqual(self.engine._next_power_of_two(8), 8)
        self.assertEqual(self.engine._next_power_of_two(9), 16)
        self.assertEqual(self.engine._next_power_of_two(100), 128)


class TestAtlasGeneratorWithLayoutEngine(unittest.TestCase):
    """Test AtlasGenerator integration with layout engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = AtlasConfig(padding=0, power_of_two=False)
        self.generator = AtlasGenerator(self.config)
    
    def test_create_unit_atlas_with_layout_engine(self):
        """Test unit atlas creation using layout engine."""
        # Create test frames
        frames = []
        for i in range(64):  # 8 directions * 8 frames
            frame = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
            frames.append(frame)
        
        spec = UnitSpec("test_worker", directions=8, frames_per_direction=8)
        
        result = self.generator.create_unit_atlas(frames, spec)
        
        self.assertEqual(result.atlas.size, (512, 512))
        self.assertEqual(len(result.frame_map), 64)
        self.assertIn("layout_efficiency", result.metadata)
        
        # Check frame map structure
        self.assertIn("walk_N_0", result.frame_map)
        self.assertIn("walk_S_7", result.frame_map)
        
        frame_data = result.frame_map["walk_N_0"]
        self.assertEqual(frame_data["x"], 0)
        self.assertEqual(frame_data["y"], 0)
        self.assertEqual(frame_data["w"], 64)
        self.assertEqual(frame_data["h"], 64)


if __name__ == '__main__':
    unittest.main()