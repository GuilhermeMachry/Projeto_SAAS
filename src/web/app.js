/* HardTrack Solutions — Interface Web Interativa Nativa (Zero-Build SPA) */

const DEMO_PERSONAS = {
  b2c: {
    tenant_id: "joao_b2c",
    nome: "João Silva (Gamer / B2C)",
    tipo: "B2C_ENTUSIASTA",
    telegram_chat_id: "11223344",
  },
  b2b: {
    tenant_id: "techparts_b2b",
    nome: "Oficina TechParts (Montadora / B2B)",
    tipo: "B2B_OFICINA",
    telegram_chat_id: "99887766",
  },
};

const state = {
  currentView: "b2c",
  tokens: {},          // tenant_id -> bearer token
  profiles: {},        // tenant_id -> TenantResponse
  siloInfo: {},        // tenant_id -> SiloInfoResponse
  targets: {},         // tenant_id -> MonitorTargetResponse[]
  history: {},         // tenant_id -> PriceRecord[]
  alerts: {},          // tenant_id -> AlertLog[]
  customTenant: null,  // { tenant_id, tipo, nome, telegram_chat_id }
  batchQty: 10,
};

// ---------------- Utilitários ----------------

function fmtBRL(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtDate(iso) {
  if (!iso) return "Aguardando varredura";
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
  } catch {
    return iso;
  }
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function toast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

async function apiFetch(path, options = {}) {
  const t0 = performance.now();
  const res = await fetch(path, options);
  const elapsed = Math.round(performance.now() - t0);

  const latEl = document.getElementById("latency-value");
  if (latEl) {
    latEl.textContent = `${elapsed} ms`;
    latEl.style.color = elapsed < 150 ? "#4ade80" : "#fbbf24";
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { ok: res.ok, status: res.status, data, elapsed };
}

function authHeaders(tenantId, extra = {}) {
  const token = state.tokens[tenantId];
  const headers = { "Content-Type": "application/json", ...extra };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

// ---------------- Autenticação e Seed dos Perfis Demo ----------------

async function ensureDemoPersona(key) {
  const p = DEMO_PERSONAS[key];
  if (state.tokens[p.tenant_id]) return true;

  // Tenta autenticar o tenant já existente
  let res = await apiFetch("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_id: p.tenant_id,
      telegram_chat_id: p.telegram_chat_id,
    }),
  });

  // Se o silo ainda não existir, cria via POST /tenants
  if (!res.ok) {
    res = await apiFetch("/tenants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
  }

  if (res.ok && res.data?.access_token) {
    state.tokens[p.tenant_id] = res.data.access_token;
    state.profiles[p.tenant_id] = res.data;
    return true;
  }
  toast(`Falha ao autenticar perfil ${p.tenant_id}`, "error");
  return false;
}

async function loadTenantData(tenantId) {
  const headers = authHeaders(tenantId);
  const [profileRes, siloRes, targetsRes, historyRes, alertsRes] = await Promise.all([
    apiFetch(`/tenants/${tenantId}`, { headers }),
    apiFetch(`/tenants/${tenantId}/silo-info`, { headers }),
    apiFetch(`/tenants/${tenantId}/targets`, { headers }),
    apiFetch(`/tenants/${tenantId}/history?limit=40`, { headers }),
    apiFetch(`/tenants/${tenantId}/alerts?limit=20`, { headers }),
  ]);

  if (profileRes.ok) state.profiles[tenantId] = profileRes.data;
  if (siloRes.ok) state.siloInfo[tenantId] = siloRes.data;
  if (targetsRes.ok) state.targets[tenantId] = targetsRes.data;
  if (historyRes.ok) state.history[tenantId] = historyRes.data;
  if (alertsRes.ok) state.alerts[tenantId] = alertsRes.data;
}

function activeTenantIdForView(view) {
  if (state.customTenant) {
    if (view === "b2c" && state.customTenant.tipo === "B2C_ENTUSIASTA") return state.customTenant.tenant_id;
    if (view === "b2b" && state.customTenant.tipo === "B2B_OFICINA") return state.customTenant.tenant_id;
  }
  return view === "b2b" ? DEMO_PERSONAS.b2b.tenant_id : DEMO_PERSONAS.b2c.tenant_id;
}

// ---------------- Renderização de Gráficos SVG ----------------

function renderPriceChart(containerId, history, accentColor) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!history || history.length === 0) {
    container.innerHTML = `<p class="muted">Sem histórico ainda. Clique em <strong>Rodar Varredura Agora</strong> para gerar leituras.</p>`;
    return;
  }

  // Pega últimas 14 leituras em ordem cronológica
  const pts = [...history].slice(0, 14).reverse();
  const w = 520;
  const h = 195;
  const padL = 56;
  const padR = 18;
  const padT = 18;
  const padB = 28;

  const prices = pts.map((p) => Number(p.preco_coletado));
  const goals = pts.map((p) => Number(p.preco_alvo));
  const minVal = Math.min(...prices, ...goals) * 0.94;
  const maxVal = Math.max(...prices, ...goals) * 1.06 || 100;
  const span = maxVal - minVal || 1;

  const xOf = (i) => padL + (pts.length === 1 ? (w - padL - padR) / 2 : (i / (pts.length - 1)) * (w - padL - padR));
  const yOf = (v) => padT + (1 - (v - minVal) / span) * (h - padT - padB);

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(p.preco_coletado).toFixed(1)}`).join(" ");
  const goalPath = pts.map((p, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(p.preco_alvo).toFixed(1)}`).join(" ");

  const circles = pts
    .map((p, i) => {
      const cx = xOf(i).toFixed(1);
      const cy = yOf(p.preco_coletado).toFixed(1);
      const fill = p.alerta_disparado ? "#22c55e" : accentColor;
      return `<circle cx="${cx}" cy="${cy}" r="4.2" fill="${fill}" stroke="#0b1020" stroke-width="1.5">
        <title>${escapeHtml(p.nome_componente)}: ${fmtBRL(p.preco_coletado)} (Meta ${fmtBRL(p.preco_alvo)})</title>
      </circle>`;
    })
    .join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Gráfico de evolução de preços">
      <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${h - padB}" stroke="rgba(148,163,184,0.25)" />
      <line x1="${padL}" y1="${h - padB}" x2="${w - padR}" y2="${h - padB}" stroke="rgba(148,163,184,0.25)" />
      <text x="6" y="${padT + 8}" fill="#94a3b8" font-size="10">${fmtBRL(maxVal)}</text>
      <text x="6" y="${h - padB}" fill="#94a3b8" font-size="10">${fmtBRL(minVal)}</text>
      <path d="${goalPath}" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.85" />
      <path d="${linePath}" fill="none" stroke="${accentColor}" stroke-width="2.5" stroke-linecap="round" />
      ${circles}
      <text x="${padL}" y="${h - 6}" fill="#94a3b8" font-size="10">● Cotação coletada (verde = meta atingida)  --- Meta de preço</text>
    </svg>
  `;
}

// ---------------- Renderização VIEW 1: B2C ----------------

function renderB2CView() {
  const tid = activeTenantIdForView("b2c");
  const profile = state.profiles[tid];
  const silo = state.siloInfo[tid];
  const targets = state.targets[tid] || [];
  const history = state.history[tid] || [];
  const alerts = state.alerts[tid] || [];

  if (profile) {
    document.getElementById("b2c-tenant-name").textContent = profile.nome;
    document.getElementById("b2c-chat-id").textContent = profile.telegram_chat_id;
  }
  if (silo) {
    document.getElementById("b2c-silo-badge").textContent = `Silo: ${silo.silo_filename} (${silo.permissions_octal})`;
    document.getElementById("b2c-quota-text").textContent = `${silo.targets_count} / ${silo.targets_quota} URLs`;
    const pct = Math.min(100, Math.round((silo.targets_count / silo.targets_quota) * 100));
    document.getElementById("b2c-quota-bar").style.width = `${pct}%`;
    document.getElementById("b2c-alerts-count").textContent = silo.alerts_count;
    document.getElementById("b2c-silo-size").textContent = `${(silo.size_bytes / 1024).toFixed(1)} KB`;
  }

  document.getElementById("b2c-history-count").textContent = `${history.length} leituras`;

  const grid = document.getElementById("b2c-targets-grid");
  if (targets.length === 0) {
    grid.innerHTML = `<div class="panel"><p class="muted">Nenhum componente monitorado. Use um preset acima ou clique em <strong>+ Monitorar Peça</strong>.</p></div>`;
  } else {
    grid.innerHTML = targets
      .map((t) => {
        const hit = t.ultimo_preco !== null && t.ultimo_preco <= t.preco_alvo;
        const diff = t.ultimo_preco !== null ? t.preco_alvo - t.ultimo_preco : null;
        const statusBadge =
          t.ultimo_preco === null
            ? `<span class="badge badge-outline">⏳ Aguardando Scan</span>`
            : hit
            ? `<span class="badge badge-success">🔥 META ATINGIDA (-${fmtBRL(Math.max(0, diff))})</span>`
            : `<span class="badge badge-warn">Acima em ${fmtBRL(Math.abs(diff))}</span>`;

        return `
          <article class="hw-card ${hit ? "hit" : ""}">
            <div class="hw-card-top">
              <div>
                <h3 class="hw-title">${escapeHtml(t.nome_componente)}</h3>
                <div class="hw-url">${escapeHtml(t.url)}</div>
              </div>
              ${statusBadge}
            </div>
            <div class="price-row">
              <div class="price-col">
                <span>Última Cotação</span>
                <strong class="${hit ? "text-success" : ""}">${fmtBRL(t.ultimo_preco)}</strong>
              </div>
              <div class="price-col">
                <span>Sua Meta B2C</span>
                <strong>${fmtBRL(t.preco_alvo)}</strong>
              </div>
            </div>
            <div class="muted">Última checagem: ${fmtDate(t.ultima_checagem)}</div>
            <div class="hw-actions">
              <button class="btn btn-success-soft btn-sm" onclick="simulateDrop('${tid}', '${t.id}')">📉 Simular Promoção</button>
              <button class="btn btn-secondary btn-sm" onclick="openEditTargetModal('${tid}', '${t.id}')">✏️ Meta</button>
              <button class="btn btn-danger btn-sm" onclick="deleteTarget('${tid}', '${t.id}')">🗑️ Remover</button>
            </div>
          </article>
        `;
      })
      .join("");
  }

  renderPriceChart("b2c-chart", history, "#8b5cf6");

  // Telegram Preview
  const tgBox = document.getElementById("b2c-telegram-preview");
  if (alerts.length === 0) {
    tgBox.innerHTML = `<div class="tg-bubble"><div class="tg-bot">@HardTrackAlertsBot</div>Nenhum alerta disparado ainda. Clique em <strong>Simular Promoção</strong> ou <strong>Rodar Varredura Agora</strong>!</div>`;
  } else {
    const latest = alerts[0];
    const target = targets.find((x) => x.id === latest.target_id);
    const compName = target ? target.nome_componente : `Componente #${latest.target_id}`;
    const affUrl = target
      ? `${target.url}${target.url.includes("?") ? "&" : "?"}tag=hardtrack-20&utm_source=hardtrack_saas`
      : "https://kabum.com.br/?tag=hardtrack-20";
    tgBox.innerHTML = `
      <div class="tg-bubble">
        <div class="tg-bot">@HardTrackAlertsBot · Push para Chat ID ${escapeHtml(profile?.telegram_chat_id || "")}</div>
        <div><strong>🔥 OPORTUNIDADE DE PREÇO — HardTrack Solutions</strong></div>
        <div style="margin-top:6px;">📦 <strong>${escapeHtml(compName)}</strong></div>
        <div>💰 ${escapeHtml(latest.mensagem)}</div>
        <div class="tg-link">🛒 Link com Tag de Afiliado: ${escapeHtml(affUrl)}</div>
        <div class="tg-time">${fmtDate(latest.timestamp)} · ✓✓ ${escapeHtml(latest.status)}</div>
      </div>
    `;
  }
}

