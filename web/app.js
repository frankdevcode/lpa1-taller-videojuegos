const state = {
  view: null,
  lastMoveDirection: null,
  player: {
    from: null,
    to: null,
    startedAt: 0,
    durationMs: 140,
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
  const cellSize = Math.floor(Math.min(canvas.width / width, canvas.height / height));
  const offsetX = Math.floor((canvas.width - cellSize * width) / 2);
  const offsetY = Math.floor((canvas.height - cellSize * height) / 2);

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const symbol = grid[y][x];
      const rectX = offsetX + x * cellSize;
      const rectY = offsetY + y * cellSize;

      const baseColor = tileBaseColor(symbol, x, y);
      ctx.fillStyle = baseColor;
      ctx.fillRect(rectX, rectY, cellSize, cellSize);

      ctx.strokeStyle = "rgba(38,49,90,0.9)";
      ctx.strokeRect(rectX + 0.5, rectY + 0.5, cellSize - 1, cellSize - 1);

      const overlay = tileOverlay(symbol);
      if (overlay) {
        ctx.font = `${Math.floor(cellSize * 0.6)}px system-ui`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "rgba(232,238,252,0.95)";
        ctx.fillText(overlay, rectX + cellSize / 2, rectY + cellSize / 2);
      }
    }
  }

  drawPlayer(ctx, view, cellSize, offsetX, offsetY);
}

function tileOverlay(symbol) {
  if (symbol === "⚔" || symbol === "♛" || symbol === "⌂" || symbol === "✦" || symbol === "🌲") {
    return symbol;
  }
  return "";
}

function tileBaseColor(symbol, x, y) {
  if (symbol === "·") {
    return "#071027";
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

function drawPlayer(ctx, view, cellSize, offsetX, offsetY) {
  const pos = view.status.position;
  if (!pos) {
    return;
  }
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
  const drawX = from.x + (to.x - from.x) * eased;
  const drawY = from.y + (to.y - from.y) * eased;

  const centerX = offsetX + drawX * cellSize + cellSize / 2;
  const centerY = offsetY + drawY * cellSize + cellSize / 2;
  const radius = Math.max(6, Math.floor(cellSize * 0.22));

  ctx.beginPath();
  ctx.fillStyle = "#ffce6b";
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.strokeStyle = "rgba(10,15,30,0.9)";
  ctx.lineWidth = 2;
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.stroke();

  if (progress < 1) {
    requestAnimationFrame(() => renderMap(state.view));
  }
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
    const cellSize = Math.floor(Math.min(canvas.width / width, canvas.height / height));
    const offsetX = Math.floor((canvas.width - cellSize * width) / 2);
    const offsetY = Math.floor((canvas.height - cellSize * height) / 2);
    const gridX = Math.floor((x - offsetX) / cellSize);
    const gridY = Math.floor((y - offsetY) / cellSize);
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
