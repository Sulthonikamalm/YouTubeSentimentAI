/**
 * render.js — Rendering functions for Pantausentimen dashboard.
 * KPI cards, insight panel, comments table, crawler activity, status strip.
 * Depends on: api.js, ui.js, charts.js.
 */

(() => {
  "use strict";

  const { formatNumber, formatDateTime, formatTimeAgo, capitalize,
          sentimentChipClass, escapeHtml, $ } = window.UI;
  const { SENTIMENT_LABELS, DIST_BAR_COLORS,
          renderTimelineChart, renderSentimentChart,
          renderDistBars, renderWordCloud } = window.Charts;

  // =========================================================================
  // KPI Cards
  // =========================================================================

  function renderKPICards(summary) {
    const grid = $("kpiGrid");
    if (!grid) return;

    const cards = [
      { label: "Total Komentar", value: formatNumber(summary.total_comments), helper: `${formatNumber(summary.new_comments_24h)} baru (24h)`, icon: "comment", color: "blue", delta: summary.new_comments_24h > 0 ? `+${summary.new_comments_24h}` : null, deltaDir: summary.new_comments_24h > 0 ? "up" : null },
      { label: "Video Dipantau", value: formatNumber(summary.videos_monitored), helper: `${summary.active_videos || 0} aktif`, icon: "play", color: "purple" },
      { label: "Komentar Baru (24h)", value: formatNumber(summary.new_comments_24h), helper: "Dari semua video", icon: "trending", color: "green", delta: summary.new_comments_24h > 0 ? "Baru" : null, deltaDir: summary.new_comments_24h > 0 ? "up" : null },
      { label: "Inference Selesai", value: formatNumber(summary.inference_completed), helper: `dari ${formatNumber(summary.inference_total)} total`, icon: "brain", color: "cyan" },
      { label: "Kuota API Terpakai", value: formatNumber(summary.api_units_used), helper: "Total unit digunakan", icon: "key", color: "amber" },
      { label: "Last Crawl", value: summary.last_run ? formatTimeAgo(summary.last_run.started_at) : "-", helper: summary.last_run ? `${summary.last_run.status} • ${summary.last_run.new_comments || 0} baru` : "Belum pernah", icon: "clock", color: "red" },
    ];

    const iconSVGs = {
      comment: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
      play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
      trending: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
      brain: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z"/></svg>',
      key: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
      clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    };

    grid.innerHTML = cards.map((c) => `
      <div class="kpi-card">
        <div class="kpi-card-header">
          <div class="kpi-card-icon ${c.color}">${iconSVGs[c.icon] || ""}</div>
          ${c.delta ? `<span class="kpi-card-delta ${c.deltaDir || ""}">${c.delta}</span>` : ""}
        </div>
        <div class="kpi-card-label">${c.label}</div>
        <div class="kpi-card-value">${c.value}</div>
        <div class="kpi-card-helper">${c.helper}</div>
      </div>`).join("");
  }

  // =========================================================================
  // Insight Panel
  // =========================================================================

  function renderInsightPanel(data) {
    const panel = $("insightPanel");
    if (!panel) return;

    if (!data.has_data) {
      panel.innerHTML = `
        <div class="empty-state" style="padding:40px;">
          <div class="empty-state-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></div>
          <div class="empty-state-title">${data.message || "Belum ada data insight"}</div>
          <div class="empty-state-desc">Insight otomatis akan muncul setelah cukup komentar dianalisis.</div>
        </div>`;
      return;
    }

    const ds = data.dominant_sentiment || {};
    const warningsHtml = (data.warnings || []).map(w => `<div class="insight-block warning"><div class="insight-block-label">⚠ Peringatan</div><div class="insight-block-value">${w}</div></div>`).join("");
    const recsHtml = (data.recommendations || []).map(r => `<div class="insight-block recommendation"><div class="insight-block-label">💡 Rekomendasi</div><div class="insight-block-value">${r}</div></div>`).join("");

    panel.innerHTML = `
      <div class="insight-panel-header">
        <div class="insight-panel-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          Rangkuman Insight
        </div>
        <span class="chip blue">${formatNumber(data.total_analyzed)} dianalisis</span>
      </div>
      <div class="insight-grid">
        <div class="insight-block">
          <div class="insight-block-label">Sentimen Dominan</div>
          <div class="insight-block-value">
            <span class="chip ${sentimentChipClass(ds.label)}">${SENTIMENT_LABELS[ds.label] || capitalize(ds.label || "-")}</span>
            <span style="margin-left:8px;">${ds.percentage || 0}%</span>
          </div>
          <div class="insight-block-detail">${ds.count || 0} dari ${data.total_analyzed || 0} komentar</div>
        </div>
        <div class="insight-block"><div class="insight-block-label">Isu Dominan</div><div class="insight-block-value">${capitalize(data.dominant_issue || "-")}</div><div class="insight-block-detail">Isu paling banyak dibahas di komentar</div></div>
        <div class="insight-block"><div class="insight-block-label">Stance Dominan</div><div class="insight-block-value">${capitalize(data.dominant_stance || "-")}</div><div class="insight-block-detail">Sikap publik yang paling umum</div></div>
        <div class="insight-block"><div class="insight-block-label">Action Intent Dominan</div><div class="insight-block-value">${capitalize(data.dominant_action || "-")}</div><div class="insight-block-detail">Kecenderungan tindakan komentator</div></div>
        ${warningsHtml}${recsHtml}
      </div>
      <div class="insight-disclaimer">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        ${data.disclaimer || "Interpretasi hanya berlaku untuk komentar video yang dipantau."}
      </div>`;
  }

  // =========================================================================
  // Comments Table
  // =========================================================================

  function renderCommentsTable(comments, representativeComments) {
    const tbody = $("commentTableBody");
    if (!tbody) return;

    if (!comments || comments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:40px;"><div class="empty-state"><div class="empty-state-title">Belum ada komentar representatif</div></div></td></tr>`;
      return;
    }

    // Store for correction modal access
    representativeComments.length = 0;
    representativeComments.push(...comments);

    tbody.innerHTML = comments.map(c => {
      const sentClass = sentimentChipClass(c.sentiment);
      const confPct = c.sentiment_confidence ? `${(c.sentiment_confidence * 100).toFixed(0)}%` : "";
      return `
        <tr>
          <td><div class="comment-text-cell">${escapeHtml(c.comment_text || "")}</div><div class="comment-meta">${c.author_name || "Anonim"} • ${formatDateTime(c.published_at)}</div></td>
          <td><span class="chip ${sentClass}">${SENTIMENT_LABELS[c.sentiment] || capitalize(c.sentiment || "-")}</span>${confPct ? `<div class="comment-meta" style="margin-top:4px;">Confidence: ${confPct}</div>` : ""}</td>
          <td><span class="chip blue">${capitalize(c.issue_label || "-")}</span></td>
          <td style="font-size:12px;color:var(--color-text-secondary);max-width:200px;">${escapeHtml(c.interpretation_short || "-")}</td>
          <td>
            <button class="btn btn-ghost btn-sm btn-correct" data-id="${c.comment_id}" style="padding: 4px 8px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              Koreksi
            </button>
          </td>
        </tr>`;
    }).join("");

    tbody.querySelectorAll(".btn-correct").forEach(btn => {
      btn.addEventListener("click", () => {
        if (typeof window.openCorrectionModal === "function") window.openCorrectionModal(btn.dataset.id);
      });
    });
  }

  // =========================================================================
  // Crawler Activity
  // =========================================================================

  function renderCrawlerActivity(data) {
    const wrap = $("crawlerActivityWrap");
    if (!wrap) return;

    const stats = data.stats_24h || {};
    const runs = data.recent_runs || [];

    const statsHtml = `
      <div class="crawler-stats">
        <div class="crawler-stat"><div class="crawler-stat-value">${stats.total_runs || 0}</div><div class="crawler-stat-label">Total Runs</div></div>
        <div class="crawler-stat"><div class="crawler-stat-value">${formatNumber(stats.total_new || 0)}</div><div class="crawler-stat-label">Komentar Baru</div></div>
        <div class="crawler-stat"><div class="crawler-stat-value">${formatNumber(stats.total_units || 0)}</div><div class="crawler-stat-label">API Units</div></div>
      </div>`;

    let runsHtml = "";
    if (runs.length === 0) {
      runsHtml = `<div class="empty-state" style="padding:20px;"><div class="empty-state-title">Belum ada crawl run tercatat</div></div>`;
    } else {
      runsHtml = `<div class="run-list">${runs.slice(0, 5).map(r => {
        const statusClass = (r.status === "completed" || r.status === "success") ? "success" : r.status === "running" ? "running" : "failed";
        return `<div class="run-item">
          <div class="run-item-status ${statusClass}"></div>
          <div class="run-item-time">${formatDateTime(r.started_at)}</div>
          <div class="run-item-detail">${r.trigger_type || "auto"} • ${r.new_comments || 0} baru / ${r.comments_fetched || 0} fetched${r.error_message ? `<br><span class="text-danger" style="font-size:11px;">${escapeHtml(r.error_message)}</span>` : ""}</div>
          <div class="run-item-units">${r.api_units_used || 0} units</div>
        </div>`;
      }).join("")}</div>`;
    }

    wrap.innerHTML = statsHtml + runsHtml;
  }

  // =========================================================================
  // Status Strip
  // =========================================================================

  function updateStatusStrip(crawlerData, summary) {
    const crawlerEl = $("statusCrawler");
    const inferenceEl = $("statusInference");
    const modelEl = $("statusModel");
    const quotaEl = $("statusQuota");
    const updatedEl = $("statusUpdated");

    if (crawlerEl && crawlerData) {
      const isRunning = crawlerData.is_running;
      crawlerEl.innerHTML = `<span class="status-dot ${isRunning ? "green" : "gray"}"></span> ${isRunning ? "Berjalan" : "Idle"}`;
    }

    if (inferenceEl && summary) {
      const completed = summary.inference_completed || 0;
      const total = summary.inference_total || 0;
      const pct = total > 0 ? ((completed / total) * 100).toFixed(0) : 0;
      inferenceEl.innerHTML = `<span class="status-dot ${completed > 0 ? "green" : "gray"}"></span> ${pct}% (${completed}/${total})`;
    }

    if (modelEl) modelEl.innerHTML = `<span class="status-dot green"></span> Sahabat-AI`;
    if (quotaEl && summary) quotaEl.textContent = formatNumber(summary.api_units_used || 0) + " unit";
    if (updatedEl) updatedEl.textContent = `Terakhir disinkronkan: ${new Date().toLocaleTimeString("id-ID")}`;
  }

  // Expose globally
  window.Render = {
    renderKPICards, renderInsightPanel, renderCommentsTable,
    renderCrawlerActivity, updateStatusStrip,
  };
})();
