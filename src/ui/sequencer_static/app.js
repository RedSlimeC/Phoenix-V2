/**
 * FiestaBot – DAW Tasten-Sequencer (Tabs, Profile, Multi-Select)
 */

let zoomLevel = 120;
const PX_PER_SEC = () => zoomLevel;
const SNAP_MS = 50;
const MIN_DURATION_MS = 50;
const DEFAULT_TRACKS = 3;
const STORAGE_KEY = "fiestabot_state_v3";
const ZOOM_MIN = 40;
const ZOOM_MAX = 400;

const $ = (id) => document.getElementById(id);

let state = null;
let history = [];
let redoStack = [];
const MAX_HISTORY = 50;

function pushHistory() {
  if (!state) return;
  const snap = JSON.stringify(state);
  if (history.length > 0 && history[history.length - 1] === snap) return;
  history.push(snap);
  if (history.length > MAX_HISTORY) history.shift();
  redoStack = [];
}

function undo() {
  if (history.length <= 1) return;
  const current = history.pop();
  redoStack.push(current);
  const prev = history[history.length - 1];
  state = JSON.parse(prev);
  render();
  saveState(false); // Nicht pushen
}

function redo() {
  if (redoStack.length === 0) return;
  const next = redoStack.pop();
  history.push(next);
  state = JSON.parse(next);
  render();
  saveState(false);
}

let selectedIds = new Set();
let editingId = null;
let dragState = null;
let playheadDrag = false;
let marqueeState = null;
let playheadRaf = null;
let contextBlockId = null;
let laneMenuAt = null;

function uid(prefix = "") {
  return (prefix || "id_") + Math.random().toString(36).slice(2, 11);
}

function msToPx(ms) {
  return (ms / 1000) * PX_PER_SEC();
}

function pxToMs(px) {
  return (px / PX_PER_SEC()) * 1000;
}

function snapMs(ms) {
  return Math.round(ms / SNAP_MS) * SNAP_MS;
}

function formatTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function playheadRulerLeft() {
  return msToPx(state.playheadMs) + "px";
}

function playheadLineLeft() {
  return `calc(var(--label-width) + ${msToPx(state.playheadMs)}px)`;
}

function pywebviewApi() {
  return window.pywebview && window.pywebview.api;
}

const I18N = {
  en: {
    account: "Account",
    settings: "Settings",
    help: "Help",
    close: "Close",
    settings_section: "Section",
    settings_language: "Language",
    settings_keybindings: "Keybindings",
    settings_address: "Addresses",
    settings_extras: "Extras",
    slimec_icon: "Slimec Icon",
    lang_de: "German",
    lang_en: "English",
    kb_toggle_play: "Sequencer start/stop",
    kb_reset_timeline: "Reset timeline",
    kb_toggle_record: "Start / stop recording",
    kb_press_key: "Press a key…",
    nav_account_body:
      "<p>Local profile without cloud login. Export/import and save under ~/.fiestabot/profiles/</p>",
    nav_help_body:
      "<p><strong>Sequencer:</strong> Right-click a track for blocks. <strong>Float:</strong> Slime icon when the window is not active.</p>",
  },
};

function defaultAppSettings() {
  return {
    language: "en",
    keybindings: { resetTimeline: "f3" },
    ultraZoom: { enabled: false, targetValue: 720 },
  };
}

function isSequencerPage() {
  return !!document.getElementById("editor-scroll");
}

function getUltraZoomSettings() {
  const s = getAppSettings();
  if (!s.ultraZoom) s.ultraZoom = defaultAppSettings().ultraZoom;
  return s.ultraZoom;
}

function ultraZoomAddresses(st) {
  const fromInstances = (st.instances || []).map((i) => i.address).filter(Boolean);
  if (fromInstances.length) return fromInstances;
  return st.address ? [st.address] : [];
}

function ultraZoomInstanceCount(st) {
  return st.instanceCount ?? ultraZoomAddresses(st).length;
}

function renderUltraZoomTooltip(st) {
  const tip = document.createElement("span");
  tip.className = "uz-status-tip";
  tip.setAttribute("role", "tooltip");

  const count = document.createElement("span");
  count.className = "uz-status-tip-count";
  count.textContent = `${ultraZoomInstanceCount(st)} x detected`;
  tip.appendChild(count);

  for (const addr of ultraZoomAddresses(st)) {
    const row = document.createElement("span");
    row.className = "uz-status-tip-addr";
    row.textContent = addr;
    tip.appendChild(row);
  }

  return tip;
}

function updateUltraZoomStatus(st) {
  const el = $("ultra-zoom-status");
  if (!el) return;
  el.classList.remove("error", "activating", "active-ready");
  el.replaceChildren();
  if (!st) return;

  if (st.activating) {
    el.textContent = "activating...";
    el.classList.add("activating");
    return;
  }
  if (st.error && !st.active) {
    el.textContent = st.error;
    el.classList.add("error");
    return;
  }
  if (st.active) {
    const label = document.createElement("span");
    label.className = "uz-status-label";
    label.textContent = "activated";
    el.classList.add("active-ready");
    if (st.warning) el.classList.add("error");
    el.append(label, renderUltraZoomTooltip(st));
    return;
  }
}

async function applyUltraZoom(enabled, targetValue) {
  const api = pywebviewApi();
  const uz = getUltraZoomSettings();
  uz.enabled = !!enabled;
  uz.targetValue = Number(targetValue) || 720;
  if ($("ultra-zoom-enabled")) $("ultra-zoom-enabled").checked = uz.enabled;
  if ($("feat-ultra-zoom")) $("feat-ultra-zoom").checked = uz.enabled;
  if ($("char-zoom-enabled")) $("char-zoom-enabled").checked = uz.enabled;
  if ($("ultra-zoom-value")) $("ultra-zoom-value").value = uz.targetValue;
  if ($("char-zoom-value")) $("char-zoom-value").value = uz.targetValue;
  saveState();

  if (!api?.zoom_enable) {
    updateUltraZoomStatus({ error: "Only available in py main.py" });
    return;
  }

  if (!uz.enabled) {
    const st = await api.zoom_disable();
    updateUltraZoomStatus(st);
    return;
  }

  updateUltraZoomStatus({ activating: true });
  const res = await api.zoom_enable(uz.targetValue);
  if (!res?.ok) {
    uz.enabled = false;
    if ($("ultra-zoom-enabled")) $("ultra-zoom-enabled").checked = false;
    if ($("feat-ultra-zoom")) $("feat-ultra-zoom").checked = false;
    if ($("char-zoom-enabled")) $("char-zoom-enabled").checked = false;
    saveState();
    updateUltraZoomStatus(res);
    return;
  }
  updateUltraZoomStatus(res);
}

function syncUltraZoomFromSettings() {
  const uz = getUltraZoomSettings();
  if ($("ultra-zoom-enabled")) $("ultra-zoom-enabled").checked = !!uz.enabled;
  if ($("feat-ultra-zoom")) $("feat-ultra-zoom").checked = !!uz.enabled;
  if ($("char-zoom-enabled")) $("char-zoom-enabled").checked = !!uz.enabled;
  if ($("ultra-zoom-value")) $("ultra-zoom-value").value = uz.targetValue ?? 720;
  if ($("char-zoom-value")) $("char-zoom-value").value = uz.targetValue ?? 720;
}

function bindUltraZoomUi() {
  syncUltraZoomFromSettings();
  $("ultra-zoom-enabled")?.addEventListener("change", () => {
    applyUltraZoom(
      $("ultra-zoom-enabled").checked,
      Number($("ultra-zoom-value")?.value) || 720
    );
  });
  $("ultra-zoom-value")?.addEventListener("change", async () => {
    const uz = getUltraZoomSettings();
    uz.targetValue = Number($("ultra-zoom-value").value) || 720;
    saveState();
    const api = pywebviewApi();
    if (uz.enabled && api?.zoom_set_target) {
      const st = await api.zoom_set_target(uz.targetValue);
      updateUltraZoomStatus(st);
    }
  });
  const api = pywebviewApi();
  if (api?.zoom_get_status) {
    api.zoom_get_status().then(updateUltraZoomStatus).catch(() => {});
  }
}

function getAppSettings() {
  if (!state.appSettings) state.appSettings = defaultAppSettings();
  if (!state.appSettings.keybindings) {
    state.appSettings.keybindings = defaultAppSettings().keybindings;
  }
  return state.appSettings;
}

function t(key) {
  return I18N.en[key] || key;
}

function formatBindingLabel(binding) {
  if (!binding) return "?";
  const b = binding.trim();
  if (b.length === 1) return b.toUpperCase();
  return b.replace(/^f(\d+)$/i, (_, n) => `F${n}`).replace(/^./, (c) => c.toUpperCase());
}

function bindingFromKeyboardEvent(e) {
  const k = e.key;
  if (!k || ["Shift", "Control", "Alt", "Meta"].includes(k)) return null;
  if (k.length === 1) return k.toLowerCase();
  return k.toLowerCase();
}

function keyEventMatchesBinding(e, binding) {
  const fromEvent = bindingFromKeyboardEvent(e);
  if (!fromEvent || !binding) return false;
  return fromEvent === binding.trim().toLowerCase();
}

let capturingKbField = null;

function whenPywebviewReady(cb) {
  if (pywebviewApi()) {
    cb();
    return;
  }
  const timer = setInterval(() => {
    if (pywebviewApi()) {
      clearInterval(timer);
      cb();
    }
  }, 50);
}

async function syncKeybindingsToBackend() {
  const api = pywebviewApi();
  if (!api?.set_keybindings) return;
  const kb = getAppSettings().keybindings;
  await api.set_keybindings(kb.resetTimeline);
  await syncTriggerKeysToBackend();
}

function collectTriggerKeys() {
  const prof = activeProfile();
  if (!prof) return [];
  const keys = new Set();
  for (const seq of prof.sequences || []) {
    if (normalizeSeqTriggerMode(seq) === "keyPress" && seq.triggerKey?.trim()) {
      keys.add(normalizeTriggerKey(seq.triggerKey));
    }
  }
  return [...keys];
}

async function syncTriggerKeysToBackend() {
  const api = pywebviewApi();
  if (!api?.set_sequence_trigger_keys) return;
  await api.set_sequence_trigger_keys(JSON.stringify(collectTriggerKeys()));
}

