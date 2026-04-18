const state = {
  view: null,
  lastMoveDirection: null,
  camera: {
    x: 0,
    y: 0,
    ready: false,
  },
  player: {
    from: null,
    to: null,
    startedAt: 0,
    durationMs: 180,
  },
};

function qs(selector) {
  const element = document.querySelector(selector);
  if (!element) {
    throw new Error(`Missing element: ${selector}`);
  }
  return element;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function apiGet(path) {
  const response = await fetch(path, { credentials: "include" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function apiPost(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Error" }));
    throw new Error(error.detail ?? "Error");
  }
  return response.json();
}

function renderStatus(view) {
  const s = view.status;
  const html = `
    <div class="list">
      <div class="list-row">
        <div>
          <strong>${escapeHtml(s.name)}</strong>
          <span>Vida: ${s.hp}/${s.max_hp} · ATQ: ${s.attack} · DEF: ${s.defense}</span>
          <span>Nivel: ${s.level} · XP: ${s.xp} · Oro: ${s.gold} · Puntaje: ${s.score}</span>
          <span>Dificultad: ${escapeHtml(s.difficulty)} · Slot: ${s.slot ?? "-"}</span>
          <span>Exploración: ${s.exploration.explored}/${s.exploration.total}</span>
        </div>
        <div></div>
      </div>
    </div>
  `;
  qs("#status").innerHTML = html;
}

function renderTile(view) {
  const t = view.tile;
  const obstacle = t.obstacle
    ? `<span>Obstáculo: ${escapeHtml(t.obstacle_name || "bloqueo")}.</span>`
    : "";
  const enemy = t.enemy
    ? `<span>Enemigo: ${escapeHtml(t.enemy.name)} (${escapeHtml(t.enemy.type)}) ${t.enemy.hp}/${t.enemy.max_hp}</span>`
    : `<span>Sin enemigo.</span>`;
  const item = t.item
    ? `<span>Objeto: ${escapeHtml(t.item.name)} · ${escapeHtml(t.item.effect)}</span>`
    : `<span>Sin objeto.</span>`;
  const html = `
    <div class="list">
      <div class="list-row">
        <div>
          <strong>${escapeHtml(t.terrain)}</strong>
          <span>Zona: ${escapeHtml(t.zone_type)}</span>
          ${obstacle}
          ${enemy}
          ${item}
          <span>Descanso: ${t.rest_available ? "sí" : "no"} · Tienda: ${t.shop_available ? "sí" : "no"}</span>
        </div>
        <div></div>
      </div>
    </div>
  `;
  qs("#tile").innerHTML = html;
}

function renderMap(view) {
  const canvas = qs("#gameCanvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const { width, height, grid } = view.map;
  const tileSize = 72;
  const playerPos = getAnimatedPlayerPosition(view);
  const camera = updateCamera(playerPos.x, playerPos.y);
  const halfTilesX = Math.ceil(canvas.width / (tileSize * 2)) + 2;
  const halfTilesY = Math.ceil(canvas.height / (tileSize * 2)) + 2;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const background = ctx.createLinearGradient(0, 0, 0, canvas.height);
  background.addColorStop(0, "#061026");
  background.addColorStop(1, "#040815");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const startX = Math.max(0, Math.floor(camera.x) - halfTilesX);
  const endX = Math.min(width - 1, Math.floor(camera.x) + halfTilesX);
  const startY = Math.max(0, Math.floor(camera.y) - halfTilesY);
  const endY = Math.min(height - 1, Math.floor(camera.y) + halfTilesY);

  for (let y = startY; y <= endY; y += 1) {
    for (let x = startX; x <= endX; x += 1) {
      const symbol = grid[y][x];
      const rectX = Math.round((x - camera.x) * tileSize + canvas.width / 2);
      const rectY = Math.round((y - camera.y) * tileSize + canvas.height / 2);

      const baseColor = tileBaseColor(symbol, x, y);
      ctx.fillStyle = baseColor;
      ctx.fillRect(rectX, rectY, tileSize, tileSize);

      if (symbol === "✓" || symbol === "·") {
        drawGrassPattern(ctx, rectX, rectY, tileSize, x, y);
      }

      ctx.strokeStyle = "rgba(38,49,90,0.55)";
      ctx.strokeRect(rectX + 0.5, rectY + 0.5, tileSize - 1, tileSize - 1);

      const overlay = tileOverlay(symbol);
      if (overlay) {
        ctx.font = `${Math.floor(tileSize * 0.48)}px system-ui`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "rgba(232,238,252,0.95)";
        ctx.fillText(overlay, rectX + tileSize / 2, rectY + tileSize / 2);
      }
    }
  }

  drawPlayer(ctx, canvas, playerPos, camera, tileSize);

  const isMoving =
    Math.abs(playerPos.x - view.status.position.x) > 0.001 ||
    Math.abs(playerPos.y - view.status.position.y) > 0.001;
  const cameraLag =
    Math.abs(camera.x - playerPos.x) > 0.001 ||
    Math.abs(camera.y - playerPos.y) > 0.001;
  if (isMoving || cameraLag) {
    requestAnimationFrame(() => renderMap(state.view));
  }
}

function tileOverlay(symbol) {
  if (symbol === "⚔" || symbol === "♛" || symbol === "⌂" || symbol === "✦" || symbol === "🌲") {
    return symbol;
  }
  return "";
}

function tileBaseColor(symbol, x, y) {
  if (symbol === "·") {
    return "#050b1b";
  }
  if (symbol === "⌂") {
    return "#131d3f";
  }
  if (symbol === "♛") {
    return "#2b1733";
  }
  if (symbol === "⚔") {
    return "#1b1431";
  }
  if (symbol === "✦") {
    return "#111f2e";
  }
  if (symbol === "🌲") {
    return "#102518";
  }
  if (symbol === "✓") {
    return grassColor(x, y);
  }
  return grassColor(x, y);
}

function grassColor(x, y) {
  const n = pseudoNoise(x, y);
  const base = 26 + Math.floor(n * 12);
  const r = 12;
  const g = base;
  const b = 24;
  return `rgb(${r},${g},${b})`;
}

function pseudoNoise(x, y) {
  const seed = (x * 9301 + y * 49297) % 233280;
  return seed / 233280;
}

function drawGrassPattern(ctx, rectX, rectY, tileSize, x, y) {
  const n = pseudoNoise(x + 7, y + 13);
  const lines = 2 + Math.floor(n * 4);
  ctx.strokeStyle = "rgba(100,170,110,0.14)";
  ctx.lineWidth = 1;
  for (let i = 0; i < lines; i += 1) {
    const px = rectX + ((i + 1) / (lines + 1)) * tileSize;
    const py = rectY + tileSize - 5 - (i % 3);
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(px + 2, py - 8);
    ctx.stroke();
  }
}

function getAnimatedPlayerPosition(view) {
  const pos = view.status.position;
  if (!pos) return { x: 0, y: 0 };
  const target = { x: pos.x, y: pos.y };
  const now = performance.now();
  const tween = state.player;

  if (!tween.to || tween.to.x !== target.x || tween.to.y !== target.y) {
    tween.from = tween.to ?? target;
    tween.to = target;
    tween.startedAt = now;
  }

  const progress = Math.min(1, (now - tween.startedAt) / tween.durationMs);
  const eased = easeOutCubic(progress);
  const from = tween.from ?? target;
  const to = tween.to ?? target;
  return {
    x: from.x + (to.x - from.x) * eased,
    y: from.y + (to.y - from.y) * eased,
  };
}

function updateCamera(targetX, targetY) {
  if (!state.camera.ready) {
    state.camera.x = targetX;
    state.camera.y = targetY;
    state.camera.ready = true;
  }
  const lerp = 0.22;
  state.camera.x += (targetX - state.camera.x) * lerp;
  state.camera.y += (targetY - state.camera.y) * lerp;
  return state.camera;
}

function drawPlayer(ctx, canvas, playerPos, camera, tileSize) {
  const centerX = (playerPos.x - camera.x) * tileSize + canvas.width / 2 + tileSize / 2;
  const centerY = (playerPos.y - camera.y) * tileSize + canvas.height / 2 + tileSize / 2;
  const radius = Math.max(8, Math.floor(tileSize * 0.24));

  ctx.beginPath();
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.ellipse(centerX, centerY + radius + 5, radius * 0.9, radius * 0.35, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.fillStyle = "#ffce6b";
  ctx.arc(centerX, centerY - radius * 0.2, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.fillStyle = "#3d5a9a";
  ctx.arc(centerX, centerY + radius * 0.7, radius * 0.75, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.strokeStyle = "rgba(8,12,24,0.92)";
  ctx.lineWidth = 2.2;
  ctx.arc(centerX, centerY - radius * 0.2, radius, 0, Math.PI * 2);
  ctx.stroke();
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

function renderLog(view) {
  const content = (view.log ?? []).slice(-12).map((line) => `• ${line}`).join("\n");
  qs("#log").textContent = content || "Sin eventos todavía.";
}

function renderInventory(view) {
  const inv = view.inventory ?? [];
  if (inv.length === 0) {
    qs("#inventory").innerHTML = "<div class='list'>Inventario vacío.</div>";
    return;
  }
  const rows = inv
    .map((item) => {
      const equipButton =
        item.kind === "weapon" || item.kind === "armor"
          ? `<button data-action="equip" data-index="${item.index}" data-kind="${item.kind}">Equipar</button>`
          : "";
      return `
        <div class="list-row">
          <div>
            <strong>${escapeHtml(item.name)} ${item.equipped ? "(equipado)" : ""}</strong>
            <span>${escapeHtml(item.kind)} · ${escapeHtml(item.effect)} · Venta: ${item.sell_price}</span>
          </div>
          <div>
            ${equipButton}
            <button data-action="sell" data-index="${item.index}">Vender</button>
          </div>
        </div>
      `;
    })
    .join("");
  qs("#inventory").innerHTML = `<div class="list">${rows}</div>`;
}

function renderShop(view) {
  const items = view.shop ?? [];
  if (!items.length) {
    qs("#shop").innerHTML = "<div class='list'>No hay tienda aquí.</div>";
    return;
  }
  const rows = items
    .map((item, index) => {
      return `
        <div class="list-row">
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <span>${escapeHtml(item.kind)} · ${escapeHtml(item.effect)} · Precio: ${item.price}</span>
          </div>
          <div>
            <button data-action="buy" data-index="${index}">Comprar</button>
          </div>
        </div>
      `;
    })
    .join("");
  qs("#shop").innerHTML = `<div class="list">${rows}</div>`;
}

function showModal(title, bodyHtml) {
  qs("#modalTitle").textContent = title;
  qs("#modalBody").innerHTML = bodyHtml;
  qs("#modal").classList.remove("hidden");
}

function hideModal() {
  qs("#modal").classList.add("hidden");
}

function render(view) {
  state.view = view;
  renderStatus(view);
  renderMap(view);
  renderTile(view);
  renderInventory(view);
  renderShop(view);
  renderLog(view);
  if (view.game_over) {
    const outcome = view.victory ? "Victoria" : "Derrota";
    showModal("Fin de partida", `<p>${outcome}. Puntaje final: ${view.status.score}</p>`);
  }
}

async function refresh() {
  const view = await apiGet("/api/state");
  render(view);
}

async function doAction(payload) {
  const view = await apiPost("/api/action", payload);
  render(view);
}

function currentSlot() {
  return Number(qs("#slotSelect").value);
}

function currentDifficulty() {
  return qs("#difficultySelect").value;
}

async function setup() {
  qs("#modalClose").addEventListener("click", hideModal);
  qs("#modal").addEventListener("click", (event) => {
    if (event.target === qs("#modal")) {
      hideModal();
    }
  });

  qs("#newBtn").addEventListener("click", async () => {
    const view = await apiPost("/api/new", { difficulty: currentDifficulty(), slot: currentSlot() });
    render(view);
  });

  qs("#loadBtn").addEventListener("click", async () => {
    const view = await apiPost("/api/load", { slot: currentSlot() });
    render(view);
  });

  qs("#saveBtn").addEventListener("click", async () => {
    await doAction({ type: "save", slot: currentSlot() });
  });

  qs("#rankingBtn").addEventListener("click", async () => {
    const leaderboard = await apiGet("/api/leaderboard");
    const rows = leaderboard
      .map((entry, idx) => {
        return `<li>#${idx + 1} ${escapeHtml(entry.name)} · ${escapeHtml(entry.difficulty)} · nivel ${
          entry.level
        } · ${entry.score} · ${entry.victory ? "victoria" : "derrota"}</li>`;
      })
      .join("");
    showModal("Ranking local", `<ol>${rows || "<li>Sin registros</li>"}</ol>`);
  });

  document.body.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const action = target.dataset.action;
    if (!action) {
      return;
    }
    if (action === "move") {
      await doAction({ type: "move", direction: target.dataset.direction });
      return;
    }
    if (action === "equip") {
      await doAction({
        type: "equip",
        index: Number(target.dataset.index),
        kind: target.dataset.kind,
      });
      return;
    }
    if (action === "buy" || action === "sell") {
      await doAction({ type: action, index: Number(target.dataset.index) });
      return;
    }
    if (action === "dodge") {
      if (!state.lastMoveDirection) {
        showModal("Esquivar", "<p>Mueve primero en una dirección (WASD/flechas) para esquivar.</p>");
        return;
      }
      await doAction({ type: "dodge", direction: state.lastMoveDirection });
      return;
    }
    await doAction({ type: action });
  });

  setupKeyboardControls();
  setupCanvasClickMove();
  await refresh();
}

function setupKeyboardControls() {
  window.addEventListener("keydown", async (event) => {
    if (event.repeat) {
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "arrowup" || key === "w") {
      event.preventDefault();
      state.lastMoveDirection = "n";
      await doAction({ type: "move", direction: "n" });
      return;
    }
    if (key === "arrowdown" || key === "s") {
      event.preventDefault();
      state.lastMoveDirection = "s";
      await doAction({ type: "move", direction: "s" });
      return;
    }
    if (key === "arrowleft" || key === "a") {
      event.preventDefault();
      state.lastMoveDirection = "o";
      await doAction({ type: "move", direction: "o" });
      return;
    }
    if (key === "arrowright" || key === "d") {
      event.preventDefault();
      state.lastMoveDirection = "e";
      await doAction({ type: "move", direction: "e" });
      return;
    }
    if (event.code === "Space") {
      event.preventDefault();
      if (!state.lastMoveDirection) {
        showModal("Esquivar", "<p>Mueve primero en una dirección (WASD/flechas) para esquivar.</p>");
        return;
      }
      await doAction({ type: "dodge", direction: state.lastMoveDirection });
      return;
    }
    if (key === "enter") {
      event.preventDefault();
      await doAction({ type: "attack" });
      return;
    }
    if (event.key === "Shift") {
      event.preventDefault();
      await doAction({ type: "defend" });
      return;
    }
    if (key === "t") {
      event.preventDefault();
      await doAction({ type: "trap" });
      return;
    }
    if (key === "u") {
      event.preventDefault();
      await doAction({ type: "use" });
      return;
    }
  });
}

function setupCanvasClickMove() {
  const canvas = qs("#gameCanvas");
  canvas.addEventListener("click", async (event) => {
    if (!state.view) {
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (canvas.width / rect.width);
    const y = (event.clientY - rect.top) * (canvas.height / rect.height);
    const { width, height } = state.view.map;
    const tileSize = 72;
    const camX = state.camera.ready ? state.camera.x : state.view.status.position.x;
    const camY = state.camera.ready ? state.camera.y : state.view.status.position.y;
    const gridX = Math.floor((x - canvas.width / 2) / tileSize + camX);
    const gridY = Math.floor((y - canvas.height / 2) / tileSize + camY);
    if (gridX < 0 || gridX >= width || gridY < 0 || gridY >= height) {
      return;
    }
    const pos = state.view.status.position;
    const dx = gridX - pos.x;
    const dy = gridY - pos.y;
    if (Math.abs(dx) + Math.abs(dy) !== 1) {
      return;
    }
    const direction = dx === 1 ? "e" : dx === -1 ? "o" : dy === 1 ? "s" : "n";
    state.lastMoveDirection = direction;
    const symbol = state.view.map.grid[gridY][gridX];
    if (symbol === "🌲") {
      await doAction({ type: "dodge", direction });
      return;
    }
    await doAction({ type: "move", direction });
  });
}

setup().catch((error) => {
  showModal("Error", `<pre>${escapeHtml(error?.message ?? String(error))}</pre>`);
});
