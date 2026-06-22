/**
 * stepper.js — Crawl progress stepper logic for Pantausentimen dashboard.
 * Manages steps state, logs parsing, run button states, and DOM updates.
 */

(() => {
  "use strict";

  const STEPS_MAP = {
    both: ["idle", "connecting", "crawling", "analyzing", "done"],
    crawl: ["idle", "connecting", "crawling", "done"],
    inference: ["idle", "connecting", "analyzing", "done"],
  };

  function getActiveStepper(state) {
    if (state.currentRunMode === "crawl") return document.getElementById("stepperCrawl");
    if (state.currentRunMode === "inference") return document.getElementById("stepperInference");
    return document.getElementById("stepperBoth");
  }

  function setCrawlStep(stepName, detail, state) {
    state.crawlStep = stepName;
    const stepper = getActiveStepper(state);
    if (!stepper) return;
    const stepArr = STEPS_MAP[state.currentRunMode] || STEPS_MAP.both;
    const stepIndex = stepArr.indexOf(stepName);
    const badge = document.getElementById("crawlStatusBadge");

    stepper.querySelectorAll(".stepper-step").forEach((el, i) => {
      el.classList.remove("completed", "active", "error");
      if (i < stepIndex) el.classList.add("completed");
      else if (i === stepIndex) el.classList.add("active");
    });

    if (badge) {
      badge.className = "crawl-progress-badge";
      const labels = {
        idle: "Sistem siap menerima perintah.",
        done: "Pekerjaan selesai.",
        connecting: "Menyambungkan/Mengecek data...",
        crawling: "Sedang mencari komentar terbaru...",
        analyzing: "Memproses sentimen dan isu dengan AI..."
      };
      badge.textContent = labels[stepName] || "Sedang Berjalan...";
      badge.classList.add(stepName === "idle" ? "idle" : stepName === "done" ? "done" : "running");
    }

    if (detail) {
      const el = stepper.querySelector(`[data-step="${stepName}"] .stepper-detail`);
      if (el) el.textContent = detail;
    }
    
    if (stepName === "idle") {
      stepper.querySelectorAll(".stepper-detail").forEach(e => e.textContent = "-");
    } else if (stepName === "done" && !detail) {
      const el = stepper.querySelector(`[data-step="done"] .stepper-detail`);
      if (el && el.textContent === "-") el.textContent = "Selesai.";
    }
  }

  function setRunMode(mode, state) {
    state.currentRunMode = mode;
    const stepperBoth = document.getElementById("stepperBoth");
    const stepperCrawl = document.getElementById("stepperCrawl");
    const stepperInference = document.getElementById("stepperInference");
    if (stepperBoth) stepperBoth.style.display = mode === "both" ? "flex" : "none";
    if (stepperCrawl) stepperCrawl.style.display = mode === "crawl" ? "flex" : "none";
    if (stepperInference) stepperInference.style.display = mode === "inference" ? "flex" : "none";
    setCrawlStep("idle", null, state);
  }

  function setCrawlError(state) {
    const stepper = getActiveStepper(state);
    if (!stepper) return;
    const stepArr = STEPS_MAP[state.currentRunMode] || STEPS_MAP.both;
    const stepIndex = stepArr.indexOf(state.crawlStep);
    const steps = stepper.querySelectorAll(".stepper-step");
    if (steps[stepIndex]) {
      steps[stepIndex].classList.remove("active");
      steps[stepIndex].classList.add("error");
    }
    const badge = document.getElementById("crawlStatusBadge");
    if (badge) {
      badge.textContent = "Pekerjaan gagal. Lihat detail error.";
      badge.className = "crawl-progress-badge error";
    }
  }

  function inferCrawlStepFromLogs(logs, state) {
    if (!logs || !logs.length) return;

    let currentRunLogs = logs;
    if (state && state.runStartTime) {
      const startTime = new Date(state.runStartTime).getTime();
      currentRunLogs = logs.filter(log => {
        const match = log.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})/);
        if (match) {
          const logDate = new Date(`${match[1]}T${match[2]}`);
          // 30-second buffer to handle minor clock differences between client and server
          return logDate.getTime() >= (startTime - 30000);
        }
        return true;
      });
    }

    if (!currentRunLogs.length) return;

    const all = currentRunLogs.join(" ");
    const last = currentRunLogs[currentRunLogs.length - 1] || "";
    if (all.includes("Selesai") || all.includes("completed") || all.includes("SUCCESS")) {
      setCrawlStep("done", window.UI.formatTimeAgo(new Date().toISOString()), state);
    } else if (all.includes("Inference") || all.includes("sentimen") || all.includes("Sahabat-AI") || all.includes("Ollama")) {
      setCrawlStep("analyzing", "Menganalisis komentar...", state);
    } else if (all.includes("komentar") || all.includes("Mengambil") || all.includes("fetch") || all.includes("comment")) {
      const m = last.match(/(\d+)\s*komentar/i);
      setCrawlStep("crawling", m ? `${m[1]} komentar diperiksa` : "Mengambil komentar...", state);
    } else if (all.includes("Memulai") || all.includes("connect") || all.includes("API")) {
      setCrawlStep("connecting", "Mengecek video yang dipantau...", state);
    }
  }

  function updateRunButtonsState(state) {
    const isRunning = state.crawlRunning;
    const btnSystem = document.getElementById("btnRunSystem");
    const btnCrawl = document.getElementById("btnRunCrawlOnly");
    const btnInference = document.getElementById("btnRunInferenceOnly");
    const btnStop = document.getElementById("btnStopInference");
    const suffix = state.selectedVideoId ? " Video Ini" : " Saja";

    if (btnSystem) {
      btnSystem.disabled = isRunning;
      if (!isRunning) {
        btnSystem.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Jalankan Sistem${state.selectedVideoId ? " (1 Video)" : ""}`;
      }
    }
    if (btnCrawl) {
      btnCrawl.disabled = isRunning;
      if (!isRunning) {
        btnCrawl.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Crawl${suffix}`;
      }
    }
    if (btnInference) {
      btnInference.disabled = isRunning;
      if (!isRunning) {
        btnInference.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z"/></svg> Analisis${suffix}`;
      }
    }

    if (btnStop) {
      if (isRunning && (state.currentRunMode === "inference" || state.currentRunMode === "both")) {
        btnStop.style.display = "inline-flex";
      } else {
        btnStop.style.display = "none";
      }
    }
  }

  // Expose globally
  window.Stepper = {
    STEPS_MAP,
    setRunMode,
    setCrawlStep,
    setCrawlError,
    inferCrawlStepFromLogs,
    updateRunButtonsState,
  };
})();
