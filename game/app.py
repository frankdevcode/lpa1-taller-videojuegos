from __future__ import annotations

import json
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .models import (
    Armor,
    Direction,
    Enemy,
    EnemyType,
    HealingItem,
    Hunter,
    Item,
    Position,
    Trap,
    Treasure,
    Weapon,
    calculate_damage,
    calculate_enemy_damage,
)
from .world import ForestMap, Tile, ZoneType

SelectableItem = TypeVar("SelectableItem", bound=Item)
DEFAULT_SAVE_PATH = Path(__file__).resolve().parent.parent / "savegame.json"
SAVE_SLOT_COUNT = 3
DEFAULT_LEADERBOARD_PATH = Path(__file__).resolve().parent.parent / "leaderboard.json"


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
    reward_multiplier: float
    healing_multiplier: float
    boss_unlock_exploration_ratio: float
    boss_unlock_defeats_required: int
    score_victory_target: int


@dataclass(frozen=True, slots=True)
class Achievement:
    name: str
    score_bonus: int


@dataclass(frozen=True, slots=True)
class SaveSlotSummary:
    slot: int
    exists: bool
    label: str
    difficulty: str
    level: str
    score: str
    objective: str


DIFFICULTY_CONFIG = {
    Difficulty.EXPLORADOR: DifficultyConfig(
        label="Explorador",
        enemy_health_bonus=0,
        enemy_attack_bonus=0,
        starting_gold=30,
        reward_multiplier=1.0,
        healing_multiplier=1.0,
        boss_unlock_exploration_ratio=0.5,
        boss_unlock_defeats_required=1,
        score_victory_target=800,
    ),
    Difficulty.CAZADOR: DifficultyConfig(
        label="Cazador",
        enemy_health_bonus=4,
        enemy_attack_bonus=1,
        starting_gold=20,
        reward_multiplier=1.1,
        healing_multiplier=0.95,
        boss_unlock_exploration_ratio=0.6,
        boss_unlock_defeats_required=2,
        score_victory_target=900,
    ),
    Difficulty.LEYENDA: DifficultyConfig(
        label="Leyenda",
        enemy_health_bonus=8,
        enemy_attack_bonus=3,
        starting_gold=10,
        reward_multiplier=1.25,
        healing_multiplier=0.9,
        boss_unlock_exploration_ratio=0.7,
        boss_unlock_defeats_required=3,
        score_victory_target=1000,
    ),
}

ACHIEVEMENTS = {
    "first_blood": Achievement(name="Primera sangre", score_bonus=25),
    "veteran_hunter": Achievement(name="Cazador veterano", score_bonus=80),
    "forest_scavenger": Achievement(name="Recolector del bosque", score_bonus=45),
    "guild_merchant": Achievement(name="Mercader del gremio", score_bonus=35),
    "alpha_tracker": Achievement(name="Rastreador alfa", score_bonus=90),
    "forest_legend": Achievement(name="Leyenda del bosque", score_bonus=150),
}

HELP_TOPICS = {
    "movimiento": "Usa n, s, e y o para explorar el bosque casilla por casilla.",
    "combate": "Usa atacar para dañar, defender para resistir y trampa para castigar enemigos.",
    "progreso": (
        "Sube a nivel 3, derrota enemigos y explora suficiente bosque "
        "para abrir la guarida alfa."
    ),
    "comercio": (
        "Compra y vende en campamentos o puestos. "
        "Usa equipar para activar tu mejor equipo."
    ),
    "consumibles": "Usa usar para consumir tónicos de curación cuando sea necesario.",
    "persistencia": "Usa guardar para almacenar la partida y cargar para restaurarla más adelante.",
    "ranking": "Usa ranking para ver el top local de puntuaciones.",
    "entorno": "Si un camino está bloqueado, usa esquivar para atravesar obstáculos del bosque.",
}


@dataclass(slots=True)
class GameSession:
    hunter: Hunter
    world: ForestMap
    position: Position
    difficulty: Difficulty
    boss_unlocked: bool = False
    enemies_defeated: int = 0
    score: int = 0
    items_bought: int = 0
    items_sold: int = 0
    discovered_treasures: int = 0
    tutorial_completed: bool = False
    achievements: list[str] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)
    game_over: bool = False
    victory: bool = False

    def log(self, message: str) -> None:
        self.event_log.append(message)
        self.event_log = self.event_log[-8:]


