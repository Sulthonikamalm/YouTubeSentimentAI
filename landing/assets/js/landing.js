"use strict";

/**
 * Entry point landing page.
 * Memuat: landing.hero.js (hero canvas) + landing.sections.js (section interaktif),
 * lalu file ini mengorkestrasi semua inisialisasi + navbar/scroll/effects.
 * Semua di-load sebagai classic script (urutan: hero, sections, lalu file ini),
 * sehingga seluruh fungsi global sudah tersedia saat initLanding() berjalan.
 */

document.addEventListener("DOMContentLoaded", initLanding);

function initLanding() {
  const reducedMotion = respectReducedMotion();

  initNavbar();
  initSmoothScroll(reducedMotion);
  initMobileMenu();
  initComparisonShowcase();
  initWorkflowStepper();
  initDashboardPreviewTabs();
  initInsightCards();
  initFAQAccordion();
  initCounters(reducedMotion);
  initScrollReveal(reducedMotion);
  initScrollParallax(reducedMotion);

  if (!reducedMotion) initHeroFrameParallax();
}

function respectReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function initNavbar() {
  const navbar = document.getElementById("navbar");
  const links = Array.from(document.querySelectorAll(".desktop-nav a, .mobile-menu a[href^='#']"));
  const sections = Array.from(document.querySelectorAll("main section[id]"));
  let ticking = false;

  function updateNavbar() {
    navbar.classList.toggle("is-scrolled", window.scrollY > 24);
    const marker = window.scrollY + window.innerHeight * 0.32;
    let activeId = "";

    sections.forEach((section) => {
      if (marker >= section.offsetTop && marker < section.offsetTop + section.offsetHeight) activeId = section.id;
    });

    links.forEach((link) => {
      const matches = link.getAttribute("href") === `#${activeId}`;
      link.classList.toggle("is-active", matches);
      if (matches) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });

    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateNavbar);
    }
  }, { passive: true });

  updateNavbar();
}

function initSmoothScroll(reducedMotion) {
  document.querySelectorAll("a[href^='#']").forEach((link) => {
    link.addEventListener("click", (event) => {
      const targetId = link.getAttribute("href");
      if (!targetId || targetId === "#") return;
      const target = document.querySelector(targetId);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
    });
  });
}

function initMobileMenu() {
  const button = document.getElementById("mobileMenuButton");
  const menu = document.getElementById("mobileMenu");
  const navbar = document.getElementById("navbar");
  if (!button || !menu) return;

  function setOpen(open) {
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "Tutup menu" : "Buka menu");
    menu.hidden = !open;
    navbar.classList.toggle("menu-active", open);
    document.body.classList.toggle("menu-open", open);
  }

  button.addEventListener("click", () => setOpen(button.getAttribute("aria-expanded") !== "true"));
  menu.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setOpen(false)));
  window.addEventListener("resize", () => {
    if (window.innerWidth > 820) setOpen(false);
  }, { passive: true });
}

function initCounters(reducedMotion) {
  const counters = Array.from(document.querySelectorAll(".counter[data-counter]"));
  if (reducedMotion || !("IntersectionObserver" in window)) {
    counters.forEach((counter) => { counter.textContent = counter.dataset.counter; });
    return;
  }

  function animateCounter(element) {
    const target = Number(element.dataset.counter);
    const duration = 900;
    const start = performance.now();

    function update(now) {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = String(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      animateCounter(entry.target);
      currentObserver.unobserve(entry.target);
    });
  }, { threshold: 0.55 });

  counters.forEach((counter) => {
    counter.textContent = "0";
    observer.observe(counter);
  });
}

function initScrollReveal(reducedMotion) {
  const elements = Array.from(document.querySelectorAll(".reveal"));
  if (reducedMotion || !("IntersectionObserver" in window)) {
    elements.forEach((element) => element.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      currentObserver.unobserve(entry.target);
    });
  }, { threshold: 0.14, rootMargin: "0px 0px -7%" });

  elements.forEach((element) => {
    observer.observe(element);
  });
}

function initScrollParallax(reducedMotion) {
  if (reducedMotion) return;
  // Disable parallax on phones for better scroll performance
  if (window.innerWidth <= 560) return;
  const elements = Array.from(document.querySelectorAll("[data-parallax]"));
  if (!elements.length) return;

  let ticking = false;

  function updateParallax() {
    const windowHeight = window.innerHeight;

    elements.forEach((el) => {
      const speed = parseFloat(el.dataset.parallax) || 0.05;
      const rect = el.getBoundingClientRect();
      const elementCenter = rect.top + rect.height / 2;
      const viewportCenter = windowHeight / 2;

      // Calculate distance from center of viewport
      const offset = (elementCenter - viewportCenter) * speed;

      el.style.transform = `translateY(${offset}px)`;
    });

    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateParallax);
    }
  }, { passive: true });

  updateParallax();
}
