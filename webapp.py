from __future__ import annotations

import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypedDict

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game.app import (
    DEFAULT_LEADERBOARD_PATH,
    DEFAULT_SAVE_PATH,
    DIFFICULTY_CONFIG,
    HELP_TOPICS,
    SAVE_SLOT_COUNT,
    BeastHunterApp,
    Difficulty,
    build_save_slot_path,
    list_save_slot_summaries,
    load_leaderboard,
)
from game.models import Armor, Direction, HealingItem, Item, Position, Trap, Weapon
from game.world import ZoneType


class ActionRequest(TypedDict, total=False):
    type: str
    direction: str
    difficulty: str
    slot: int
    index: int
    kind: str
    view: str


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI()
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

SESSIONS: dict[str, BeastHunterApp] = {}


def create_session_id() -> str:
    return secrets.token_urlsafe(24)


def get_or_create_session(sid: str | None) -> tuple[str, BeastHunterApp]:
    if sid is not None and sid in SESSIONS:
        return sid, SESSIONS[sid]
    session_id = create_session_id()
    game = BeastHunterApp(
        difficulty=Difficulty.CAZADOR,
        save_path=DEFAULT_SAVE_PATH,
        active_slot=1,
        leaderboard_path=DEFAULT_LEADERBOARD_PATH,
    )
    SESSIONS[session_id] = game
    return session_id, game


def item_kind(item: Item) -> str:
    if isinstance(item, Weapon):
        return "weapon"
    if isinstance(item, Armor):
        return "armor"
    if isinstance(item, Trap):
        return "trap"
    if isinstance(item, HealingItem):
        return "healing"
    return "treasure"


def item_effect(item: Item) -> str:
    if isinstance(item, Weapon):
        return f"+{item.attack_bonus} ATQ"
    if isinstance(item, Armor):
        return f"+{item.defense_bonus} DEF"
    if isinstance(item, Trap):
        return f"{item.explosion_damage} daño"
    if isinstance(item, HealingItem):
        return f"+{item.heal_amount} PV"
    return "Valor de venta"


def serialize_item(item: Item, *, use_sell_price: bool = False) -> dict[str, Any]:
    return {
        "name": item.name,
        "kind": item_kind(item),
        "effect": item_effect(item),
        "price": item.sell_price() if use_sell_price else item.buy_price(),
    }


def build_map_symbol(game: BeastHunterApp, position: Position) -> str:
    tile = game.session.world.tile_at(position)
    if position == game.session.position:
        return "🧙"
    if not tile.explored:
        return "·"
    if tile.zone_type is ZoneType.GUARIDA and tile.enemy and tile.enemy.is_alive():
        return "♛"
    if tile.shop_inventory or tile.rest_available:
        return "⌂"
    if tile.enemy and tile.enemy.is_alive():
        return "⚔"
    if tile.item:
        return "✦"
    return "✓"


def build_view(game: BeastHunterApp) -> dict[str, Any]:
    hunter = game.session.hunter
    explored, total = game.session.world.exploration_progress()
    tile = game.session.world.tile_at(game.session.position)

    enemy_payload: dict[str, Any] | None = None
    if tile.enemy and tile.enemy.is_alive():
        enemy_payload = {
            "name": tile.enemy.name,
            "type": tile.enemy.enemy_type.value,
            "hp": tile.enemy.current_health,
            "max_hp": tile.enemy.max_health,
            "is_boss": tile.enemy.is_boss,
        }

    item_payload: dict[str, Any] | None = None
    if tile.item is not None:
        item_payload = serialize_item(tile.item)

    inventory = hunter.inventory
    inventory_payload = [
        {
            "index": index,
            "name": item.name,
            "kind": item_kind(item),
            "effect": item_effect(item),
            "equipped": hunter.equipped_weapon is item or hunter.equipped_armor is item,
            "sell_price": item.sell_price(),
        }
        for index, item in enumerate(inventory)
    ]

    shop_payload = [serialize_item(item) for item in tile.shop_inventory]

    grid = [
        [
            build_map_symbol(game, Position(x, y))
            for x in range(game.session.world.width)
        ]
        for y in range(game.session.world.height)
    ]

    leaderboard = load_leaderboard(game.leaderboard_path)

    return {
        "status": {
            "name": hunter.name,
            "hp": hunter.current_health,
            "max_hp": hunter.max_health,
            "attack": hunter.total_attack(),
            "defense": hunter.total_defense(),
            "level": hunter.level,
            "xp": hunter.experience,
            "gold": hunter.gold,
            "score": game.session.score,
            "difficulty": DIFFICULTY_CONFIG[game.session.difficulty].label,
            "slot": game.active_slot,
            "exploration": {"explored": explored, "total": total},
        },
        "tile": {
            "terrain": tile.terrain_name,
            "zone_type": tile.zone_type.value,
            "rest_available": tile.rest_available,
            "shop_available": bool(tile.shop_inventory),
            "enemy": enemy_payload,
            "item": item_payload,
        },
        "progress": {
            "boss_unlocked": game.session.boss_unlocked,
            "enemies_defeated": game.session.enemies_defeated,
            "treasures": game.session.discovered_treasures,
            "items_bought": game.session.items_bought,
            "items_sold": game.session.items_sold,
            "tutorial_completed": game.session.tutorial_completed,
            "achievements": list(game.session.achievements),
        },
        "map": {
            "width": game.session.world.width,
            "height": game.session.world.height,
            "grid": grid,
        },
        "inventory": inventory_payload,
        "shop": shop_payload,
        "log": list(game.session.event_log),
        "help": {"topics": HELP_TOPICS},
        "slots": [asdict(summary) for summary in list_save_slot_summaries()],
        "leaderboard": leaderboard[:10],
        "game_over": game.session.game_over,
        "victory": game.session.victory,
    }


