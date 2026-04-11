from __future__ import annotations

import random
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .models import Direction, Enemy, Hunter, Item, Position, Trap, calculate_damage
from .world import ForestMap, Tile


@dataclass(slots=True)
class GameSession:
    hunter: Hunter
    world: ForestMap
    position: Position
    discovered_treasures: int = 0
    event_log: list[str] = field(default_factory=list)
    game_over: bool = False
    victory: bool = False

    def log(self, message: str) -> None:
        self.event_log.append(message)
        self.event_log = self.event_log[-8:]


class BeastHunterApp:
    def __init__(self) -> None:
        self.console = Console()
        self.rng = random.Random()
        self.session = self._create_session()

    def _create_session(self) -> GameSession:
        hunter = Hunter(
            name="Aren, cazador del bosque",
            max_health=48,
            current_health=48,
            base_attack=11,
            base_defense=5,
        )
        world = ForestMap(width=5, height=5, rng=self.rng)
        session = GameSession(hunter=hunter, world=world, position=world.start_position)
        session.log("Comienza la expedición en el corazón del bosque.")
        session.log("Tu misión inicial es sobrevivir, explorar y recolectar reliquias.")
        return session

    def run(self) -> None:
        self._render_intro()
        while not self.session.game_over:
            self._render()
            command = Prompt.ask(
                "Acción",
                choices=["n", "s", "e", "o", "atacar", "defender", "trampa", "inventario", "salir"],
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
                "exploración, combate, objetos y progreso.\n"
                "Comandos: n, s, e, o, atacar, defender, trampa, inventario, salir",
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
        table.add_row(
            hunter.name,
            f"{hunter.current_health}/{hunter.max_health}",
            str(hunter.total_attack()),
            str(hunter.total_defense()),
            str(hunter.level),
            str(hunter.experience),
            str(hunter.gold),
            f"{explored}/{total}",
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
        lines = [f"Zona actual: {tile.terrain_name}"]
        if tile.enemy and tile.enemy.is_alive():
            lines.append(
                f"Enemigo: {tile.enemy.name} ({tile.enemy.enemy_type.value}) "
                f"{tile.enemy.current_health}/{tile.enemy.max_health} PV"
            )
        elif tile.item:
            lines.append(f"Objeto detectado: {tile.item.name}")
        else:
            lines.append("La zona está despejada.")
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
            "salir": self._quit_game,
        }
        action = actions[command]
        action()
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
        auto_equip_message = self.session.hunter.auto_equip(item)
        if auto_equip_message is not None:
            self.session.log(auto_equip_message)
            return
        self.session.hunter.gold += item.value
        self.session.discovered_treasures += 1
        self.session.log(f"El hallazgo suma {item.value} monedas a tu bolsa.")

    def _attack(self) -> None:
        tile = self.session.world.tile_at(self.session.position)
        enemy = tile.enemy
        if enemy is None or not enemy.is_alive():
            self.session.log("No hay ningún enemigo que atacar aquí.")
            return

        hunter_damage = calculate_damage(self.session.hunter, enemy)
        applied_to_enemy = enemy.receive_damage(hunter_damage)
        self.session.log(f"Golpeas a {enemy.name} e infliges {applied_to_enemy} de daño.")
        self.session.hunter.reset_guard()

        if not enemy.is_alive():
            self.session.hunter.gold += enemy.reward_gold
            for message in self.session.hunter.gain_experience(enemy.reward_experience):
                self.session.log(message)
            self.session.log(f"Derrotas a {enemy.name} y obtienes {enemy.reward_gold} monedas.")
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
        self.session.hunter.gold += enemy.reward_gold
        for message in self.session.hunter.gain_experience(enemy.reward_experience):
            self.session.log(message)
        self.session.log(
            f"La explosión elimina a {enemy.name}. "
            f"Obtienes {enemy.reward_gold} monedas."
        )

    def _enemy_turn(self, enemy: Enemy) -> None:
        enemy_damage = calculate_damage(enemy, self.session.hunter)
        applied_to_hunter = self.session.hunter.receive_damage(enemy_damage)
        self.session.log(f"{enemy.name} contraataca y te causa {applied_to_hunter} de daño.")
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
            grouped_items[item.name] = grouped_items.get(item.name, 0) + 1
        summary = ", ".join(f"{name} x{count}" for name, count in grouped_items.items())
        self.session.log(f"Inventario: {summary}.")

    def _quit_game(self) -> None:
        self.session.game_over = True
        self.session.victory = False
        self.session.log("Abandonas temporalmente la expedición.")

    def _check_victory(self) -> None:
        explored, total = self.session.world.exploration_progress()
        if self.session.game_over:
            return
        if explored == total and self.session.hunter.is_alive():
            self.session.game_over = True
            self.session.victory = True
            self.session.log("Exploraste por completo el bosque y sobreviviste a la cacería.")


def run() -> None:
    BeastHunterApp().run()