class BeastHunterApp:
    def __init__(
        self,
        difficulty: Difficulty = Difficulty.CAZADOR,
        save_path: Path = DEFAULT_SAVE_PATH,
        active_slot: int | None = None,
        leaderboard_path: Path = DEFAULT_LEADERBOARD_PATH,
    ) -> None:
        self.console = Console()
        self.rng = random.Random()
        self.save_path = save_path
        self.active_slot = active_slot
        self.leaderboard_path = leaderboard_path
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
        session.log("Usa tutorial o ayuda para recibir orientación táctica.")
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
                    "usar",
                    "descansar",
                    "guardar",
                    "cargar",
                    "ranking",
                    "tutorial",
                    "ayuda",
                    "esquivar",
                    "salir",
                ],
                default="n",
                show_choices=False,
            )
            self._handle_command(command)

        self._render()
        result_title = "Victoria" if self.session.victory else "Fin de la cacería"
        result_style = "bold green" if self.session.victory else "bold red"
        achievements = ", ".join(self.session.achievements) or "Sin logros"
        content = "\n".join(
            [
                *self.session.event_log[-4:],
                f"Puntaje final: {self.session.score}",
                f"Logros: {achievements}",
            ]
        )
        self.console.print(
            Panel(content, title=result_title, style=result_style)
        )
        leaderboard = load_leaderboard(self.leaderboard_path)
        if leaderboard:
            self.console.print(build_leaderboard_table(leaderboard[:5]))

    def _render_intro(self) -> None:
        self.console.print(
            Panel.fit(
                "Cazador de Bestias del Bosque\n\n"
                "Vertical slice profesional del proyecto: "
                "exploración, combate, progresión y jefe final.\n"
                "Comandos: n, s, e, o, atacar, defender, trampa, inventario, "
                "equipar, tienda, usar, descansar, guardar, cargar, ranking, "
                "tutorial, ayuda, esquivar, salir",
                title="Inicio de Partida",
                border_style="green",
            )
        )

    def _render(self) -> None:
        self.console.clear()
        self.console.print(self._build_status_table())
        self.console.print(self._build_map_table())
        self.console.print(self._build_tile_panel())
        self.console.print(self._build_progress_panel())
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
        table.add_column("Puntaje")
        table.add_column("Exploración")
        table.add_column("Dificultad")
        table.add_column("Slot")
        table.add_column("Objetivo")
        table.add_row(
            hunter.name,
            f"{hunter.current_health}/{hunter.max_health}",
            str(hunter.total_attack()),
            str(hunter.total_defense()),
            str(hunter.level),
            str(hunter.experience),
            str(hunter.gold),
            str(self.session.score),
            f"{explored}/{total}",
            DIFFICULTY_CONFIG[self.session.difficulty].label,
            self._slot_label(),
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
                elif tile.obstacle:
                    row.append("🌲")
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
        elif tile.obstacle:
            lines.append(f"Obstáculo: {tile.obstacle_name}.")
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
        lines.append(f"Consejo: {self._context_hint()}")
        return Panel("\n".join(lines), title="Entorno", border_style="cyan")

    def _build_progress_panel(self) -> Panel:
        achievements = self.session.achievements[-3:] or ["Sin logros desbloqueados todavía."]
        lines = [
            f"Enemigos derrotados: {self.session.enemies_defeated}",
            f"Tesoros descubiertos: {self.session.discovered_treasures}",
            f"Compras/Ventas: {self.session.items_bought}/{self.session.items_sold}",
            f"Logros: {len(self.session.achievements)}",
            f"Tutorial completado: {'sí' if self.session.tutorial_completed else 'no'}",
            f"Últimos logros: {' | '.join(achievements)}",
        ]
        return Panel("\n".join(lines), title="Progreso", border_style="magenta")

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
            "usar": self._use_healing_item,
            "descansar": self._rest,
            "guardar": self._save_game,
            "cargar": self.load_game,
            "ranking": self._show_leaderboard,
            "tutorial": self._run_tutorial,
            "ayuda": self._show_help,
            "esquivar": self._dodge_prompt,
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
        target_position = self.session.world.move(self.session.position, direction)
        tile = self.session.world.tile_at(target_position)
        if tile.obstacle:
            self.session.log(f"Un obstáculo bloquea el paso: {tile.obstacle_name}.")
            self.session.log("Usa esquivar para intentar atravesarlo.")
            return
        self.session.position = target_position
        if not tile.explored:
            tile.explored = True
            self._award_score(10, f"Exploras {tile.terrain_name}.")
            self.session.log(f"Descubres {tile.terrain_name}.")
        else:
            self.session.log(f"Regresas a {tile.terrain_name}.")
        self._resolve_tile(tile)

    def _dodge_prompt(self) -> None:
        direction_value = Prompt.ask(
            "¿En qué dirección esquivas?",
            choices=["n", "s", "e", "o", "salir"],
            default="salir",
            show_choices=False,
        )
        if direction_value == "salir":
            self.session.log("Decides no arriesgarte a esquivar.")
            return
        direction = {
            "n": Direction.NORTE,
            "s": Direction.SUR,
            "e": Direction.ESTE,
            "o": Direction.OESTE,
        }[direction_value]
        self._dodge(direction)

    def _dodge(self, direction: Direction) -> None:
        if not self.session.world.can_move(self.session.position, direction):
            self.session.log("No puedes esquivar en esa dirección.")
            return
        target_position = self.session.world.move(self.session.position, direction)
        tile = self.session.world.tile_at(target_position)
        if not tile.obstacle:
            self.session.log("No hay ningún obstáculo que esquivar en esa dirección.")
            return
        chance = min(0.9, 0.55 + (self.session.hunter.level - 1) * 0.05)
        roll = self.rng.random()
        if roll > chance:
            damage = 3
            applied_damage = self.session.hunter.receive_damage(damage)
            self.session.log("Intentas esquivar, pero fallas entre la maleza.")
            self.session.log(f"Recibes {applied_damage} de daño al golpearte con el obstáculo.")
            if not self.session.hunter.is_alive():
                self.session.game_over = True
                self.session.victory = False
                self.session.log("Has caído durante la expedición.")
                self._finalize_run()
            return
        tile.obstacle = False
        tile.obstacle_name = ""
        self.session.log("Esquivas con éxito y despejas el camino.")
        self.session.position = target_position
        if not tile.explored:
            tile.explored = True
            self._award_score(10, f"Exploras {tile.terrain_name}.")
            self.session.log(f"Descubres {tile.terrain_name}.")
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
            self._award_score(10, f"Recolectas {item.name}.")
            self.session.log(
                f"Trampa almacenada: alcance {item.explosion_range}, daño {item.explosion_damage}."
            )
            return
        if isinstance(item, Weapon):
            self._award_score(15, f"Aseguras el arma {item.name}.")
            self.session.log(
                f"Nueva arma en inventario: {item.name}. Usa equipar para cambiar tu arma."
            )
            return
        if isinstance(item, Armor):
            self._award_score(15, f"Aseguras la defensa {item.name}.")
            self.session.log(
                f"Nueva defensa en inventario: {item.name}. Usa equipar para mejorar tu defensa."
            )
            return
        if isinstance(item, HealingItem):
            self._award_score(10, f"Aseguras {item.name}.")
            self.session.log(
                f"Consumible de curación listo: {item.name}. "
                f"Restaura {item.heal_amount} PV al usar."
            )
            return
        self.session.discovered_treasures += 1
        self._award_score(item.value, f"Catalogas el tesoro {item.name}.")
        self._evaluate_achievements()
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
        if self.rng.random() < 0.1:
            hunter_damage *= 2
            self.session.log("Golpe crítico.")
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

    def _use_healing_item(self) -> None:
        hunter = self.session.hunter
        healing_item = hunter.use_healing_item()
        if healing_item is None:
            self.session.log("No tienes consumibles de curación disponibles.")
            return
        config = DIFFICULTY_CONFIG[self.session.difficulty]
        heal_amount = max(1, round(healing_item.heal_amount * config.healing_multiplier))
        recovered = hunter.heal(heal_amount)
        if recovered == 0:
            self.session.log("Ya estás en plena forma. Guardas el consumible para más adelante.")
            hunter.add_item(healing_item)
            return
        self._award_score(8, f"Te curas con {healing_item.name}.")
        self.session.log(f"Recuperas {recovered} PV.")

    def _enemy_turn(self, enemy: Enemy) -> None:
        enemy_damage, action_text = calculate_enemy_damage(enemy, self.session.hunter)
        applied_to_hunter = self.session.hunter.receive_damage(enemy_damage)
        self.session.log(f"{enemy.name} {action_text} y te causa {applied_to_hunter} de daño.")
        self.session.hunter.reset_guard()
        if not self.session.hunter.is_alive():
            self.session.game_over = True
            self.session.victory = False
            self.session.log("Has caído durante la expedición.")
            self._finalize_run()

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
        self.session.items_bought += 1
        self._award_score(10, f"Inviertes en {item.name}.")
        self._evaluate_achievements()
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
        self.session.items_sold += 1
        self._award_score(sale_price, f"Comercializas {selected_item.name}.")
        self._evaluate_achievements()
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
        self._award_score(5, "Descansas y recuperas energías.")
        self.session.log("Descansas junto al fuego y recuperas toda tu vitalidad.")

    def _run_tutorial(self) -> None:
        steps = [
            "Explora con n, s, e y o para descubrir zonas, tesoros y amenazas.",
            "Cuando encuentres enemigos, alterna atacar, defender y trampa según la situación.",
            "Visita campamentos y puestos para comprar, vender, equipar y descansar.",
            "Sube a nivel 3 y explora suficiente bosque para desbloquear la guarida alfa.",
            "Usa guardar y cargar para administrar sesiones largas con seguridad.",
        ]
        self.console.print(
            Panel(
                "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1)),
                title="Tutorial del cazador",
                border_style="blue",
            )
        )
        if not self.session.tutorial_completed:
            self.session.tutorial_completed = True
            self._award_score(20, "Completas el tutorial del gremio.")
        self.session.log("Tutorial revisado. Ya conoces el flujo principal de la expedición.")

    def _show_help(self) -> None:
        table = Table(title="Ayuda contextual", expand=True)
        table.add_column("Tema")
        table.add_column("Detalle")
        for topic, detail in HELP_TOPICS.items():
            table.add_row(topic.capitalize(), detail)
        self.console.print(table)
        self.session.log(f"Ayuda táctica: {self._context_hint()}")

    def _show_leaderboard(self) -> None:
        leaderboard = load_leaderboard(self.leaderboard_path)
        if not leaderboard:
            self.session.log("Todavía no hay registros en el ranking local.")
            return
        view = Prompt.ask(
            "Vista de ranking",
            choices=["general", "victorias", "derrotas", "dificultad"],
            default="general",
            show_choices=False,
        )
        entries = leaderboard
        title = "Ranking local - Top 10"
        if view == "victorias":
            entries = [entry for entry in leaderboard if bool(entry.get("victory", False))]
            title = "Ranking - Victorias"
        elif view == "derrotas":
            entries = [entry for entry in leaderboard if not bool(entry.get("victory", False))]
            title = "Ranking - Derrotas"
        elif view == "dificultad":
            difficulty = self.session.difficulty.value
            entries = [
                entry
                for entry in leaderboard
                if str(entry.get("difficulty", "")) == difficulty
            ]
            title = f"Ranking - {difficulty.capitalize()}"
        self.console.print(build_leaderboard_table(entries[:10], title=title))
        self.session.log(f"Ranking mostrado: {view}.")

    def _context_hint(self) -> str:
        tile = self.session.world.tile_at(self.session.position)
        hunter = self.session.hunter
        if tile.zone_type is ZoneType.GUARIDA and not self.session.boss_unlocked:
            return "Necesitas nivel 3 y suficiente exploración para romper el sello alfa."
        if tile.enemy and tile.enemy.is_alive():
            if hunter.trap_count() > 0:
                return "Tienes trampas listas; son ideales para abrir el combate."
            if hunter.current_health <= max(12, hunter.max_health // 3):
                if hunter.healing_item_count() > 0:
                    return (
                        "Tu vida es baja; usa un tónico de curación "
                        "o retrocede a una zona segura."
                    )
                return "Tu vida es baja; considera defender o retroceder a una zona segura."
            return "Ataca para tomar la iniciativa o defiende si el enemigo te supera."
        if tile.rest_available and hunter.current_health < hunter.max_health:
            return "Descansar aquí restaurará toda tu vitalidad."
        if tile.item:
            return "Recoge el objeto para mejorar tu economía o tu equipamiento."
        if tile.shop_inventory:
            return "Revisa la tienda para invertir tu oro en ventaja táctica."
        if not self.session.tutorial_completed:
            return "Usa tutorial para una guía rápida del flujo completo del juego."
        if not self.session.boss_unlocked:
            return "Sigue explorando y subiendo nivel para abrir la guarida alfa."
        return "Tu siguiente meta es derrotar a la Bestia Alfa."

    def _objective_status(self) -> str:
        config = DIFFICULTY_CONFIG[self.session.difficulty]
        explored, total = self.session.world.exploration_progress()
        score_target = config.score_victory_target
        if self.session.game_over and self.session.victory:
            return "Victoria"
        if self.session.boss_unlocked:
            return f"Jefe final | {self.session.score}/{score_target}"
        return f"Explora {explored}/{total} | {self.session.score}/{score_target}"

    def _boss_unlock_requirements_met(self) -> bool:
        config = DIFFICULTY_CONFIG[self.session.difficulty]
        explored, total = self.session.world.exploration_progress()
        required_tiles = max(1, int(total * config.boss_unlock_exploration_ratio))
        required_defeats = config.boss_unlock_defeats_required
        return (
            self.session.hunter.level >= 3
            and explored >= required_tiles
            and self.session.enemies_defeated >= required_defeats
        )

    def _refresh_boss_unlock(self) -> None:
        if self.session.boss_unlocked or self.session.game_over:
            return
        if not self._boss_unlock_requirements_met():
            return
        self.session.boss_unlocked = True
        boss_tile = self.session.world.boss_tile()
        boss_tile.explored = True
        self._unlock_achievement("alpha_tracker")
        self.session.log("La barrera ancestral de la guarida alfa se ha disipado.")
        self.session.log("Ahora puedes desafiar a la Bestia Alfa en el extremo del bosque.")

    def _resolve_enemy_defeat(self, enemy: Enemy) -> None:
        self.session.enemies_defeated += 1
        config = DIFFICULTY_CONFIG[self.session.difficulty]
        reward_experience = max(1, round(enemy.reward_experience * config.reward_multiplier))
        reward_gold = max(1, round(enemy.reward_gold * config.reward_multiplier))
        reward_score = reward_experience + reward_gold
        self._award_score(reward_score, f"Vences a {enemy.name}.")
        self.session.hunter.gold += reward_gold
        for message in self.session.hunter.gain_experience(reward_experience):
            self.session.log(message)
        self._evaluate_achievements()
        self.session.log(f"Derrotas a {enemy.name} y obtienes {reward_gold} monedas.")
        if enemy.is_boss:
            self._unlock_achievement("forest_legend")
            self.session.game_over = True
            self.session.victory = True
            self.session.log("La Bestia Alfa cae. El bosque vuelve a estar en calma.")
            self._finalize_run()

    def _award_score(self, amount: int, reason: str) -> None:
        self.session.score += amount
        self.session.log(f"+{amount} puntaje: {reason}")

    def _unlock_achievement(self, key: str) -> None:
        achievement = ACHIEVEMENTS[key]
        if achievement.name in self.session.achievements:
            return
        self.session.achievements.append(achievement.name)
        self.session.score += achievement.score_bonus
        self.session.log(f"Logro desbloqueado: {achievement.name}.")
        self.session.log(f"+{achievement.score_bonus} puntaje por logro.")

    def _evaluate_achievements(self) -> None:
        if self.session.enemies_defeated >= 1:
            self._unlock_achievement("first_blood")
        if self.session.enemies_defeated >= 5:
            self._unlock_achievement("veteran_hunter")
        if self.session.discovered_treasures >= 3:
            self._unlock_achievement("forest_scavenger")
        if self.session.items_bought >= 1 and self.session.items_sold >= 1:
            self._unlock_achievement("guild_merchant")

    def _finalize_run(self) -> None:
        entry = {
            "name": self.session.hunter.name,
            "difficulty": self.session.difficulty.value,
            "level": self.session.hunter.level,
            "score": self.session.score,
            "enemies_defeated": self.session.enemies_defeated,
            "treasures": self.session.discovered_treasures,
            "victory": self.session.victory,
        }
        leaderboard = load_leaderboard(self.leaderboard_path)
        leaderboard.append(entry)
        leaderboard.sort(
            key=lambda e: (
                int(e.get("score", 0)),
                int(e.get("level", 0)),
            ),
            reverse=True,
        )
        leaderboard = leaderboard[:10]
        save_leaderboard(self.leaderboard_path, leaderboard)

    def save_game(self) -> None:
        payload = self._serialize_session()
        self.save_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.session.log(f"Partida guardada en {self._slot_label()}.")

    def _save_game(self) -> None:
        slot = self._prompt_slot_selection("Selecciona slot para guardar")
        if slot is None:
            self.session.log("Guardado cancelado.")
            return
        self.save_to_slot(slot)

    def load_game(self) -> None:
        slot = self._prompt_slot_selection("Selecciona slot para cargar", existing_only=True)
        if slot is None:
            self.session.log("Carga cancelada.")
            return
        self._set_active_slot(slot)
        if not self.save_path.exists():
            self.session.log("No existe una partida guardada disponible en ese slot.")
            return
        data = json.loads(self.save_path.read_text(encoding="utf-8"))
        self.session = self._deserialize_session(data)
        self.session.log(f"Partida cargada desde {self._slot_label()}.")

    def load_saved_game(self) -> bool:
        if not self.save_path.exists():
            return False
        data = json.loads(self.save_path.read_text(encoding="utf-8"))
        self.session = self._deserialize_session(data)
        self.session.log(f"Partida cargada desde {self._slot_label()}.")
        return True

    def save_to_slot(self, slot: int) -> None:
        self._set_active_slot(slot)
        self.save_game()

    def _serialize_session(self) -> dict[str, Any]:
        inventory = self.session.hunter.inventory
        return {
            "difficulty": self.session.difficulty.value,
            "position": self._serialize_position(self.session.position),
            "boss_unlocked": self.session.boss_unlocked,
            "enemies_defeated": self.session.enemies_defeated,
            "score": self.session.score,
            "items_bought": self.session.items_bought,
            "items_sold": self.session.items_sold,
            "discovered_treasures": self.session.discovered_treasures,
            "tutorial_completed": self.session.tutorial_completed,
            "achievements": list(self.session.achievements),
            "event_log": list(self.session.event_log),
            "game_over": self.session.game_over,
            "victory": self.session.victory,
            "hunter": {
                "name": self.session.hunter.name,
                "max_health": self.session.hunter.max_health,
                "current_health": self.session.hunter.current_health,
                "base_attack": self.session.hunter.base_attack,
                "base_defense": self.session.hunter.base_defense,
                "guard_bonus": self.session.hunter.guard_bonus,
                "level": self.session.hunter.level,
                "experience": self.session.hunter.experience,
                "gold": self.session.hunter.gold,
                "inventory": [self._serialize_item(item) for item in inventory],
                "equipped_weapon_index": self._inventory_index(
                    inventory,
                    self.session.hunter.equipped_weapon,
                ),
                "equipped_armor_index": self._inventory_index(
                    inventory,
                    self.session.hunter.equipped_armor,
                ),
            },
            "world": {
                "width": self.session.world.width,
                "height": self.session.world.height,
                "enemy_health_bonus": self.session.world.enemy_health_bonus,
                "enemy_attack_bonus": self.session.world.enemy_attack_bonus,
                "tiles": [
                    {
                        "position": self._serialize_position(tile.position),
                        "terrain_name": tile.terrain_name,
                        "explored": tile.explored,
                        "enemy": self._serialize_enemy(tile.enemy),
                        "item": self._serialize_item(tile.item),
                        "zone_type": tile.zone_type.value,
                        "rest_available": tile.rest_available,
                        "obstacle": tile.obstacle,
                        "obstacle_name": tile.obstacle_name,
                        "shop_inventory": [
                            self._serialize_item(item) for item in tile.shop_inventory
                        ],
                    }
                    for tile in self.session.world.tiles.values()
                ],
            },
        }

    def _slot_label(self) -> str:
        if self.active_slot is not None:
            return f"slot {self.active_slot}"
        return self.save_path.name

    def _set_active_slot(self, slot: int) -> None:
        self.active_slot = slot
        self.save_path = build_save_slot_path(slot)

    def _prompt_slot_selection(
        self,
        title: str,
        existing_only: bool = False,
    ) -> int | None:
        summaries = list_save_slot_summaries()
        self.console.print(build_save_slot_table(summaries, title))
        valid_slots = [
            str(summary.slot)
            for summary in summaries
            if summary.exists or not existing_only
        ]
        if not valid_slots:
            return None
        choices = [*valid_slots, "salir"]
        selected = Prompt.ask(
            title,
            choices=choices,
            default=valid_slots[0],
            show_choices=False,
        )
        if selected == "salir":
            return None
        return int(selected)

    def _deserialize_session(self, data: dict[str, Any]) -> GameSession:
        world_data = data["world"]
        world = ForestMap(
            width=int(world_data["width"]),
            height=int(world_data["height"]),
            rng=self.rng,
            enemy_health_bonus=int(world_data["enemy_health_bonus"]),
            enemy_attack_bonus=int(world_data["enemy_attack_bonus"]),
        )
        for tile_data in world_data["tiles"]:
            tile = world.tile_at(self._deserialize_position(tile_data["position"]))
            tile.terrain_name = str(tile_data["terrain_name"])
            tile.explored = bool(tile_data["explored"])
            tile.enemy = self._deserialize_enemy(tile_data["enemy"])
            tile_item = self._deserialize_item(tile_data["item"])
            allowed_item_types = (Treasure, Trap, Weapon, Armor, HealingItem)
            if isinstance(tile_item, allowed_item_types) or tile_item is None:
                tile.item = tile_item
            tile.zone_type = ZoneType(str(tile_data["zone_type"]))
            tile.rest_available = bool(tile_data["rest_available"])
            tile.obstacle = bool(tile_data.get("obstacle", False))
            tile.obstacle_name = str(tile_data.get("obstacle_name", ""))
            tile.shop_inventory = [
                item
                for item in (
                    self._deserialize_item(item_data)
                    for item_data in tile_data["shop_inventory"]
                )
                if item is not None
            ]

        hunter_data = data["hunter"]
        inventory = [
            item
            for item in (
                self._deserialize_item(item_data) for item_data in hunter_data["inventory"]
            )
            if item is not None
        ]
        hunter = Hunter(
            name=str(hunter_data["name"]),
            max_health=int(hunter_data["max_health"]),
            current_health=int(hunter_data["current_health"]),
            base_attack=int(hunter_data["base_attack"]),
            base_defense=int(hunter_data["base_defense"]),
            guard_bonus=int(hunter_data["guard_bonus"]),
            level=int(hunter_data["level"]),
            experience=int(hunter_data["experience"]),
            gold=int(hunter_data["gold"]),
            inventory=inventory,
        )
        weapon_index = hunter_data["equipped_weapon_index"]
        armor_index = hunter_data["equipped_armor_index"]
        if weapon_index is not None:
            weapon_item = inventory[int(weapon_index)]
            if isinstance(weapon_item, Weapon):
                hunter.equipped_weapon = weapon_item
        if armor_index is not None:
            armor_item = inventory[int(armor_index)]
            if isinstance(armor_item, Armor):
                hunter.equipped_armor = armor_item

        return GameSession(
            hunter=hunter,
            world=world,
            position=self._deserialize_position(data["position"]),
            difficulty=Difficulty(str(data["difficulty"])),
            boss_unlocked=bool(data["boss_unlocked"]),
            enemies_defeated=int(data["enemies_defeated"]),
            score=int(data["score"]),
            items_bought=int(data["items_bought"]),
            items_sold=int(data["items_sold"]),
            discovered_treasures=int(data["discovered_treasures"]),
            tutorial_completed=bool(data.get("tutorial_completed", False)),
            achievements=[str(name) for name in data["achievements"]],
            event_log=[str(entry) for entry in data["event_log"]],
            game_over=bool(data["game_over"]),
            victory=bool(data["victory"]),
        )

    def _serialize_position(self, position: Position) -> dict[str, int]:
        return {"x": position.x, "y": position.y}

    def _deserialize_position(self, data: dict[str, Any]) -> Position:
        return Position(x=int(data["x"]), y=int(data["y"]))

    def _serialize_item(self, item: Item | None) -> dict[str, Any] | None:
        if item is None:
            return None
        payload: dict[str, Any] = {"name": item.name, "value": item.value}
        if isinstance(item, Weapon):
            payload["kind"] = "weapon"
            payload["attack_bonus"] = item.attack_bonus
            return payload
        if isinstance(item, Armor):
            payload["kind"] = "armor"
            payload["defense_bonus"] = item.defense_bonus
            return payload
        if isinstance(item, Trap):
            payload["kind"] = "trap"
            payload["explosion_range"] = item.explosion_range
            payload["explosion_damage"] = item.explosion_damage
            return payload
        if isinstance(item, HealingItem):
            payload["kind"] = "healing"
            payload["heal_amount"] = item.heal_amount
            return payload
        payload["kind"] = "treasure"
        return payload

    def _deserialize_item(self, data: dict[str, Any] | None) -> Item | None:
        if data is None:
            return None
        kind = str(data["kind"])
        if kind == "weapon":
            return Weapon(
                name=str(data["name"]),
                value=int(data["value"]),
                attack_bonus=int(data["attack_bonus"]),
            )
        if kind == "armor":
            return Armor(
                name=str(data["name"]),
                value=int(data["value"]),
                defense_bonus=int(data["defense_bonus"]),
            )
        if kind == "trap":
            return Trap(
                name=str(data["name"]),
                value=int(data["value"]),
                explosion_range=int(data["explosion_range"]),
                explosion_damage=int(data["explosion_damage"]),
            )
        if kind == "healing":
            return HealingItem(
                name=str(data["name"]),
                value=int(data["value"]),
                heal_amount=int(data["heal_amount"]),
            )
        return Treasure(name=str(data["name"]), value=int(data["value"]))

    def _serialize_enemy(self, enemy: Enemy | None) -> dict[str, Any] | None:
        if enemy is None:
            return None
        return {
            "name": enemy.name,
            "max_health": enemy.max_health,
            "current_health": enemy.current_health,
            "base_attack": enemy.base_attack,
            "base_defense": enemy.base_defense,
            "guard_bonus": enemy.guard_bonus,
            "enemy_type": enemy.enemy_type.value,
            "reward_experience": enemy.reward_experience,
            "reward_gold": enemy.reward_gold,
            "is_boss": enemy.is_boss,
        }

    def _deserialize_enemy(self, data: dict[str, Any] | None) -> Enemy | None:
        if data is None:
            return None
        return Enemy(
            name=str(data["name"]),
            max_health=int(data["max_health"]),
            current_health=int(data["current_health"]),
            base_attack=int(data["base_attack"]),
            base_defense=int(data["base_defense"]),
            guard_bonus=int(data["guard_bonus"]),
            enemy_type=EnemyType(str(data["enemy_type"])),
            reward_experience=int(data["reward_experience"]),
            reward_gold=int(data["reward_gold"]),
            is_boss=bool(data["is_boss"]),
        )

    def _inventory_index(self, inventory: list[Item], equipped: Item | None) -> int | None:
        if equipped is None:
            return None
        for index, item in enumerate(inventory):
            if item is equipped:
                return index
        return None

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
        if isinstance(item, HealingItem):
            return "Curación"
        return "Tesoro"

    def _item_effect(self, item: Item) -> str:
        if isinstance(item, Weapon):
            return f"+{item.attack_bonus} ATQ"
        if isinstance(item, Armor):
            return f"+{item.defense_bonus} DEF"
        if isinstance(item, Trap):
            return f"{item.explosion_damage} daño"
        if isinstance(item, HealingItem):
            return f"+{item.heal_amount} PV"
        return "Valor de venta"

    def _quit_game(self) -> None:
        self.session.game_over = True
        self.session.victory = False
        self.session.log("Abandonas temporalmente la expedición.")

    def _check_victory(self) -> None:
        if self.session.game_over:
            return
        explored, total = self.session.world.exploration_progress()
        if explored == total:
            self.session.game_over = True
            self.session.victory = True
            self.session.log("Victoria por exploración: completaste el mapa del bosque.")
            self._finalize_run()
            return
        config = DIFFICULTY_CONFIG[self.session.difficulty]
        if self.session.score >= config.score_victory_target:
            self.session.game_over = True
            self.session.victory = True
            self.session.log("Victoria por puntaje: alcanzaste el puntaje objetivo.")
            self._finalize_run()


def build_save_slot_path(slot: int) -> Path:
    if slot == 1:
        return DEFAULT_SAVE_PATH
    return DEFAULT_SAVE_PATH.with_name(f"savegame_slot_{slot}.json")


def read_save_slot_summary(slot: int) -> SaveSlotSummary:
    save_path = build_save_slot_path(slot)
    if not save_path.exists():
        return SaveSlotSummary(
            slot=slot,
            exists=False,
            label=f"Slot {slot}",
            difficulty="-",
            level="-",
            score="-",
            objective="Vacío",
        )
    try:
        data = json.loads(save_path.read_text(encoding="utf-8"))
        hunter_data = data.get("hunter", {})
        difficulty = str(data.get("difficulty", "-"))
        level = str(hunter_data.get("level", "-"))
        score = str(data.get("score", "-"))
        victory = bool(data.get("victory", False))
        boss_unlocked = bool(data.get("boss_unlocked", False))
        objective = "Victoria" if victory else (
            "Guarida abierta" if boss_unlocked else "En progreso"
        )
        return SaveSlotSummary(
            slot=slot,
            exists=True,
            label=f"Slot {slot}",
            difficulty=difficulty,
            level=level,
            score=score,
            objective=objective,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return SaveSlotSummary(
            slot=slot,
            exists=False,
            label=f"Slot {slot}",
            difficulty="-",
            level="-",
            score="-",
            objective="Corrupto",
        )


def list_save_slot_summaries() -> list[SaveSlotSummary]:
    return [read_save_slot_summary(slot) for slot in range(1, SAVE_SLOT_COUNT + 1)]


def build_save_slot_table(
    summaries: list[SaveSlotSummary],
    title: str,
) -> Table:
    table = Table(title=title, expand=True)
    table.add_column("Slot")
    table.add_column("Estado")
    table.add_column("Dificultad")
    table.add_column("Nivel")
    table.add_column("Puntaje")
    table.add_column("Objetivo")
    for summary in summaries:
        status = "Disponible" if summary.exists else "Vacío"
        table.add_row(
            summary.label,
            status,
            summary.difficulty.capitalize() if summary.difficulty != "-" else "-",
            summary.level,
            summary.score,
            summary.objective,
        )
    return table


def load_leaderboard(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [entry for entry in data if isinstance(entry, dict)]
        return []
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []


def save_leaderboard(path: Path, entries: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def build_leaderboard_table(
    entries: list[dict[str, Any]],
    title: str = "Ranking local",
) -> Table:
    table = Table(title=title, expand=True)
    table.add_column("#")
    table.add_column("Jugador")
    table.add_column("Dif.")
    table.add_column("Nivel")
    table.add_column("Puntaje")
    table.add_column("Estado")
    for idx, entry in enumerate(entries, start=1):
        table.add_row(
            str(idx),
            str(entry.get("name", "-")),
            str(entry.get("difficulty", "-")),
            str(entry.get("level", "-")),
            str(entry.get("score", "-")),
            "Victoria" if bool(entry.get("victory", False)) else "Derrota",
        )
    return table


def _prompt_main_menu_slot(existing_only: bool) -> int | None:
    console = Console()
    summaries = list_save_slot_summaries()
    console.print(build_save_slot_table(summaries, "Slots de guardado"))
    valid_slots = [
        str(summary.slot)
        for summary in summaries
        if summary.exists or not existing_only
    ]
    if not valid_slots:
        return None
    selected = Prompt.ask(
        "Selecciona slot",
        choices=[*valid_slots, "salir"],
        default=valid_slots[0],
        show_choices=False,
    )
    if selected == "salir":
        return None
    return int(selected)


def run() -> None:
    summaries = list_save_slot_summaries()
    console = Console()
    console.print(build_save_slot_table(summaries, "Menú principal"))
    available_actions = ["nueva", "salir"]
    if any(summary.exists for summary in summaries):
        available_actions.insert(0, "continuar")
    action = Prompt.ask(
        "Inicio",
        choices=available_actions,
        default=available_actions[0],
        show_choices=False,
    )
    if action == "salir":
        return
    if action == "continuar":
        slot = _prompt_main_menu_slot(existing_only=True)
        if slot is None:
            return
        save_path = build_save_slot_path(slot)
        app = BeastHunterApp(save_path=save_path, active_slot=slot)
        if app.load_saved_game():
            app.run()
        return
    slot = _prompt_main_menu_slot(existing_only=False)
    if slot is None:
        return
    selected_difficulty = Prompt.ask(
        "Elige dificultad",
        choices=[difficulty.value for difficulty in Difficulty],
        default=Difficulty.CAZADOR.value,
        show_choices=False,
    )
    BeastHunterApp(
        difficulty=Difficulty(selected_difficulty),
        save_path=build_save_slot_path(slot),
        active_slot=slot,
    ).run()