// ---------------- Renderização VIEW 2: B2B ----------------

function renderB2BView() {
  const tid = activeTenantIdForView("b2b");
  const profile = state.profiles[tid];
  const silo = state.siloInfo[tid];
  const targets = state.targets[tid] || [];
  const history = state.history[tid] || [];
  const alerts = state.alerts[tid] || [];
  const qty = state.batchQty;

  if (profile) {
    document.getElementById("b2b-tenant-name").textContent = profile.nome;
    document.getElementById("b2b-chat-id").textContent = profile.telegram_chat_id;
  }
  if (silo) {
    document.getElementById("b2b-silo-badge").textContent = `Silo: ${silo.silo_filename} (${silo.permissions_octal})`;
    document.getElementById("b2b-quota-text").textContent = `${silo.targets_count} / ${silo.targets_quota} URLs`;
    const pct = Math.min(100, Math.round((silo.targets_count / silo.targets_quota) * 100));
    document.getElementById("b2b-quota-bar").style.width = `${pct}%`;
    document.getElementById("b2b-kpi-alerts").textContent = `${silo.alerts_count} alertas`;
    document.getElementById("b2b-kpi-size").textContent = `${(silo.size_bytes / 1024).toFixed(1)} KB · ${silo.permissions_octal}`;
  }

  let hits = 0;
  let totalBatchSavings = 0;
  targets.forEach((t) => {
    if (t.ultimo_preco !== null && t.ultimo_preco <= t.preco_alvo) {
      hits += 1;
      totalBatchSavings += Math.max(0, t.preco_alvo - t.ultimo_preco) * qty;
    }
  });

  document.getElementById("b2b-kpi-targets").textContent = targets.length;
  document.getElementById("b2b-kpi-hits").textContent = hits;
  document.getElementById("b2b-kpi-savings").textContent = fmtBRL(totalBatchSavings);
  document.getElementById("b2b-kpi-batch-label").textContent = `Calculado para lote de ${qty} un.`;
  document.getElementById("b2b-history-count").textContent = `${history.length} registros`;

  const tbody = document.getElementById("b2b-table-body");
  if (targets.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">Nenhum item de estoque cadastrado no silo B2B.</td></tr>`;
  } else {
    tbody.innerHTML = targets
      .map((t) => {
        const hit = t.ultimo_preco !== null && t.ultimo_preco <= t.preco_alvo;
        const unitSave = t.ultimo_preco !== null ? Math.max(0, t.preco_alvo - t.ultimo_preco) : 0;
        const batchSave = unitSave * qty;
        const host = (() => {
          try {
            return new URL(t.url).hostname;
          } catch {
            return t.url;
          }
        })();

        return `
          <tr>
            <td><strong>${escapeHtml(t.nome_componente)}</strong><br/><small class="muted">ID: ${escapeHtml(t.id)}</small></td>
            <td><code>${escapeHtml(host)}</code></td>
            <td><strong class="${hit ? "text-success" : ""}">${fmtBRL(t.ultimo_preco)}</strong></td>
            <td>${fmtBRL(t.preco_alvo)}</td>
            <td class="${batchSave > 0 ? "text-amber" : "muted"}"><strong>${batchSave > 0 ? fmtBRL(batchSave) : "—"}</strong> <small>(${qty}x)</small></td>
            <td>${
              t.ultimo_preco === null
                ? `<span class="badge badge-outline">Pendente</span>`
                : hit
                ? `<span class="badge badge-success">🔥 COMPRAR LOTE</span>`
                : `<span class="badge badge-warn">⏳ AGUARDANDO</span>`
            }</td>
            <td>
              <button class="btn btn-success-soft btn-sm" onclick="simulateDrop('${tid}', '${t.id}')">📉 Promo</button>
              <button class="btn btn-secondary btn-sm" onclick="openEditTargetModal('${tid}', '${t.id}')">✏️</button>
              <button class="btn btn-danger btn-sm" onclick="deleteTarget('${tid}', '${t.id}')">🗑️</button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  renderPriceChart("b2b-chart", history, "#f59e0b");

  const alertsList = document.getElementById("b2b-alerts-list");
  if (alerts.length === 0) {
    alertsList.innerHTML = `<p class="muted">Nenhum alerta auditado ainda.</p>`;
  } else {
    alertsList.innerHTML = alerts
      .slice(0, 8)
      .map(
        (a) => `
        <div class="alert-row">
          <div>
            <strong>${escapeHtml(a.mensagem)}</strong>
            <div class="muted">Alvo #${escapeHtml(a.target_id)} · Canal: ${escapeHtml(a.canal)}</div>
          </div>
          <div class="muted">${fmtDate(a.timestamp)}</div>
        </div>
      `
      )
      .join("");
  }
}

// ---------------- Renderização VIEW 3: COMPARE & SECURITY ----------------

function renderCompareView() {
  const pairs = [
    { prefix: "b2c", tid: DEMO_PERSONAS.b2c.tenant_id },
    { prefix: "b2b", tid: DEMO_PERSONAS.b2b.tenant_id },
  ];

  for (const { prefix, tid } of pairs) {
    const profile = state.profiles[tid];
    const silo = state.siloInfo[tid];
    const targets = state.targets[tid] || [];
    const token = state.tokens[tid] || "";

    document.getElementById(`cmp-${prefix}-title`).textContent = profile ? profile.nome : tid;
    document.getElementById(`cmp-${prefix}-meta`).innerHTML = silo
      ? `
        <div><span>Arquivo Silo</span><strong>${escapeHtml(silo.silo_filename)}</strong></div>
        <div><span>Permissão POSIX</span><strong>${escapeHtml(silo.permissions_octal)}</strong></div>
        <div><span>Cota do Plano</span><strong>${silo.targets_count} / ${silo.targets_quota} URLs</strong></div>
        <div><span>Token Bearer</span><code>${escapeHtml(token.slice(0, 18))}...</code></div>
      `
      : `<div class="muted">Carregando metadados do silo...</div>`;

    const ul = document.getElementById(`cmp-${prefix}-items`);
    ul.innerHTML =
      targets.length === 0
        ? `<li class="muted">Sem componentes cadastrados.</li>`
        : targets
            .map(
              (t) => `
          <li>
            <span><strong>${escapeHtml(t.nome_componente)}</strong></span>
            <span>Meta: <strong>${fmtBRL(t.preco_alvo)}</strong> · Atual: ${fmtBRL(t.ultimo_preco)}</span>
          </li>
        `
            )
            .join("");
  }
}

// ---------------- Ações Interativas (CRUD, Scan, Simulação, CSV) ----------------

async function runScan(tenantId) {
  toast(`Executando varredura isolada no silo '${tenantId}'...`, "info");
  const res = await apiFetch(`/tenants/${tenantId}/scan`, {
    method: "POST",
    headers: authHeaders(tenantId),
  });
  if (res.ok) {
    await loadTenantData(tenantId);
    renderCurrentView();
    const s = res.data;
    toast(
      `Varredura concluída em ${s.duracao_segundos}s: ${s.cotacoes_sucesso}/${s.componentes_checados} cotações · ${s.alertas_disparados} alerta(s)!`,
      s.alertas_disparados > 0 ? "success" : "info"
    );
  } else {
    toast(res.data?.detail || "Erro ao executar varredura.", "error");
  }
}

window.simulateDrop = async function simulateDrop(tenantId, targetId) {
  const list = state.targets[tenantId] || [];
  const item = list.find((t) => t.id === targetId);
  if (!item) return;

  const newMockPrice = Math.max(50, Number((item.preco_alvo * 0.92).toFixed(2)));
  const cleanBase = item.url.startsWith("mock://")
    ? item.url.split("?")[0]
    : `mock://oferta-relampago.com.br/${targetId}`;
  const updatedUrl = `${cleanBase}?price=${newMockPrice.toFixed(2)}`;

  const patchRes = await apiFetch(`/tenants/${tenantId}/targets/${targetId}`, {
    method: "PATCH",
    headers: authHeaders(tenantId),
    body: JSON.stringify({ url: updatedUrl }),
  });
  if (!patchRes.ok) {
    toast(patchRes.data?.detail || "Erro ao simular queda de preço.", "error");
    return;
  }
  await runScan(tenantId);
};

window.deleteTarget = async function deleteTarget(tenantId, targetId) {
  const res = await apiFetch(`/tenants/${tenantId}/targets/${targetId}`, {
    method: "DELETE",
    headers: authHeaders(tenantId),
  });
  if (res.ok) {
    await loadTenantData(tenantId);
    renderCurrentView();
    toast("Componente removido do silo com sucesso.", "success");
  } else {
    toast(res.data?.detail || "Erro ao remover componente.", "error");
  }
};

async function quickAddPreset(view, name, url, targetPrice) {
  const tid = activeTenantIdForView(view);
  const res = await apiFetch(`/tenants/${tid}/targets`, {
    method: "POST",
    headers: authHeaders(tid),
    body: JSON.stringify({
      nome_componente: name,
      url,
      preco_alvo: Number(targetPrice),
    }),
  });
  if (res.ok) {
    toast(`'${name}' adicionado ao silo de ${tid}!`, "success");
    await runScan(tid);
  } else {
    toast(res.data?.detail || `Erro HTTP ${res.status}`, "error");
  }
}

function exportB2BCSV() {
  const tid = activeTenantIdForView("b2b");
  const history = state.history[tid] || [];
  if (history.length === 0) {
    toast("Sem registros de histórico para exportar.", "warn");
    return;
  }
  const header = ["timestamp", "componente", "preco_coletado", "preco_alvo", "alerta_disparado", "url"];
  const rows = history.map((r) => [
    r.timestamp,
    `"${String(r.nome_componente).replace(/"/g, '""')}"`,
    r.preco_coletado,
    r.preco_alvo,
    r.alerta_disparado,
    `"${r.url}"`,
  ]);
  const csv = [header.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `auditoria_${tid}.csv`;
  a.click();
  toast(`CSV 'auditoria_${tid}.csv' exportado com ${history.length} linhas!`, "success");
}

// ---------------- Modal Add/Edit ----------------

function openAddTargetModal(view) {
  const tid = activeTenantIdForView(view);
  document.getElementById("modal-title").textContent = `Novo Componente — Silo ${tid}`;
  document.getElementById("ft-mode").value = "create";
  document.getElementById("ft-id").value = "";
  document.getElementById("ft-name").value = "";
  document.getElementById("ft-url").value = "";
  document.getElementById("ft-price").value = "";
  document.getElementById("modal-target").dataset.tenantId = tid;
  document.getElementById("modal-target").classList.remove("hidden");
}

window.openEditTargetModal = function openEditTargetModal(tenantId, targetId) {
  const item = (state.targets[tenantId] || []).find((t) => t.id === targetId);
  if (!item) return;
  document.getElementById("modal-title").textContent = `Editar Meta — ${item.nome_componente}`;
  document.getElementById("ft-mode").value = "edit";
  document.getElementById("ft-id").value = item.id;
  document.getElementById("ft-name").value = item.nome_componente;
  document.getElementById("ft-url").value = item.url;
  document.getElementById("ft-price").value = item.preco_alvo;
  document.getElementById("modal-target").dataset.tenantId = tenantId;
  document.getElementById("modal-target").classList.remove("hidden");
};

function closeTargetModal() {
  document.getElementById("modal-target").classList.add("hidden");
}

// ---------------- Security Lab Probes ----------------

function logProbe(title, reqDesc, res) {
  const pre = document.getElementById("probe-log");
  const statusIcon = res.status >= 400 ? "✅ BLOQUEADO COM SEGURANÇA" : "⚠️ RESPOSTA INESPERADA";
  const output = [
    `=== ${title} ===`,
    `Requisição: ${reqDesc}`,
    `Status HTTP: ${res.status} (${statusIcon}) | Latência: ${res.elapsed} ms`,
    `Payload de Resposta:`,
    JSON.stringify(res.data, null, 2),
  ].join("\n");
  pre.textContent = output;
  toast(`${title} → HTTP ${res.status}`, res.status >= 400 ? "success" : "error");
}

async function runSecurityProbes() {
  document.getElementById("probe-idor").addEventListener("click", async () => {
    const res = await apiFetch("/tenants/techparts_b2b/targets", {
      headers: authHeaders("joao_b2c"),
    });
    logProbe("1. Invasão Cross-Tenant (IDOR)", "GET /tenants/techparts_b2b/targets [Token: joao_b2c]", res);
  });

  document.getElementById("probe-spoof").addEventListener("click", async () => {
    const res = await apiFetch("/tenants/joao_b2c/targets", {
      headers: authHeaders("joao_b2c", { "X-Tenant-ID": "techparts_b2b" }),
    });
    logProbe("2. Header Spoofing (X-Tenant-ID)", "GET /tenants/joao_b2c/targets [Token: joao_b2c, X-Tenant-ID: techparts_b2b]", res);
  });

  document.getElementById("probe-noauth").addEventListener("click", async () => {
    const res = await apiFetch("/tenants/joao_b2c/targets");
    logProbe("3. Acesso Sem Autenticação", "GET /tenants/joao_b2c/targets [Sem header Authorization]", res);
  });

  document.getElementById("probe-ssrf").addEventListener("click", async () => {
    const res = await apiFetch("/tenants/joao_b2c/targets", {
      method: "POST",
      headers: authHeaders("joao_b2c"),
      body: JSON.stringify({
        nome_componente: "Teste SSRF AWS Metadata",
        url: "http://169.254.169.254/latest/meta-data/",
        preco_alvo: 100,
      }),
    });
    logProbe("4. Ataque SSRF (Cloud Metadata)", "POST /tenants/joao_b2c/targets [url=http://169.254.169.254/latest/meta-data/]", res);
  });

  document.getElementById("probe-traversal").addEventListener("click", async () => {
    const res = await apiFetch("/tenants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: "../etc/passwd",
        nome: "Atacante Traversal",
        tipo: "B2C_ENTUSIASTA",
        telegram_chat_id: "0000",
      }),
    });
    logProbe("5. Path Traversal no Silo", "POST /tenants [tenant_id='../etc/passwd']", res);
  });
}

// ---------------- Navegação ----------------

window.switchView = async function switchView(view) {
  state.currentView = view;
  document.body.className = `theme-${view}`;

  document.querySelectorAll(".mode-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
  });
  document.getElementById("view-b2c").classList.toggle("hidden", view !== "b2c");
  document.getElementById("view-b2b").classList.toggle("hidden", view !== "b2b");
  document.getElementById("view-compare").classList.toggle("hidden", view !== "compare");

  if (view === "compare") {
    await Promise.all([
      loadTenantData(DEMO_PERSONAS.b2c.tenant_id),
      loadTenantData(DEMO_PERSONAS.b2b.tenant_id),
    ]);
  } else {
    await loadTenantData(activeTenantIdForView(view));
  }
  renderCurrentView();
};

