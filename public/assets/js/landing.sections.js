"use strict";

/**
 * Interaksi untuk section konten landing page:
 * comparison showcase, workflow stepper, dashboard preview tabs,
 * insight accordion, dan FAQ accordion.
 * Bergantung pada respectReducedMotion() (didefinisikan di landing.js).
 */

function initComparisonShowcase() {
  const stage = document.querySelector(".comparison-stage");
  if (!stage) return;

  const tabs = Array.from(document.querySelectorAll("[data-comparison-target]"));
  const cards = Array.from(stage.querySelectorAll("[data-comparison-card]"));
  const previews = Array.from(stage.querySelectorAll("[data-comparison-preview]"));

  function activate(state, moveFocus = false) {
    stage.dataset.comparisonActive = state;

    tabs.forEach((tab) => {
      const active = tab.dataset.comparisonTarget === state;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && moveFocus) tab.focus();
    });

    cards.forEach((card) => {
      const active = card.dataset.comparisonCard === state;
      card.classList.toggle("is-active", active);
      card.setAttribute("aria-hidden", String(!active));
    });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab.dataset.comparisonTarget));
    tab.addEventListener("pointerenter", () => activate(tab.dataset.comparisonTarget));
    tab.addEventListener("focus", () => activate(tab.dataset.comparisonTarget));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      activate(tabs[nextIndex].dataset.comparisonTarget, true);
    });
  });

  cards.forEach((card) => {
    card.addEventListener("pointerenter", () => {
      if (card.getAttribute("aria-hidden") === "true") activate(card.dataset.comparisonCard);
    });
    card.addEventListener("click", () => {
      if (card.getAttribute("aria-hidden") === "true") activate(card.dataset.comparisonCard);
    });
  });

  previews.forEach((preview) => {
    preview.addEventListener("pointerenter", () => activate(preview.dataset.comparisonPreview));
    preview.addEventListener("click", () => activate(preview.dataset.comparisonPreview));
  });
}

function initWorkflowStepper() {
  const section = document.querySelector(".workflow");
  const steps = Array.from(document.querySelectorAll(".workflow-step"));
  const preview = document.querySelector(".workflow-preview");
  const progress = document.getElementById("workflowProgress");
  if (!steps.length || !preview || !section) return;

  const workflowData = [
    {
      status: "Sumber pemantauan",
      title: "Pilih video yang ingin dipantau",
      description: "Masukkan URL video YouTube publik dan kelompokkan ke proyek pemantauan yang sesuai.",
      label: "URL video YouTube",
      field: "youtube.com/watch?v=isu-publik",
      meta: "Proyek: Respons kebijakan",
      result: "Siap dipantau",
      variant: "video"
    },
    {
      status: "Pengambilan data",
      title: "Ambil komentar dan reply terbaru",
      description: "Sistem mengambil komentar dan reply terbaru dari video yang dipantau melalui API resmi.",
      label: "Status pengambilan",
      field: "89 komentar baru ditemukan",
      meta: "Komentar utama dan reply",
      result: "Berjalan",
      variant: "collect"
    },
    {
      status: "Pemeriksaan data",
      title: "Lewati komentar yang sudah tersimpan",
      description: "Komentar yang sudah pernah tersimpan dilewati agar data tidak dobel.",
      label: "Pemeriksaan ID komentar",
      field: "89 baru · 27 sudah tersimpan",
      meta: "Pencocokan berdasarkan ID",
      result: "Data bersih",
      variant: "filter"
    },
    {
      status: "Analisis komentar",
      title: "Baca sentimen, isu, dan arah respons",
      description: "Setiap komentar dianalisis untuk membantu melihat sentimen, isu dominan, stance, dan action intent.",
      label: "Antrean analisis",
      field: "363 dari 363 komentar dianalisis",
      meta: "Sentimen · isu · stance · intent",
      result: "100% selesai",
      variant: "analysis"
    },
    {
      status: "Ringkasan insight",
      title: "Tampilkan konteks yang dapat ditinjau",
      description: "Dashboard menyatukan metrik, komentar representatif, dan rekomendasi tindakan dalam satu tampilan.",
      label: "Insight terbaru",
      field: "Isu ekonomi rakyat perlu ditinjau",
      meta: "Berdasarkan komentar terkumpul",
      result: "Siap diperiksa",
      variant: "insight"
    }
  ];

  let currentActiveIndex = 0;

  function activate(index, focusStep, fromScroll = false) {
    if (fromScroll && index === currentActiveIndex) return;
    currentActiveIndex = index;

    const data = workflowData[index];

    if (fromScroll) {
      updateDOM(index, data, focusStep);
    } else {
      preview.classList.add("is-changing");
      window.setTimeout(() => {
        updateDOM(index, data, focusStep);
        preview.classList.remove("is-changing");
      }, 170);
    }
  }

  function updateDOM(index, data, focusStep) {
    document.getElementById("workflowStatus").textContent = data.status;
    document.getElementById("workflowLabel").textContent = `Langkah ${index + 1} dari ${steps.length}`;
    document.getElementById("workflowPreviewTitle").textContent = data.title;
    document.getElementById("workflowPreviewDescription").textContent = data.description;
    const mock = document.getElementById("workflowMock");
    mock.dataset.variant = data.variant;
    mock.querySelector(".preview-ui__label").textContent = data.label;
    mock.querySelector(".preview-ui__field").textContent = data.field;
    mock.querySelector(".preview-ui__meta span").textContent = data.meta;
    mock.querySelector(".preview-ui__meta strong").textContent = data.result;

    steps.forEach((step, stepIndex) => {
      const active = stepIndex === index;
      step.classList.toggle("is-active", active);
      step.classList.toggle("is-complete", stepIndex < index);
      step.setAttribute("aria-selected", String(active));
      step.tabIndex = active ? 0 : -1;
    });
    progress.style.height = `${(index / (steps.length - 1)) * 100}%`;
    if (focusStep) steps[index].focus();
  }

  steps.forEach((step, index) => {
    step.addEventListener("click", () => activate(index, false));
    step.addEventListener("keydown", (event) => {
      if (!["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === "ArrowDown" || event.key === "ArrowRight" ? 1 : -1;
      activate((index + direction + steps.length) % steps.length, true);
    });
  });

  let ticking = false;
  function updateScroll() {
    if (window.innerWidth <= 820) {
      ticking = false;
      return;
    }
    const rect = section.getBoundingClientRect();
    const stickyTop = 114; // var(--nav-height) + 40
    const distance = section.offsetHeight - window.innerHeight;

    if (distance > 0 && rect.top <= stickyTop) {
      let progressRatio = (stickyTop - rect.top) / distance;
      progressRatio = Math.max(0, Math.min(1, progressRatio));

      let targetIndex = Math.floor(progressRatio * steps.length);
      if (targetIndex >= steps.length) targetIndex = steps.length - 1;

      activate(targetIndex, false, true);
    }
    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateScroll);
    }
  }, { passive: true });
}

