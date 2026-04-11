from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EnemyType(StrEnum):
    TERRESTRE = "terrestre"
    VOLADOR = "volador"


class Direction(StrEnum):
    NORTE = "norte"
    SUR = "sur"
    ESTE = "este"
    OESTE = "oeste"


@dataclass(frozen=True)
class Position:
    x: int
    y: int


@dataclass(slots=True)
class Item:
    name: str
    value: int


@dataclass(slots=True)
class Treasure(Item):
    pass


@dataclass(slots=True)
class Trap(Item):
    explosion_range: int
    explosion_damage: int


@dataclass(slots=True)
class Weapon(Item):
    attack_bonus: int


@dataclass(slots=True)
class Armor(Item):
    defense_bonus: int


@dataclass(slots=True)
class Character:
    name: str
    max_health: int
    current_health: int
    base_attack: int
    base_defense: int
    guard_bonus: int = 0

    def is_alive(self) -> bool:
        return self.current_health > 0

    def total_attack(self) -> int:
        return self.base_attack

    def total_defense(self) -> int:
        return self.base_defense + self.guard_bonus

    def receive_damage(self, damage: int) -> int:
        applied_damage = min(self.current_health, max(1, damage))
        self.current_health -= applied_damage
        return applied_damage

    def prepare_guard(self) -> None:
        self.guard_bonus = max(2, self.base_defense // 2)

    def reset_guard(self) -> None:
        self.guard_bonus = 0


@dataclass(slots=True)
class Hunter(Character):
    level: int = 1
    experience: int = 0
    gold: int = 0
    inventory: list[Item] = field(default_factory=list)
    equipped_weapon: Weapon | None = None
    equipped_armor: Armor | None = None

    def total_attack(self) -> int:
        attack_bonus = self.equipped_weapon.attack_bonus if self.equipped_weapon else 0
        return self.base_attack + attack_bonus

    def total_defense(self) -> int:
        armor_bonus = self.equipped_armor.defense_bonus if self.equipped_armor else 0
        return self.base_defense + armor_bonus + self.guard_bonus

    def gain_experience(self, amount: int) -> list[str]:
        messages = [f"Ganas {amount} de experiencia."]
        self.experience += amount
        while self.experience >= self.level * 100:
            self.experience -= self.level * 100
            self.level += 1
            self.max_health += 12
            self.base_attack += 3
            self.base_defense += 2
            self.current_health = self.max_health
            messages.append(f"Subes al nivel {self.level}. Tus estadísticas han mejorado.")
        return messages

    def add_item(self, item: Item) -> None:
        self.inventory.append(item)

    def auto_equip(self, item: Item) -> str | None:
        if isinstance(item, Weapon):
            should_equip = (
                self.equipped_weapon is None
                or item.attack_bonus > self.equipped_weapon.attack_bonus
            )
            if should_equip:
                self.equipped_weapon = item
                return f"Equipada arma {item.name} (+{item.attack_bonus} ATQ)."
        if isinstance(item, Armor):
            should_equip = (
                self.equipped_armor is None
                or item.defense_bonus > self.equipped_armor.defense_bonus
            )
            if should_equip:
                self.equipped_armor = item
                return f"Equipada defensa {item.name} (+{item.defense_bonus} DEF)."
        return None

    def trap_count(self) -> int:
        return sum(isinstance(item, Trap) for item in self.inventory)

    def use_trap(self) -> Trap | None:
        for index, item in enumerate(self.inventory):
            if isinstance(item, Trap):
                trap = item
                self.inventory.pop(index)
                return trap
        return None


@dataclass(slots=True)
class Enemy(Character):
    enemy_type: EnemyType = EnemyType.TERRESTRE
    reward_experience: int = 0
    reward_gold: int = 0


def calculate_damage(attacker: Character, defender: Character) -> int:
    return max(1, attacker.total_attack() - defender.total_defense())
