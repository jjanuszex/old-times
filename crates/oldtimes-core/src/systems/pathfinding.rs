use bevy::prelude::*;
use pathfinding::prelude::astar;
use crate::{
    components::{Position, Pathfinding, Tile},
    resources::{MapData, PathfindingCache},
    events::{PathfindingRequestEvent, MapChangedEvent},
};

/// System that handles pathfinding requests
pub fn pathfinding_system(
    mut commands: Commands,
    mut cache: ResMut<PathfindingCache>,
    map: Res<MapData>,
    mut requests: EventReader<PathfindingRequestEvent>,
) {
    for request in requests.read() {
        let path = find_path(&mut cache, &map, request.from, request.to);
        
        if let Some(path) = path {
            commands.entity(request.entity).insert(Pathfinding::new(path));
        } else {
            log::warn!("No path found from {:?} to {:?}", request.from, request.to);
        }
    }
}

/// System that moves entities along their paths
pub fn movement_system(
    mut query: Query<(&mut Position, &mut Pathfinding)>,
    tick: Res<crate::resources::GameTick>,
) {
    let delta_time = tick.delta_time();
    
    for (mut position, mut pathfinding) in query.iter_mut() {
        if pathfinding.is_complete() {
            continue;
        }
        
        if let Some(target) = pathfinding.current_target() {
            // Simple movement - instantly move to next waypoint each tick
            // In a real game, you'd interpolate based on movement speed
            *position = target;
            
            if !pathfinding.advance_target() {
                // Path completed, remove pathfinding component
                // This would be done via commands in a real system
            }
        }
    }
}

/// System that clears pathfinding cache when map changes
pub fn invalidate_pathfinding_cache_system(
    mut cache: ResMut<PathfindingCache>,
    mut events: EventReader<MapChangedEvent>,
) {
    for _event in events.read() {
        cache.clear();
        log::debug!("Pathfinding cache cleared due to map change");
    }
}

fn find_path(
    cache: &mut PathfindingCache,
    map: &MapData,
    from: Position,
    to: Position,
) -> Option<Vec<Position>> {
    // Check cache first
    if let Some(cached_path) = cache.get(from, to) {
        return Some(cached_path);
    }
    
    let result = astar(
        &from,
        |pos| get_neighbors(map, *pos),
        |pos| pos.distance_to(&to) as u32,
        |pos| *pos == to,
    );
    
    if let Some((path, _cost)) = result {
        cache.insert(from, to, path.clone());
        Some(path)
    } else {
        None
    }
}

fn get_neighbors(map: &MapData, pos: Position) -> Vec<(Position, u32)> {
    let mut neighbors = Vec::new();
    
    for dx in -1..=1 {
        for dy in -1..=1 {
            if dx == 0 && dy == 0 {
                continue;
            }
            
            let new_pos = Position::new(pos.x + dx, pos.y + dy);
            
            if let Some(tile) = map.get_tile(new_pos.x, new_pos.y) {
                if tile.is_passable() {
                    let cost = (tile.movement_cost() * 100.0) as u32;
                    // Diagonal movement costs more
                    let diagonal_cost = if dx != 0 && dy != 0 { 141 } else { 100 };
                    neighbors.push((new_pos, cost * diagonal_cost / 100));
                }
            }
        }
    }
    
    neighbors
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::components::TileType;
    
    #[test]
    fn test_pathfinding_simple() {
        let mut map = MapData::new(10, 10);
        let mut cache = PathfindingCache::new(100);
        
        let from = Position::new(0, 0);
        let to = Position::new(5, 5);
        
        let path = find_path(&mut cache, &map, from, to);
        assert!(path.is_some());
        
        let path = path.unwrap();
        assert_eq!(path.first(), Some(&from));
        assert_eq!(path.last(), Some(&to));
    }
    
    #[test]
    fn test_pathfinding_with_obstacles() {
        let mut map = MapData::new(10, 10);
        
        // Create a wall
        for y in 1..9 {
            map.set_tile(5, y, Tile {
                tile_type: TileType::Water,
                elevation: 0,
            });
        }
        
        let mut cache = PathfindingCache::new(100);
        let from = Position::new(0, 5);
        let to = Position::new(9, 5);
        
        let path = find_path(&mut cache, &map, from, to);
        assert!(path.is_some());
        
        // Path should go around the obstacle
        let path = path.unwrap();
        assert!(path.len() > 10); // Should be longer than direct path
    }
    
    #[test]
    fn test_pathfinding_cache() {
        let map = MapData::new(10, 10);
        let mut cache = PathfindingCache::new(100);
        
        let from = Position::new(0, 0);
        let to = Position::new(5, 5);
        
        // First call should miss cache
        let _path1 = find_path(&mut cache, &map, from, to);
        assert_eq!(cache.cache_misses, 1);
        assert_eq!(cache.cache_hits, 0);
        
        // Second call should hit cache
        let _path2 = find_path(&mut cache, &map, from, to);
        assert_eq!(cache.cache_misses, 1);
        assert_eq!(cache.cache_hits, 1);
    }
}