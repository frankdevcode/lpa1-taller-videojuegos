from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .models import (
    Armor,
    Direction,
    Enemy,
    Hunter,
    Item,
    Position,
    Trap,
    Weapon,
    calculate_damage,
    calculate_enemy_damage,
)
from .world import ForestMap, Tile, ZoneType

SelectableItem = TypeVar("SelectableItem", bound=Item)


class Difficulty(StrEnum):
    EXPLORADOR = "explorador"
    CAZADOR = "cazador"
    LEYENDA = "leyenda"


@dataclass(frozen=True, slots=True)
class DifficultyConfig:
    label: str
    enemy_health_bonus: int
    enemy_attack_bonus: int
    starting_gold: int


DIFFICULTY_CONFIG = {
    Difficulty.EXPLORADOR: DifficultyConfig(
        label="Explorador",
        enemy_health_bonus=0,
        enemy_attack_bonus=0,
        starting_gold=30,
    ),
    Difficulty.CAZADOR: DifficultyConfig(
        label="Cazador",
        enemy_health_bonus=4,
        enemy_attack_bonus=1,
        starting_gold=20,
    ),
    Difficulty.LEYENDA: DifficultyConfig(
        label="Leyenda",
        enemy_health_bonus=8,
        enemy_attack_bonus=3,
        starting_gold=10,
    ),
}


@dataclass(slots=True)
class GameSession:
    hunter: Hunter
    world: ForestMap
    position: Position
    difficulty: Difficulty
    boss_unlocked: bool = False
    enemies_defeated: int = 0
    discovered_treasures: int = 0
    event_log: list[str] = field(default_factory=list)
    game_over: bool = False
    victory: bool = False

    def log(self, message: str) -> None:
        self.event_log.append(message)
        self.event_log = self.event_log[-8:]


