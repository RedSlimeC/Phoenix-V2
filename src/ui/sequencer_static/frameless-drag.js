/**
 * Slimec – Rahmenloses Hauptfenster per Drag verschieben (inkl. Login).
 */
(function () {
  if (document.body.dataset.view !== "main" && document.body.dataset.view !== "sequencer") return;

  const DRAG_PX = 4;
  const NO_DRAG =
    "input, textarea, select, button, a, label, .toggle-switch, .feature-gear, .footer-btn, .pager-arrow, .compact-link-btn, .btn-ocr-close, .btn-ocr-action, .btn-ocr-link, .btn-auth-primary, .auth-field, .modal:not(.hidden) .modal-box, .modal:not(.hidden) .modal-box *";

  let down = null;
  let dragging = false;
  let winStart = null;
  let pendingPos = null;
  let moveRaf = 0;
  let lastScreen = null;

  function api() {
    return window.pywebview && window.pywebview.api;
  }

  function isBlockedTarget(el) {
    return !!(el && el.closest && el.closest(NO_DRAG));
  }

  function flushMove() {
    moveRaf = 0;
    if (!pendingPos || !dragging) return;
    const a = api();
    if (a?.main_set_position) {
      a.main_set_position(pendingPos.x, pendingPos.y);
    }
    pendingPos = null;
  }

  function queueMove(x, y) {
    pendingPos = { x, y };
    if (!moveRaf) moveRaf = requestAnimationFrame(flushMove);
  }

  function onPointerDown(e) {
    if (e.button !== 0) return;
    if (isBlockedTarget(e.target)) return;

    down = { x: e.screenX, y: e.screenY };
    lastScreen = { x: e.screenX, y: e.screenY };
    dragging = false;
    winStart = null;
    pendingPos = null;

    const a = api();
    if (a?.main_get_position) {
      a.main_get_position().then((pos) => {
        if (pos?.ok && down) winStart = { x: pos.x, y: pos.y };
      });
    }
  }

  function onPointerMove(e) {
    if (!down) return;
    const total = Math.hypot(e.screenX - down.x, e.screenY - down.y);
    if (total >= DRAG_PX) {
      if (!dragging) {
        dragging = true;
        document.body.classList.add("window-dragging");
      }
    }
    if (!dragging) return;

    if (winStart) {
      queueMove(
        Math.round(winStart.x + (e.screenX - down.x)),
        Math.round(winStart.y + (e.screenY - down.y))
      );
      return;
    }

    const dx = e.screenX - lastScreen.x;
    const dy = e.screenY - lastScreen.y;
    lastScreen = { x: e.screenX, y: e.screenY };
    if (!dx && !dy) return;
    const a = api();
    if (a?.main_move_by) a.main_move_by(dx, dy);
  }

  function onPointerUp(e) {
    if (!down || e.button !== 0) return;
    const finalPos = pendingPos;
    down = null;
    dragging = false;
    winStart = null;
    lastScreen = null;
    pendingPos = null;
    document.body.classList.remove("window-dragging");
    if (moveRaf) {
      cancelAnimationFrame(moveRaf);
      moveRaf = 0;
    }
    if (finalPos) {
      const a = api();
      if (a?.main_set_position) a.main_set_position(finalPos.x, finalPos.y);
    }
  }

  document.addEventListener("pointerdown", onPointerDown);
  document.addEventListener("pointermove", onPointerMove);
  document.addEventListener("pointerup", onPointerUp);
  document.addEventListener("pointercancel", onPointerUp);
})();
