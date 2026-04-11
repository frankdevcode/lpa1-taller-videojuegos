import random
from pathlib import Path

from pytest import MonkeyPatch

import game.app as app_module
from game.app import (
    DEFAULT_SAVE_PATH,
    BeastHunterApp,
    Difficulty,
    build_save_slot_path,
    list_save_slot_summaries,
    load_leaderboard,
    save_leaderboard,
)
from game.models import (
    Armor,
    Enemy,
    EnemyType,
    HealingItem,
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
    app.session.enemies_defeated = 1

    for tile in app.session.world.tiles.values():
        tile.explored = True

    app._refresh_boss_unlock()

    assert app.session.boss_unlocked is True


def test_boss_unlock_requires_more_defeats_on_legend_difficulty() -> None:
    app = BeastHunterApp(Difficulty.LEYENDA)
    app.session.hunter.level = 3
    for tile in app.session.world.tiles.values():
        tile.explored = True

    app.session.enemies_defeated = 2
    app._refresh_boss_unlock()
    assert app.session.boss_unlocked is False

    app.session.enemies_defeated = 3
    app._refresh_boss_unlock()
    assert app.session.boss_unlocked is True


def test_boss_defeat_ends_the_game_with_victory(tmp_path: Path) -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR, leaderboard_path=tmp_path / "leaderboard.json")
    boss = app.session.world.boss_tile().enemy

    assert boss is not None

    app._resolve_enemy_defeat(boss)

    assert app.session.victory is True
    assert app.session.game_over is True


def test_boss_defeat_writes_leaderboard_entry(tmp_path: Path) -> None:
    lb_path = tmp_path / "leaderboard.json"
    app = BeastHunterApp(Difficulty.EXPLORADOR, leaderboard_path=lb_path)
    boss = app.session.world.boss_tile().enemy

    assert boss is not None

    app._resolve_enemy_defeat(boss)

    loaded = load_leaderboard(lb_path)
    assert len(loaded) == 1
    assert loaded[0]["victory"] is True


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


def test_save_and_load_restore_core_session_state(tmp_path: Path) -> None:
    save_path = tmp_path / "savegame.json"
    app = BeastHunterApp(Difficulty.EXPLORADOR, save_path=save_path)
    weapon = Weapon(name="Arco ritual", value=120, attack_bonus=9)
    tonic = HealingItem(name="Tónico de hierbas", value=30, heal_amount=20)

    app.session.position = app.session.world.boss_position
    app.session.hunter.add_item(weapon)
    app.session.hunter.add_item(tonic)
    app.session.hunter.equip_weapon(weapon)
    app.session.score = 240
    app.session.items_bought = 2
    app.session.items_sold = 1
    app.session.discovered_treasures = 4
    app.session.achievements = ["Primera sangre", "Rastreador alfa"]
    app.session.boss_unlocked = True
    app.session.world.boss_tile().explored = True

    app.save_game()

    loaded_app = BeastHunterApp(Difficulty.LEYENDA, save_path=save_path)
    loaded = loaded_app.load_saved_game()

    assert loaded is True
    assert loaded_app.session.position == app.session.position
    assert loaded_app.session.score == 240
    assert loaded_app.session.boss_unlocked is True
    assert loaded_app.session.achievements == ["Primera sangre", "Rastreador alfa"]
    assert loaded_app.session.hunter.equipped_weapon is not None
    assert loaded_app.session.hunter.equipped_weapon.name == "Arco ritual"
    assert any(isinstance(item, HealingItem) for item in loaded_app.session.hunter.inventory)


def test_load_saved_game_returns_false_when_file_does_not_exist(tmp_path: Path) -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR, save_path=tmp_path / "missing-save.json")

    loaded = app.load_saved_game()

    assert loaded is False


def test_tutorial_marks_session_as_completed_and_awards_score() -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR)

    app._run_tutorial()

    assert app.session.tutorial_completed is True
    assert app.session.score == 20


def test_context_hint_recommends_rest_when_health_is_low_in_safe_zone() -> None:
    app = BeastHunterApp(Difficulty.EXPLORADOR)
    app.session.hunter.current_health = 10

    hint = app._context_hint()

    assert "Descansar" in hint


def test_save_and_load_preserves_tutorial_state(tmp_path: Path) -> None:
    save_path = tmp_path / "tutorial-save.json"
    app = BeastHunterApp(Difficulty.EXPLORADOR, save_path=save_path)
    app.session.tutorial_completed = True
    app.save_game()

    loaded_app = BeastHunterApp(Difficulty.EXPLORADOR, save_path=save_path)
    loaded_app.load_saved_game()

    assert loaded_app.session.tutorial_completed is True


def test_build_save_slot_path_uses_default_file_for_first_slot() -> None:
    assert build_save_slot_path(1) == DEFAULT_SAVE_PATH
    assert build_save_slot_path(2).name == "savegame_slot_2.json"


def test_list_save_slot_summaries_detects_existing_slot(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    slot_path = tmp_path / "slot1.json"
    monkeypatch.setattr(app_module, "DEFAULT_SAVE_PATH", slot_path)
    app = BeastHunterApp(Difficulty.EXPLORADOR, save_path=slot_path, active_slot=1)
    app.save_game()

    summaries = list_save_slot_summaries()

    assert len(summaries) == 3
    assert summaries[0].exists is True


def test_leaderboard_persists_and_sorts_by_score(tmp_path: Path) -> None:
    lb_path = tmp_path / "leaderboard.json"
    entries = [
        {"name": "A", "difficulty": "explorador", "level": 2, "score": 100, "victory": False},
        {"name": "B", "difficulty": "cazador", "level": 3, "score": 200, "victory": True},
        {"name": "C", "difficulty": "leyenda", "level": 1, "score": 150, "victory": False},
    ]
    save_leaderboard(lb_path, entries)

    loaded = load_leaderboard(lb_path)
    loaded.sort(
        key=lambda e: (
            int(e.get("score", 0)),
            int(e.get("level", 0)),
        ),
        reverse=True,
    )

    assert loaded[0]["name"] == "B"
    assert loaded[1]["name"] == "C"
    assert loaded[2]["name"] == "A"


def test_hunter_can_use_healing_items() -> None:
    hunter = Hunter(
        name="Aren",
        max_health=50,
        current_health=20,
        base_attack=8,
        base_defense=5,
    )
    tonic = HealingItem(name="Tónico de hierbas", value=30, heal_amount=20)
    hunter.add_item(tonic)

    consumed = hunter.use_healing_item()

    assert consumed is not None
    recovered = hunter.heal(consumed.heal_amount)
    assert recovered == 20
    assert hunter.current_health == 40
    assert hunter.healing_item_count() == 0
