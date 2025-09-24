use bevy::prelude::*;
use crate::{
    components::{Position, Stockpile, Worker, WorkerTask, TaskPurpose},
    events::{TransferResourceEvent, PathfindingRequestEvent, PathfindingPriority},
};

/// System that handles resource transport between stockpiles
pub fn transport_system(
    mut events: EventReader<TransferResourceEvent>,
    mut stockpiles: Query<&mut Stockpile>,
    positions: Query<&Position>,
    mut workers: Query<(Entity, &mut Worker, &Position)>,
    mut pathfinding_events: EventWriter<PathfindingRequestEvent>,
) {
    for event in events.read() {
        // Find available worker for transport
        let available_worker = workers.iter_mut()
            .find(|(_, worker, _)| matches!(worker.current_task, WorkerTask::Idle) && worker.carrying.is_none());
        
        if let Some((worker_entity, mut worker, worker_pos)) = available_worker {
            // Get source and destination positions
            let source_pos = positions.get(event.from).ok();
            let dest_pos = positions.get(event.to).ok();
            
            if let (Some(source_pos), Some(dest_pos)) = (source_pos, dest_pos) {
                // Check if source has the resource
                if let Ok(source_stockpile) = stockpiles.get(event.from) {
                    if source_stockpile.get_item_count(&event.resource) >= event.amount {
                        // Assign transport task
                        worker.current_task = WorkerTask::MovingTo {
                            target: *source_pos,
                            purpose: TaskPurpose::PickupResource {
                                item: event.resource.clone(),
                                amount: event.amount,
                            },
                        };
                        
                        // Request pathfinding to source
                        pathfinding_events.send(PathfindingRequestEvent {
                            entity: worker_entity,
                            from: *worker_pos,
                            to: *source_pos,
                            priority: PathfindingPriority::Normal,
                        });
                        
                        log::debug!("Assigned transport task: {} {} from {:?} to {:?}", 
                                   event.amount, event.resource, event.from, event.to);
                    }
                }
            }
        } else {
            log::warn!("No available workers for transport task");
        }
    }
}

/// System that handles automatic resource distribution
pub fn resource_distribution_system(
    stockpiles: Query<(Entity, &Stockpile, &Position)>,
    mut transfer_events: EventWriter<TransferResourceEvent>,
    tick: Res<crate::resources::GameTick>,
) {
    // Run distribution logic every 5 seconds
    if tick.current % (tick.target_tps as u64 * 5) != 0 {
        return;
    }
    
    let stockpiles_vec: Vec<_> = stockpiles.iter().collect();
    
    // Simple distribution: move excess resources to stockpiles that need them
    for (source_entity, source_stockpile, _source_pos) in &stockpiles_vec {
        for (item, &amount) in &source_stockpile.items {
            if amount > 10 { // If we have excess (more than 10)
                // Find a stockpile that needs this resource
                for (dest_entity, dest_stockpile, _dest_pos) in &stockpiles_vec {
                    if source_entity == dest_entity {
                        continue;
                    }
                    
                    let dest_amount = dest_stockpile.get_item_count(item);
                    if dest_amount < 5 && dest_stockpile.available_space() > 0 {
                        // Transfer some resources
                        let transfer_amount = (amount - 10).min(5).min(dest_stockpile.available_space());
                        
                        if transfer_amount > 0 {
                            transfer_events.send(TransferResourceEvent {
                                from: *source_entity,
                                to: *dest_entity,
                                resource: item.clone(),
                                amount: transfer_amount,
                            });
                            
                            log::debug!("Auto-distributing {} {} from {:?} to {:?}", 
                                       transfer_amount, item, source_entity, dest_entity);
                            break; // Only one transfer per item per tick
                        }
                    }
                }
            }
        }
    }
}

/// System that processes completed transport tasks
pub fn transport_completion_system(
    mut task_events: EventReader<crate::events::TaskCompletedEvent>,
    mut workers: Query<&mut Worker>,
    stockpiles: Query<(Entity, &Stockpile)>,
    positions: Query<&Position>,
    mut pathfinding_events: EventWriter<PathfindingRequestEvent>,
) {
    for event in task_events.read() {
        if event.task_type == "pickup" {
            if let Ok(mut worker) = workers.get_mut(event.worker) {
                if let Some((item, amount)) = &worker.carrying {
                    // Find destination for the carried item
                    // For now, just find any stockpile with space
                    let mut dest_entity = None;
                    for (entity, stockpile) in stockpiles.iter() {
                        if stockpile.available_space() >= *amount {
                            dest_entity = Some(entity);
                            break;
                        }
                    }
                    
                    if let Some(dest_entity) = dest_entity {
                        if let Ok(dest_pos) = positions.get(dest_entity) {
                            if let Ok(worker_pos) = positions.get(event.worker) {
                                worker.current_task = WorkerTask::Carrying {
                                    from: *worker_pos,
                                    to: *dest_pos,
                                    item: item.clone(),
                                    amount: *amount,
                                };
                                
                                pathfinding_events.send(PathfindingRequestEvent {
                                    entity: event.worker,
                                    from: *worker_pos,
                                    to: *dest_pos,
                                    priority: PathfindingPriority::Normal,
                                });
                            }
                        }
                    }
                }
            }
        } else if event.task_type == "delivery" {
            // Handle completed delivery - remove from source, add to destination
            if let Ok(worker) = workers.get(event.worker) {
                // In a real implementation, you'd track the source and destination
                // and actually transfer the resources between stockpiles
                log::debug!("Delivery completed by worker {:?}", event.worker);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_resource_distribution_logic() {
        // Test that excess resources are identified correctly
        let mut stockpile = Stockpile::new(100);
        stockpile.add_item("wood".to_string(), 15);
        
        assert!(stockpile.get_item_count("wood") > 10);
        
        let mut dest_stockpile = Stockpile::new(100);
        dest_stockpile.add_item("wood".to_string(), 3);
        
        assert!(dest_stockpile.get_item_count("wood") < 5);
        assert!(dest_stockpile.available_space() > 0);
    }
}