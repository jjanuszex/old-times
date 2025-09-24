use super::economy::GlobalResources;
use bevy::prelude::*;

/// Plugin for creating and updating the game's user interface.
pub struct UiPlugin;

// Marker components for UI elements to easily query them.
#[derive(Component)]
struct WoodText;
#[derive(Component)]
struct PlanksText;
#[derive(Component)]
struct FoodText;
#[derive(Component)]
struct StoneText;

/// System to create the main HUD.
fn setup_ui(mut commands: Commands) {
    // Root node for the HUD
    commands
        .spawn(NodeBundle {
            style: Style {
                width: Val::Percent(100.0),
                height: Val::Px(50.0),
                justify_content: JustifyContent::SpaceEvenly,
                align_items: AlignItems::Center,
                position_type: PositionType::Absolute,
                top: Val::Px(0.0),
                ..default()
            },
            background_color: Color::srgba(0.0, 0.0, 0.0, 0.5).into(),
            ..default()
        })
        .with_children(|parent| {
            // Wood Display
            parent.spawn((
                TextBundle::from_section(
                    "Wood: 0",
                    TextStyle {
                        font_size: 20.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                WoodText,
            ));

            // Planks Display
            parent.spawn((
                TextBundle::from_section(
                    "Planks: 0",
                    TextStyle {
                        font_size: 20.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                PlanksText,
            ));

            // Food Display
            parent.spawn((
                TextBundle::from_section(
                    "Food: 0",
                    TextStyle {
                        font_size: 20.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                FoodText,
            ));

            // Stone Display
            parent.spawn((
                TextBundle::from_section(
                    "Stone: 0",
                    TextStyle {
                        font_size: 20.0,
                        color: Color::WHITE,
                        ..default()
                    },
                ),
                StoneText,
            ));
        });

    log::info!("UI setup complete.");
}

// A more efficient way to write the update system
#[allow(clippy::type_complexity)]
fn update_resource_display_combined(
    resources: Res<GlobalResources>,
    mut queries: ParamSet<(
        Query<&mut Text, With<WoodText>>,
        Query<&mut Text, With<PlanksText>>,
        Query<&mut Text, With<FoodText>>,
        Query<&mut Text, With<StoneText>>,
    )>,
) {
    if resources.is_changed() {
        queries.p0().single_mut().sections[0].value = format!("Wood: {}", resources.wood);
        queries.p1().single_mut().sections[0].value = format!("Planks: {}", resources.planks);
        queries.p2().single_mut().sections[0].value = format!("Food: {}", resources.food);
        queries.p3().single_mut().sections[0].value = format!("Stone: {}", resources.stone);
    }
}

impl Plugin for UiPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, setup_ui);
        app.add_systems(
            Update,
            update_resource_display_combined.in_set(crate::GameSystemSet::Render),
        );
    }
}
