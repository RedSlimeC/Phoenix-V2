/**
 * Slimec – Authentifizierung (Login & Register)
 */

(function () {
  const $ = (id) => document.getElementById(id);

  function showError(msg) {
    const errEl = $("auth-error");
    if (!errEl) return;
    errEl.textContent = msg;
    errEl.classList.remove("hidden");
    setTimeout(() => errEl.classList.add("hidden"), 5000);
  }

  function api() {
    return window.pywebview && window.pywebview.api;
  }

  async function handleLogin() {
    const user = $("login-user").value.trim();
    const pass = $("login-pass").value;

    if (!user || !pass) {
      return showError("Bitte alle Felder ausfüllen.");
    }

    const a = api();
    if (!a) return;

    try {
      const res = await a.auth_login(user, pass);
      if (res.success) {
        $("auth-overlay").classList.add("hidden");
        if (window.FiestaApp) {
            window.FiestaApp.currentUser = res.user;
        }
    window.FiestaCompact?.applyRankRestrictions?.();
    window.FiestaCompact?.updateRankLabel?.(res.user);
    window.FiestaOcr?.applyModalRankRestrictions?.();
    window.FiestaCompact?.refresh?.();
      } else {
        showError(res.message || "Login fehlgeschlagen.");
      }
    } catch (err) {
      showError("Verbindungsfehler zum Server.");
    }
  }

  async function handleRegister() {
    const user = $("reg-user").value.trim();
    const email = $("reg-email").value.trim();
    const pass = $("reg-pass").value;

    if (!user || !email || !pass) {
      return showError("Bitte alle Felder ausfüllen.");
    }

    const a = api();
    if (!a) return;

    try {
      const res = await a.auth_register(user, email, pass);
      if (res.success) {
        showError("Registrierung erfolgreich! Bitte einloggen.");
        switchForm("login");
      } else {
        showError(res.message || "Registrierung fehlgeschlagen.");
      }
    } catch (err) {
      showError("Verbindungsfehler zum Server.");
    }
  }

  function switchForm(mode) {
    if (mode === "register") {
      $("login-form").classList.add("hidden");
      $("register-form").classList.remove("hidden");
      $("auth-title").textContent = "Registrieren";
    } else {
      $("register-form").classList.add("hidden");
      $("login-form").classList.remove("hidden");
      $("auth-title").textContent = "Login";
    }
  }

  function initAuth() {
    $("btn-do-login").onclick = handleLogin;
    $("btn-do-register").onclick = handleRegister;

    $("link-to-register").onclick = (e) => {
      e.preventDefault();
      switchForm("register");
    };

    $("link-to-login").onclick = (e) => {
      e.preventDefault();
      switchForm("login");
    };

    // Enter-Key Support
    const handleEnter = (e, callback) => {
      if (e.key === "Enter") {
        e.preventDefault();
        callback();
      }
    };
    $("login-user").onkeydown = (e) => handleEnter(e, handleLogin);
    $("login-pass").onkeydown = (e) => handleEnter(e, handleLogin);
    $("reg-user").onkeydown = (e) => handleEnter(e, handleRegister);
    $("reg-email").onkeydown = (e) => handleEnter(e, handleRegister);
    $("reg-pass").onkeydown = (e) => handleEnter(e, handleRegister);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAuth);
  } else {
    initAuth();
  }
})();
