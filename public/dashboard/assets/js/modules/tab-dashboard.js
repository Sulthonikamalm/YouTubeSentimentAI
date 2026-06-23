/**
 * tab-dashboard.js — Logic for Dashboard Main Tab & Realtime
 */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, formatNumber, showToast, showKPISkeleton } = window.UI;
  const { DIST_BAR_COLORS, renderTimelineChart, renderSentimentChart,
          renderDistBars, renderWordCloud } = window.Charts;
  const { renderKPICards, renderInsightPanel, renderCommentsTable,
          renderCrawlerActivity, updateStatusStrip } = window.Render;

  const REFRESH_INTERVAL_MS = 30000;
  const REALTIME_POLL_INTERVAL_MS = 15000;
  let refreshTimer = null;
  let realtimeTimer = null;
  let activeLoadId = 0;

  async function loadDashboard() {
    const loadId = ++activeLoadId;
    showKPISkeleton();
    const videoParam = window.MainState.selectedVideoId ? `&video_id=${window.MainState.selectedVideoId}` : "";
    const typeParam = window.MainState.selectedType !== "all" ? `&type=${window.MainState.selectedType}` : "";
    const projectParam = window.MainState.selectedProjectId ? `&project_id=${window.MainState.selectedProjectId}` : "";
    const filterQuery = `?video_id=${window.MainState.selectedVideoId || ""}&type=${window.MainState.selectedType === "all" ? "" : window.MainState.selectedType}${projectParam}`;

    try {
      const [summary, distributions, timeline, repComments, interpretation, crawlerStatus] =
        await Promise.allSettled([
          apiFetch(`/dashboard/summary${filterQuery}`),
          apiFetch(`/dashboard/distributions${filterQuery}`),
          apiFetch(`/dashboard/timeline?days=${Number.isFinite(window.MainState.selectedDays) ? window.MainState.selectedDays : 30}${videoParam}${typeParam}${projectParam}`),
          apiFetch(`/dashboard/representative-comments?limit=8${videoParam}${typeParam}${projectParam}`),
          apiFetch(`/dashboard/interpretation${filterQuery}`),
          apiFetch("/crawler/status"),
        ]);

      if (loadId !== activeLoadId) return; // Ignore stale request

      if (summary.status === "fulfilled") renderKPICards(summary.value);
      else $("kpiGrid").innerHTML = `<div class="error-state"><div class="error-state-title">Gagal memuat KPI</div></div>`;

      if (timeline.status === "fulfilled") renderTimelineChart(timeline.value);
      if (distributions.status === "fulfilled") {
        renderSentimentChart(distributions.value);
        renderDistBars("issueChartWrap", distributions.value.issue, DIST_BAR_COLORS);
        renderDistBars("stanceChartWrap", distributions.value.stance, DIST_BAR_COLORS);
        renderDistBars("actionIntentChartWrap", distributions.value.action_intent, DIST_BAR_COLORS);
        renderWordCloud(distributions.value);
      }
      if (interpretation.status === "fulfilled") renderInsightPanel(interpretation.value);
      if (repComments.status === "fulfilled") {
        window.MainState.representativeComments = repComments.value.comments;
        renderCommentsTable(repComments.value.comments, window.MainState.representativeComments);
      }
      
      if (crawlerStatus.status === "fulfilled") {
        renderCrawlerActivity(crawlerStatus.value);
        
        const isRunning = crawlerStatus.value.is_running;
        if (isRunning && !window.MainState.crawlRunning) {
          window.MainState.crawlRunning = true;
          const activeRun = (crawlerStatus.value.recent_runs || []).find(r => r.status === "running" || r.status === "pending");
          if (activeRun && activeRun.started_at) {
            window.MainState.runStartTime = new Date(activeRun.started_at);
          } else {
            window.MainState.runStartTime = new Date();
          }
          window.Stepper.updateRunButtonsState(window.MainState);
          window.Stepper.setCrawlStep("connecting", "Menghubungkan...", window.MainState);
          if (window.CrawlerFeed) window.CrawlerFeed.startLogPolling();
        } else if (!isRunning && window.MainState.crawlRunning) {
          window.MainState.crawlRunning = false;
          window.Stepper.updateRunButtonsState(window.MainState);

          const lastRun = (crawlerStatus.value.recent_runs || [])[0];
          const lastStatus = lastRun ? lastRun.status : "unknown";
          if (lastStatus === "completed") {
            window.Stepper.setCrawlStep("done", "Baru saja selesai", window.MainState);
          } else if (lastStatus === "quota_exceeded") {
            window.Stepper.setCrawlStep("done", "Berhenti: kuota API habis", window.MainState);
            showToast("warning", "Kuota API", "Crawl berhenti karena batas kuota harian tercapai.");
          } else if (lastStatus === "failed") {
            window.Stepper.setCrawlStep("error", lastRun?.error_message || "Crawl gagal", window.MainState);
            showToast("error", "Crawl Error", lastRun?.error_message || "Proses crawl mengalami kegagalan.");
          } else {
            window.Stepper.setCrawlStep("done", `Selesai (status: ${lastStatus})`, window.MainState);
          }
          if (window.CrawlerFeed) window.CrawlerFeed.stopLogPolling();
          setTimeout(() => { if (!window.MainState.crawlRunning) window.Stepper.setCrawlStep("idle", "", window.MainState); }, 10000);
        }
        
        updateStatusStrip(crawlerStatus.value, summary.status === "fulfilled" ? summary.value : null);
      }
    } catch (err) {
      if (loadId !== activeLoadId) return;
      showToast("error", "Error", "Gagal memuat data dashboard: " + err.message);
    }
  }

  async function loadRealtimeMetrics() {
    try {
      const projectParam = window.MainState.selectedProjectId ? `&project_id=${window.MainState.selectedProjectId}` : "";
      const data = await apiFetch(`/dashboard/realtime?minutes=30${projectParam}`);
      window.Charts.updateRealtimeChart(data);

      const s = data.summary || {};
      const ingestedNow = $("rtIngestedNow");
      const inferredNow = $("rtInferredNow");
      const avgRate = $("rtAvgRate");
      if (ingestedNow) ingestedNow.textContent = formatNumber(s.ingested_this_minute || 0);
      if (inferredNow) inferredNow.textContent = formatNumber(s.inferred_this_minute || 0);
      if (avgRate) avgRate.textContent = s.avg_inference_rate ?? 0;

      const active = (s.ingested_this_minute || 0) > 0 || (s.inferred_this_minute || 0) > 0;
      const dot = $("rtStatusDot");
      const txt = $("rtStatusText");
      if (dot) dot.className = `pulse-indicator ${active ? "green" : "gray"}`;
      if (txt) txt.textContent = active ? "Aktif" : "Idle";
      const updated = $("rtUpdatedAt");
      if (updated) updated.textContent = `Diperbarui ${new Date().toLocaleTimeString("id-ID")}`;
    } catch (err) {
      const dot = $("rtStatusDot");
      const txt = $("rtStatusText");
      if (dot) dot.className = "pulse-indicator gray";
      if (txt) txt.textContent = "Gagal memuat";
    }
  }

  function startRealtimePolling() {
    if (realtimeTimer) return;
    window.Charts.initRealtimeChart();
    loadRealtimeMetrics();
    realtimeTimer = setInterval(loadRealtimeMetrics, REALTIME_POLL_INTERVAL_MS);
  }

  function stopRealtimePolling() {
    if (realtimeTimer) { clearInterval(realtimeTimer); realtimeTimer = null; }
  }

  function startAutoRefresh() { stopAutoRefresh(); refreshTimer = setInterval(loadDashboard, REFRESH_INTERVAL_MS); }
  function stopAutoRefresh() { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; } }

  // Expose
  window.TabDashboard = {
    loadDashboard,
    startRealtimePolling,
    stopRealtimePolling,
    startAutoRefresh,
    stopAutoRefresh
  };

})();
