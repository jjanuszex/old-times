use crate::resources::{GameTick, PerformanceMetrics};
use bevy::prelude::*;

/// System that advances the game tick
pub fn advance_tick_system(
    mut tick: ResMut<GameTick>,
    mut metrics: ResMut<PerformanceMetrics>,
    query: Query<Entity>,
) {
    let start_time = std::time::Instant::now();

    tick.tick();
    metrics.entities_count = query.iter().count() as u32;

    let elapsed = start_time.elapsed().as_secs_f32() * 1000.0;
    metrics.tick_time = elapsed;

    if tick.current % 100 == 0 {
        log::debug!(
            "Tick: {}, Entities: {}, Time: {:.2}ms",
            tick.current,
            metrics.entities_count,
            elapsed
        );
    }
}

/// System that profiles other systems performance
pub fn profile_systems_system(
    mut metrics: ResMut<PerformanceMetrics>,
    mut events: EventReader<crate::events::ProfileEvent>,
) {
    for event in events.read() {
        metrics.record_system_time(event.system_name.clone(), event.duration_ms);
    }
}

/// Macro to wrap systems with profiling
#[macro_export]
macro_rules! profile_system {
    ($system:expr, $name:expr) => {
        move |world: &mut World| {
            let start = std::time::Instant::now();
            $system(world);
            let duration = start.elapsed().as_secs_f32() * 1000.0;

            if let Some(mut events) =
                world.get_resource_mut::<Events<crate::events::ProfileEvent>>()
            {
                events.send(crate::events::ProfileEvent {
                    system_name: $name.to_string(),
                    duration_ms: duration,
                });
            }
        }
    };
}