function renderCurrentView() {
  const customBar = document.getElementById("custom-tenant-bar");
  if (state.customTenant) {
    customBar.classList.remove("hidden");
    document.getElementById("custom-tenant-label").textContent =
      `${state.customTenant.nome} (${state.customTenant.tenant_id} · ${state.customTenant.tipo})`;
  } else {
    customBar.classList.add("hidden");
  }

  if (state.currentView === "b2c") renderB2CView();
  if (state.currentView === "b2b") renderB2BView();
  if (state.currentView === "compare") renderCompareView();
}

// ---------------- Bootstrap ----------------

async function init() {
  // Healthcheck
  const health = await apiFetch("/health");
  const healthText = document.getElementById("health-text");
  if (health.ok) {
    healthText.textContent = `API Online (v${health.data.version})`;
  } else {
    healthText.textContent = "API Offline";
  }

  // Autentica os dois perfis SaaS demo
  await Promise.all([ensureDemoPersona("b2c"), ensureDemoPersona("b2b")]);
  await Promise.all([
    loadTenantData(DEMO_PERSONAS.b2c.tenant_id),
    loadTenantData(DEMO_PERSONAS.b2b.tenant_id),
  ]);

  // Listeners de navegação
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });

  // Listeners de ações B2C / B2B
  document.getElementById("btn-b2c-scan").addEventListener("click", () => runScan(activeTenantIdForView("b2c")));
  document.getElementById("btn-b2b-scan").addEventListener("click", () => runScan(activeTenantIdForView("b2b")));
  document.getElementById("btn-b2c-add").addEventListener("click", () => openAddTargetModal("b2c"));
  document.getElementById("btn-b2b-add").addEventListener("click", () => openAddTargetModal("b2b"));
  document.getElementById("btn-b2b-csv").addEventListener("click", exportB2BCSV);
  document.getElementById("btn-refresh-compare").addEventListener("click", () => switchView("compare"));

  document.getElementById("b2b-batch-qty").addEventListener("change", (e) => {
    state.batchQty = Number(e.target.value) || 10;
    renderB2BView();
  });

  // Presets rápidos
  document.querySelectorAll(".chip[data-preset]").forEach((chip) => {
    chip.addEventListener("click", () => {
      quickAddPreset(chip.dataset.preset, chip.dataset.name, chip.dataset.url, chip.dataset.target);
    });
  });

  // Modal Target Form
  document.getElementById("modal-close").addEventListener("click", closeTargetModal);
  document.getElementById("modal-cancel").addEventListener("click", closeTargetModal);
  document.getElementById("modal-backdrop").addEventListener("click", closeTargetModal);

  document.getElementById("form-target").addEventListener("submit", async (e) => {
    e.preventDefault();
    const tid = document.getElementById("modal-target").dataset.tenantId;
    const mode = document.getElementById("ft-mode").value;
    const targetId = document.getElementById("ft-id").value;
    const payload = {
      nome_componente: document.getElementById("ft-name").value.trim(),
      url: document.getElementById("ft-url").value.trim(),
      preco_alvo: Number(document.getElementById("ft-price").value),
    };

    const res =
      mode === "edit"
        ? await apiFetch(`/tenants/${tid}/targets/${targetId}`, {
            method: "PATCH",
            headers: authHeaders(tid),
            body: JSON.stringify(payload),
          })
        : await apiFetch(`/tenants/${tid}/targets`, {
            method: "POST",
            headers: authHeaders(tid),
            body: JSON.stringify(payload),
          });

    if (res.ok) {
      closeTargetModal();
      await loadTenantData(tid);
      renderCurrentView();
      toast(mode === "edit" ? "Meta atualizada com sucesso!" : "Componente cadastrado no silo!", "success");
    } else {
      const detail =
        typeof res.data?.detail === "string"
          ? res.data.detail
          : JSON.stringify(res.data?.detail || "Erro de validação");
      toast(`Bloqueado (HTTP ${res.status}): ${detail}`, "error");
    }
  });

  // Novo Tenant + Expurgo LGPD
  document.getElementById("form-new-tenant").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      tenant_id: document.getElementById("nt-id").value.trim(),
      nome: document.getElementById("nt-nome").value.trim(),
      tipo: document.getElementById("nt-tipo").value,
      telegram_chat_id: document.getElementById("nt-chat").value.trim(),
    };
    const res = await apiFetch("/tenants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      state.tokens[res.data.tenant_id] = res.data.access_token;
      state.profiles[res.data.tenant_id] = res.data;
      state.customTenant = res.data;
      toast(`Novo silo 'tenant_${res.data.tenant_id}.json' criado com token HMAC-SHA256!`, "success");
      e.target.reset();
      await switchView(res.data.tipo === "B2B_OFICINA" ? "b2b" : "b2c");
    } else {
      toast(`Erro HTTP ${res.status}: ${res.data?.detail || "Falha ao criar tenant"}`, "error");
    }
  });

  document.getElementById("btn-purge-custom").addEventListener("click", async () => {
    if (!state.customTenant) return;
    const tid = state.customTenant.tenant_id;
    const res = await apiFetch(`/tenants/${tid}`, {
      method: "DELETE",
      headers: authHeaders(tid),
    });
    if (res.ok) {
      toast(res.data.message, "success");
      delete state.tokens[tid];
      state.customTenant = null;
      await switchView("compare");
    } else {
      toast(res.data?.detail || "Erro no expurgo LGPD", "error");
    }
  });

  document.getElementById("btn-back-default").addEventListener("click", async () => {
    state.customTenant = null;
    await switchView("b2c");
  });

  await runSecurityProbes();
  renderCurrentView();
}

init();
