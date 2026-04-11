import random

from game.app import BeastHunterApp, Difficulty
from game.models import (
    Armor,
    Enemy,
    EnemyType,
    Hunter,
    Weapon,
    calculate_damage,
    calculate_enemy_damage,
)
from game.world import ForestMap, ZoneType


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
    boss_tile = world.boss_tile()

    assert start_tile.explored is True
    assert start_tile.zone_type is ZoneType.CAMPAMENTO
    assert start_tile.rest_available is True
    assert len(start_tile.shop_inventory) > 0
    assert boss_tile.zone_type is ZoneType.GUARIDA
    assert boss_tile.enemy is not None
    assert boss_tile.enemy.is_boss is True


def test_forest_map_progress_matches_grid_size() -> None:
    world = ForestMap(width=4, height=3, rng=random.Random(4))

    explored, total = world.exploration_progress()

    assert explored == 1
    assert total == 12


def test_hunter_can_equip_items_manually() -> None:
    hunter = Hunter(
        name="Aren",
        max_health=50,
        current_health=50,
        base_attack=8,
        base_defense=5,
    )
    weapon = Weapon(name="Arco largo", value=60, attack_bonus=4)
    armor = Armor(name="Coraza ligera", value=50, defense_bonus=3)

    hunter.add_item(weapon)
    hunter.add_item(armor)

    hunter.equip_weapon(weapon)
    hunter.equip_armor(armor)

    assert hunter.total_attack() == 12
    assert hunter.total_defense() == 8


def test_selling_equipped_item_removes_equipment_and_grants_gold() -> None:
    hunter = Hunter(
        name="Aren",
        max_health=50,
        current_health=50,
        base_attack=8,
        base_defense=5,
    )
    weapon = Weapon(name="Lanza corta", value=80, attack_bonus=5)
    hunter.add_item(weapon)
    hunter.equip_weapon(weapon)

    sale_price = hunter.sell_item(weapon)

    assert sale_price == 40
    assert hunter.gold == 40
    assert hunter.equipped_weapon is None


def test_flying_enemies_ignore_part_of_defense() -> None:
    hunter = Hunter(
        name="Aren",
        max_health=50,
        current_health=50,
        base_attack=8,
        base_defense=8,
    )
    ground_enemy = Enemy(
        name="Bestia terrestre",
        max_health=40,
        current_health=40,
        base_attack=10,
        base_defense=3,
        enemy_type=EnemyType.TERRESTRE,
    )
    flying_enemy = Enemy(
        name="Bestia voladora",
        max_health=40,
        current_health=40,
        base_attack=10,
        base_defense=3,
        enemy_type=EnemyType.VOLADOR,
    )

    ground_damage, _ = calculate_enemy_damage(ground_enemy, hunter)
    flying_damage, _ = calculate_enemy_damage(flying_enemy, hunter)

    assert flying_damage > ground_damage


def test_boss_unlock_requires_level_and_exploration() -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR)
    app.session.hunter.level = 3

    for tile in app.session.world.tiles.values():
        tile.explored = True

    app._refresh_boss_unlock()

    assert app.session.boss_unlocked is True


def test_boss_defeat_ends_the_game_with_victory() -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR)
    boss = app.session.world.boss_tile().enemy

    assert boss is not None

    app._resolve_enemy_defeat(boss)

    assert app.session.victory is True
    assert app.session.game_over is True


def test_achievements_unlock_from_progression() -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR)
    app.session.discovered_treasures = 3
    app.session.items_bought = 1
    app.session.items_sold = 1
    app.session.enemies_defeated = 5

    app._evaluate_achievements()

    assert "Primera sangre" in app.session.achievements
    assert "Cazador veterano" in app.session.achievements
    assert "Recolector del bosque" in app.session.achievements
    assert "Mercader del gremio" in app.session.achievements


def test_award_score_increases_session_score() -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR)

    app._award_score(25, "Prueba de puntaje.")

    assert app.session.score == 25
