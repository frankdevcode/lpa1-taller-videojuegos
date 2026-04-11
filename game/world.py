from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from .models import (
    Armor,
    Direction,
    Enemy,
    EnemyType,
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


@dataclass(slots=True)
class Tile:
    position: Position
    terrain_name: str
    explored: bool = False
    enemy: Enemy | None = None
    item: Treasure | Trap | Weapon | Armor | None = None


class ForestMap:
    def __init__(self, width: int, height: int, rng: random.Random) -> None:
        self.width = width
        self.height = height
        self.rng = rng
        self.start_position = Position(width // 2, height // 2)
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
            roll = self.rng.random()
            if roll < 0.48:
                tile.enemy = self._create_enemy()
            elif roll < 0.85:
                tile.item = self._create_item()
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
            max_health=blueprint.health,
            current_health=blueprint.health,
            base_attack=blueprint.attack,
            base_defense=blueprint.defense,
            enemy_type=blueprint.enemy_type,
            reward_experience=blueprint.experience,
            reward_gold=blueprint.gold,
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

    def tile_at(self, position: Position) -> Tile:
        return self.tiles[position]

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