function initDashboardPreviewTabs() {
  const tabs = Array.from(document.querySelectorAll("[data-dashboard-tab]"));
  const shell = document.querySelector(".dashboard-shell");
  if (!tabs.length || !shell) return;

  const descriptions = {
    sentiment: "Lihat keseimbangan sentimen dan perubahan respons pada komentar yang telah dianalisis.",
    issues: "Temukan isu yang paling sering muncul beserta istilah dan komentar yang memberi konteks.",
    recommendation: "Tinjau rekomendasi tindakan dan dasar data sebelum membawanya ke keputusan tim."
  };

  function activate(index, focusTab) {
    const key = tabs[index].dataset.dashboardTab;
    shell.dataset.activeDashboard = key;
    document.getElementById("dashboardTabDescription").textContent = descriptions[key];
    document.querySelectorAll("[data-dashboard-module]").forEach((module) => {
      module.classList.toggle("is-highlighted", module.dataset.dashboardModule === key);
    });
    tabs.forEach((tab, tabIndex) => {
      const active = tabIndex === index;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    if (focusTab) tabs[index].focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(index, false));
    tab.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      activate((index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length, true);
    });
  });
}

function initInsightCards() {
  const cards = Array.from(document.querySelectorAll(".insight-item"));
  if (!cards.length) return;

  function setOpen(target, shouldOpen) {
    cards.forEach((card) => {
      const open = card === target && shouldOpen;
      card.classList.toggle("is-open", open);
      card.querySelector("button").setAttribute("aria-expanded", String(open));
      card.querySelector(".insight-item__body").hidden = !open;
    });
  }

  cards.forEach((card) => {
    card.querySelector("button").addEventListener("click", () => setOpen(card, !card.classList.contains("is-open")));
  });

  const openInsightButton = document.querySelector("[data-open-insight]");
  if (openInsightButton) {
    openInsightButton.addEventListener("click", () => {
      setOpen(cards[2], true);
      document.getElementById("insight").scrollIntoView({ behavior: respectReducedMotion() ? "auto" : "smooth" });
    });
  }
}

function initFAQAccordion() {
  const items = Array.from(document.querySelectorAll(".faq-item"));
  items.forEach((item) => {
    const button = item.querySelector("button");
    const body = item.querySelector("div");
    button.addEventListener("click", () => {
      const shouldOpen = !item.classList.contains("is-open");
      items.forEach((other) => {
        other.classList.remove("is-open");
        other.querySelector("button").setAttribute("aria-expanded", "false");
        other.querySelector("div").hidden = true;
      });
      if (shouldOpen) {
        item.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");
        body.hidden = false;
      }
    });
  });
}
