/**
 * Slimec – OCR Einstellungen (Auto Heal + Auto Quest)
 */

(function () {
  const $ = (id) => document.getElementById(id);
  let ocrPollTimer = null;
  let editingCondId = null;
  let activeOcrTab = "heal";

  // Aktueller Charakter, dessen Bedingungen bearbeitet werden
  let editingCharName = null;

  function defaultHeal() {
    return {
      enabled: true,
      intervalMs: 500,
      conditions: [],
      zoom: { enabled: false, targetValue: 720 },
      mining: { enabled: false, region: null, delayMs: 0, tolerance: 75 }
    };
  }

  function getProfileOcr() {
    const prof = window.FiestaApp?.activeProfile?.();
    if (!prof) return { instances: {} };
    if (!prof.ocr) prof.ocr = { instances: {} };
    if (!prof.ocr.instances) prof.ocr.instances = {};
    return prof.ocr;
  }

  function getCharConfig(charName) {
    const ocr = getProfileOcr();
    if (!ocr.instances[charName]) {
      ocr.instances[charName] = defaultHeal();
    }
    // Migration für Zoom und Mining falls noch nicht da
    if (!ocr.instances[charName].zoom) {
      ocr.instances[charName].zoom = { enabled: false, targetValue: 720 };
    }
    if (!ocr.instances[charName].mining) {
      ocr.instances[charName].mining = { enabled: false, region: null, delayMs: 0, tolerance: 75 };
    }
    // Toleranz auf 75 erzwingen
    ocr.instances[charName].mining.tolerance = 75;
    return ocr.instances[charName];
  }

  function getHeal() {
    if (editingCharName) return getCharConfig(editingCharName);
    return defaultHeal();
  }

  function getQuest() {
    const ocr = getProfileOcr();
    if (!ocr.quest) ocr.quest = { enabled: false, questWindowEnabled: false };
    if (ocr.quest.questWindowEnabled === undefined) ocr.quest.questWindowEnabled = false;
    return ocr.quest;
  }

  function questMonitorActive(q) {
    return !!(q && q.enabled && (q.region || q.questWindowRegion));
  }

  function api() {
    return window.pywebview && window.pywebview.api;
  }

  function syncQuestTargetPid() {
    const ocr = getProfileOcr();
    if (!ocr.quest) ocr.quest = { enabled: false };
    const inst = getSelectedInstance();
    ocr.quest.targetPid = inst?.pid ?? null;
  }

  async function pushConfigToBackend() {
    const a = api();
    if (!a) return;
    const ocr = getProfileOcr();
    syncQuestTargetPid();
    await a.ocr_start(JSON.stringify(ocr));
  }

  async function autoStartMonitors() {
    let a = api();
    if (!a) {
        // Warte bis zu 5 Sekunden auf das API
        for (let i = 0; i < 50; i++) {
            await new Promise(r => setTimeout(r, 100));
            a = api();
            if (a) break;
        }
    }
    if (!a) return;
    await pushConfigToBackend();
    startPoll();
  }

  function formatPct(v) {
    if (v == null || Number.isNaN(v)) return "0%";
    return Math.round(v) + "%";
  }

  let detectedInstances = [];
  let selectedInstanceIndex = 0;

  function getSelectedInstance() {
    return detectedInstances[selectedInstanceIndex] || null;
  }

  function clampSelectedIndex() {
    if (!detectedInstances.length) {
      selectedInstanceIndex = 0;
      return;
    }
    if (selectedInstanceIndex >= detectedInstances.length) {
      selectedInstanceIndex = detectedInstances.length - 1;
    }
    if (selectedInstanceIndex < 0) selectedInstanceIndex = 0;
  }

  function updateInstanceIndicator() {
    const ind = $("instance-indicator");
    const total = Math.max(detectedInstances.length, 1);
    const current = detectedInstances.length ? selectedInstanceIndex + 1 : 1;
    if (ind) ind.textContent = `${current} / ${total}`;

    const canCycle = detectedInstances.length > 1;
    const prevBtn = $("btn-instance-prev");
    const nextBtn = $("btn-instance-next");
    if (prevBtn) prevBtn.disabled = !canCycle;
    if (nextBtn) nextBtn.disabled = !canCycle;
  }

  function cycleInstance(delta) {
    if (detectedInstances.length <= 1) return;
    selectedInstanceIndex =
      (selectedInstanceIndex + delta + detectedInstances.length) % detectedInstances.length;
    updateInstanceIndicator();
    updateCompactStatus(getSelectedInstance());
    syncQuestTargetPid();
    void pushConfigToBackend();
    window.FiestaCompact?.refresh?.();
  }

  function syncInstancesFromStatus(instances) {
    const prevPid = detectedInstances[selectedInstanceIndex]?.pid;
    const prevQuestPid = getProfileOcr().quest?.targetPid ?? null;
    detectedInstances = instances || [];
    if (prevPid != null) {
      const idx = detectedInstances.findIndex((i) => i.pid === prevPid);
      selectedInstanceIndex = idx >= 0 ? idx : 0;
    } else {
      selectedInstanceIndex = 0;
    }
    clampSelectedIndex();
    updateInstanceIndicator();
    updateCompactStatus(getSelectedInstance());
    syncQuestTargetPid();
    const newQuestPid = getProfileOcr().quest?.targetPid ?? null;
    if (newQuestPid !== prevQuestPid) {
      void pushConfigToBackend();
    }
    window.FiestaCompact?.refresh?.();
  }

  function getPrimaryCharName() {
    const inst = getSelectedInstance();
    if (inst?.charName) return inst.charName;
    const el = $("compact-char-name");
    if (el && el.dataset.charName) return el.dataset.charName;
    return editingCharName;
  }

  function updateCompactStatus(inst) {
    const panel = $("compact-status-panel");
    if (!panel) return;
    const nameEl = $("compact-char-name");
    const hpFill = $("compact-hp-fill");
    const hpText = $("compact-hp-text");
    const mpFill = $("compact-mp-fill");
    const mpText = $("compact-mp-text");
    const hpStones = $("compact-hp-stones");
    const mpStones = $("compact-mp-stones");

    if (!inst) {
      panel.classList.add("hidden");
      if (nameEl) {
        nameEl.textContent = "—";
        delete nameEl.dataset.charName;
      }
      return;
    }
    panel.classList.remove("hidden");
    if (nameEl) {
      nameEl.textContent = inst.charName || "Unbekannt";
      nameEl.dataset.charName = inst.charName || "";
    }
    const hpPct = inst.hpPercent || 0;
    if (hpFill) hpFill.style.width = hpPct + "%";
    if (hpText) hpText.textContent = `${inst.hpCurrent || 0} / ${inst.hpMax || 0} (${Math.round(hpPct)}%)`;
    const mpPct = inst.mpPercent || 0;
    if (mpFill) mpFill.style.width = mpPct + "%";
    if (mpText) mpText.textContent = `${inst.mpCurrent || 0} / ${inst.mpMax || 0} (${Math.round(mpPct)}%)`;
    if (hpStones) hpStones.textContent = inst.hpStone || 0;
    if (mpStones) mpStones.textContent = inst.mpStone || 0;
    lastPrimaryPid = inst.pid;
  }

  function updateLiveDisplay(status) {
    const container = $("stat-cards-container");
    if (!status.instances) return;

    const discoveryEl = $("discovery-status-container");
    const discoveryText = $("discovery-status-text");
    if (discoveryEl && discoveryText) {
      const showDiscovery = status.instances.length === 0;
      discoveryEl.classList.toggle("hidden", !showDiscovery || status.discoveryStatus === "verbunden");
      if (status.discoveryStatus) {
        discoveryText.textContent = status.discoveryStatus.charAt(0).toUpperCase() + status.discoveryStatus.slice(1);
      }
    }

    syncInstancesFromStatus(status.instances);

    if (!container) return;

    const currentPids = Array.from(container.querySelectorAll(".stat-card-instance")).map(el => parseInt(el.dataset.pid));
    const newPids = status.instances.map(inst => inst.pid);

    currentPids.forEach(pid => {
      if (!newPids.includes(pid)) {
        container.querySelector(`.stat-card-instance[data-pid="${pid}"]`)?.remove();
      }
    });

    status.instances.forEach(inst => {
      let card = container.querySelector(`.stat-card-instance[data-pid="${inst.pid}"]`);
      if (!card) {
        card = createStatCard(inst);
        container.appendChild(card);
      }
      updateStatCard(card, inst);
    });

    const qs = $("quest-status-line");
    if (qs && status.quest) {
      const q = status.quest;
      if (q.busy) qs.textContent = "Quest: Sequenz läuft…";
      else if (q.lastTrigger) qs.textContent = "Quest: " + q.lastTrigger;
      else qs.textContent = q.running ? "Quest: aktiv" : "Quest: inaktiv";
    }
  }

  function createStatCard(inst) {
    const div = document.createElement("div");
    div.className = "stat-card-instance";
    div.dataset.pid = inst.pid;
    div.dataset.charName = inst.charName || "";
    
    div.innerHTML = `
      <div class="stat-card-header">
        <span class="stat-card-name">${inst.charName || "Unbekannt"}</span>
        <button type="button" class="stat-card-settings-btn">⚙</button>
      </div>
      <div class="stat-bar-compact hp">
        <div class="stat-bar-fill-compact hp" style="width: 0%"></div>
        <div class="stat-bar-text hp-text">0 / 0 (0%)</div>
      </div>
      <div class="stat-bar-compact mp">
        <div class="stat-bar-fill-compact mp" style="width: 0%"></div>
        <div class="stat-bar-text mp-text">0 / 0 (0%)</div>
      </div>
      <div class="stat-row-stones">
        <span class="stat-stone-item">HP STONES: <b class="hp-stones stat-stone-val">0</b></span>
        <span class="stat-stone-item">MP STONES: <b class="mp-stones stat-stone-val">0</b></span>
      </div>
    `;

    div.querySelector(".stat-card-settings-btn").onclick = () => {
      openOcrSettings(inst.charName || "Unbekannt");
    };

    return div;
  }

  function updateStatCard(card, inst) {
    const hpFill = card.querySelector(".stat-bar-fill-compact.hp");
    const hpText = card.querySelector(".stat-bar-text.hp-text");
    const mpFill = card.querySelector(".stat-bar-fill-compact.mp");
    const mpText = card.querySelector(".stat-bar-text.mp-text");
    const hpStones = card.querySelector(".hp-stones");
    const mpStones = card.querySelector(".mp-stones");
    const nameEl = card.querySelector(".stat-card-name");

    if (nameEl.textContent !== (inst.charName || "Unbekannt")) {
        nameEl.textContent = inst.charName || "Unbekannt";
        card.dataset.charName = inst.charName || "";
    }

    const hpPct = inst.hpPercent || 0;
    hpFill.style.width = hpPct + "%";
    hpText.textContent = `${inst.hpCurrent || 0} / ${inst.hpMax || 0} (${Math.round(hpPct)}%)`;

    const mpPct = inst.mpPercent || 0;
    mpFill.style.width = mpPct + "%";
    mpText.textContent = `${inst.mpCurrent || 0} / ${inst.mpMax || 0} (${Math.round(mpPct)}%)`;

    if (hpStones) hpStones.textContent = inst.hpStone || 0;
    if (mpStones) mpStones.textContent = inst.mpStone || 0;
  }

  function statShort(stat) {
    return stat === "mp" ? "MP" : "HP";
  }

  function formatConditionMid(c) {
    const op = c.operator || "<=";
    const suffix = c.mode === "percent" ? "%" : "";
    return `${op} ${c.threshold}${suffix}`;
  }

  function renderConditions() {
    const list = $("ocr-conditions-box");
    if (!list) return;
    list.innerHTML = "";
    const heal = getHeal();

    if (!heal.conditions.length) {
      const empty = document.createElement("div");
      empty.className = "ocr-cond-empty";
      empty.textContent = "Keine Bedingungen – optional für Auto-Tasten";
      list.appendChild(empty);
      return;
    }

    heal.conditions.forEach((c, i) => {
      const row = document.createElement("div");
      row.className = "ocr-cond-row" + (c.enabled ? "" : " disabled");
      if (i > 0) row.classList.add("has-border");
      row.innerHTML = `
        <span class="ah-col-stat">${statShort(c.stat)}</span>
        <span class="ah-col-rule">${formatConditionMid(c)}</span>
        <span class="ah-col-key">${(c.key || "?").toUpperCase()}</span>`;
      row.addEventListener("click", () => openCondModal(c.id));
      list.appendChild(row);
    });
  }

  function syncHealFormFromProfile() {
    const heal = getHeal();
    if ($("ocr-enabled")) $("ocr-enabled").checked = !!heal.enabled;
    if ($("ocr-interval")) $("ocr-interval").value = heal.intervalMs ?? 500;
    renderConditions();
  }

  function syncZoomFormFromProfile() {
    const config = getHeal();
    const zoom = config.zoom || { enabled: false, targetValue: 720 };
    if ($("char-zoom-enabled")) $("char-zoom-enabled").checked = !!zoom.enabled;
    if ($("char-zoom-value")) $("char-zoom-value").value = zoom.targetValue ?? 720;
  }

  function syncMiningFormFromProfile() {
    const config = getHeal();
    const mining = config.mining || { enabled: false, region: null, delayMs: 0, tolerance: 75 };
    if ($("mining-enabled")) $("mining-enabled").checked = !!mining.enabled;
    
    if ($("mining-region-info")) {
      const r = mining.region;
      $("mining-region-info").textContent = r
        ? `${r.width}x${r.height} @ ${r.left},${r.top}`
        : "Kein Bereich";
    }
  }

  function syncQuestTogglesFromProfile() {
    const q = getQuest();
    if ($("quest-enabled")) $("quest-enabled").checked = !!q.enabled;
    if ($("quest-window-enabled")) $("quest-window-enabled").checked = !!q.questWindowEnabled;
  }

  async function applyQuestEnabled(enabled) {
    const q = getQuest();
    q.enabled = !!enabled;
    syncQuestTogglesFromProfile();
    window.FiestaApp?.saveState?.();
    const a = api();
    if (!a) return;
    await pushConfigToBackend();
    if (questMonitorActive(q)) await a.quest_start();
    else if (a.quest_stop) await a.quest_stop();
  }

  function syncQuestFormFromProfile() {
    const q = getQuest();
    if ($("quest-enabled")) $("quest-enabled").checked = !!q.enabled;
    if ($("quest-space-count")) $("quest-space-count").value = q.spaceCount || 10;
    if ($("quest-space-interval")) $("quest-space-interval").value = q.spaceIntervalMs || 100;
    
    if ($("quest-window-enabled")) $("quest-window-enabled").checked = !!q.questWindowEnabled;
    if ($("quest-window-interval")) {
      $("quest-window-interval").value = q.questWindowIntervalMs || 1000;
    }
    if ($("quest-window-cooldown")) {
      $("quest-window-cooldown").value = q.questWindowCooldownMs || 1500;
    }
    if ($("quest-window-key")) {
      $("quest-window-key").value = q.questWindowKey || "l";
    }

    if ($("quest-region-info")) {
      const r = q.region;
      $("quest-region-info").textContent = r
        ? `${r.width}x${r.height} @ ${r.left},${r.top}`
        : "Kein Bereich";
    }
    if ($("quest-click-info")) {
      const c = q.clickTarget;
      $("quest-click-info").textContent = c ? `${c.x}, ${c.y}` : "Nicht gesetzt";
    }
    if ($("quest-window-region-info")) {
      const r = q.questWindowRegion;
      $("quest-window-region-info").textContent = r
        ? `${r.width}x${r.height} @ ${r.left},${r.top}`
        : "Kein Bereich";
    }
  }

  function syncQuestFormToProfile() {
    const q = getQuest();
    if ($("quest-enabled")) q.enabled = $("quest-enabled").checked;
    if ($("quest-space-count")) q.spaceCount = parseInt($("quest-space-count").value, 10) || 10;
    if ($("quest-space-interval")) q.spaceIntervalMs = parseInt($("quest-space-interval").value, 10) || 100;
    
    if ($("quest-window-enabled")) q.questWindowEnabled = $("quest-window-enabled").checked;
    if ($("quest-window-interval")) {
      q.questWindowIntervalMs = parseInt($("quest-window-interval").value, 10) || 1000;
    }
    if ($("quest-window-cooldown")) {
      q.questWindowCooldownMs = parseInt($("quest-window-cooldown").value, 10) || 1500;
    }
    if ($("quest-window-key")) {
      q.questWindowKey = ($("quest-window-key").value || "l").trim().toLowerCase();
    }
  }

  const FEATURE_SETTINGS_TITLES = {
    heal: "Auto Heal Settings",
    zoom: "Ultra Zoom Settings",
    mining: "Fast Mining Settings",
    quest: "Auto Quest Settings",
  };

  function showFeaturePane(tab) {
    activeOcrTab = tab;
    ["heal", "zoom", "mining", "quest"].forEach((t) => {
      $("ocr-tab-" + t)?.classList.toggle("hidden", t !== tab);
    });
    const title = $("ocr-settings-title");
    if (title) title.textContent = FEATURE_SETTINGS_TITLES[tab] || "Settings";
  }

  const DEFAULT_COND_COOLDOWN_MS = 1500;
  const DEFAULT_COND_KEY_DURATION_MS = 80;

  function defaultCondition() {
    return {
      id: "c_" + Math.random().toString(36).slice(2, 9),
      enabled: true,
      stat: "hp",
      mode: "percent",
      operator: "<=",
      threshold: 50,
      key: "q",
      cooldownMs: DEFAULT_COND_COOLDOWN_MS,
      keyDurationMs: DEFAULT_COND_KEY_DURATION_MS,
    };
  }

  function openCondModal(id) {
    const heal = getHeal();
    let c;
    if (id) {
      c = heal.conditions.find((x) => x.id === id);
      editingCondId = id;
      $("ocr-cond-delete").style.display = "block";
      $("ocr-cond-title").textContent = "Bedingung bearbeiten";
    } else {
      c = defaultCondition();
      editingCondId = c.id;
      $("ocr-cond-delete").style.display = "none";
      $("ocr-cond-title").textContent = "Neue Bedingung";
    }
    // $("ocr-cond-enabled").checked = c.enabled; // Entfernt
    $("ocr-cond-stat").value = c.stat;
    $("ocr-cond-mode").value = c.mode;
    $("ocr-cond-op").value = c.operator;
    $("ocr-cond-threshold").value = c.threshold;
    $("ocr-cond-key").value = c.key;
    $("ocr-cond-modal").classList.remove("hidden");
  }

  function closeCondModal() {
    $("ocr-cond-modal").classList.add("hidden");
    editingCondId = null;
  }

  function saveCondModal() {
    const heal = getHeal();
    if (!heal.conditions) heal.conditions = [];
    
    let c = heal.conditions.find((x) => x.id === editingCondId);
    
    if (!c) {
      c = { id: editingCondId };
      heal.conditions.push(c);
    }
    
    c.enabled = true;
    c.stat = $("ocr-cond-stat").value;
    c.mode = $("ocr-cond-mode").value;
    c.operator = $("ocr-cond-op").value;
    c.threshold = parseFloat($("ocr-cond-threshold").value) || 0;
    c.key = ($("ocr-cond-key").value || "q").trim().toLowerCase();
    c.cooldownMs = DEFAULT_COND_COOLDOWN_MS;
    c.keyDurationMs = DEFAULT_COND_KEY_DURATION_MS;
    
    closeCondModal();
    renderConditions();
    
    if (window.FiestaApp?.saveState) window.FiestaApp.saveState();
    pushConfigToBackend();
  }

  function captureCondKey(e) {
    e.preventDefault();
    let key = e.key;
    if (key === " ") key = "space";
    $("ocr-cond-key").value = key.length === 1 ? key.toLowerCase() : key.toLowerCase();
  }

  async function pollStatus() {
    const a = api();
    if (!a) return;
    try {
      updateLiveDisplay(await a.ocr_get_status());
    } catch (_) {}
  }

  function startPoll() {
    stopPoll();
    ocrPollTimer = setInterval(pollStatus, 400);
    pollStatus();
  }

  function stopPoll() {
    if (ocrPollTimer) clearInterval(ocrPollTimer);
    ocrPollTimer = null;
  }

  function hasPremiumRank() {
    return Number(window.FiestaApp?.currentUser?.rank ?? 1) >= 2;
  }

  function applyModalRankRestrictions() {
    /* Premium-Features werden über openFeatureSettings blockiert – keine Tabs mehr. */
  }

  function openFeatureSettings(feature, charName) {
    if ((feature === "mining" || feature === "quest") && !hasPremiumRank()) {
      alert("Premium-Member erforderlich (Rank 2+).");
      return;
    }
    const tabMap = { heal: "heal", zoom: "zoom", mining: "mining", quest: "quest" };
    const tab = tabMap[feature] || "heal";

    if (tab === "quest") {
      editingCharName = charName || getPrimaryCharName();
      syncQuestFormFromProfile();
    } else {
      editingCharName = charName || getPrimaryCharName() || "Unbekannt";
      if (tab === "heal") syncHealFormFromProfile();
      else if (tab === "zoom") syncZoomFormFromProfile();
      else if (tab === "mining") syncMiningFormFromProfile();
    }

    showFeaturePane(tab);
    $("ocr-settings-modal").classList.remove("hidden");
  }

  function openOcrSettings(charName, tab) {
    openFeatureSettings(tab || "heal", charName);
  }

  async function setCharHealEnabled(charName, enabled) {
    const cfg = getCharConfig(charName);
    cfg.enabled = !!enabled;
    window.FiestaApp?.saveState?.();
    await pushConfigToBackend();
    window.FiestaCompact?.refresh?.();
  }

  async function setCharMiningEnabled(charName, enabled) {
    if (!hasPremiumRank()) return;
    const cfg = getCharConfig(charName);
    cfg.mining.enabled = !!enabled;
    window.FiestaApp?.saveState?.();
    await pushConfigToBackend();
  }

  async function setQuestEnabled(enabled) {
    if (!hasPremiumRank()) return;
    await applyQuestEnabled(enabled);
    window.FiestaCompact?.refresh?.();
  }

  function closeOcrSettings() {
    window.FiestaApp?.saveState?.();
    pushConfigToBackend();
    $("ocr-settings-modal").classList.add("hidden");
    editingCharName = null;
    window.FiestaCompact?.refresh?.();
  }

  function bindQuestFieldChanges() {
    const modalToggle = $("quest-enabled");
    if (modalToggle) {
      modalToggle.addEventListener("change", () => applyQuestEnabled(modalToggle.checked));
    }

    const ids = [
      "quest-space-count",
      "quest-space-interval",
      "quest-window-enabled",
      "quest-window-interval",
      "quest-window-cooldown",
      "quest-window-key",
    ];
    const onChange = async () => {
      syncQuestFormToProfile();
      window.FiestaApp?.saveState?.();
      await pushConfigToBackend();
      const q = getQuest();
      const a = api();
      if (!a) return;
      if (questMonitorActive(q)) await a.quest_start();
      else if (a.quest_stop) await a.quest_stop();
    };
    ids.forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", onChange);
      if (el.type === "text" || el.type === "number") el.addEventListener("blur", onChange);
    });
  }

  function initOcrUi() {
    // $("btn-ocr-settings").onclick = openOcrSettings; // Entfernt, da nun pro Karte
    const closeBtn = $("ocr-settings-close");
    if (closeBtn) closeBtn.onclick = closeOcrSettings;

    const ocrEnabled = $("ocr-enabled");
    if (ocrEnabled) {
      ocrEnabled.onchange = async () => {
        if (!editingCharName) return;
        getHeal().enabled = ocrEnabled.checked;
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
      };
    }

    const intervalInput = $("ocr-interval");
    if (intervalInput) {
        intervalInput.onchange = async () => {
          if (!editingCharName) return;
          getHeal().intervalMs = parseInt(intervalInput.value, 10) || 500;
          window.FiestaApp?.saveState?.();
          await pushConfigToBackend();
        };
    }

    $("btn-ocr-add-cond").onclick = () => openCondModal();
    $("ocr-cond-cancel").onclick = closeCondModal;
    $("ocr-cond-save").onclick = saveCondModal;
    $("ocr-cond-delete").onclick = () => {
      const heal = getHeal();
      heal.conditions = heal.conditions.filter((x) => x.id !== editingCondId);
      closeCondModal();
      window.FiestaApp?.saveState?.();
      pushConfigToBackend();
      renderConditions();
    };

    $("ocr-cond-key").onkeydown = captureCondKey;

    const charZoomEnabled = $("char-zoom-enabled");
    if (charZoomEnabled) {
      charZoomEnabled.onchange = async () => {
        if (!editingCharName) return;
        const config = getHeal();
        config.zoom.enabled = charZoomEnabled.checked;
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
      };
    }

    const charZoomValue = $("char-zoom-value");
    if (charZoomValue) {
      charZoomValue.onchange = async () => {
        if (!editingCharName) return;
        const config = getHeal();
        config.zoom.targetValue = parseInt(charZoomValue.value, 10) || 720;
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
      };
    }

    const miningEnabled = $("mining-enabled");
    if (miningEnabled) {
      miningEnabled.onchange = async () => {
        if (!editingCharName) return;
        const config = getHeal();
        config.mining.enabled = miningEnabled.checked;
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
      };
    }

    $("btn-mining-region").onclick = async () => {
      const a = api();
      if (!a) return;
      // Wir nutzen ocr_select_region, da es den gleichen Overlay nutzt
      const res = await a.ocr_select_region();
      if (res.ok) {
        const config = getHeal();
        config.mining.region = res.region;
        syncMiningFormFromProfile();
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
      }
    };

    $("btn-quest-region").onclick = async () => {
      const a = api();
      if (!a) return;
      const res = await a.ocr_select_quest_region();
      if (res.ok) {
        const q = getQuest();
        q.region = res.region;
        syncQuestFormFromProfile();
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
        if (questMonitorActive(q)) await a.quest_start();
        else if (a.quest_stop) await a.quest_stop();
      }
    };

    $("btn-quest-click").onclick = async () => {
      const a = api();
      if (!a) return;
      const res = await a.quest_pick_click_target();
      if (res.ok) {
        const q = getQuest();
        q.clickTarget = res.point;
        syncQuestFormFromProfile();
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
        if (questMonitorActive(q)) await a.quest_start();
        else if (a.quest_stop) await a.quest_stop();
      }
    };

    $("btn-quest-window-region").onclick = async () => {
      const a = api();
      if (!a) return;
      const res = await a.ocr_select_quest_window_region();
      if (res.ok) {
        const q = getQuest();
        q.questWindowRegion = res.region;
        syncQuestFormFromProfile();
        window.FiestaApp?.saveState?.();
        await pushConfigToBackend();
        if (questMonitorActive(q)) await a.quest_start();
        else if (a.quest_stop) await a.quest_stop();
      }
    };

    bindQuestFieldChanges();

    // Hilfe Modal Logik
    const helpModal = $("help-modal");
    const helpImg = $("help-modal-img");
    const helpClose = $("help-modal-close");

    const showHelp = (imgName) => {
      if (!helpModal || !helpImg) return;
      helpImg.src = `images/help/${imgName}`;
      helpModal.classList.remove("hidden");
    };

    if (helpClose) {
      helpClose.onclick = () => helpModal.classList.add("hidden");
    }

    document.querySelectorAll(".btn-help-icon").forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const img = btn.dataset.help;
        if (img) showHelp(img);
      };
    });

    window.FiestaOcr = {
      onProfileSwitch: async () => {
        await autoStartMonitors();
        window.FiestaCompact?.refresh?.();
      },
      pushConfig: pushConfigToBackend,
      autoStartMonitor: autoStartMonitors,
      startPoll,
      stopPoll,
      getPrimaryCharName,
      getSelectedInstance,
      cycleInstance,
      updateInstanceIndicator,
      openFeatureSettings,
      openOcrSettings,
      setCharHealEnabled,
      setCharMiningEnabled,
      setQuestEnabled,
      applyModalRankRestrictions,
    };

    autoStartMonitors();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initOcrUi);
  } else {
    initOcrUi();
  }
})();
