const state = {
  view: null,
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
  const { width, grid } = view.map;
  const mapEl = qs("#map");
  mapEl.style.gridTemplateColumns = `repeat(${width}, 34px)`;
  mapEl.innerHTML = "";
  for (const row of grid) {
    for (const cell of row) {
      const div = document.createElement("div");
      div.className = "map-cell";
      div.textContent = cell;
      mapEl.appendChild(div);
    }
  }
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
    await doAction({ type: action });
  });

  await refresh();
}

setup().catch((error) => {
  showModal("Error", `<pre>${escapeHtml(error?.message ?? String(error))}</pre>`);
});
