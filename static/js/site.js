/*
  Small enhancements. Every page works without JavaScript; this file only
  makes things nicer: the mobile menu, + / − bottle steppers, closing
  messages, the age check and "are you sure?" prompts.
*/

(() => {
  "use strict";

  // ── Mobile navigation drawer ───────────────────────────────────────
  const nav = document.getElementById("site-nav");
  const backdrop = document.querySelector(".nav-backdrop");
  const openers = document.querySelectorAll("[data-nav-open]");
  const closers = document.querySelectorAll("[data-nav-close]");

  function setNav(open) {
    if (!nav) return;
    nav.toggleAttribute("data-open", open);
    backdrop?.toggleAttribute("hidden", !open);
    openers.forEach((button) => button.setAttribute("aria-expanded", String(open)));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) nav.querySelector("a, input, button")?.focus();
  }

  openers.forEach((button) => button.addEventListener("click", () => setNav(true)));
  closers.forEach((button) => button.addEventListener("click", () => setNav(false)));
  backdrop?.addEventListener("click", () => setNav(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav?.hasAttribute("data-open")) setNav(false);
  });

  // ── Bottle steppers: <div class="stepper" data-stepper> ───────────
  document.querySelectorAll("[data-stepper]").forEach((stepper) => {
    const input = stepper.querySelector("input");
    if (!input) return;
    const min = Number(input.min || 0);
    const max = Number(input.max || 999);

    stepper.querySelectorAll("[data-step]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = Math.min(max, Math.max(min, (Number(input.value) || 0) + Number(button.dataset.step)));
        if (next === Number(input.value)) return;
        input.value = next;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });
    });
  });

  // Cart lines save themselves when the quantity changes.
  document.querySelectorAll("form[data-autosubmit]").forEach((form) => {
    let timer;
    form.addEventListener("change", () => {
      clearTimeout(timer);
      timer = setTimeout(() => form.requestSubmit(), 450);
    });
    form.querySelector("[data-autosubmit-hide]")?.setAttribute("hidden", "");
  });

  // ── Messages: close button, success messages fade after a while ────
  document.querySelectorAll(".message").forEach((message) => {
    message.querySelector(".message__close")?.addEventListener("click", () => message.remove());
    if (message.classList.contains("message--success")) {
      setTimeout(() => message.remove(), 8000);
    }
  });

  // ── "Are you sure?" for buttons with data-confirm ───────────────────
  document.addEventListener("submit", (event) => {
    const button = event.submitter;
    const question = button?.dataset.confirm || event.target.dataset.confirm;
    if (question && !window.confirm(question)) event.preventDefault();
  });

  // ── Age check (EU: wine is only sold to adults) ─────────────────────
  const gate = document.getElementById("age-gate");
  const COOKIE = "vinop_age_ok=1";
  if (gate && typeof gate.showModal === "function" && !document.cookie.includes(COOKIE)) {
    gate.showModal();
    gate.addEventListener("cancel", (event) => event.preventDefault()); // Esc doesn't skip it
    gate.querySelector("[data-age-yes]")?.addEventListener("click", () => {
      document.cookie = `${COOKIE}; max-age=${60 * 60 * 24 * 365}; path=/; SameSite=Lax`;
      gate.close();
    });
    gate.querySelector("[data-age-no]")?.addEventListener("click", () => {
      gate.querySelector("[data-age-question]").hidden = true;
      gate.querySelector("[data-age-sorry]").hidden = false;
    });
  }
})();
