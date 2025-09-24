use crate::{BuildingPlacer, DebugOverlay, GameSpeed};
use bevy::prelude::*;
use oldtimes_core::resources::*;

pub fn setup_ui(mut commands: Commands) {
    // Root UI node
    commands.spawn(NodeBundle {
        style: Style {
            width: Val::Percent(100.0),
            height: Val::Percent(100.0),
            justify_content: JustifyContent::SpaceBetween,
            ..default()
        },
        ..default()
    }).with_children(|parent| {
        // Top bar
        parent.spawn(NodeBundle {
            style: Style {
                width: Val::Percent(100.0),
                height: Val::Px(60.0),
                padding: UiRect::all(Val::Px(10.0)),
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            },
            background_color: Color::srgba(0.0, 0.0, 0.0, 0.8).into(),
            ..default()
        }).with_children(|parent| {
            // Game info
            parent.spawn((
                TextBundle::from_section(
                    "Old Times - Tick: 0",
                    TextStyle {
                        font_size: 20.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                GameInfoText,
            ));

            // Speed controls
            parent.spawn((
                TextBundle::from_section(
                    "Speed: 1x | SPACE: Pause | 1/2/4: Speed",
                    TextStyle {
                        font_size: 16.0,
                        color: Color::srgb(0.7, 0.7, 0.7),
                        ..default()
                    },
                ),
                SpeedInfoText,
            ));
        });

        // Bottom bar - building selection
        parent.spawn(NodeBundle {
            style: Style {
                width: Val::Percent(100.0),
                height: Val::Px(80.0),
                padding: UiRect::all(Val::Px(10.0)),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                ..default()
            },
            background_color: Color::srgba(0.0, 0.0, 0.0, 0.8).into(),
            ..default()
        }).with_children(|parent| {
            parent.spawn((
                TextBundle::from_section(
                    "Buildings: Q-Lumberjack | E-Sawmill | R-Farm | T-Mill | Y-Bakery | U-Quarry | ESC-Cancel",
                    TextStyle {
                        font_size: 16.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                BuildingHelpText,
            ));
        });
    });

    // Debug overlay (initially hidden)
    commands
        .spawn((
            NodeBundle {
                style: Style {
                    position_type: PositionType::Absolute,
                    top: Val::Px(70.0),
                    left: Val::Px(10.0),
                    width: Val::Px(300.0),
                    height: Val::Px(200.0),
                    padding: UiRect::all(Val::Px(10.0)),
                    flex_direction: FlexDirection::Column,
                    ..default()
                },
                background_color: Color::srgba(0.0, 0.0, 0.0, 0.9).into(),
                visibility: Visibility::Hidden,
                ..default()
            },
            DebugOverlayUI,
        ))
        .with_children(|parent| {
            parent.spawn((
                TextBundle::from_section(
                    "Debug Info",
                    TextStyle {
                        font_size: 18.0,
                        color: Color::srgb(1.0, 1.0, 0.0), // Yellow
                        ..default()
                    },
                ),
                DebugTitleText,
            ));

            parent.spawn((
                TextBundle::from_section(
                    "Performance metrics will appear here",
                    TextStyle {
                        font_size: 14.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                DebugContentText,
            ));
        });
}

pub fn update_ui_system(
    tick: Res<GameTick>,
    game_speed: Res<GameSpeed>,
    placer: Res<BuildingPlacer>,
    mut game_info_query: Query<
        &mut Text,
        (
            With<GameInfoText>,
            Without<SpeedInfoText>,
            Without<BuildingHelpText>,
        ),
    >,
    mut speed_info_query: Query<
        &mut Text,
        (
            With<SpeedInfoText>,
            Without<GameInfoText>,
            Without<BuildingHelpText>,
        ),
    >,
    mut building_help_query: Query<
        &mut Text,
        (
            With<BuildingHelpText>,
            Without<GameInfoText>,
            Without<SpeedInfoText>,
        ),
    >,
) {
    // Update game info
    if let Ok(mut text) = game_info_query.get_single_mut() {
        text.sections[0].value = format!("Old Times - Tick: {}", tick.current);
    }

    // Update speed info
    if let Ok(mut text) = speed_info_query.get_single_mut() {
        let status = if game_speed.paused {
            "PAUSED"
        } else {
            &format!("{}x", game_speed.speed_multiplier)
        };
        text.sections[0].value = format!("Speed: {} | SPACE: Pause | 1/2/4: Speed", status);
    }

    // Update building help
    if let Ok(mut text) = building_help_query.get_single_mut() {
        if let Some(selected) = &placer.selected_building {
            text.sections[0].value =
                format!("Selected: {} | Click to place | ESC: Cancel", selected);
            text.sections[0].style.color = Color::srgb(0.0, 1.0, 0.0); // Green
        } else {
            text.sections[0].value = "Buildings: Q-Lumberjack | E-Sawmill | R-Farm | T-Mill | Y-Bakery | U-Quarry | ESC-Cancel".to_string();
            text.sections[0].style.color = Color::WHITE;
        }
    }
}

pub fn update_debug_overlay_system(
    debug_overlay: Res<DebugOverlay>,
    metrics: Res<PerformanceMetrics>,
    pathfinding_cache: Res<PathfindingCache>,
    tick: Res<GameTick>,
    mut overlay_query: Query<&mut Visibility, With<DebugOverlayUI>>,
    mut content_query: Query<&mut Text, With<DebugContentText>>,
) {
    // Toggle visibility
    if let Ok(mut visibility) = overlay_query.get_single_mut() {
        *visibility = if debug_overlay.enabled {
            Visibility::Visible
        } else {
            Visibility::Hidden
        };
    }

    // Update content
    if debug_overlay.enabled {
        if let Ok(mut text) = content_query.get_single_mut() {
            let mut content = String::new();

            content.push_str(&format!("Tick: {}\n", tick.current));
            content.push_str(&format!("TPS: {}\n", tick.target_tps));
            content.push_str(&format!("Entities: {}\n", metrics.entities_count));
            content.push_str(&format!("Tick Time: {:.2}ms\n", metrics.tick_time));

            if debug_overlay.show_performance {
                content.push_str("\nSystem Times:\n");
                for (system, time) in &metrics.system_times {
                    content.push_str(&format!("  {}: {:.2}ms\n", system, time));
                }
            }

            if debug_overlay.show_pathfinding {
                content.push_str(&format!("\nPathfinding Cache:\n"));
                content.push_str(&format!(
                    "  Hit Rate: {:.1}%\n",
                    pathfinding_cache.hit_rate() * 100.0
                ));
                content.push_str(&format!("  Entries: {}\n", pathfinding_cache.cache.len()));
            }

            text.sections[0].value = content;
        }
    }
}

// Marker components for UI elements
#[derive(Component)]
pub struct GameInfoText;

#[derive(Component)]
pub struct SpeedInfoText;

#[derive(Component)]
pub struct BuildingHelpText;

#[derive(Component)]
pub struct DebugOverlayUI;

#[derive(Component)]
pub struct DebugTitleText;

#[derive(Component)]
pub struct DebugContentText;
