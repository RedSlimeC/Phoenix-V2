/**
 * Slimec – Kompakte Hauptansicht (Feature-Panel)
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const RANK_MEMBER = 1;
  const RANK_PREMIUM = 2;
  const PREMIUM_MSG = "Premium-Member erforderlich (Rank 2+).";

  function api() {
    return window.pywebview && window.pywebview.api;
  }

  function userRank() {
    return Number(window.FiestaApp?.currentUser?.rank ?? RANK_MEMBER);
  }

  function hasPremium() {
    return userRank() >= RANK_PREMIUM;
  }

  function isPremiumFeature(name) {
    return name === "mining" || name === "quest" || name === "sequencer";
  }

  function canUseFeature(name) {
    if (!isPremiumFeature(name)) return true;
    return hasPremium();
  }

  function denyPremium() {
    alert(PREMIUM_MSG);
  }

  function updateRankLabel(user) {
    const el = $("user-rank-label");
    if (!el) return;
    if (!user?.accountname) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    const label = user.rankLabel || (user.rank >= 9 ? "Admin" : user.rank >= 2 ? "Premium-Member" : "Member");
    el.textContent = `${user.accountname} · ${label}`;
    el.classList.remove("hidden");
  }

  function applyRankRestrictions() {
    document.querySelectorAll(".feature-row[data-premium='true']").forEach((row) => {
      const locked = !hasPremium();
      row.classList.toggle("feature-locked", locked);
      const toggle = row.querySelector("input[type='checkbox']");
      const gear = row.querySelector(".feature-gear");
      if (toggle && !toggle.classList.contains("feature-toggle-dummy")) {
        toggle.disabled = locked;
      }
      if (gear) gear.disabled = locked;

      row.querySelector(".feature-premium-badge")?.remove();

      let overlay = row.querySelector(".feature-lock-overlay");
      if (locked) {
        if (!overlay) {
          overlay = document.createElement("div");
          overlay.className = "feature-lock-overlay";
          overlay.textContent = "Requires Premium-Membership";
          row.appendChild(overlay);
        }
      } else if (overlay) {
        overlay.remove();
      }
    });
  }

  function primaryCharName() {
    return window.FiestaOcr?.getPrimaryCharName?.() || null;
  }

  function toggleSettings() {
    const settings = $("page-2");
    const main = $("page-1");
    if (!settings || !main) return;
    const opening = settings.classList.contains("hidden");
    settings.classList.toggle("hidden", !opening);
    main.classList.toggle("hidden", opening);
  }

  function syncFeatureToggles() {
    const char = primaryCharName();
    const prof = window.FiestaApp?.activeProfile?.();
    const healEl = $("feat-auto-heal");
    const miningEl = $("feat-fast-mining");
    const questEl = $("feat-auto-quest");
    const zoomEl = $("feat-ultra-zoom");
    const seqEl = $("feat-sequencer");

    if (healEl && char && prof?.ocr?.instances?.[char]) {
      healEl.checked = !!prof.ocr.instances[char].enabled;
    } else if (healEl) healEl.checked = false;

    if (miningEl && char && prof?.ocr?.instances?.[char] && hasPremium()) {
      miningEl.checked = !!prof.ocr.instances[char].mining?.enabled;
    } else if (miningEl) miningEl.checked = false;

    if (questEl && prof?.ocr?.quest && hasPremium()) {
      questEl.checked = !!prof.ocr.quest.enabled;
    } else if (questEl) questEl.checked = false;

    const uz = window.FiestaApp?.getUltraZoomSettings?.();
    if (zoomEl && uz) zoomEl.checked = !!uz.enabled;

    if (seqEl) {
      const a = api();
      if (a?.get_playhead) {
        a.get_playhead().then((res) => {
          seqEl.checked = !!res?.playing;
        });
      }
    }
  }

  async function setAutoHeal(enabled) {
    if (!canUseFeature("heal")) return denyPremium();
    const char = primaryCharName();
    if (!char || char === "—") {
      alert("Kein Fiesta-Charakter gefunden.");
      syncFeatureToggles();
      return;
    }
    window.FiestaOcr?.setCharHealEnabled?.(char, enabled);
    syncFeatureToggles();
  }

  async function setFastMining(enabled) {
    if (!canUseFeature("mining")) return denyPremium();
    const char = primaryCharName();
    if (!char || char === "—") {
      alert("Kein Fiesta-Charakter gefunden.");
      syncFeatureToggles();
      return;
    }
    window.FiestaOcr?.setCharMiningEnabled?.(char, enabled);
    syncFeatureToggles();
  }

  async function setAutoQuest(enabled) {
    if (!canUseFeature("quest")) return denyPremium();
    window.FiestaOcr?.setQuestEnabled?.(enabled);
    syncFeatureToggles();
  }

  async function setUltraZoom(enabled) {
    if (!canUseFeature("zoom")) return denyPremium();
    const uz = window.FiestaApp?.getUltraZoomSettings?.();
    if (!uz) return;
    await window.FiestaApp?.applyUltraZoom?.(enabled, uz.targetValue ?? 720);
    syncFeatureToggles();
  }

  async function setSequencerEnabled(enabled) {
    if (!canUseFeature("sequencer")) return denyPremium();
    if (enabled) {
      if (typeof window.startPlay === "function") {
        await window.startPlay();
      }
    } else {
      if (typeof window.stopPlay === "function") {
        await window.stopPlay();
      }
    }
    syncFeatureToggles();
  }

  function bindFeatureToggles() {
    $("feat-auto-heal")?.addEventListener("change", (e) => setAutoHeal(e.target.checked));
    $("feat-fast-mining")?.addEventListener("change", (e) => setFastMining(e.target.checked));
    $("feat-auto-quest")?.addEventListener("change", (e) => setAutoQuest(e.target.checked));
    $("feat-ultra-zoom")?.addEventListener("change", (e) => setUltraZoom(e.target.checked));
    $("feat-sequencer")?.addEventListener("change", (e) => setSequencerEnabled(e.target.checked));

    document.querySelectorAll(".feature-gear").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const gear = btn.dataset.gear;
        if (!canUseFeature(gear)) return denyPremium();
        if (gear === "sequencer") {
          const a = api();
          if (!a?.open_sequencer_window) return;
          const res = await a.open_sequencer_window();
          if (res?.error) alert(res.error);
          return;
        }
        const char = primaryCharName();
        if (!char && gear !== "quest") {
          alert("Kein Fiesta-Charakter gefunden. Spiel starten und warten.");
          return;
        }
        window.FiestaOcr?.openFeatureSettings?.(gear, char);
      });
    });
  }

  function bindInstancePager() {
    $("btn-instance-prev")?.addEventListener("click", () => {
      window.FiestaOcr?.cycleInstance?.(-1);
    });
    $("btn-instance-next")?.addEventListener("click", () => {
      window.FiestaOcr?.cycleInstance?.(1);
    });
  }

  function bindFooter() {
    $("btn-exit")?.addEventListener("click", () => {
      const a = api();
      if (a?.quit_app) a.quit_app();
      else window.close();
    });
    $("btn-footer-help")?.addEventListener("click", () => {
      if (window.openNavModal) window.openNavModal("help");
      else $("help-modal")?.classList.remove("hidden");
    });
    $("btn-footer-chat")?.addEventListener("click", () => toggleSettings());
    document.querySelectorAll(".compact-link-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (window.openNavModal) window.openNavModal(btn.dataset.nav);
      });
    });
  }

  function initCompactUi() {
    if (document.body.dataset.view !== "main") return;
    bindInstancePager();
    bindFeatureToggles();
    bindFooter();
    applyRankRestrictions();
    syncFeatureToggles();
    window.FiestaOcr?.updateInstanceIndicator?.();

    // Regelmäßig Toggles synchronisieren (besonders für Sequencer wichtig)
    setInterval(syncFeatureToggles, 2000);

    window.addEventListener("focus", () => {
      window.FiestaApp?.reloadFromDisk?.().then?.(() => syncFeatureToggles());
    });

    window.FiestaCompact = {
      refresh: syncFeatureToggles,
      toggleSettings,
      applyRankRestrictions,
      updateRankLabel,
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCompactUi);
  } else {
    initCompactUi();
  }
})();
