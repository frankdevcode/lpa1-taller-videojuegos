from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from .models import (
    Armor,
    Direction,
    Enemy,
    EnemyType,
    Item,
    Position,
    Trap,
    Treasure,
    Weapon,
)


@dataclass(frozen=True, slots=True)
class EnemyBlueprint:
    name: str
    health: int
    attack: int
    defense: int
    enemy_type: EnemyType
    experience: int
    gold: int


class ZoneType(StrEnum):
    BOSQUE = "bosque salvaje"
    CAMPAMENTO = "campamento"
    PUESTO = "puesto avanzado"
    GUARIDA = "guarida ancestral"


@dataclass(slots=True)
class Tile:
    position: Position
    terrain_name: str
    explored: bool = False
    enemy: Enemy | None = None
    item: Treasure | Trap | Weapon | Armor | None = None
    zone_type: ZoneType = ZoneType.BOSQUE
    rest_available: bool = False
    shop_inventory: list[Item] = field(default_factory=list)


class ForestMap:
    def __init__(
        self,
        width: int,
        height: int,
        rng: random.Random,
        enemy_health_bonus: int = 0,
        enemy_attack_bonus: int = 0,
    ) -> None:
        self.width = width
        self.height = height
        self.rng = rng
        self.enemy_health_bonus = enemy_health_bonus
        self.enemy_attack_bonus = enemy_attack_bonus
        self.start_position = Position(width // 2, height // 2)
        self.boss_position = Position(width - 1, height - 1)
        self.tiles = self._generate_tiles()

    def _generate_tiles(self) -> dict[Position, Tile]:
        terrain_names = [
            "claro antiguo",
            "sendero cubierto",
            "cascada escondida",
            "arboleda densa",
            "cueva musgosa",
            "pantano silencioso",
            "altar olvidado",
        ]
        tiles = {
            Position(x, y): Tile(
                position=Position(x, y),
                terrain_name=self.rng.choice(terrain_names),
            )
            for y in range(self.height)
            for x in range(self.width)
        }
        for position, tile in tiles.items():
            if position == self.start_position:
                tile.explored = True
                continue
            if position == self.boss_position:
                continue
            roll = self.rng.random()
            if roll < 0.48:
                tile.enemy = self._create_enemy()
            elif roll < 0.85:
                tile.item = self._create_item()
        self._configure_special_tiles(tiles)
        return tiles

    def _create_enemy(self) -> Enemy:
        blueprints = [
            EnemyBlueprint(
                name="Lobo sombrío",
                health=24,
                attack=9,
                defense=3,
                enemy_type=EnemyType.TERRESTRE,
                experience=35,
                gold=18,
            ),
            EnemyBlueprint(
                name="Jabalí furioso",
                health=30,
                attack=10,
                defense=4,
                enemy_type=EnemyType.TERRESTRE,
                experience=40,
                gold=20,
            ),
            EnemyBlueprint(
                name="Harpía del dosel",
                health=22,
                attack=11,
                defense=2,
                enemy_type=EnemyType.VOLADOR,
                experience=42,
                gold=24,
            ),
        ]
        blueprint = self.rng.choice(blueprints)
        return Enemy(
            name=blueprint.name,
            max_health=blueprint.health + self.enemy_health_bonus,
            current_health=blueprint.health + self.enemy_health_bonus,
            base_attack=blueprint.attack + self.enemy_attack_bonus,
            base_defense=blueprint.defense,
            enemy_type=blueprint.enemy_type,
            reward_experience=blueprint.experience,
            reward_gold=blueprint.gold,
        )

    def _create_boss(self) -> Enemy:
        base_health = 58 + (self.enemy_health_bonus * 2)
        base_attack = 15 + self.enemy_attack_bonus
        return Enemy(
            name="Bestia Alfa del Dosel",
            max_health=base_health,
            current_health=base_health,
            base_attack=base_attack,
            base_defense=6,
            enemy_type=EnemyType.VOLADOR,
            reward_experience=120,
            reward_gold=90,
            is_boss=True,
        )

    def _create_item(self) -> Treasure | Trap | Weapon | Armor:
        item_factories: tuple[Callable[[], Treasure | Trap | Weapon | Armor], ...] = (
            lambda: Treasure(name="Colmillo raro", value=20),
            lambda: Treasure(name="Amuleto del bosque", value=35),
            lambda: Trap(
                name="Trampa de raíces",
                value=15,
                explosion_range=1,
                explosion_damage=16,
            ),
            lambda: Weapon(name="Lanza del rastreador", value=60, attack_bonus=4),
            lambda: Armor(name="Capa reforzada", value=55, defense_bonus=3),
        )
        return self.rng.choice(item_factories)()

    def _configure_special_tiles(self, tiles: dict[Position, Tile]) -> None:
        start_tile = tiles[self.start_position]
        start_tile.terrain_name = "Campamento del gremio"
        start_tile.zone_type = ZoneType.CAMPAMENTO
        start_tile.rest_available = True
        start_tile.shop_inventory = self._create_shop_inventory()
        start_tile.enemy = None
        start_tile.item = None

        outpost_candidates = [
            position
            for position in tiles
            if position not in {self.start_position, self.boss_position}
        ]
        outpost_position = self.rng.choice(outpost_candidates)
        outpost_tile = tiles[outpost_position]
        outpost_tile.terrain_name = "Puesto del guardabosques"
        outpost_tile.zone_type = ZoneType.PUESTO
        outpost_tile.rest_available = True
        outpost_tile.shop_inventory = self._create_shop_inventory()
        outpost_tile.enemy = None
        outpost_tile.item = None

        boss_tile = tiles[self.boss_position]
        boss_tile.terrain_name = "Guarida de la bestia alfa"
        boss_tile.zone_type = ZoneType.GUARIDA
        boss_tile.rest_available = False
        boss_tile.shop_inventory = []
        boss_tile.item = None
        boss_tile.enemy = self._create_boss()

    def _create_shop_inventory(self) -> list[Item]:
        return [
            Weapon(name="Arco de fresno", value=75, attack_bonus=5),
            Weapon(name="Lanza pesada", value=95, attack_bonus=7),
            Armor(name="Armadura de cuero", value=70, defense_bonus=4),
            Armor(name="Manto del veterano", value=92, defense_bonus=6),
            Trap(name="Carga de pólvora", value=40, explosion_range=2, explosion_damage=24),
        ]

    def tile_at(self, position: Position) -> Tile:
        return self.tiles[position]

    def boss_tile(self) -> Tile:
        return self.tiles[self.boss_position]

    def can_move(self, position: Position, direction: Direction) -> bool:
        target = self.move(position, direction)
        return 0 <= target.x < self.width and 0 <= target.y < self.height

    def move(self, position: Position, direction: Direction) -> Position:
        offsets = {
            Direction.NORTE: (0, -1),
            Direction.SUR: (0, 1),
            Direction.ESTE: (1, 0),
            Direction.OESTE: (-1, 0),
        }
        dx, dy = offsets[direction]
        return Position(position.x + dx, position.y + dy)

    def exploration_progress(self) -> tuple[int, int]:
        explored_tiles = sum(tile.explored for tile in self.tiles.values())
        return explored_tiles, len(self.tiles)
