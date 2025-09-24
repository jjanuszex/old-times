use bevy::prelude::*;
use crate::{
    components::{Worker, Position, Building, WorkerTask, TaskPurpose},
    resources::GameTick,
    events::{AssignWorkerEvent, TaskCompletedEvent, PathfindingRequestEvent, PathfindingPriority},
};

/// System that manages worker AI and task execution
pub fn worker_ai_system(
    mut workers: Query<(Entity, &mut Worker, &mut Position)>,
    buildings: Query<(Entity, &Building, &Position), Without<Worker>>,
    tick: Res<GameTick>,
    mut task_events: EventWriter<TaskCompletedEvent>,
    mut pathfinding_events: EventWriter<PathfindingRequestEvent>,
) {
    let delta_time = tick.delta_time();
    
    for (worker_entity, mut worker, mut worker_pos) in workers.iter_mut() {
        match &mut worker.current_task {
            WorkerTask::Idle => {
                // Try to find work
                if let Some(building_entity) = worker.assigned_building {
                    if let Ok((_, building, building_pos)) = buildings.get(building_entity) {
                        if building.is_constructed {
                            // Move to assigned building
                            worker.current_task = WorkerTask::MovingTo {
                                target: *building_pos,
                                purpose: TaskPurpose::GoToWork,
                            };
                            
                            pathfinding_events.send(PathfindingRequestEvent {
                                entity: worker_entity,
                                from: *worker_pos,
                                to: *building_pos,
                                priority: PathfindingPriority::Normal,
                            });
                        }
                    }
                }
            },
            
            WorkerTask::MovingTo { target, purpose } => {
                // Check if we've reached the target
                if worker_pos.distance_to(target) < 1.0 {
                    match purpose {
                        TaskPurpose::GoToWork => {
                            if let Some(building_entity) = worker.assigned_building {
                                worker.current_task = WorkerTask::Working {
                                    building: building_entity,
                                    progress: 0.0,
                                };
                            } else {
                                worker.current_task = WorkerTask::Idle;
                            }
                        },
                        TaskPurpose::PickupResource { item, amount } => {
                            // Handle resource pickup
                            worker.carrying = Some((item.clone(), *amount));
                            worker.current_task = WorkerTask::Idle;
                            
                            task_events.send(TaskCompletedEvent {
                                worker: worker_entity,
                                task_type: "pickup".to_string(),
                            });
                        },
                        TaskPurpose::DeliverResource { item, amount } => {
                            // Handle resource delivery
                            worker.carrying = None;
                            worker.current_task = WorkerTask::Idle;
                            
                            task_events.send(TaskCompletedEvent {
                                worker: worker_entity,
                                task_type: "delivery".to_string(),
                            });
                        },
                        TaskPurpose::Construction => {
                            // Handle construction work
                            worker.current_task = WorkerTask::Idle;
                            
                            task_events.send(TaskCompletedEvent {
                                worker: worker_entity,
                                task_type: "construction".to_string(),
                            });
                        },
                    }
                }
            },
            
            WorkerTask::Working { building, progress } => {
                // Work at the assigned building
                *progress += delta_time * 1.0; // Fixed movement speed for now
                
                if *progress >= 10.0 { // 10 seconds of work
                    worker.current_task = WorkerTask::Idle;
                    
                    task_events.send(TaskCompletedEvent {
                        worker: worker_entity,
                        task_type: "work".to_string(),
                    });
                }
            },
            
            WorkerTask::Carrying { from: _, to, item, amount } => {
                // Move to delivery location
                if worker_pos.distance_to(to) < 1.0 {
                    // Deliver the item
                    worker.carrying = None;
                    worker.current_task = WorkerTask::Idle;
                    
                    task_events.send(TaskCompletedEvent {
                        worker: worker_entity,
                        task_type: "delivery".to_string(),
                    });
                }
            },
        }
    }
}

/// System that handles worker assignment events
pub fn worker_assignment_system(
    mut events: EventReader<AssignWorkerEvent>,
    mut workers: Query<&mut Worker>,
    mut buildings: Query<&mut Building>,
) {
    for event in events.read() {
        if let Ok(mut worker) = workers.get_mut(event.worker) {
            // Unassign from previous building
            if let Some(old_building) = worker.assigned_building {
                if let Ok(mut old_building_comp) = buildings.get_mut(old_building) {
                    old_building_comp.assigned_workers = old_building_comp.assigned_workers.saturating_sub(1);
                }
            }
            
            // Get the new building
            if let Ok(mut building) = buildings.get_mut(event.building) {
            
                // Assign to new building
                if building.assigned_workers < building.worker_capacity {
                    worker.assigned_building = Some(event.building);
                    worker.current_task = WorkerTask::Idle;
                    building.assigned_workers += 1;
                    
                    log::info!("Worker {:?} assigned to building {:?}", event.worker, event.building);
                } else {
                    log::warn!("Building {:?} is at full capacity", event.building);
                }
            }
        }
    }
}

/// System that spawns initial workers
pub fn spawn_workers_system(
    mut commands: Commands,
    tick: Res<GameTick>,
) {
    // Spawn some initial workers at the start
    if tick.current == 1 {
        for i in 0..5 {
            commands.spawn((
                Position::new(10 + i, 10),
                Worker::new("worker".to_string()),
            ));
        }
        log::info!("Spawned 5 initial workers");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::components::Stockpile;
    
    #[test]
    fn test_worker_assignment() {
        let mut world = World::new();
        world.init_resource::<Events<AssignWorkerEvent>>();
        
        // Create a worker and building
        let worker_entity = world.spawn(Worker::new("test_worker".to_string())).id();
        let building_entity = world.spawn((
            Building::new("test_building".to_string(), 2),
            Position::new(5, 5),
            Stockpile::new(10),
        )).id();
        
        // Send assignment event
        let mut events = world.resource_mut::<Events<AssignWorkerEvent>>();
        events.send(AssignWorkerEvent {
            worker: worker_entity,
            building: building_entity,
        });
        
        // Run the system
        let mut system = IntoSystem::into_system(worker_assignment_system);
        system.initialize(&mut world);
        system.run((), &mut world);
        
        // Check assignment
        let worker = world.get::<Worker>(worker_entity).unwrap();
        let building = world.get::<Building>(building_entity).unwrap();
        
        assert_eq!(worker.assigned_building, Some(building_entity));
        assert_eq!(building.assigned_workers, 1);
    }
}