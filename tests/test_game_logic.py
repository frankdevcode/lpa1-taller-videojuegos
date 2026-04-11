import random

from game.models import Enemy, EnemyType, Hunter, calculate_damage
from game.world import ForestMap


def test_damage_is_never_lower_than_one() -> None:
    hunter = Hunter(
        name="Aren",
        max_health=50,
        current_health=50,
        base_attack=8,
        base_defense=5,
    )
    enemy = Enemy(
        name="Bestia acorazada",
        max_health=40,
        current_health=40,
        base_attack=6,
        base_defense=99,
        enemy_type=EnemyType.TERRESTRE,
    )

    assert calculate_damage(hunter, enemy) == 1


def test_hunter_levels_up_and_restores_health() -> None:
    hunter = Hunter(
        name="Aren",
        max_health=50,
        current_health=10,
        base_attack=8,
        base_defense=5,
    )

    messages = hunter.gain_experience(100)

    assert hunter.level == 2
    assert hunter.current_health == hunter.max_health
    assert any("Subes al nivel 2" in message for message in messages)


def test_forest_map_marks_start_tile_as_explored() -> None:
    world = ForestMap(width=5, height=5, rng=random.Random(7))

    start_tile = world.tile_at(world.start_position)

    assert start_tile.explored is True


def test_forest_map_progress_matches_grid_size() -> None:
    world = ForestMap(width=4, height=3, rng=random.Random(4))

    explored, total = world.exploration_progress()

    assert explored == 1
    assert total == 12