def parse_direction(value: str) -> Direction:
    mapping = {
        "n": Direction.NORTE,
        "s": Direction.SUR,
        "e": Direction.ESTE,
        "o": Direction.OESTE,
        "norte": Direction.NORTE,
        "sur": Direction.SUR,
        "este": Direction.ESTE,
        "oeste": Direction.OESTE,
    }
    if value not in mapping:
        raise HTTPException(status_code=400, detail="Dirección inválida")
    return mapping[value]


def ensure_slot(value: int) -> int:
    if value < 1 or value > SAVE_SLOT_COUNT:
        raise HTTPException(status_code=400, detail="Slot inválido")
    return value


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/state")
def get_state(response: Response, sid: str | None = Cookie(default=None)) -> dict[str, Any]:
    session_id, game = get_or_create_session(sid)
    response.set_cookie("sid", session_id, httponly=True, samesite="lax")
    return build_view(game)


@app.get("/api/slots")
def get_slots() -> list[dict[str, Any]]:
    return [asdict(summary) for summary in list_save_slot_summaries()]


@app.get("/api/leaderboard")
def get_leaderboard() -> list[dict[str, Any]]:
    return load_leaderboard(DEFAULT_LEADERBOARD_PATH)[:10]


@app.post("/api/new")
def new_game(
    body: ActionRequest,
    response: Response,
) -> dict[str, Any]:
    difficulty_value = body.get("difficulty", Difficulty.CAZADOR.value)
    slot_value = int(body.get("slot", 1))
    difficulty = Difficulty(difficulty_value)
    slot = ensure_slot(slot_value)
    save_path = build_save_slot_path(slot)
    game = BeastHunterApp(
        difficulty=difficulty,
        save_path=save_path,
        active_slot=slot,
        leaderboard_path=DEFAULT_LEADERBOARD_PATH,
    )
    session_id = create_session_id()
    SESSIONS[session_id] = game
    response.set_cookie("sid", session_id, httponly=True, samesite="lax")
    return build_view(game)


@app.post("/api/load")
def load_game(
    body: ActionRequest,
    response: Response,
) -> dict[str, Any]:
    slot_value = int(body.get("slot", 1))
    slot = ensure_slot(slot_value)
    save_path = build_save_slot_path(slot)
    game = BeastHunterApp(
        difficulty=Difficulty.CAZADOR,
        save_path=save_path,
        active_slot=slot,
        leaderboard_path=DEFAULT_LEADERBOARD_PATH,
    )
    if not game.load_saved_game():
        raise HTTPException(status_code=404, detail="No existe guardado en ese slot")
    session_id = create_session_id()
    SESSIONS[session_id] = game
    response.set_cookie("sid", session_id, httponly=True, samesite="lax")
    return build_view(game)


@app.post("/api/action")
def action(
    body: ActionRequest,
    response: Response,
    sid: str | None = Cookie(default=None),
) -> dict[str, Any]:
    session_id, game = get_or_create_session(sid)
    response.set_cookie("sid", session_id, httponly=True, samesite="lax")

    action_type = body.get("type", "")
    if action_type == "move":
        direction_value = body.get("direction", "")
        game._move(parse_direction(direction_value))
    elif action_type == "attack":
        game._attack()
    elif action_type == "defend":
        game._defend()
    elif action_type == "trap":
        game._use_trap()
    elif action_type == "use":
        game._use_healing_item()
    elif action_type == "rest":
        game._rest()
    elif action_type == "equip":
        index = int(body.get("index", -1))
        kind = str(body.get("kind", ""))
        inventory = game.session.hunter.inventory
        if index < 0 or index >= len(inventory):
            raise HTTPException(status_code=400, detail="Índice inválido")
        item = inventory[index]
        if kind == "weapon" and isinstance(item, Weapon):
            game.session.log(game.session.hunter.equip_weapon(item))
        elif kind == "armor" and isinstance(item, Armor):
            game.session.log(game.session.hunter.equip_armor(item))
        else:
            raise HTTPException(status_code=400, detail="Equipamiento inválido")
    elif action_type == "buy":
        index = int(body.get("index", -1))
        tile = game.session.world.tile_at(game.session.position)
        if index < 0 or index >= len(tile.shop_inventory):
            raise HTTPException(status_code=400, detail="Índice inválido")
        game._buy_item(tile, tile.shop_inventory[index])
    elif action_type == "sell":
        index = int(body.get("index", -1))
        inventory = game.session.hunter.inventory
        if index < 0 or index >= len(inventory):
            raise HTTPException(status_code=400, detail="Índice inválido")
        item = inventory[index]
        sale_price = game.session.hunter.sell_item(item)
        game.session.items_sold += 1
        game._award_score(sale_price, f"Comercializas {item.name}.")
        game.session.log(f"Vendiste {item.name} por {sale_price} monedas.")
    elif action_type == "save":
        slot_value = int(body.get("slot", 1))
        slot = ensure_slot(slot_value)
        game.save_to_slot(slot)
    else:
        raise HTTPException(status_code=400, detail="Acción inválida")

    game._refresh_boss_unlock()
    game._check_victory()
    return build_view(game)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
