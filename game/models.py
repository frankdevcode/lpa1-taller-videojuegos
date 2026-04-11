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

    def buy_price(self) -> int:
        return self.value

    def sell_price(self) -> int:
        return max(1, self.value // 2)


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
class HealingItem(Item):
    heal_amount: int


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

    def heal(self, amount: int) -> int:
        if amount <= 0:
            return 0
        missing = self.max_health - self.current_health
        applied = min(missing, amount)
        self.current_health += applied
        return applied

    def prepare_guard(self) -> None:
        self.guard_bonus = max(2, self.base_defense // 2)

    def reset_guard(self) -> None:
        self.guard_bonus = 0

    def health_ratio(self) -> float:
        if self.max_health == 0:
            return 0.0
        return self.current_health / self.max_health


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

    def weapons(self) -> list[Weapon]:
        return [item for item in self.inventory if isinstance(item, Weapon)]

    def armors(self) -> list[Armor]:
        return [item for item in self.inventory if isinstance(item, Armor)]

    def treasures(self) -> list[Treasure]:
        return [item for item in self.inventory if isinstance(item, Treasure)]

    def equip_weapon(self, weapon: Weapon) -> str:
        if weapon not in self.inventory:
            return "No puedes equipar un arma que no está en tu inventario."
        self.equipped_weapon = weapon
        return f"Equipada arma {weapon.name} (+{weapon.attack_bonus} ATQ)."

    def equip_armor(self, armor: Armor) -> str:
        if armor not in self.inventory:
            return "No puedes equipar una defensa que no está en tu inventario."
        self.equipped_armor = armor
        return f"Equipada defensa {armor.name} (+{armor.defense_bonus} DEF)."

    def sell_item(self, item: Item) -> int:
        self.inventory.remove(item)
        if self.equipped_weapon is item:
            self.equipped_weapon = None
        if self.equipped_armor is item:
            self.equipped_armor = None
        sale_price = item.sell_price()
        self.gold += sale_price
        return sale_price

    def trap_count(self) -> int:
        return sum(isinstance(item, Trap) for item in self.inventory)

    def use_trap(self) -> Trap | None:
        for index, item in enumerate(self.inventory):
            if isinstance(item, Trap):
                trap = item
                self.inventory.pop(index)
                return trap
        return None

    def healing_item_count(self) -> int:
        return sum(isinstance(item, HealingItem) for item in self.inventory)

    def use_healing_item(self) -> HealingItem | None:
        for index, item in enumerate(self.inventory):
            if isinstance(item, HealingItem):
                healing_item = item
                self.inventory.pop(index)
                return healing_item
        return None


@dataclass(slots=True)
class Enemy(Character):
    enemy_type: EnemyType = EnemyType.TERRESTRE
    reward_experience: int = 0
    reward_gold: int = 0
    is_boss: bool = False


def calculate_damage(attacker: Character, defender: Character) -> int:
    return max(1, attacker.total_attack() - defender.total_defense())


def calculate_enemy_damage(attacker: Enemy, defender: Character) -> tuple[int, str]:
    attack_power = attacker.total_attack()
    defense_power = defender.total_defense()
    action_text = "contraataca"

    if attacker.is_boss:
        attack_power += 2
        action_text = "golpea con una fuerza ancestral"
        if attacker.health_ratio() <= 0.5:
            attack_power += 3
            defense_power = max(0, defense_power - 1)
            action_text = "desata una furia ancestral"
    elif attacker.enemy_type is EnemyType.VOLADOR:
        defense_power = max(0, defense_power - 2)
        action_text = "se lanza en picada"
    elif attacker.health_ratio() <= 0.5:
        attack_power += 2
        action_text = "embiste con ferocidad"

    return max(1, attack_power - defense_power), action_text
