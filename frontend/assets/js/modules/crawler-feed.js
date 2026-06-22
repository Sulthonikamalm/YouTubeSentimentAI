/**
 * crawler-feed.js — Logic for Crawler Polling and Run Buttons
 */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, showToast, escapeHtml } = window.UI;

  const LOG_POLL_INTERVAL_MS = 5000;
  let logPollTimer = null;
  let _lastLogHash = "";

  const setRunMode = (mode) => window.Stepper.setRunMode(mode, window.MainState);
  const setCrawlStep = (step, detail) => window.Stepper.setCrawlStep(step, detail, window.MainState);
  const setCrawlError = () => window.Stepper.setCrawlError(window.MainState);
  const inferCrawlStepFromLogs = (logs) => window.Stepper.inferCrawlStepFromLogs(logs, window.MainState);
  const updateRunButtonsState = () => window.Stepper.updateRunButtonsState(window.MainState);

  async function pollCrawlerLogs() {
    try {
      const data = await apiFetch("/crawler/logs?limit=50");
      const body = $("liveFeedBody");
      if (data.logs && body) {
        const filtered = data.logs.filter(l => !l.includes("API Call logged:"));
        const newHtml = filtered.map(log => {
          let cls = "info";
          if (log.includes("ERROR") || log.includes("Exception")) cls = "error";
          else if (log.includes("WARNING") || log.includes("Rate Limit")) cls = "warning";
          else if (log.includes("SUCCESS") || log.includes("Selesai") || log.includes("completed")) cls = "success";
          return `<div class="terminal-line"><span class="${cls}">${escapeHtml(log)}</span></div>`;
        }).join("");

        const hashKey = `${filtered.length}:${newHtml.slice(0, 100)}:${newHtml.slice(-100)}`;
        if (hashKey !== _lastLogHash) {
          _lastLogHash = hashKey;
          body.innerHTML = newHtml;
          body.scrollTop = body.scrollHeight;
        }
        inferCrawlStepFromLogs(data.logs);
      }
    } catch { /* ignore */ }
  }

  function startLogPolling() {
    if (logPollTimer) return;
    const el = $("liveFeedStatus"); if (el) el.className = "pulse-indicator green";
    pollCrawlerLogs();
    logPollTimer = setInterval(pollCrawlerLogs, LOG_POLL_INTERVAL_MS);
  }

  function stopLogPolling() {
    if (logPollTimer) { clearInterval(logPollTimer); logPollTimer = null; }
    const el = $("liveFeedStatus"); if (el) el.className = "pulse-indicator gray";
  }

  function initCrawlerFeedEvents() {
    $("btnRunSystem")?.addEventListener("click", async () => {
      const btn = $("btnRunSystem"); btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Menjalankan Sistem...';
      setRunMode("both"); 
      window.MainState.crawlRunning = true;
      window.MainState.abortRequested = false;
      window.MainState.runStartTime = new Date();
      updateRunButtonsState();
      setCrawlStep("connecting", "Menyiapkan Crawl & Analisis..."); 
      startLogPolling();
      await new Promise(r => setTimeout(r, 1500));
      try {
        const videoParam = window.MainState.selectedVideoId ? `&video_id=${window.MainState.selectedVideoId}` : "";
        const r = await apiFetch(`/crawler/run?mode=both${videoParam}`, { method: "POST" });
        if (window.MainState.abortRequested) {
          window.MainState.abortRequested = false;
          setCrawlStep("idle", "Analisis dihentikan oleh pengguna.");
          return;
        }
        if (r.success) { 
          showToast("success", "Sistem Berjalan", `Run ID: ${r.run_id || "-"}`); 
          setCrawlStep("crawling", "Sistem sedang bekerja..."); 
          setTimeout(window.TabDashboard.loadDashboard, 3000); 
        } else { 
          showToast("warning", "Gagal", r.error); setCrawlError(); 
        }
      } catch (err) { 
        if (!window.MainState.abortRequested) {
          const msg = err.message === "crawl_already_running" ? "Sistem sedang bekerja di latar belakang. Harap tunggu sejenak." : err.message;
          showToast("error", "Error", msg); setCrawlError(); 
        }
      }
      finally { 
        btn.disabled = false; btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Jalankan Sistem'; 
        window.MainState.crawlRunning = false;
        updateRunButtonsState(); 
      }
    });

    $("btnRunCrawlOnly")?.addEventListener("click", async () => {
      const btn = $("btnRunCrawlOnly"); btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Crawling...';
      setRunMode("crawl"); 
      window.MainState.crawlRunning = true;
      window.MainState.abortRequested = false;
      window.MainState.runStartTime = new Date();
      updateRunButtonsState();
      setCrawlStep("connecting", "Menyambungkan ke YouTube API..."); 
      startLogPolling();
      await new Promise(r => setTimeout(r, 1500));
      try {
        const videoParam = window.MainState.selectedVideoId ? `&video_id=${window.MainState.selectedVideoId}` : "";
        const r = await apiFetch(`/crawler/run?mode=crawl_only${videoParam}`, { method: "POST" });
        if (window.MainState.abortRequested) {
          window.MainState.abortRequested = false;
          setCrawlStep("idle", "Proses dihentikan oleh pengguna.");
          return;
        }
        if (r.success) { 
          showToast("success", "Crawl Dimulai", `Run ID: ${r.run_id || "-"}`); 
          setCrawlStep("crawling", "Mencari komentar..."); 
          setTimeout(window.TabDashboard.loadDashboard, 3000); 
        } else { 
          showToast("warning", "Crawl Gagal", r.error); setCrawlError(); 
        }
      } catch (err) { 
        if (!window.MainState.abortRequested) {
          const msg = err.message === "crawl_already_running" ? "Sistem sedang bekerja di latar belakang. Harap tunggu sejenak." : err.message;
          showToast("error", "Error", msg); setCrawlError(); 
        }
      }
      finally { 
        btn.disabled = false; btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Crawl Saja'; 
        window.MainState.crawlRunning = false;
        updateRunButtonsState(); 
      }
    });

    $("btnRunInferenceOnly")?.addEventListener("click", async () => {
      const btn = $("btnRunInferenceOnly"); btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Analisis...';
      setRunMode("inference"); 
      window.MainState.crawlRunning = true;
      window.MainState.abortRequested = false;
      window.MainState.runStartTime = new Date();
      updateRunButtonsState();
      setCrawlStep("connecting", "Mengecek antrean..."); 
      startLogPolling();
      await new Promise(r => setTimeout(r, 1500));
      try {
        const videoParam = window.MainState.selectedVideoId ? `&video_id=${window.MainState.selectedVideoId}` : "";
        const r = await apiFetch(`/crawler/run?mode=inference_only${videoParam}`, { method: "POST" });
        if (window.MainState.abortRequested) {
          window.MainState.abortRequested = false;
          setCrawlStep("idle", "Analisis dihentikan oleh pengguna.");
          return;
        }
        if (r.success) { 
          showToast("success", "Analisis Dimulai", `Run ID: ${r.run_id || "-"}`); 
          setCrawlStep("analyzing", "Memproses komentar pending..."); 
          setTimeout(window.TabDashboard.loadDashboard, 1000); 
        }
      } catch (err) { 
        if (!window.MainState.abortRequested) {
          const msg = err.message === "crawl_already_running" ? "Sistem sedang bekerja di latar belakang. Harap tunggu sejenak." : err.message;
          showToast("error", "Error Analisis", msg); 
        }
      }
      finally { 
        btn.disabled = false; btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> Analisis Saja'; 
        window.MainState.crawlRunning = false;
        updateRunButtonsState(); 
      }
    });

    $("btnStopInference")?.addEventListener("click", async () => {
      const btn = $("btnStopInference"); 
      btn.disabled = true; 
      btn.innerHTML = '<div class="spinner"></div> Menghentikan...';
      
      window.MainState.abortRequested = true;
      window.MainState.crawlRunning = false;
      updateRunButtonsState();
      
      const btnSystem = $("btnRunSystem");
      if (btnSystem) {
        btnSystem.disabled = false;
        btnSystem.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Jalankan Sistem';
      }
      const btnCrawl = $("btnRunCrawlOnly");
      if (btnCrawl) {
        btnCrawl.disabled = false;
        btnCrawl.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Crawl Saja';
      }
      const btnInference = $("btnRunInferenceOnly");
      if (btnInference) {
        btnInference.disabled = false;
        btnInference.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> Analisis Saja';
      }
      
      setCrawlStep("idle", "Menghentikan analisis...");
      
      try {
        const r = await apiFetch("/crawler/stop_inference", { method: "POST" });
        if (r.success) {
          showToast("info", "Analisis Dihentikan", "Proses analisis LLM dihentikan.");
          setCrawlStep("idle", "Analisis berhasil dihentikan.");
        }
      } catch (err) {
        showToast("error", "Gagal", "Gagal menghentikan analisis: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16"/></svg> Hentikan Analisis';
      }
    });

    let isTogglingAutoMonitor = false;
    $("toggleAutoMonitor")?.addEventListener("click", async () => {
      if (isTogglingAutoMonitor) return;
      isTogglingAutoMonitor = true;
      window.MainState.autoMonitor = !window.MainState.autoMonitor; 
      const t = $("autoMonitorTrack"); if (t) t.classList.toggle("on", window.MainState.autoMonitor);
      try {
        if (window.MainState.autoMonitor) { 
          await apiFetch("/crawler/start", { method: "POST" }); 
          showToast("success", "Auto Monitoring ON", "Sistem akan crawl otomatis."); 
          if (window.TabDashboard) window.TabDashboard.startAutoRefresh(); 
        }
        else { 
          await apiFetch("/crawler/stop", { method: "POST" }); 
          showToast("info", "Auto Monitoring OFF", "Auto-crawl dihentikan."); 
          if (window.TabDashboard) window.TabDashboard.stopAutoRefresh(); 
        }
      } catch (err) { 
        showToast("error", "Error", err.message); 
        window.MainState.autoMonitor = !window.MainState.autoMonitor; 
        if (t) t.classList.toggle("on", window.MainState.autoMonitor);
      }
      finally { isTogglingAutoMonitor = false; }
    });
  }

  // Expose
  window.CrawlerFeed = {
    startLogPolling,
    stopLogPolling,
    pollCrawlerLogs,
    initCrawlerFeedEvents
  };

})();