function applyLanguage() {
  document.documentElement.lang = "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (!key) return;
    const val = t(key);
    if (el.tagName === "OPTION") el.textContent = val;
    else el.textContent = val;
  });
  const closeBtn = $("nav-modal-close");
  if (closeBtn) closeBtn.textContent = t("close");
  const ocrClose = $("ocr-settings-close");
  if (ocrClose) ocrClose.textContent = "Close";
}

async function refreshAddressList() {
  const listEl = $("address-list");
  if (!listEl) return;
  const api = pywebviewApi();
  if (!api?.get_fiesta_processes) {
    listEl.innerHTML = '<div class="address-list-error">API not available</div>';
    return;
  }

  listEl.innerHTML = '<div class="address-list-loading">Loading...</div>';
  try {
    const res = await api.get_fiesta_processes();
    if (!res?.ok || !res.processes) {
      listEl.innerHTML = '<div class="address-list-empty">No Fiesta.exe found</div>';
      return;
    }
    if (res.processes.length === 0) {
      listEl.innerHTML = '<div class="address-list-empty">No running Fiesta.exe instances</div>';
      return;
    }

    listEl.innerHTML = res.processes
      .map(
        (p) => `
      <div class="address-item-complex">
         <div class="address-item-header">
           <span class="addr-pid">PID: ${p.pid}</span>
           <span class="addr-base">EXE: 0x${p.base}</span>
           <span class="addr-playerbase">Player: 0x${p.playerBase || "???"}</span>
         </div>
         <div class="address-details vertical">
            <div class="address-row-detail"><span>Char Name:</span> <b>${p.stats?.charName || "—"}</b> <small>(0x${p.offsets?.CHAR_NAME || "???"})</small></div>
            <div class="address-row-detail"><span>Current HP:</span> <b>${p.stats?.hpCurrent || 0}</b> <small>(0x${p.offsets?.CURRENT_HP || "???"})</small></div>
            <div class="address-row-detail"><span>Maximum HP:</span> <b>${p.stats?.hpMax || 0}</b> <small>(0x${p.offsets?.MAX_HP || "???"})</small></div>
            <div class="address-row-detail"><span>Current SP:</span> <b>${p.stats?.mpCurrent || 0}</b> <small>(0x${p.offsets?.CURRENT_MP || "???"})</small></div>
            <div class="address-row-detail"><span>Maximum SP:</span> <b>${p.stats?.mpMax || 0}</b> <small>(0x${p.offsets?.MAX_MP || "???"})</small></div>
            <div class="address-row-detail"><span>Health Stone:</span> <b>${p.stats?.hpStone || 0}</b> <small>(0x${p.offsets?.HP_STONE || "???"})</small></div>
            <div class="address-row-detail"><span>Mana Stone:</span> <b>${p.stats?.mpStone || 0}</b> <small>(0x${p.offsets?.MP_STONE || "???"})</small></div>
            <div class="address-row-detail"><span>Zoom Distance:</span> <b>${p.currentZoom ? p.currentZoom.toFixed(1) : "—"}</b> <small>(0x${p.offsets?.ZOOM_DISTANCE || "???"})</small></div>
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    listEl.innerHTML = `<div class="address-list-error">Error: ${err}</div>`;
  }
}

function renderSettingsPanel() {
  const kb = getAppSettings().keybindings;
  $("nav-modal-body").innerHTML = `
    <div class="settings-panel">
      <label class="settings-row">
        <span class="settings-label" data-i18n="settings_section">${t("settings_section")}</span>
        <select id="settings-section" class="settings-select">
          <option value="keybindings" data-i18n="settings_keybindings">${t("settings_keybindings")}</option>
          <option value="address" data-i18n="settings_address">${t("settings_address")}</option>
        </select>
      </label>
      <div id="settings-pane-keybindings" class="settings-pane">
        <div class="settings-kb-row">
          <span class="settings-label" data-i18n="kb_reset_timeline">${t("kb_reset_timeline")}</span>
          <button type="button" id="kb-reset-timeline" class="kb-capture-btn">${formatBindingLabel(kb.resetTimeline)}</button>
        </div>
      </div>
      <div id="settings-pane-address" class="settings-pane hidden">
        <div class="address-list-header">
          <span></span>
          <button type="button" id="btn-refresh-address" class="btn btn-sm">Refresh</button>
        </div>
        <div id="address-list" class="address-list">
          <div class="address-list-empty">Searching for Fiesta.exe...</div>
        </div>
      </div>
    </div>`;

  $("settings-section").onchange = () => {
    const val = $("settings-section").value;
    const kbPane = $("settings-pane-keybindings");
    const addrPane = $("settings-pane-address");

    kbPane.classList.toggle("hidden", val !== "keybindings");
    addrPane.classList.toggle("hidden", val !== "address");

    if (val === "address") {
      refreshAddressList();
    }
  };

  $("btn-refresh-address").onclick = () => refreshAddressList();

  const bindCapture = (btnId, field) => {
    const btn = $(btnId);
    if (!btn) return;
    btn.onclick = () => {
      capturingKbField = field;
      btn.textContent = t("kb_press_key");
      btn.classList.add("capturing");
    };
  };
  bindCapture("kb-reset-timeline", "resetTimeline");
}

function onSettingsKeyCapture(e) {
  if (!capturingKbField) return;
  e.preventDefault();
  e.stopPropagation();
  if (e.key === "Escape") {
    capturingKbField = null;
    renderSettingsPanel();
    openNavModal("settings");
    return;
  }
  const binding = bindingFromKeyboardEvent(e);
  if (!binding) return;
  getAppSettings().keybindings[capturingKbField] = binding;
  capturingKbField = null;
  saveState();
  syncKeybindingsToBackend();
  renderSettingsPanel();
  openNavModal("settings");
}

function activeProfile() {
  return state.profiles.find((p) => p.id === state.activeProfileId);
}

function activeSequence() {
  const prof = activeProfile();
  if (!prof) return null;
  return prof.sequences.find((s) => s.id === prof.activeSequenceId);
}

function syncCurrentSeqToState() {
  const seq = activeSequence();
  if (!seq) return;
  seq.playheadMs = state.playheadMs;
}

function defaultPlayback() {
  return {
    mode: "loop",
    scope: "current",
    count: 3,
    minutes: 5,
    stopCondition: "none",
    selectedSequenceIds: [],
  };
}

function getProfilePlayback(prof) {
  const p = prof || activeProfile();
  if (!p) return defaultPlayback();
  if (!p.playback) {
    p.playback = defaultPlayback();
    const seq = p.sequences?.[0];
    if (seq?.playback) {
      p.playback.mode = seq.playback.mode || "once";
      p.playback.count = seq.playback.count ?? 3;
      p.playback.minutes = seq.playback.minutes ?? 5;
    }
  }
  return p.playback;
}

function defaultSeqPlayback() {
  return { mode: "once", count: 3, minutes: 5 };
}

function normalizeSeqTriggerMode(seq) {
  const m = seq?.triggerMode || "auto";
  if (m === "keyHold" || m === "keyPress") return "keyPress";
  return "auto";
}

function getSeqPlayback(seq) {
  if (!seq.seqPlayback) {
    seq.seqPlayback = defaultSeqPlayback();
    if (seq.keyTriggerPlayMode) {
      seq.seqPlayback.mode = seq.keyTriggerPlayMode;
      seq.seqPlayback.count = seq.keyTriggerPlayCount ?? 3;
    }
  }
  return seq.seqPlayback;
}

function newSequence(name) {
  return {
    id: uid("seq_"),
    name: name || "Sequence",
    enabled: false,
    trackCount: DEFAULT_TRACKS,
    blocks: [],
    playheadMs: 0,
    triggerMode: "auto",
    triggerKey: "",
    seqPlayback: defaultSeqPlayback(),
  };
}

function defaultBlock(track, startMs) {
  return {
    id: uid("b_"),
    type: "keyboard",
    track,
    startMs: snapMs(startMs),
    durationMs: 500,
    key: "x",
    mouseButton: "left",
    doubleClick: false,
    clickX: null,
    clickY: null,
  };
}

function migrateBlock(b) {
  if (!b.type) b.type = b.mouseButton && b.clickX != null ? "mouse" : "keyboard";
  if (b.type === "mouse") {
    b.mouseButton = b.mouseButton || "left";
    b.doubleClick = !!b.doubleClick;
  } else {
    b.key = b.key || "x";
  }
  return b;
}

function migrateSequence(seq) {
  seq.blocks = (seq.blocks || []).map(migrateBlock);
  if (seq.enabled === undefined) seq.enabled = false;
  if (!seq.trackCount || seq.trackCount < 1) seq.trackCount = DEFAULT_TRACKS;
  if (!seq.triggerMode) seq.triggerMode = "auto";
  if (seq.triggerMode === "keyHold") seq.triggerMode = "keyPress";
  if (!seq.triggerKey) seq.triggerKey = "";
  getSeqPlayback(seq);
  return seq;
}

function migrateProfile(prof) {
  prof.sequences?.forEach(migrateSequence);
  if (!prof.playback) {
    prof.playback = defaultPlayback();
    const first = prof.sequences?.[0];
    if (first?.playback) {
      prof.playback.mode = first.playback.mode || "once";
      prof.playback.count = first.playback.count ?? 3;
      prof.playback.minutes = first.playback.minutes ?? 5;
      delete first.playback;
    }
  }
  if (!prof.playback.scope) prof.playback.scope = "current";
  if (!prof.playback.scheduleTime) prof.playback.scheduleTime = "12:00:00";
  if (!prof.playback.schedulePlayCount) prof.playback.schedulePlayCount = 1;
  if (!prof.playback.selectedSequenceIds) prof.playback.selectedSequenceIds = [];
  if (!prof.playback.stopCondition) prof.playback.stopCondition = "none";
  return prof;
}

function defaultOcr() {
  return {
    heal: {
      enabled: false,
      intervalMs: 500,
      region: null,
      conditions: [],
    },
    quest: {
      enabled: false,
      intervalMs: 500,
      region: null,
      keywords: ["belohnung", "reward"],
      redRMin: 140,
      redGMax: 110,
      redBMax: 110,
      clickTarget: null,
      delayAfterRewardMs: 300,
      delayAfterClickMs: 200,
      spaceCount: 10,
      spaceIntervalMs: 100,
      cooldownMs: 3000,
      questWindowRegion: null,
      questWindowIntervalMs: 1000,
      questWindowKey: "l",
      questWindowCooldownMs: 1500,
    },
  };
}

function migrateProfileOcr(prof) {
  if (!prof.ocr) {
    prof.ocr = defaultOcr();
    return;
  }
  if (prof.ocr.heal && prof.ocr.quest) return;
  if (prof.ocr.region !== undefined || prof.ocr.conditions) {
    prof.ocr = {
      heal: {
        enabled: !!prof.ocr.enabled,
        intervalMs: prof.ocr.intervalMs ?? 500,
        region: prof.ocr.region ?? null,
        conditions: prof.ocr.conditions || [],
      },
      quest: defaultOcr().quest,
    };
  }
}

function newProfile(name) {
  const seq = newSequence("Sequence 1");
  return {
    id: uid("prof_"),
    name: name || "Profile",
    sequences: [seq],
    activeSequenceId: seq.id,
    ocr: defaultOcr(),
  };
}

function defaultState() {
  const prof = newProfile("Standard");
  return {
    version: 3,
    activeProfileId: prof.id,
    playheadMs: 0,
    profiles: [prof],
    appSettings: defaultAppSettings(),
  };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.version >= 2 && parsed.profiles?.length) {
        state = parsed;
        state.version = 3;
        if (parsed.zoomLevel) zoomLevel = parsed.zoomLevel;
        if (!state.appSettings) state.appSettings = defaultAppSettings();
        state.profiles.forEach((p) => {
          migrateProfileOcr(p);
          migrateProfile(p);
        });
        return true;
      }
    }
  } catch (_) {}
  state = defaultState();
  return false;
}

const APP_META_KEY = "_app_meta";

function saveAppMetaToLocal() {
  try {
    localStorage.setItem(
      APP_META_KEY,
      JSON.stringify({
        activeProfileId: state.activeProfileId,
        playheadMs: state.playheadMs,
        zoomLevel,
        appSettings: state.appSettings,
      })
    );
  } catch (_) {}
}

function loadAppMetaFromLocal() {
  try {
    const raw = localStorage.getItem(APP_META_KEY);
    if (!raw) return;
    const meta = JSON.parse(raw);
    if (meta.activeProfileId && state.profiles.some((p) => p.id === meta.activeProfileId)) {
      state.activeProfileId = meta.activeProfileId;
    }
    if (meta.playheadMs != null) state.playheadMs = meta.playheadMs;
    if (meta.zoomLevel) zoomLevel = meta.zoomLevel;
    if (meta.appSettings) state.appSettings = meta.appSettings;
  } catch (_) {}
}

async function waitForPywebviewApi(maxMs = 8000) {
  const start = Date.now();
  while (!pywebviewApi() && Date.now() - start < maxMs) {
    await new Promise((r) => setTimeout(r, 50));
  }
  return !!pywebviewApi();
}

async function persistProfilesToDisk() {
  const api = pywebviewApi();
  if (!api?.save_profile_disk) return false;
  try {
    for (const prof of state.profiles) {
      const res = await api.save_profile_disk(
        prof.id,
        JSON.stringify({
          version: 3,
          profile: prof,
        })
      );
      if (!res?.ok) return false;
    }
    const metaRes = await api.save_profile_disk(
      APP_META_KEY,
      JSON.stringify({
        version: 3,
        activeProfileId: state.activeProfileId,
        playheadMs: state.playheadMs,
        zoomLevel,
        appSettings: state.appSettings,
      })
    );
    return !!metaRes?.ok;
  } catch (_) {
    return false;
  }
}

function saveStateLocal(push = true) {
  syncCurrentSeqToState();
  state.zoomLevel = zoomLevel;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (_) {}
  saveAppMetaToLocal();
  if (push) pushHistory();
}

function saveState(push = true) {
  saveStateLocal(push);
  void persistProfilesToDisk();
  void syncTriggerKeysToBackend();
}

async function saveStateAndDisk() {
  saveStateLocal();
  return persistProfilesToDisk();
}

function getBlocks() {
  const seq = activeSequence();
  return seq ? seq.blocks : [];
}

function setBlocks(blocks) {
  const seq = activeSequence();
  if (seq) seq.blocks = blocks;
}

function getTrackCount() {
  const seq = activeSequence();
  return seq ? seq.trackCount : DEFAULT_TRACKS;
}

function setTrackCount(n) {
  const seq = activeSequence();
  if (seq) seq.trackCount = n;
}

function removeTrack(index) {
  const seq = activeSequence();
  if (!seq || seq.trackCount <= 1) return;

  // Blöcke auf der gelöschten Spur entfernen
  seq.blocks = seq.blocks.filter((b) => b.track !== index);

  // Blöcke auf höheren Spuren nach unten schieben
  seq.blocks.forEach((b) => {
    if (b.track > index) b.track--;
  });

  seq.trackCount--;
  saveState();
  renderTracks();
}

function totalDurationMs(blocks = getBlocks()) {
  if (!blocks.length) return 0;
  return Math.max(...blocks.map((b) => b.startMs + b.durationMs));
}

function sequencesForPlayback(prof = activeProfile(), { includeKeyTrigger = false } = {}) {
  if (!prof) return [];
  const pb = getProfilePlayback(prof);
  let list = [];
  const all = prof.sequences || [];
  if (pb.scope === "all") list = all;
  else if (pb.scope === "current") {
    const cur = all.find((s) => s.id === prof.activeSequenceId);
    list = cur ? [cur] : [];
  } else {
    const ids = pb.selectedSequenceIds || [];
    if (ids.length) list = all.filter((s) => ids.includes(s.id));
    else list = all.filter((s) => s.enabled === true);
  }
  if (includeKeyTrigger) return list;
  return list.filter((s) => normalizeSeqTriggerMode(s) === "auto");
}

function sequencesForKeyTrigger(key, prof = activeProfile()) {
  if (!prof || !key) return [];
  const k = normalizeTriggerKey(key);
  return (prof.sequences || []).filter(
    (s) => normalizeSeqTriggerMode(s) === "keyPress" && normalizeTriggerKey(s.triggerKey) === k
  );
}

function mergedPlayBlocks(seqList) {
  const merged = [];
  for (const seq of seqList || sequencesForPlayback()) {
    for (const b of seq.blocks) {
      merged.push({ ...b });
    }
  }
  return merged;
}

let keyTriggerActiveKey = null;

function timelineDurationMs() {
  const prof = activeProfile();
  let maxDur = 30000; // Mindestens 30 Sekunden Basis
  if (prof) {
    for (const seq of prof.sequences) {
      maxDur = Math.max(maxDur, totalDurationMs(seq.blocks));
    }
  }

  // Berücksichtige die Container-Breite, damit die Timeline immer den Platz ausfüllt
  const editorScroll = $("editor-scroll");
  if (editorScroll) {
    const labelWidth = 80; // var(--label-width)
    const containerW = editorScroll.clientWidth - labelWidth;
    if (containerW > 0) {
      const containerMs = pxToMs(containerW);
      maxDur = Math.max(maxDur, containerMs);
    }
  }

  return maxDur + 2000; // Etwas Puffer am Ende
}

function timelineWidthPx() {
  // Die Breite muss mindestens 100% sein, aber bei viel Content eben mehr
  return msToPx(timelineDurationMs()) + 80; 
}

let rulerLabeledUntilMs = 0;

function ensureTimelineWidths() {
  const w = timelineWidthPx();
  const labelWidth = 80;
  const laneW = w - labelWidth;
  
  const rulerWrap = document.querySelector(".ruler-wrap");
  if (rulerWrap) {
    rulerWrap.style.width = "100%";
    rulerWrap.style.minWidth = w + "px";
  }
  const ruler = $("ruler");
  if (ruler) {
    ruler.style.width = "100%";
    ruler.style.minWidth = laneW + "px";
  }
  const tracks = $("tracks");
  if (tracks) {
    tracks.style.width = "100%";
    tracks.style.minWidth = w + "px";
  }
  document.querySelectorAll(".track-lane").forEach((lane) => {
    lane.style.width = "100%";
    lane.style.minWidth = laneW + "px";
  });
}

function syncTimelineLayout() {
  const dur = timelineDurationMs();
  if (dur > rulerLabeledUntilMs) renderRuler();
  else ensureTimelineWidths();
}

let simPlaying = false;
let simStart = 0;
let simFrom = 0;

function getPlaybackOptions() {
  const pb = getProfilePlayback();
  const mode = pb.mode || "loop";
  return {
    mode: mode,
    count: Number(pb.count) || 3,
    minutes: Number(pb.minutes) || 5,
    stopCondition: pb.stopCondition || "none",
    teleportKey: pb.teleportKey || "",
  };
}

let clockOffsetMs = 0;
let clockSyncTimer = null;
let clockTickTimer = null;
let clockReady = false;

function appLanguage() {
  return getAppSettings().language === "en" ? "en" : "de";
}

function appTimeZone() {
  return appLanguage() === "en" ? "America/Los_Angeles" : "Europe/Berlin";
}

function formatAppClock(now = new Date()) {
  const locale = appLanguage() === "en" ? "en-US" : "de-DE";
  return now.toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: appTimeZone(),
  });
}

function accurateClockNow() {
  return new Date(Date.now() + clockOffsetMs);
}

function waitMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForNextClockSecond() {
  const ms = 1000 - (Date.now() % 1000);
  return waitMs(ms > 0 ? ms : 1000);
}

async function syncClockOffset() {
  const api = pywebviewApi();
  if (!api) return false;
  try {
    const res = api.set_app_timezone
      ? await api.set_app_timezone(appLanguage())
      : await api.get_german_time();
    if (res?.offsetMs != null && Number.isFinite(Number(res.offsetMs))) {
      clockOffsetMs = Number(res.offsetMs);
      console.log("Time synced. Offset (ms):", clockOffsetMs);
    }
    return !!res?.synced || !!res?.ok;
  } catch (err) {
    console.error("Time sync error:", err);
    return false;
  }
}

function stopAtomicClockTimers() {
  if (clockTickTimer) clearTimeout(clockTickTimer);
  if (clockSyncTimer) clearInterval(clockSyncTimer);
  clockTickTimer = null;
  clockSyncTimer = null;
  clockReady = false;
}

function runAtomicClockTick() {
  const el = $("atomic-clock");
  if (!el || !clockReady) return;
  const now = accurateClockNow();
  const text = formatAppClock(now);
  
  if (el.textContent !== text) {
    el.textContent = text;
    el.setAttribute("datetime", text);
  }
  
  // Maximale Präzision: Alle 50ms prüfen
  const ms = now.getMilliseconds();
  const delay = ms < 950 ? 50 : (1000 - ms + 2); 
  clockTickTimer = setTimeout(runAtomicClockTick, delay);
}

async function bootAtomicClock() {
  const el = $("atomic-clock");
  if (!el) return;
  stopAtomicClockTimers();
  el.classList.add("clock-loading");
  el.textContent = "--:--:--";

  await syncClockOffset();
  await waitForNextClockSecond();

  el.classList.remove("clock-loading");
  clockReady = true;
  runAtomicClockTick();

  clockSyncTimer = setInterval(() => syncClockOffset(), 10 * 60 * 1000);
}

async function restartAtomicClock() {
  await bootAtomicClock();
}

function setupFocusFloat() {
  const notify = (focused) => {
    const api = pywebviewApi();
    if (api?.set_app_focused) api.set_app_focused(focused).catch(() => {});
  };
  const syncFocus = () => notify(document.hasFocus() && !document.hidden);
  document.addEventListener("visibilitychange", syncFocus);
  window.addEventListener("blur", () => notify(false));
  window.addEventListener("focus", syncFocus);
  whenPywebviewReady(() => notify(true));
}

window.openNavModal = function openNavModal(kind) {
  const titles = { account: t("account"), settings: t("settings"), help: t("help") };
  $("nav-modal-title").textContent = titles[kind] || "Info";
  if (kind === "settings") {
    renderSettingsPanel();
  } else {
    $("nav-modal-body").innerHTML =
      kind === "account" ? t("nav_account_body") : kind === "help" ? t("nav_help_body") : "";
  }
  $("nav-modal").classList.remove("hidden");
}

async function apiPlay(fromMs, blocks, options) {
  const api = pywebviewApi();
  if (!api) {
    simulatePlay(fromMs);
    return;
  }
  await api.play_sequence(JSON.stringify(blocks), fromMs, JSON.stringify(options || getPlaybackOptions()));
}

async function apiStop() {
  const api = pywebviewApi();
  if (api) return api.stop_playback();
  return { positionMs: simulateStop() };
}

async function apiReset() {
  const api = pywebviewApi();
  if (api) return api.reset_playback();
  simPlaying = false;
  return { positionMs: 0 };
}

async function apiGetPlayhead() {
  const api = pywebviewApi();
  if (api) return api.get_playhead_ms();
  return simulateGetPlayhead();
}

async function apiSeek(ms) {
  const api = pywebviewApi();
  if (api) api.seek_playhead(ms);
}

function simulatePlay(fromMs) {
  simPlaying = true;
  simFrom = fromMs;
  simStart = performance.now();
}

function simulateStop() {
  const pos = simulateGetPlayhead().positionMs;
  simPlaying = false;
  return pos;
}

function simulateGetPlayhead() {
  if (!simPlaying) return { positionMs: state.playheadMs, playing: false };
  return {
    positionMs: simFrom + (performance.now() - simStart),
    playing: true,
  };
}

function seekPlayhead(ms, skipApi = false) {
  state.playheadMs = Math.max(0, snapMs(ms));
  syncCurrentSeqToState();
  if (!skipApi) apiSeek(state.playheadMs);
  updatePlayheadVisual();
}

async function resetTimeline() {
  stopPlayheadLoop();
  keyTriggerActiveKey = null;
  await apiReset();
  state.playheadMs = 0;
  syncCurrentSeqToState();
  updatePlayheadVisual();
}

function updatePlayheadVisual() {
  const rph = $("ruler-playhead");
  const line = $("playhead-line");
  if (rph) rph.style.left = playheadRulerLeft();
  if (line) {
    line.style.left = playheadLineLeft();
    line.style.transform = "";
  }
}

function updatePlayheadLineHeight() {
  const line = $("playhead-line");
  const rulerWrap = document.querySelector(".ruler-wrap");
  const tracks = $("tracks");
  if (line && rulerWrap && tracks) {
    line.style.height = (rulerWrap.offsetHeight + tracks.offsetHeight) + "px";
  }
}

function displayBlockLabel(b) {
  migrateBlock(b);
  if (b.type === "mouse") {
    const btn = b.mouseButton === "right" ? "Rechts" : "Links";
    const dbl = b.doubleClick ? " ×2" : "";
    const pos = b.clickX != null ? ` @${b.clickX},${b.clickY}` : "";
    return `🖱 ${btn}${dbl}${pos}`;
  }
  const k = b.key || "?";
  return k
    .split("+")
    .map((p) => (p.length === 1 ? p.toUpperCase() : p.charAt(0).toUpperCase() + p.slice(1)))
    .join("+");
}

function renderProfileSelect() {
  const sel = $("profile-select");
  if (!sel || !state) return;
  sel.innerHTML = "";
  state.profiles.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    if (p.id === state.activeProfileId) opt.selected = true;
    sel.appendChild(opt);
  });
}

function renderSeqTabs() {
  const prof = activeProfile();
  const container = $("seq-tabs");
  container.innerHTML = "";
  if (!prof) return;

  prof.sequences.forEach((seq) => {
    const tab = document.createElement("div");
    tab.className = "seq-tab" + (seq.id === prof.activeSequenceId ? " active" : "");
    tab.dataset.id = seq.id;

    const name = document.createElement("span");
    name.textContent = seq.name;
    name.title = "Doppelklick zum Umbenennen";
    name.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      const n = prompt("Sequenzname:", seq.name);
      if (n?.trim()) {
        seq.name = n.trim();
        saveState();
        renderSeqTabs();
        renderPlayChecks();
      }
    });

    const close = document.createElement("span");
    close.className = "tab-close";
    close.textContent = "×";
    close.title = "Sequenz schließen";
    close.addEventListener("click", (e) => {
      e.stopPropagation();
      if (prof.sequences.length <= 1) {
        alert("Mindestens eine Sequenz muss bleiben.");
        return;
      }
      if (!confirm(`„${seq.name}“ löschen?`)) return;
      prof.sequences = prof.sequences.filter((s) => s.id !== seq.id);
      if (prof.activeSequenceId === seq.id) {
        prof.activeSequenceId = prof.sequences[0].id;
        state.playheadMs = prof.sequences[0].playheadMs || 0;
      }
      selectedIds.clear();
      saveState();
      render();
    });

    tab.appendChild(name);
    tab.appendChild(close);
    tab.addEventListener("click", () => switchSequence(seq.id));
    container.appendChild(tab);
  });

  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.id = "btn-add-seq";
  addBtn.className = "btn btn-tab-add";
  addBtn.textContent = "+";
  addBtn.title = "Neue Sequenz";
  addBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    addSequence();
  });
  container.appendChild(addBtn);
}

function renderPlaybackSettings() {
  const prof = activeProfile();
  if (!prof) return;
  migrateProfile(prof);
  const pb = getProfilePlayback(prof);
  $("pb-scope").value = pb.scope || "current";
  $("pb-mode").value = pb.mode || "loop";
  $("pb-count").value = pb.count ?? 3;
  $("pb-minutes").value = pb.minutes ?? 5;
  if ($("pb-stop-condition")) $("pb-stop-condition").value = pb.stopCondition || "none";
  if ($("pb-teleport-key")) $("pb-teleport-key").value = pb.teleportKey || "";
  $("pb-count-wrap").classList.toggle("hidden", pb.mode !== "count");
  $("pb-minutes-wrap").classList.toggle("hidden", pb.mode !== "minutes");
  $("pb-stop-condition-wrap")?.classList.toggle("hidden", pb.mode !== "loop");
  $("pb-teleport-wrap")?.classList.toggle("hidden", pb.mode !== "hpStonesEmpty" && pb.mode !== "mpStonesEmpty" && pb.stopCondition !== "hpStonesEmpty" && pb.stopCondition !== "mpStonesEmpty");
  const scope = pb.scope || "current";
  $("play-checks").classList.toggle("hidden", scope === "current" || scope === "all");
  renderSequenceTriggerSettings();
}

function renderSequenceTriggerSettings() {
  const seq = activeSequence();
  if (!seq || !$("seq-trigger-mode")) return;
  migrateSequence(seq);
  const mode = normalizeSeqTriggerMode(seq);
  $("seq-trigger-mode").value = mode;
  $("seq-trigger-key").value = seq.triggerKey || "";
  $("seq-key-wrap").classList.toggle("hidden", mode !== "keyPress");
}

function renderPlayChecks() {
  const prof = activeProfile();
  const box = $("play-checks");
  box.innerHTML = "";
  if (!prof) return;
  migrateProfile(prof);
  const pb = getProfilePlayback(prof);
  const scope = pb.scope || "current";
  if (scope === "current" || scope === "all") {
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  const selected = new Set(pb.selectedSequenceIds || []);
  prof.sequences.forEach((seq) => {
    const label = document.createElement("label");
    label.className = "play-check";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = selected.has(seq.id) || seq.enabled === true;
    cb.addEventListener("change", () => {
      if (cb.checked) {
        if (!pb.selectedSequenceIds.includes(seq.id)) pb.selectedSequenceIds.push(seq.id);
        seq.enabled = true;
      } else {
        pb.selectedSequenceIds = pb.selectedSequenceIds.filter((id) => id !== seq.id);
        seq.enabled = false;
      }
      saveState();
    });
    label.appendChild(cb);
    label.appendChild(document.createTextNode(seq.name));
    box.appendChild(label);
  });
}

function switchSequence(seqId) {
  syncCurrentSeqToState();
  const prof = activeProfile();
  if (!prof) return;
  const seq = prof.sequences.find((s) => s.id === seqId);
  if (!seq) return;
  prof.activeSequenceId = seqId;
  state.playheadMs = seq.playheadMs || 0;
  selectedIds.clear();
  saveState();
  render();
  renderPlaybackSettings();
}

function addSequence() {
  const prof = activeProfile();
  if (!prof) return;
  syncCurrentSeqToState();
  const n = prof.sequences.length + 1;
  const seq = newSequence(`Sequence ${n}`);
  prof.sequences.push(seq);
  prof.activeSequenceId = seq.id;
  state.playheadMs = 0;
  selectedIds.clear();
  saveState();
  render();
}

function renderRuler() {
  const ruler = $("ruler");
  if (!ruler) return;
  ruler.innerHTML = "";
  const durationMs = timelineDurationMs();
  rulerLabeledUntilMs = durationMs;
  ensureTimelineWidths();

  for (let ms = 0; ms <= durationMs; ms += 1000) {
    const tick = document.createElement("div");
    tick.className = "ruler-tick";
    tick.style.left = msToPx(ms) + "px";
    tick.textContent = formatTime(ms);
    ruler.appendChild(tick);
  }

  const handle = document.createElement("div");
  handle.className = "ruler-playhead";
  handle.id = "ruler-playhead";
  handle.style.left = playheadRulerLeft();
  handle.addEventListener("mousedown", onPlayheadMouseDown);
  ruler.appendChild(handle);
}

function renderTracks() {
  const container = $("tracks");
  const blocks = getBlocks();
  const trackCount = getTrackCount();
  container.innerHTML = "";

  for (let t = 0; t < trackCount; t++) {
    const row = document.createElement("div");
    row.className = "track-row";

    const label = document.createElement("div");
    label.className = "track-label";
    
    const labelText = document.createElement("span");
    labelText.textContent = "Spur " + (t + 1);
    label.appendChild(labelText);

    // Entfernen-Button nur wenn mehr als 1 Spur da ist
    if (trackCount > 1) {
      const delBtn = document.createElement("button");
      delBtn.className = "track-delete-btn";
      delBtn.innerHTML = "×";
      delBtn.title = "Spur entfernen";
      delBtn.onclick = (e) => {
        e.stopPropagation();
        if (confirm(`Spur ${t + 1} wirklich entfernen? Alle Blöcke auf dieser Spur werden gelöscht.`)) {
          removeTrack(t);
        }
      };
      label.appendChild(delBtn);
    }

    const lane = document.createElement("div");
    lane.className = "track-lane";
    lane.dataset.track = String(t);

    lane.addEventListener("mousedown", (e) => onLaneMouseDown(e, t));
    lane.addEventListener("click", (e) => onLaneClick(e, t));
    lane.addEventListener("contextmenu", (e) => onLaneContextMenu(e, t));

    blocks
      .filter((b) => b.track === t)
      .forEach((b) => lane.appendChild(createBlockEl(b)));

    row.appendChild(label);
    row.appendChild(lane);
    container.appendChild(row);
  }

  ensureTimelineWidths();
  syncTimelineLayout();
  updatePlayheadVisual();
  updatePlayheadLineHeight();
}

function createBlockEl(b) {
  const el = document.createElement("div");
  el.className = "block" + (selectedIds.has(b.id) ? " selected" : "");
  el.dataset.id = b.id;
  applyBlockStyle(el, b);

  const keySpan = document.createElement("span");
  keySpan.className = "block-key";
  keySpan.textContent = displayBlockLabel(b);
  if (b.type === "mouse") el.classList.add("block-mouse");

  const durSpan = document.createElement("span");
  durSpan.className = "block-duration";
  durSpan.textContent = b.durationMs + " ms";

  el.appendChild(keySpan);
  el.appendChild(durSpan);

  const resizeR = document.createElement("div");
  resizeR.className = "block-resize";
  const resizeL = document.createElement("div");
  resizeL.className = "block-resize block-resize-left";

  el.appendChild(keySpan);
  el.appendChild(durSpan);
  el.appendChild(resizeL);
  el.appendChild(resizeR);

  el.addEventListener("mousedown", (e) => onBlockMouseDown(e, b, "move"));
  resizeR.addEventListener("mousedown", (e) => onBlockMouseDown(e, b, "resize-r"));
  resizeL.addEventListener("mousedown", (e) => onBlockMouseDown(e, b, "resize-l"));
  el.addEventListener("dblclick", (e) => {
    e.stopPropagation();
    openModal(b.id);
  });
  el.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    if (!selectedIds.has(b.id)) {
      selectedIds.clear();
      selectedIds.add(b.id);
      refreshBlockSelectionClasses();
    }
    contextBlockId = b.id;
    showContextMenu(e.clientX, e.clientY);
  });

  return el;
}

function applyBlockStyle(el, b) {
  el.style.left = msToPx(b.startMs) + "px";
  el.style.width = Math.max(msToPx(b.durationMs), 24) + "px";
  const keyEl = el.querySelector(".block-key");
  const durEl = el.querySelector(".block-dur");
  if (keyEl) keyEl.textContent = displayBlockLabel(b);
  if (durEl) durEl.textContent = b.durationMs + " ms";
}

/** Nächste Spur zur Maus-Y (Mitte der Zeile), nicht zwischen Spuren. */
function trackIndexFromClientY(clientY) {
  const rows = document.querySelectorAll(".track-row");
  let best = 0;
  let bestDist = Infinity;
  rows.forEach((row) => {
    const lane = row.querySelector(".track-lane");
    if (!lane) return;
    const rect = row.getBoundingClientRect();
    const center = rect.top + rect.height / 2;
    const dist = Math.abs(clientY - center);
    const track = Number(lane.dataset.track);
    if (dist < bestDist) {
      bestDist = dist;
      best = track;
    }
  });
  return Math.max(0, Math.min(getTrackCount() - 1, best));
}

function reparentBlockToTrack(el, track) {
  const lane = document.querySelector(`.track-lane[data-track="${track}"]`);
  if (lane && el.parentElement !== lane) lane.appendChild(el);
}

/** Horizontale Position + Spurwechsel mit Live-Vorschau entlang der Maus. */
function applyBlockDragStyle(el, b, clientY) {
  applyBlockStyle(el, b);
  reparentBlockToTrack(el, b.track);
  const lane = el.parentElement;
  if (!lane) return;
  const laneRect = lane.getBoundingClientRect();
  const blockH = el.offsetHeight || laneRect.height - 12;
  let top = clientY - laneRect.top - blockH / 2;
  const maxTop = Math.max(6, laneRect.height - blockH - 6);
  el.style.top = Math.max(6, Math.min(maxTop, top)) + "px";
}

function clearBlockDragPreview(el) {
  el.style.top = "";
  el.style.pointerEvents = "";
}

function refreshBlockSelectionClasses() {
  document.querySelectorAll(".block").forEach((el) => {
    el.classList.toggle("selected", selectedIds.has(el.dataset.id));
  });
}

function render() {
  if (!state || !isSequencerPage()) return;
  renderProfileSelect();
  renderSeqTabs();
  renderPlayChecks();
  renderPlaybackSettings();
  void syncTriggerKeysToBackend();
  renderRuler();
  renderTracks();

  const prof = activeProfile();
  let dur = 0;
  if (prof) {
    for (const s of prof.sequences) dur = Math.max(dur, totalDurationMs(s.blocks));
  }
}

function onRulerClick(e) {
  if (e.target.id === "ruler-playhead" || e.target.closest(".ruler-playhead")) return;
  const ruler = $("ruler");
  const rect = ruler.getBoundingClientRect();
  const x = e.clientX - rect.left;
  seekPlayhead(pxToMs(x));
}

function onPlayheadMouseDown(e) {
  e.stopPropagation();
  e.preventDefault();
  playheadDrag = true;
  document.addEventListener("mousemove", onPlayheadDragMove);
  document.addEventListener("mouseup", onPlayheadDragEnd);
}

function onPlayheadDragMove(e) {
  if (!playheadDrag) return;
  const ruler = $("ruler");
  const rect = ruler.getBoundingClientRect();
  const x = Math.max(0, e.clientX - rect.left);
  seekPlayhead(pxToMs(x), true);
}

function onPlayheadDragEnd() {
  playheadDrag = false;
  document.removeEventListener("mousemove", onPlayheadDragMove);
  document.removeEventListener("mouseup", onPlayheadDragEnd);
  apiSeek(state.playheadMs);
}

function selectBlock(id, additive) {
  if (!additive) selectedIds.clear();
  if (selectedIds.has(id) && additive) selectedIds.delete(id);
  else selectedIds.add(id);
  refreshBlockSelectionClasses();
}

function onLaneClick(e, track) {
  if (e.target.classList.contains("block")) return;
  if (marqueeState?.moved) return;
  if (dragState || playheadDrag) return;
}

function onLaneContextMenu(e, track) {
  if (e.target.classList.contains("block")) return;
  e.preventDefault();
  const lane = e.currentTarget;
  const rect = lane.getBoundingClientRect();
  const startMs = snapMs(pxToMs(e.clientX - rect.left));
  showLaneMenu(e.clientX, e.clientY, track, startMs);
}

function showLaneMenu(x, y, track, startMs) {
  laneMenuAt = { track, startMs };
  const menu = $("lane-menu");
  menu.classList.remove("hidden");
  menu.style.left = x + "px";
  menu.style.top = y + "px";
}

function hideLaneMenu() {
  $("lane-menu").classList.add("hidden");
  laneMenuAt = null;
}

function createBlockAt(track, startMs) {
  const blocks = getBlocks();
  const b = defaultBlock(track, startMs);
  blocks.push(b);
  setBlocks(blocks);
  selectedIds.clear();
  selectedIds.add(b.id);
  saveState();
  renderTracks();
  openModal(b.id);
}

function onLaneMouseDown(e, track) {
  if (e.target.classList.contains("block")) return;
  if (e.button !== 0) return;

  if (e.shiftKey || e.ctrlKey || e.metaKey) {
    startMarquee(e, track);
    return;
  }

  if (!e.target.classList.contains("track-lane")) return;
  selectedIds.clear();
  refreshBlockSelectionClasses();

  const lane = e.currentTarget;
  const rect = lane.getBoundingClientRect();
  const startMs = snapMs(pxToMs(e.clientX - rect.left));

  marqueeState = {
    startX: e.clientX,
    startY: e.clientY,
    track,
    startMs,
    moved: false,
    lane,
  };

  document.addEventListener("mousemove", onLaneMouseMove);
  document.addEventListener("mouseup", onLaneMouseUp);
}

function onLaneMouseMove(e) {
  if (!marqueeState || marqueeState.marqueeActive) return;
  const dx = Math.abs(e.clientX - marqueeState.startX);
  const dy = Math.abs(e.clientY - marqueeState.startY);
  if (dx >= 5 || dy >= 5) {
    marqueeState.marqueeActive = true;
    document.removeEventListener("mousemove", onLaneMouseMove);
    document.removeEventListener("mouseup", onLaneMouseUp);
    startMarqueeFromState(e);
  }
}

function onLaneMouseUp(e) {
  document.removeEventListener("mousemove", onLaneMouseMove);
  document.removeEventListener("mouseup", onLaneMouseUp);
  if (!marqueeState) return;
  marqueeState = null;
}

function startMarqueeFromState(e) {
  const track = marqueeState.track;
  const area = $("tracks-area");
  const rect = area.getBoundingClientRect();
  const scroll = $("editor-scroll");
  marqueeState = {
    startX: marqueeState.startX - rect.left + scroll.scrollLeft,
    startY: marqueeState.startY - rect.top + scroll.scrollTop,
    track,
    moved: true,
  };
  const mq = $("marquee");
  mq.hidden = false;
  mq.style.left = marqueeState.startX + "px";
  mq.style.top = marqueeState.startY + "px";
  mq.style.width = "0";
  mq.style.height = "0";
  document.addEventListener("mousemove", onMarqueeMove);
  document.addEventListener("mouseup", onMarqueeEnd);
  onMarqueeMove(e);
}

function startMarquee(e, track) {
  const area = $("tracks-area");
  const rect = area.getBoundingClientRect();
  const scroll = $("editor-scroll");
  marqueeState = {
    startX: e.clientX - rect.left + scroll.scrollLeft,
    startY: e.clientY - rect.top + scroll.scrollTop,
    track,
    moved: false,
  };
  const mq = $("marquee");
  mq.hidden = false;
  mq.style.left = marqueeState.startX + "px";
  mq.style.top = marqueeState.startY + "px";
  mq.style.width = "0";
  mq.style.height = "0";

  document.addEventListener("mousemove", onMarqueeMove);
  document.addEventListener("mouseup", onMarqueeEnd);
}

function onMarqueeMove(e) {
  if (!marqueeState) return;
  const area = $("tracks-area");
  const rect = area.getBoundingClientRect();
  const scroll = $("editor-scroll");
  const x = e.clientX - rect.left + scroll.scrollLeft;
  const y = e.clientY - rect.top + scroll.scrollTop;
  const dx = Math.abs(x - marqueeState.startX);
  const dy = Math.abs(y - marqueeState.startY);
  if (dx > 4 || dy > 4) marqueeState.moved = true;

  const left = Math.min(marqueeState.startX, x);
  const top = Math.min(marqueeState.startY, y);
  const mq = $("marquee");
  mq.style.left = left + "px";
  mq.style.top = top + "px";
  mq.style.width = Math.abs(x - marqueeState.startX) + "px";
  mq.style.height = Math.abs(y - marqueeState.startY) + "px";
}

function onMarqueeEnd(e) {
  document.removeEventListener("mousemove", onMarqueeMove);
  document.removeEventListener("mouseup", onMarqueeEnd);
  const mq = $("marquee");
  mq.hidden = true;

  if (!marqueeState) return;

  if (marqueeState.moved) {
    const left = parseFloat(mq.style.left);
    const top = parseFloat(mq.style.top);
    const w = parseFloat(mq.style.width);
    const h = parseFloat(mq.style.height);
    const right = left + w;
    const bottom = top + h;

    const blocks = getBlocks();
    selectedIds.clear();
    blocks.forEach((b) => {
      const bx = 88 + msToPx(b.startMs);
      const by = b.track * 56 + 6;
      const bw = msToPx(b.durationMs);
      const bh = 44;
      if (bx < right && bx + bw > left && by < bottom && by + bh > top) {
        selectedIds.add(b.id);
      }
    });
    refreshBlockSelectionClasses();
  }

  marqueeState = null;
}

function getDragIds(primaryId) {
  if (selectedIds.has(primaryId) && selectedIds.size > 1) {
    return [...selectedIds];
  }
  return [primaryId];
}

function onBlockMouseDown(e, b, mode) {
  e.stopPropagation();
  if (e.button !== 0) return;

  if (e.ctrlKey || e.metaKey) {
    selectBlock(b.id, true);
  } else if (!selectedIds.has(b.id)) {
    selectedIds.clear();
    selectedIds.add(b.id);
    refreshBlockSelectionClasses();
  }

  if (mode !== "move") {
    e.preventDefault();
    beginBlockDrag(e, b, mode);
    return;
  }

  const startX = e.clientX;
  const startY = e.clientY;

  function onPendingMove(ev) {
    if (Math.abs(ev.clientX - startX) <= 4 && Math.abs(ev.clientY - startY) <= 4) return;
    document.removeEventListener("mousemove", onPendingMove);
    document.removeEventListener("mouseup", onPendingUp);
    ev.preventDefault();
    beginBlockDrag(e, b, mode);
  }

  function onPendingUp() {
    document.removeEventListener("mousemove", onPendingMove);
    document.removeEventListener("mouseup", onPendingUp);
  }

  document.addEventListener("mousemove", onPendingMove);
  document.addEventListener("mouseup", onPendingUp);
}

function beginBlockDrag(e, b, mode) {
  const ids = getDragIds(b.id);
  const blocks = getBlocks();
  const snapshots = ids.map((id) => {
    const bl = blocks.find((x) => x.id === id);
    return {
      id,
      startMs: bl.startMs,
      durationMs: bl.durationMs,
      track: bl.track,
    };
  });

  dragState = {
    mode,
    startX: e.clientX,
    snapshots,
    primaryId: b.id,
  };

  ids.forEach((id) => {
    const el = document.querySelector(`.block[data-id="${id}"]`);
    if (el) {
      el.classList.add("dragging");
      el.style.pointerEvents = "none";
    }
  });

  showDragTooltip(e.clientX, e.clientY, b);
  document.addEventListener("mousemove", onDragMove);
  document.addEventListener("mouseup", onDragEnd);
}

function onDragMove(e) {
  if (!dragState) return;
  const blocks = getBlocks();
  const dx = e.clientX - dragState.startX;
  const dMs = snapMs(pxToMs(dx));

  if (dragState.mode === "move") {
    const primarySnap = dragState.snapshots.find((s) => s.id === dragState.primaryId);
    const targetTrack = trackIndexFromClientY(e.clientY);
    const trackDelta = primarySnap ? targetTrack - primarySnap.track : 0;

    dragState.snapshots.forEach((snap) => {
      const bl = blocks.find((x) => x.id === snap.id);
      if (!bl) return;
      bl.startMs = Math.max(0, snap.startMs + dMs);
      bl.track = Math.max(0, Math.min(getTrackCount() - 1, snap.track + trackDelta));
      const el = document.querySelector(`.block[data-id="${bl.id}"]`);
      if (el) applyBlockDragStyle(el, bl, e.clientY);
    });

    const primary = blocks.find((x) => x.id === dragState.primaryId);
    if (primary) showDragTooltip(e.clientX, e.clientY, primary);
  } else {
    const snap = dragState.snapshots[0];
    const bl = blocks.find((x) => x.id === snap.id);
    if (!bl) return;

    if (dragState.mode === "resize-r") {
      bl.durationMs = Math.max(MIN_DURATION_MS, snap.durationMs + dMs);
    } else if (dragState.mode === "resize-l") {
      const newDur = snap.durationMs - dMs;
      if (newDur >= MIN_DURATION_MS) {
        bl.startMs = Math.max(0, snap.startMs + dMs);
        bl.durationMs = newDur;
      }
    }
    const el = document.querySelector(`.block[data-id="${bl.id}"]`);
    if (el) {
      applyBlockStyle(el, bl);
      showDragTooltip(e.clientX, e.clientY, bl);
    }
  }

  syncTimelineLayout();
}

function onDragEnd() {
  if (!dragState) return;
  document.querySelectorAll(".block.dragging").forEach((el) => {
    el.classList.remove("dragging");
    clearBlockDragPreview(el);
  });
  hideDragTooltip();
  dragState = null;
  document.removeEventListener("mousemove", onDragMove);
  document.removeEventListener("mouseup", onDragEnd);
  saveState();
  renderTracks();
}

function showDragTooltip(x, y, b) {
  const tip = $("drag-tooltip");
  tip.textContent = `${displayBlockLabel(b)} · ${formatTime(b.startMs)} · ${b.durationMs} ms · Spur ${b.track + 1}`;
  tip.style.left = x + 14 + "px";
  tip.style.top = y + 14 + "px";
  tip.classList.remove("hidden");
}

function hideDragTooltip() {
  $("drag-tooltip").classList.add("hidden");
}

function showContextMenu(x, y) {
  const menu = $("context-menu");
  menu.classList.remove("hidden");
  menu.style.left = x + "px";
  menu.style.top = y + "px";
}

function hideContextMenu() {
  $("context-menu").classList.add("hidden");
  contextBlockId = null;
}

function duplicateBlocks(ids) {
  const blocks = getBlocks();
  const newIds = [];
  ids.forEach((id) => {
    const src = blocks.find((b) => b.id === id);
    if (!src) return;
    const copy = {
      ...src,
      id: uid("b_"),
      startMs: src.startMs + src.durationMs + SNAP_MS,
    };
    blocks.push(copy);
    newIds.push(copy.id);
  });
  setBlocks(blocks);
  selectedIds.clear();
  newIds.forEach((id) => selectedIds.add(id));
  saveState();
  render();
}

function deleteBlocks(ids) {
  const blocks = getBlocks().filter((b) => !ids.includes(b.id));
  setBlocks(blocks);
  ids.forEach((id) => selectedIds.delete(id));
  saveState();
  render();
}

function updateModalTypeUI() {
  const isMouse = $("modal-type").value === "mouse";
  $("modal-keyboard-fields").classList.toggle("hidden", isMouse);
  $("modal-mouse-fields").classList.toggle("hidden", !isMouse);
}

function formatPosLabel(x, y) {
  return x != null && y != null ? `${x}, ${y}` : "—";
}

function openModal(id) {
  editingId = id;
  const blocks = getBlocks();
  const b = blocks.find((x) => x.id === id);
  if (!b) return;
  migrateBlock(b);
  $("modal-title").textContent = "Block bearbeiten";
  $("modal-type").value = b.type || "keyboard";
  $("modal-key").value = b.key || "x";
  $("modal-mouse-btn").value = b.mouseButton || "left";
  $("modal-double").checked = !!b.doubleClick;
  $("modal-click-pos").textContent = formatPosLabel(b.clickX, b.clickY);
  $("modal-duration").value = b.durationMs;
  $("modal-start").value = b.startMs;
  $("modal-track").value = b.track;
  $("modal-delete").style.display = "block";
  updateModalTypeUI();
  $("modal").classList.remove("hidden");
}

function openNewBlockModal() {
  createBlockAt(0, state.playheadMs);
}

function closeModal() {
  stopKeyCapture();
  $("modal").classList.add("hidden");
  editingId = null;
}

function saveModal() {
  const blocks = getBlocks();
  const b = blocks.find((x) => x.id === editingId);
  if (!b) {
    closeModal();
    return;
  }
  b.type = $("modal-type").value;
  b.durationMs = Math.max(MIN_DURATION_MS, Number($("modal-duration").value) || 500);
  b.startMs = Math.max(0, Number($("modal-start").value) || 0);
  b.track = Math.max(0, Math.min(getTrackCount() - 1, Number($("modal-track").value) || 0));
  if (b.type === "mouse") {
    b.mouseButton = $("modal-mouse-btn").value;
    b.doubleClick = $("modal-double").checked;
    if (b.clickX == null || b.clickY == null) {
      alert("Please pick a click position.");
      return;
    }
  } else {
    b.key = $("modal-key").value.trim().toLowerCase() || "x";
  }
  migrateBlock(b);
  closeModal();
  saveState();
  render();
}

const MODIFIER_ORDER = ["ctrl", "alt", "shift", "win"];
let keyCaptureState = null;

function normalizeCaptureKey(e) {
  if (e.key === " ") return "space";
  if (["Control", "Alt", "Shift", "Meta"].includes(e.key)) {
    return { Control: "ctrl", Alt: "alt", Shift: "shift", Meta: "win" }[e.key];
  }
  return e.key.length === 1 ? e.key.toLowerCase() : e.key.toLowerCase();
}

function normalizeTriggerKey(k) {
  if (!k) return "";
  const parts = k.trim().toLowerCase().split("+").filter(Boolean);
  const mods = MODIFIER_ORDER.filter((m) => parts.includes(m));
  const rest = parts.filter((p) => !MODIFIER_ORDER.includes(p)).sort();
  return [...mods, ...rest].join("+");
}

function buildModalChord(parts) {
  const mods = MODIFIER_ORDER.filter((m) => parts.includes(m));
  const rest = parts.filter((p) => !MODIFIER_ORDER.includes(p));
  return [...mods, ...rest].join("+");
}

function stopKeyCapture() {
  if (!keyCaptureState) return;
  const { inputId } = keyCaptureState;
  $(inputId)?.classList.remove("capturing");
  document.removeEventListener("keydown", onKeyCaptureDown, true);
  document.removeEventListener("keyup", onKeyCaptureUp, true);
  keyCaptureState = null;
}

function finishKeyCapture() {
  if (!keyCaptureState) return;
  const { inputId, parts, onFinish } = keyCaptureState;
  if (parts.length) {
    $(inputId).value = buildModalChord(parts);
  }
  const finish = onFinish;
  stopKeyCapture();
  finish?.();
}

function startKeyCapture(inputId, options = {}) {
  stopKeyCapture();
  const input = $(inputId);
  if (!input) return;
  const { canStart = () => true, onFinish = null, clearOnStart = true } = options;
  if (!canStart()) return;
  keyCaptureState = { inputId, parts: [], held: new Set(), onFinish, clearOnStart };
  if (clearOnStart) input.value = "";
  input.classList.add("capturing");
  document.addEventListener("keydown", onKeyCaptureDown, true);
  document.addEventListener("keyup", onKeyCaptureUp, true);
}

function startModalKeyCapture() {
  startKeyCapture("modal-key", {
    canStart: () => $("modal-type").value === "keyboard",
  });
}

function onKeyCaptureDown(e) {
  if (!keyCaptureState) return;
  e.preventDefault();
  e.stopPropagation();
  if (e.key === "Escape") {
    $(keyCaptureState.inputId).value = "";
    stopKeyCapture();
    return;
  }
  if (e.repeat) return;
  const part = normalizeCaptureKey(e);
  if (!keyCaptureState.parts.includes(part)) keyCaptureState.parts.push(part);
  keyCaptureState.held.add(e.code);
}

function onKeyCaptureUp(e) {
  if (!keyCaptureState) return;
  e.preventDefault();
  e.stopPropagation();
  keyCaptureState.held.delete(e.code);
  if (keyCaptureState.held.size === 0) finishKeyCapture();
}

async function playSequences(seqList, fromMs = 0) {
  const blocks = mergedPlayBlocks(seqList);
  if (!blocks.length) return false;
  await apiPlay(fromMs, blocks, getPlaybackOptions());
  startPlayheadLoop();
  return true;
}

async function startPlay() {
  const prof = activeProfile();
  const pb = getProfilePlayback(prof);
  const seqList = sequencesForPlayback(prof, { includeKeyTrigger: true });
  if (!seqList.length) {
    return;
  }
  const blocks = mergedPlayBlocks(seqList);
  if (!blocks.length) {
    return;
  }
  keyTriggerActiveKey = null;
  await playSequences(seqList, state.playheadMs);
}

async function toggleKeyTriggeredPlay(key, isDown) {
  if (!isDown) return;
  const normalized = normalizeTriggerKey(key);
  const seqList = sequencesForKeyTrigger(normalized);
  if (!seqList.length) return;

  const { playing } = await apiGetPlayhead();

  // Wenn bereits diese Taste aktiv ist ODER die Wiedergabe läuft und Trigger diese Sequenz steuert: STOP
  const isSameKey = keyTriggerActiveKey === normalized;
  
  // Wir stoppen, wenn die Wiedergabe läuft und entweder dieselbe Taste gedrückt wurde 
  // oder die gedrückte Taste eine der Sequenzen triggert, die gerade (potenziell) laufen.
  if (playing && isSameKey) {
    await stopPlay();
    return;
  }

  // Wenn etwas anderes spielt: STOP und dann START
  if (playing) await stopPlay();

  keyTriggerActiveKey = normalized;
  
  // Wir spielen die Sequenzen ab, die dieser Taste zugeordnet sind
  await playSequences(seqList, state.playheadMs);
}

async function stopPlay() {
  const res = await apiStop();
  stopPlayheadLoop();
  keyTriggerActiveKey = null;
  if (res?.positionMs != null) {
    state.playheadMs = res.positionMs;
    syncCurrentSeqToState();
  }
  updatePlayheadVisual();
}

async function togglePlayback() {
  const { playing } = await apiGetPlayhead();
  if (playing) {
    await stopPlay();
  } else {
    await startPlay();
  }
}

function startPlayheadLoop() {
  stopPlayheadLoop();
  const tick = async () => {
    const { positionMs, playing } = await apiGetPlayhead();
    state.playheadMs = positionMs;
    updatePlayheadVisual();
    if (playing) playheadRaf = requestAnimationFrame(tick);
    else {
      keyTriggerActiveKey = null;
      syncCurrentSeqToState();
      saveState();
    }
  };
  playheadRaf = requestAnimationFrame(tick);
}

function stopPlayheadLoop() {
  if (playheadRaf) cancelAnimationFrame(playheadRaf);
  playheadRaf = null;
}

function switchProfile(profileId) {
  syncCurrentSeqToState();
  saveState();
  state.activeProfileId = profileId;
  const prof = activeProfile();
  if (prof) {
    migrateProfileOcr(prof);
    const seq = activeSequence();
    state.playheadMs = seq?.playheadMs || 0;
    if (window.FiestaOcr) {
      window.FiestaOcr.pushConfig?.();
      window.FiestaOcr.onProfileSwitch?.();
    }
  }
  selectedIds.clear();
  render();
}

function createProfile() {
  const name = prompt("Profile Name:", "New Profile");
  if (!name?.trim()) return;
  const prof = newProfile(name.trim());
  state.profiles.push(prof);
  state.activeProfileId = prof.id;
  state.playheadMs = 0;
  selectedIds.clear();
  saveState();
  render();
}

function deleteProfile() {
  if (state.profiles.length <= 1) {
    alert("At least one profile must remain.");
    return;
  }
  const prof = activeProfile();
  if (!prof || !confirm(`Really delete profile "${prof.name}"?`)) return;
  const api = pywebviewApi();
  if (api) api.delete_profile_disk(prof.id, prof.name);
  state.profiles = state.profiles.filter((p) => p.id !== prof.id);
  state.activeProfileId = state.profiles[0].id;
  const seq = activeSequence();
  state.playheadMs = seq?.playheadMs || 0;
  saveState();
  render();
}

async function loadProfilesFromDisk() {
  const api = pywebviewApi();
  if (!api?.list_profiles) return false;
  try {
    const { profiles: names } = await api.list_profiles();
    const profileFiles = (names || []).filter((n) => n !== APP_META_KEY);
    if (!profileFiles.length) return false;

    const loadedProfiles = [];
    for (const name of profileFiles) {
      const res = await api.load_profile_disk(name);
      if (!res?.ok || !res.data) continue;
      const data = JSON.parse(res.data);
      if (data.profile?.id) {
        loadedProfiles.push(data.profile);
      } else if (data.profiles?.length) {
        loadedProfiles.push(...data.profiles);
      }
    }

    if (!loadedProfiles.length) return false;

    const byId = new Map();
    loadedProfiles.forEach((p) => {
      migrateProfileOcr(p);
      migrateProfile(p);
      byId.set(p.id, p);
    });
    state.profiles = [...byId.values()];

    const metaRes = await api.load_profile_disk(APP_META_KEY);
    if (metaRes?.ok && metaRes.data) {
      const meta = JSON.parse(metaRes.data);
      if (meta.activeProfileId && state.profiles.some((p) => p.id === meta.activeProfileId)) {
        state.activeProfileId = meta.activeProfileId;
      }
      if (meta.playheadMs != null) state.playheadMs = meta.playheadMs;
      if (meta.zoomLevel) zoomLevel = meta.zoomLevel;
      if (meta.appSettings) state.appSettings = meta.appSettings;
    }

    if (state.profiles.length && !state.profiles.some((p) => p.id === state.activeProfileId)) {
      state.activeProfileId = state.profiles[0].id;
    }

    return true;
  } catch (_) {
    return false;
  }
}

function ensureActiveProfileId() {
  if (!state?.profiles?.length) return;
  if (!state.profiles.some((p) => p.id === state.activeProfileId)) {
    state.activeProfileId = state.profiles[0].id;
  }
}

async function reloadFromDisk() {
  const hadDisk = await loadProfilesFromDisk();
  if (!hadDisk) loadState();
  ensureActiveProfileId();
  state.profiles.forEach((p) => {
    migrateProfileOcr(p);
    migrateProfile(p);
  });
  render();
  renderProfileSelect();
  syncUltraZoomFromSettings();
  window.FiestaCompact?.refresh?.();
  window.FiestaOcr?.onProfileSwitch?.();
}

async function init() {
  state = defaultState();
  await waitForPywebviewApi();
  const hadDisk = await loadProfilesFromDisk();
  if (!hadDisk && !loadState()) {
    state = defaultState();
  }
  ensureActiveProfileId();
  state.profiles.forEach((p) => {
    migrateProfileOcr(p);
    migrateProfile(p);
  });
  if (!state?.profiles?.length) {
    state = defaultState();
  }
  await persistProfilesToDisk();
  await syncTriggerKeysToBackend();
  render();
  renderProfileSelect();
  syncUltraZoomFromSettings();

  const seqPage = isSequencerPage();

  $("profile-select")?.addEventListener("change", (e) => switchProfile(e.target.value));
  $("btn-profile-new")?.addEventListener("click", createProfile);
  $("btn-profile-save")?.addEventListener("click", async () => {
    const ok = await saveStateAndDisk();
    const api = pywebviewApi();
    let dir = "profiles";
    if (api?.get_profiles_dir) {
      try {
        const info = await api.get_profiles_dir();
        if (info?.path) dir = info.path;
      } catch (_) {}
    }
    if (ok) alert(`Profile saved.\n\nFolder:\n${dir}`);
    else alert("Saving failed. Please restart the app and try again.");
  });
  $("btn-profile-delete")?.addEventListener("click", deleteProfile);

  window.FiestaApp = {
    activeProfile,
    saveState,
    state: () => state,
    reloadFromDisk,
    getUltraZoomSettings,
    applyUltraZoom,
    togglePlayback,
    resetTimeline,
  };

  if (!seqPage) {
    $("nav-modal-close")?.addEventListener("click", () => $("nav-modal").classList.add("hidden"));
    $("nav-modal")?.addEventListener("click", (e) => {
      if (e.target.id === "nav-modal") $("nav-modal").classList.add("hidden");
    });
    document.addEventListener("keydown", onSettingsKeyCapture, true);
    await bootAtomicClock();
    const prof = activeProfile();
    if (prof?.ocr && window.FiestaOcr?.autoStartMonitor) {
      window.FiestaOcr.autoStartMonitor();
    }
    return;
  }

  $("btn-add-track").onclick = () => {
    setTrackCount(getTrackCount() + 1);
    saveState();
    renderTracks();
  };
  $("btn-add-block").onclick = openNewBlockModal;
  $("btn-play").onclick = startPlay;
  $("btn-stop").onclick = stopPlay;
  window.addEventListener("resize", () => {
    ensureTimelineWidths();
    renderRuler(); // Ticks neu zeichnen, falls sich die Dauer geändert hat
    updatePlayheadLineHeight();
  });
  bindUltraZoomUi();
  const editorScroll = $("editor-scroll");
  $("ruler").addEventListener("mousedown", onRulerClick);
  editorScroll.addEventListener(
    "wheel",
    (e) => {
      if (!e.target.closest(".sequencer-panel")) return;
      if (!e.target.closest(".editor-scroll, .tracks-area, .track-lane, .ruler")) return;
      if (!e.ctrlKey) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -12 : 12;
      zoomLevel = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoomLevel + delta));
      renderRuler();
      renderTracks();
      updatePlayheadVisual();
    },
    { passive: false }
  );

  $("pb-scope").onchange = () => {
    const prof = activeProfile();
    if (!prof) return;
    getProfilePlayback(prof).scope = $("pb-scope").value;
    renderPlayChecks();
    renderPlaybackSettings();
    saveState();
  };
  $("pb-mode").onchange = () => {
    const prof = activeProfile();
    if (!prof) return;
    getProfilePlayback(prof).mode = $("pb-mode").value;
    renderPlaybackSettings();
    saveState();
  };
  if ($("pb-stop-condition")) {
    $("pb-stop-condition").onchange = () => {
      const prof = activeProfile();
      if (!prof) return;
      getProfilePlayback(prof).stopCondition = $("pb-stop-condition").value;
      renderPlaybackSettings();
      saveState();
    };
  }

  const bindSeqTrigger = () => {
    $("seq-trigger-mode")?.addEventListener("change", () => {
      const seq = activeSequence();
      if (!seq) return;
      seq.triggerMode = $("seq-trigger-mode").value;
      renderSequenceTriggerSettings();
      saveState();
      void syncTriggerKeysToBackend();
    });
    $("seq-trigger-key")?.addEventListener("mousedown", (e) => {
      e.preventDefault();
      $("seq-trigger-key").focus();
      startKeyCapture("seq-trigger-key", {
        onFinish: () => {
          const seq = activeSequence();
          if (!seq) return;
          seq.triggerKey = normalizeTriggerKey($("seq-trigger-key").value);
          saveState();
          void syncTriggerKeysToBackend();
        },
      });
    });
    $("seq-trigger-key")?.addEventListener("blur", () => {
      if (keyCaptureState?.inputId === "seq-trigger-key") {
        if (keyCaptureState.parts.length) finishKeyCapture();
        else stopKeyCapture();
      }
    });
  };
  bindSeqTrigger();
  $("pb-count").onchange = () => {
    const prof = activeProfile();
    if (prof) getProfilePlayback(prof).count = Number($("pb-count").value) || 3;
    saveState();
  };
  $("pb-minutes").onchange = () => {
    const prof = activeProfile();
    if (prof) getProfilePlayback(prof).minutes = Number($("pb-minutes").value) || 5;
    saveState();
  };
  $("pb-teleport-key").onchange = () => {
    const prof = activeProfile();
    if (prof) getProfilePlayback(prof).teleportKey = $("pb-teleport-key").value.trim().toLowerCase();
    saveState();
  };

  document.querySelectorAll(".top-nav-btn").forEach((btn) => {
    btn.dataset.i18n = btn.dataset.nav;
    btn.addEventListener("click", () => openNavModal(btn.dataset.nav));
  });
  document.addEventListener("keydown", onSettingsKeyCapture, true);
  $("nav-modal-close").onclick = () => $("nav-modal").classList.add("hidden");
  $("nav-modal").addEventListener("click", (e) => {
    if (e.target.id === "nav-modal") $("nav-modal").classList.add("hidden");
  });

  setupFocusFloat();
  applyLanguage();
  whenPywebviewReady(syncKeybindingsToBackend);

  $("modal-type").onchange = updateModalTypeUI;
  $("btn-pick-click").onclick = async () => {
    const api = pywebviewApi();
    if (!api) return alert("Only in py main.py available");
    const res = await api.pick_click_position();
    if (res.point) {
      const b = getBlocks().find((x) => x.id === editingId);
      if (b) {
        b.clickX = res.point.x;
        b.clickY = res.point.y;
        $("modal-click-pos").textContent = formatPosLabel(b.clickX, b.clickY);
      }
    }
  };

  $("lane-menu").addEventListener("click", (e) => {
    const action = e.target.dataset?.action;
    if (action === "new-block" && laneMenuAt) {
      createBlockAt(laneMenuAt.track, laneMenuAt.startMs);
      hideLaneMenu();
    }
  });

  $("modal-save").onclick = saveModal;
  $("modal-cancel").onclick = closeModal;
  $("btn-win-close").onclick = () => {
    const api = pywebviewApi();
    if (api?.close_app) api.close_app();
  };
  $("modal-delete").onclick = () => {
    if (editingId) deleteBlocks([editingId]);
    closeModal();
  };
  $("modal-key").addEventListener("mousedown", (e) => {
    e.preventDefault();
    $("modal-key").focus();
    startModalKeyCapture();
  });
  $("modal-key").addEventListener("blur", () => {
    if (keyCaptureState?.inputId === "modal-key") {
      if (keyCaptureState.parts.length) finishKeyCapture();
      else stopKeyCapture();
    }
  });

  $("context-menu").addEventListener("click", (e) => {
    const action = e.target.dataset?.action;
    if (!action) return;
    const ids = selectedIds.size ? [...selectedIds] : contextBlockId ? [contextBlockId] : [];
    hideContextMenu();
    if (action === "edit" && ids[0]) openModal(ids[0]);
    if (action === "duplicate") duplicateBlocks(ids);
    if (action === "delete") deleteBlocks(ids);
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#context-menu")) hideContextMenu();
    if (!e.target.closest("#lane-menu")) hideLaneMenu();
  });

  document.addEventListener("keydown", (e) => {
    if (capturingKbField) return;
    if (!$("modal").classList.contains("hidden")) return;
    if (!$("nav-modal").classList.contains("hidden") && $("settings-section")) return;
    if (!pywebviewApi()) {
      const kb = getAppSettings().keybindings;
      if (keyEventMatchesBinding(e, kb.togglePlay)) {
        e.preventDefault();
        window.FiestaHotkeys.togglePlay();
        return;
      }
      if (keyEventMatchesBinding(e, kb.resetTimeline)) {
        e.preventDefault();
        window.FiestaHotkeys.resetTimeline();
        return;
      }
      if (keyEventMatchesBinding(e, kb.toggleRecord)) {
        e.preventDefault();
        window.FiestaHotkeys.toggleRecord();
        return;
      }
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "z") {
      e.preventDefault();
      undo();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "y") {
      e.preventDefault();
      redo();
    }
    if (e.code === "Space") {
      e.preventDefault();
      apiGetPlayhead().then(({ playing }) => (playing ? stopPlay() : startPlay()));
    }
    if (e.key === "Delete" && selectedIds.size) {
      deleteBlocks([...selectedIds]);
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "d") {
      e.preventDefault();
      if (selectedIds.size) duplicateBlocks([...selectedIds]);
    }
  });

  let lastHotkeyTime = 0;

  window.FiestaHotkeys = {
    async togglePlay() {
      if (Date.now() - lastHotkeyTime < 200) return;
      lastHotkeyTime = Date.now();
      await togglePlayback();
    },
    resetTimeline() {
      resetTimeline();
    },
    triggerKeyDown(key) {
      if (Date.now() - lastHotkeyTime < 200) return;
      lastHotkeyTime = Date.now();
      toggleKeyTriggeredPlay(key, true);
    },
    triggerKeyUp(key) {
      // KeyUp darf öfter kommen, da es keinen Toggle auslöst
      toggleKeyTriggeredPlay(key, false);
    },
  };

  window.syncInitialSettingsToBackend = async () => {
    const api = pywebviewApi();
    if (!api) return;
    await syncKeybindingsToBackend();
  };

  setInterval(() => {
    if (isSequencerPage() && !playheadRaf) updatePlayheadVisual();
  }, 150);

  await bootAtomicClock();

  window.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && clockReady) {
      restartAtomicClock();
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