class BeastHunterApp:
    def __init__(self, difficulty: Difficulty = Difficulty.CAZADOR) -> None:
        self.console = Console()
        self.rng = random.Random()
        self.session = self._create_session(difficulty)

    def _create_session(self, difficulty: Difficulty) -> GameSession:
        config = DIFFICULTY_CONFIG[difficulty]
        hunter = Hunter(
            name="Aren, cazador del bosque",
            max_health=48,
            current_health=48,
            base_attack=11,
            base_defense=5,
            gold=config.starting_gold,
        )
        world = ForestMap(
            width=5,
            height=5,
            rng=self.rng,
            enemy_health_bonus=config.enemy_health_bonus,
            enemy_attack_bonus=config.enemy_attack_bonus,
        )
        session = GameSession(
            hunter=hunter,
            world=world,
            position=world.start_position,
            difficulty=difficulty,
        )
        session.log("Comienza la expedición en el corazón del bosque.")
        session.log("Tu misión inicial es sobrevivir, explorar y recolectar reliquias.")
        session.log(f"Dificultad activa: {config.label}.")
        session.log("Explora el bosque y prepárate para derrotar a la Bestia Alfa.")
        return session

    def run(self) -> None:
        self._render_intro()
        while not self.session.game_over:
            self._render()
            command = Prompt.ask(
                "Acción",
                choices=[
                    "n",
                    "s",
                    "e",
                    "o",
                    "atacar",
                    "defender",
                    "trampa",
                    "inventario",
                    "equipar",
                    "tienda",
                    "descansar",
                    "salir",
                ],
                default="n",
                show_choices=False,
            )
            self._handle_command(command)

        self._render()
        result_title = "Victoria" if self.session.victory else "Fin de la cacería"
        result_style = "bold green" if self.session.victory else "bold red"
        content = "\n".join(self.session.event_log[-4:])
        self.console.print(
            Panel(content, title=result_title, style=result_style)
        )

    def _render_intro(self) -> None:
        self.console.print(
            Panel.fit(
                "Cazador de Bestias del Bosque\n\n"
                "Vertical slice profesional del proyecto: "
                "exploración, combate, progresión y jefe final.\n"
                "Comandos: n, s, e, o, atacar, defender, trampa, inventario, "
                "equipar, tienda, descansar, salir",
                title="Inicio de Partida",
                border_style="green",
            )
        )

    def _render(self) -> None:
        self.console.clear()
        self.console.print(self._build_status_table())
        self.console.print(self._build_map_table())
        self.console.print(self._build_tile_panel())
        self.console.print(self._build_log_panel())

    def _build_status_table(self) -> Table:
        hunter = self.session.hunter
        explored, total = self.session.world.exploration_progress()
        table = Table(title="Estado del cazador", expand=True)
        table.add_column("Nombre")
        table.add_column("Vida")
        table.add_column("Ataque")
        table.add_column("Defensa")
        table.add_column("Nivel")
        table.add_column("XP")
        table.add_column("Oro")
        table.add_column("Exploración")
        table.add_column("Dificultad")
        table.add_column("Objetivo")
        table.add_row(
            hunter.name,
            f"{hunter.current_health}/{hunter.max_health}",
            str(hunter.total_attack()),
            str(hunter.total_defense()),
            str(hunter.level),
            str(hunter.experience),
            str(hunter.gold),
            f"{explored}/{total}",
            DIFFICULTY_CONFIG[self.session.difficulty].label,
            self._objective_status(),
        )
        return table

    def _build_map_table(self) -> Table:
        table = Table(title="Mapa del bosque", expand=False)
        for _ in range(self.session.world.width):
            table.add_column(justify="center", width=3)
        for y in range(self.session.world.height):
            row: list[str] = []
            for x in range(self.session.world.width):
                position = Position(x, y)
                tile = self.session.world.tile_at(position)
                if position == self.session.position:
                    row.append("🧙")
                elif not tile.explored:
                    row.append("·")
                elif tile.zone_type is ZoneType.GUARIDA and tile.enemy and tile.enemy.is_alive():
                    row.append("♛")
                elif tile.shop_inventory or tile.rest_available:
                    row.append("⌂")
                elif tile.enemy and tile.enemy.is_alive():
                    row.append("⚔")
                elif tile.item:
                    row.append("✦")
                else:
                    row.append("✓")
            table.add_row(*row)
        return table

    def _build_tile_panel(self) -> Panel:
        tile = self.session.world.tile_at(self.session.position)
        lines = [f"Zona actual: {tile.terrain_name}", f"Tipo de zona: {tile.zone_type.value}"]
        if tile.zone_type is ZoneType.GUARIDA and not self.session.boss_unlocked:
            lines.append("Una barrera ancestral impide retar a la Bestia Alfa.")
        elif tile.enemy and tile.enemy.is_alive():
            lines.append(
                f"Enemigo: {tile.enemy.name} ({tile.enemy.enemy_type.value}) "
                f"{tile.enemy.current_health}/{tile.enemy.max_health} PV"
            )
        elif tile.item:
            lines.append(f"Objeto detectado: {tile.item.name}")
        else:
            lines.append("La zona está despejada.")
        if tile.rest_available:
            lines.append("Descanso disponible.")
        if tile.shop_inventory:
            lines.append(f"Tienda disponible con {len(tile.shop_inventory)} artículos.")
        return Panel("\n".join(lines), title="Entorno", border_style="cyan")

    def _build_log_panel(self) -> Panel:
        content = "\n".join(self.session.event_log[-6:]) or "Sin eventos todavía."
        return Panel(content, title="Registro", border_style="yellow")

    def _handle_command(self, command: str) -> None:
        actions = {
            "n": lambda: self._move(Direction.NORTE),
            "s": lambda: self._move(Direction.SUR),
            "e": lambda: self._move(Direction.ESTE),
            "o": lambda: self._move(Direction.OESTE),
            "atacar": self._attack,
            "defender": self._defend,
            "trampa": self._use_trap,
            "inventario": self._show_inventory,
            "equipar": self._manage_equipment,
            "tienda": self._open_shop,
            "descansar": self._rest,
            "salir": self._quit_game,
        }
        action = actions[command]
        action()
        self._refresh_boss_unlock()
        self._check_victory()

    def _move(self, direction: Direction) -> None:
        if not self.session.world.can_move(self.session.position, direction):
            self.session.log("No puedes avanzar en esa dirección.")
            return
        self.session.position = self.session.world.move(self.session.position, direction)
        tile = self.session.world.tile_at(self.session.position)
        if not tile.explored:
            tile.explored = True
            self.session.log(f"Descubres {tile.terrain_name}.")
        else:
            self.session.log(f"Regresas a {tile.terrain_name}.")
        self._resolve_tile(tile)

    def _resolve_tile(self, tile: Tile) -> None:
        if tile.zone_type is ZoneType.CAMPAMENTO:
            self.session.log("Llegas al campamento del gremio. Puedes comerciar y descansar.")
        elif tile.zone_type is ZoneType.PUESTO:
            self.session.log("Encuentras un puesto avanzado seguro entre la maleza.")
        elif tile.zone_type is ZoneType.GUARIDA:
            if self.session.boss_unlocked:
                self.session.log("La guarida vibra. La Bestia Alfa te espera.")
            else:
                self.session.log(
                    "La guarida permanece sellada. Debes explorar más y alcanzar nivel 3."
                )
        if tile.item is not None:
            found_item = tile.item
            tile.item = None
            self.session.hunter.add_item(found_item)
            self.session.log(f"Recoges {found_item.name}.")
            self._process_loot(found_item)
        if tile.enemy and tile.enemy.is_alive():
            self.session.log(f"Te enfrentas a {tile.enemy.name}.")

    def _process_loot(self, item: Item) -> None:
        if isinstance(item, Trap):
            self.session.log(
                f"Trampa almacenada: alcance {item.explosion_range}, daño {item.explosion_damage}."
            )
            return
        if isinstance(item, Weapon):
            self.session.log(
                f"Nueva arma en inventario: {item.name}. Usa equipar para cambiar tu arma."
            )
            return
        if isinstance(item, Armor):
            self.session.log(
                f"Nueva defensa en inventario: {item.name}. Usa equipar para mejorar tu defensa."
            )
            return
        self.session.discovered_treasures += 1
        self.session.log(
            f"Guardas {item.name} en el inventario. "
            f"Valor de venta estimado: {item.sell_price()} monedas."
        )

    def _attack(self) -> None:
        tile = self.session.world.tile_at(self.session.position)
        enemy = tile.enemy
        if tile.zone_type is ZoneType.GUARIDA and not self.session.boss_unlocked:
            self.session.log("La barrera ancestral rechaza tu ataque.")
            return
        if enemy is None or not enemy.is_alive():
            self.session.log("No hay ningún enemigo que atacar aquí.")
            return

        hunter_damage = calculate_damage(self.session.hunter, enemy)
        applied_to_enemy = enemy.receive_damage(hunter_damage)
        self.session.log(f"Golpeas a {enemy.name} e infliges {applied_to_enemy} de daño.")
        self.session.hunter.reset_guard()

        if not enemy.is_alive():
            self._resolve_enemy_defeat(enemy)
            return

        self._enemy_turn(enemy)

    def _defend(self) -> None:
        tile = self.session.world.tile_at(self.session.position)
        enemy = tile.enemy
        self.session.hunter.prepare_guard()
        self.session.log("Adoptas una postura defensiva.")
        if enemy and enemy.is_alive():
            self._enemy_turn(enemy)
        else:
            self.session.log("No hay amenazas inmediatas, pero te mantienes alerta.")
            self.session.hunter.reset_guard()

    def _use_trap(self) -> None:
        tile = self.session.world.tile_at(self.session.position)
        enemy = tile.enemy
        if tile.zone_type is ZoneType.GUARIDA and not self.session.boss_unlocked:
            self.session.log("La barrera ancestral consume la explosión antes de llegar al jefe.")
            return
        if enemy is None or not enemy.is_alive():
            self.session.log("No hay objetivo para usar una trampa.")
            return
        trap = self.session.hunter.use_trap()
        if trap is None:
            self.session.log("No tienes trampas disponibles.")
            return
        applied_damage = enemy.receive_damage(trap.explosion_damage)
        self.session.log(f"Activaste {trap.name} e infligiste {applied_damage} de daño explosivo.")
        if enemy.is_alive():
            self._enemy_turn(enemy)
            return
        self.session.log(f"La explosión elimina a {enemy.name}.")
        self._resolve_enemy_defeat(enemy)

    def _enemy_turn(self, enemy: Enemy) -> None:
        enemy_damage, action_text = calculate_enemy_damage(enemy, self.session.hunter)
        applied_to_hunter = self.session.hunter.receive_damage(enemy_damage)
        self.session.log(f"{enemy.name} {action_text} y te causa {applied_to_hunter} de daño.")
        self.session.hunter.reset_guard()
        if not self.session.hunter.is_alive():
            self.session.game_over = True
            self.session.victory = False
            self.session.log("Has caído durante la expedición.")

    def _show_inventory(self) -> None:
        inventory = self.session.hunter.inventory
        if not inventory:
            self.session.log("Tu inventario está vacío.")
            return
        grouped_items: dict[str, int] = {}
        for item in inventory:
            label = item.name
            is_equipped = (
                self.session.hunter.equipped_weapon is item
                or self.session.hunter.equipped_armor is item
            )
            if is_equipped:
                label = f"{label} (equipado)"
            grouped_items[label] = grouped_items.get(label, 0) + 1
        summary = ", ".join(f"{name} x{count}" for name, count in grouped_items.items())
        self.session.log(f"Inventario: {summary}.")

    def _manage_equipment(self) -> None:
        hunter = self.session.hunter
        choice = Prompt.ask(
            "¿Qué deseas equipar?",
            choices=["arma", "armadura", "salir"],
            default="salir",
            show_choices=False,
        )
        if choice == "salir":
            self.session.log("Mantienes el equipamiento actual.")
            return
        if choice == "arma":
            weapons = hunter.weapons()
            if not weapons:
                self.session.log("No tienes armas en el inventario.")
                return
            self._print_item_selection("Armas disponibles", weapons)
            selected_weapon = self._prompt_item_selection(weapons)
            if selected_weapon is None:
                self.session.log("No cambiaste tu arma.")
                return
            self.session.log(hunter.equip_weapon(selected_weapon))
            return
        armors = hunter.armors()
        if not armors:
            self.session.log("No tienes defensas en el inventario.")
            return
        self._print_item_selection("Defensas disponibles", armors)
        selected_armor = self._prompt_item_selection(armors)
        if selected_armor is None:
            self.session.log("No cambiaste tu defensa.")
            return
        self.session.log(hunter.equip_armor(selected_armor))

    def _open_shop(self) -> None:
        tile = self.session.world.tile_at(self.session.position)
        if not tile.shop_inventory:
            self.session.log("No hay ninguna tienda en esta zona.")
            return
        self._print_item_selection("Tienda del bosque", tile.shop_inventory)
        action = Prompt.ask(
            "Operación de tienda",
            choices=["comprar", "vender", "salir"],
            default="salir",
            show_choices=False,
        )
        if action == "comprar":
            selected_item = self._prompt_item_selection(tile.shop_inventory)
            if selected_item is None:
                self.session.log("No realizaste ninguna compra.")
                return
            self._buy_item(tile, selected_item)
            return
        if action == "vender":
            self._sell_item()
            return
        self.session.log("Te retiras del puesto comercial.")

    def _buy_item(self, tile: Tile, item: Item) -> None:
        price = item.buy_price()
        if self.session.hunter.gold < price:
            self.session.log(f"No tienes suficiente oro para comprar {item.name}.")
            return
        self.session.hunter.gold -= price
        self.session.hunter.add_item(item)
        tile.shop_inventory.remove(item)
        self.session.log(f"Compraste {item.name} por {price} monedas.")
        if isinstance(item, Trap):
            self.session.log("La trampa quedó lista en tu inventario.")
        else:
            self.session.log("Usa equipar si deseas activar el nuevo equipo.")

    def _sell_item(self) -> None:
        inventory = self.session.hunter.inventory
        if not inventory:
            self.session.log("No tienes objetos para vender.")
            return
        self._print_item_selection("Inventario vendible", inventory, use_sell_price=True)
        selected_item = self._prompt_item_selection(inventory)
        if selected_item is None:
            self.session.log("No vendiste ningún objeto.")
            return
        sale_price = self.session.hunter.sell_item(selected_item)
        self.session.log(f"Vendiste {selected_item.name} por {sale_price} monedas.")

    def _rest(self) -> None:
        tile = self.session.world.tile_at(self.session.position)
        if not tile.rest_available:
            self.session.log("Este lugar no es seguro para descansar.")
            return
        hunter = self.session.hunter
        if hunter.current_health == hunter.max_health:
            self.session.log("Ya estás en plena forma.")
            return
        hunter.current_health = hunter.max_health
        self.session.log("Descansas junto al fuego y recuperas toda tu vitalidad.")

    def _objective_status(self) -> str:
        if self.session.victory:
            return "Bestia Alfa derrotada"
        if self.session.boss_unlocked:
            return "Derrota a la Bestia Alfa"
        return "Desbloquear guarida alfa"

    def _boss_unlock_requirements_met(self) -> bool:
        explored, total = self.session.world.exploration_progress()
        required_tiles = max(1, int(total * 0.6))
        return self.session.hunter.level >= 3 and explored >= required_tiles

    def _refresh_boss_unlock(self) -> None:
        if self.session.boss_unlocked or self.session.game_over:
            return
        if not self._boss_unlock_requirements_met():
            return
        self.session.boss_unlocked = True
        boss_tile = self.session.world.boss_tile()
        boss_tile.explored = True
        self.session.log("La barrera ancestral de la guarida alfa se ha disipado.")
        self.session.log("Ahora puedes desafiar a la Bestia Alfa en el extremo del bosque.")

    def _resolve_enemy_defeat(self, enemy: Enemy) -> None:
        self.session.enemies_defeated += 1
        self.session.hunter.gold += enemy.reward_gold
        for message in self.session.hunter.gain_experience(enemy.reward_experience):
            self.session.log(message)
        self.session.log(f"Derrotas a {enemy.name} y obtienes {enemy.reward_gold} monedas.")
        if enemy.is_boss:
            self.session.game_over = True
            self.session.victory = True
            self.session.log("La Bestia Alfa cae. El bosque vuelve a estar en calma.")

    def _print_item_selection(
        self,
        title: str,
        items: Sequence[Item],
        use_sell_price: bool = False,
    ) -> None:
        table = Table(title=title, expand=True)
        table.add_column("N°")
        table.add_column("Objeto")
        table.add_column("Tipo")
        table.add_column("Efecto")
        table.add_column("Precio")
        for index, item in enumerate(items, start=1):
            table.add_row(
                str(index),
                item.name,
                self._item_kind(item),
                self._item_effect(item),
                str(item.sell_price() if use_sell_price else item.buy_price()),
            )
        self.console.print(table)

    def _prompt_item_selection(
        self,
        items: Sequence[SelectableItem],
    ) -> SelectableItem | None:
        valid_choices = [str(index) for index in range(1, len(items) + 1)]
        valid_choices.append("salir")
        selected = Prompt.ask(
            "Selecciona un número",
            choices=valid_choices,
            default="salir",
            show_choices=False,
        )
        if selected == "salir":
            return None
        return items[int(selected) - 1]

    def _item_kind(self, item: Item) -> str:
        if isinstance(item, Weapon):
            return "Arma"
        if isinstance(item, Armor):
            return "Defensa"
        if isinstance(item, Trap):
            return "Trampa"
        return "Tesoro"

    def _item_effect(self, item: Item) -> str:
        if isinstance(item, Weapon):
            return f"+{item.attack_bonus} ATQ"
        if isinstance(item, Armor):
            return f"+{item.defense_bonus} DEF"
        if isinstance(item, Trap):
            return f"{item.explosion_damage} daño"
        return "Valor de venta"

    def _quit_game(self) -> None:
        self.session.game_over = True
        self.session.victory = False
        self.session.log("Abandonas temporalmente la expedición.")

    def _check_victory(self) -> None:
        if self.session.game_over:
            return
        if self.session.boss_unlocked:
            return
        if self._boss_unlock_requirements_met():
            self._refresh_boss_unlock()


def run() -> None:
    selected_difficulty = Prompt.ask(
        "Elige dificultad",
        choices=[difficulty.value for difficulty in Difficulty],
        default=Difficulty.CAZADOR.value,
        show_choices=False,
    )
    BeastHunterApp(difficulty=Difficulty(selected_difficulty)).run()
