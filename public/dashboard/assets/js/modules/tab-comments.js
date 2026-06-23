/**
 * tab-comments.js — Logic for the Comments Tab
 */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, $$, formatNumber, formatTimeAgo, capitalize, showToast, escapeHtml, sentimentChipClass, formatDateTime } = window.UI;
  const { SENTIMENT_LABELS } = window.Charts;

  let commentsPageState = {
    search: "",
    videoId: "",
    sentiment: "",
    issueLabel: "",
    stanceLabel: "",
    type: "",
    limit: 50,
    offset: 0,
    total: 0,
  };

  async function loadCommentsPage() {
    const tableBody = $("commentsPageTableBody");
    const pageInfo = $("commentsPageInfo");
    if (!tableBody) return;

    tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:40px;"><div class="spinner dark" style="margin:0 auto;"></div><div style="margin-top:10px;font-size:13px;color:var(--color-text-muted);">Memuat komentar...</div></td></tr>`;

    const params = new URLSearchParams();
    if (commentsPageState.search) params.append("search", commentsPageState.search);
    if (commentsPageState.videoId) params.append("video_id", commentsPageState.videoId);
    if (commentsPageState.sentiment) params.append("sentiment", commentsPageState.sentiment);
    if (commentsPageState.issueLabel) params.append("issue_label", commentsPageState.issueLabel);
    if (commentsPageState.stanceLabel) params.append("stance_label", commentsPageState.stanceLabel);
    if (commentsPageState.type) params.append("type", commentsPageState.type);
    if (window.MainState && window.MainState.selectedProjectId) params.append("project_id", window.MainState.selectedProjectId);
    params.append("limit", commentsPageState.limit);
    params.append("offset", commentsPageState.offset);

    try {
      const res = await apiFetch(`/comments?${params.toString()}`);
      commentsPageState.total = res.total;

      const videoSelect = $("commentsFilterVideo");
      const mainVideoSelect = $("filterVideo");
      if (videoSelect && mainVideoSelect && videoSelect.options.length <= 1) {
        videoSelect.innerHTML = mainVideoSelect.innerHTML;
        videoSelect.value = commentsPageState.videoId;
      }

      if (!res.comments || res.comments.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:40px;"><div class="empty-state"><div class="empty-state-title">Tidak ada komentar ditemukan</div><div class="empty-state-desc">Coba sesuaikan kata kunci atau filter pencarian Anda.</div></div></td></tr>`;
        if (pageInfo) pageInfo.textContent = "Menampilkan 0-0 dari 0 komentar";
        togglePageButtons();
        return;
      }

      if (window.MainState) {
        window.MainState.representativeComments = res.comments;
      }

      tableBody.innerHTML = res.comments.map(c => {
        const sentClass = sentimentChipClass(c.sentiment);
        const confPct = c.sentiment_confidence ? `${(c.sentiment_confidence * 100).toFixed(0)}%` : "";
        
        let typeBadge = "";
        if (c.is_baseline) {
          typeBadge = `<span class="chip" style="background:#E2E8F0;color:#475569;margin-left:4px;font-size:10px;padding:1px 6px;">Baseline</span>`;
        } else {
          typeBadge = `<span class="chip" style="background:var(--color-primary-soft);color:var(--color-primary);margin-left:4px;font-size:10px;padding:1px 6px;">Baru</span>`;
        }

        return `
          <tr>
            <td>
              <div style="font-weight:600;color:var(--color-text);">${escapeHtml(c.author_name || "Anonim")}</div>
              <div class="comment-meta" style="margin-top:2px;">${formatDateTime(c.published_at)}</div>
              <div style="margin-top:4px;display:flex;align-items:center;">
                ${typeBadge}
                ${c.like_count ? `<span style="font-size:11px;color:var(--color-text-muted);margin-left:8px;display:inline-flex;align-items:center;gap:3px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px;"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg> ${c.like_count}</span>` : ""}
              </div>
            </td>
            <td>
              <div style="max-width:320px; white-space:pre-wrap; font-size:13px; color:var(--color-text-secondary); line-height:1.5; max-height:120px; overflow-y:auto;">${escapeHtml(c.comment_text || "")}</div>
            </td>
            <td>
              <span class="chip ${sentClass}">${SENTIMENT_LABELS[c.sentiment] || capitalize(c.sentiment || "-")}</span>
              ${confPct && c.sentiment ? `<div class="comment-meta" style="margin-top:4px;">Conf: ${confPct}</div>` : ""}
            </td>
            <td>
              <div style="display:flex; flex-direction:column; gap:4px; align-items:flex-start;">
                <span class="chip blue">${capitalize(c.issue_label || "-")}</span>
                ${c.stance_label && c.stance_label !== "tidak_terdeteksi" ? `<span class="chip" style="background:#F3E8FF;color:var(--color-purple);font-size:11px;">${capitalize(c.stance_label)}</span>` : ""}
                ${c.action_intent_label && c.action_intent_label !== "tidak_terdeteksi" ? `<span class="chip" style="background:#ECFEFF;color:var(--color-cyan);font-size:11px;">${capitalize(c.action_intent_label)}</span>` : ""}
              </div>
            </td>
            <td style="font-size:12px;color:var(--color-text-secondary);max-width:240px;line-height:1.4;">
              ${escapeHtml(c.interpretation_short || "-")}
            </td>
            <td>
              <button class="btn btn-secondary btn-sm btn-page-correct" data-id="${c.comment_id}" style="padding: 4px 8px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px; border-radius: 6px;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Koreksi
              </button>
            </td>
          </tr>`;
      }).join("");

      const start = commentsPageState.offset + 1;
      const end = Math.min(commentsPageState.offset + res.comments.length, res.total);
      if (pageInfo) pageInfo.textContent = `Menampilkan ${start}-${end} dari ${formatNumber(res.total)} komentar`;

      togglePageButtons();

      tableBody.querySelectorAll(".btn-page-correct").forEach(btn => {
        btn.addEventListener("click", () => {
          if (typeof window.openCorrectionModal === "function") window.openCorrectionModal(btn.dataset.id);
        });
      });

    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:40px;"><div class="error-state"><div class="error-state-title">Gagal memuat data komentar</div><div class="error-state-desc">${escapeHtml(err.message)}</div></div></td></tr>`;
    }
  }

  function togglePageButtons() {
    const prevBtn = $("btnPrevCommentsPage");
    const nextBtn = $("btnNextCommentsPage");
    if (prevBtn) prevBtn.disabled = commentsPageState.offset <= 0;
    if (nextBtn) nextBtn.disabled = commentsPageState.offset + commentsPageState.limit >= commentsPageState.total;
  }

  function initCommentsPageFilters() {
    const searchInput = $("commentsSearchInput");
    const videoSelect = $("commentsFilterVideo");
    const sentimentSelect = $("commentsFilterSentiment");
    const issueSelect = $("commentsFilterIssue");
    const stanceSelect = $("commentsFilterStance");
    const typeSelect = $("commentsFilterType");
    const limitSelect = $("commentsPageLimit");
    const resetBtn = $("btnResetCommentsFilters");
    const prevBtn = $("btnPrevCommentsPage");
    const nextBtn = $("btnNextCommentsPage");

    let searchTimeout = null;

    const triggerReload = () => {
      commentsPageState.offset = 0;
      loadCommentsPage();
    };

    searchInput?.addEventListener("input", e => {
      clearTimeout(searchTimeout);
      commentsPageState.search = e.target.value;
      searchTimeout = setTimeout(triggerReload, 400);
    });

    videoSelect?.addEventListener("change", e => {
      commentsPageState.videoId = e.target.value;
      triggerReload();
    });

    sentimentSelect?.addEventListener("change", e => {
      commentsPageState.sentiment = e.target.value;
      triggerReload();
    });

    issueSelect?.addEventListener("change", e => {
      commentsPageState.issueLabel = e.target.value;
      triggerReload();
    });

    stanceSelect?.addEventListener("change", e => {
      commentsPageState.stanceLabel = e.target.value;
      triggerReload();
    });

    typeSelect?.addEventListener("change", e => {
      commentsPageState.type = e.target.value;
      triggerReload();
    });

    limitSelect?.addEventListener("change", e => {
      commentsPageState.limit = parseInt(e.target.value, 10) || 50;
      triggerReload();
    });

    resetBtn?.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      if (videoSelect) videoSelect.value = "";
      if (sentimentSelect) sentimentSelect.value = "";
      if (issueSelect) issueSelect.value = "";
      if (stanceSelect) stanceSelect.value = "";
      if (typeSelect) typeSelect.value = "";
      
      commentsPageState = {
        search: "",
        videoId: "",
        sentiment: "",
        issueLabel: "",
        stanceLabel: "",
        type: "",
        limit: limitSelect ? (parseInt(limitSelect.value, 10) || 50) : 50,
        offset: 0,
        total: 0,
      };
      loadCommentsPage();
      showToast("info", "Filter Direset", "Pencarian komentar telah dikembalikan ke awal.");
    });

    prevBtn?.addEventListener("click", () => {
      if (commentsPageState.offset > 0) {
        commentsPageState.offset = Math.max(0, commentsPageState.offset - commentsPageState.limit);
        loadCommentsPage();
      }
    });

    nextBtn?.addEventListener("click", () => {
      if (commentsPageState.offset + commentsPageState.limit < commentsPageState.total) {
        commentsPageState.offset += commentsPageState.limit;
        loadCommentsPage();
      }
    });
  }

  window.openCorrectionModal = function(id) {
    if (!window.MainState || !window.MainState.representativeComments) return;
    const c = window.MainState.representativeComments.find(c => c.comment_id === id); 
    if (!c) return;
    $("correctionCommentId").value = id;
    $("correctionCommentText").textContent = c.comment_text;
    $("correctSentiment").value = c.sentiment || "neutral";
    $("correctIssue").value = c.issue_label || "lainnya";
    $("correctStance").value = c.stance_label || "tidak_terdeteksi";
    $("correctAction").value = c.action_intent_label || "tidak_terdeteksi";
    $("correctionModal").classList.add("open");
  };

  window.closeCorrectionModal = function() { 
    $("correctionModal").classList.remove("open"); 
  };

  window.saveCorrection = async function() {
    const id = $("correctionCommentId").value;
    const btn = $("btnSaveCorrection"); btn.disabled = true; btn.textContent = "Menyimpan...";
    try {
      const res = await apiFetch("/comments/correct", { method: "POST", body: JSON.stringify({
        comment_id: id, sentiment: $("correctSentiment").value, issue_label: $("correctIssue").value,
        stance_label: $("correctStance").value, action_intent_label: $("correctAction").value,
      })});
      if (res.success) {
        showToast("success", "Koreksi Berhasil", "Hasil analisis komentar berhasil diperbarui.");
        window.closeCorrectionModal();
        if (!$("viewComments").classList.contains("hidden")) {
          loadCommentsPage();
        } else if (window.loadDashboard) {
          window.loadDashboard();
        }
      }
      else showToast("error", "Gagal", res.error || "Gagal menyimpan koreksi.");
    } catch (err) { showToast("error", "Error", err.message); }
    finally { btn.disabled = false; btn.textContent = "Simpan Koreksi"; }
  };

  // Expose
  window.TabComments = {
    loadCommentsPage,
    initCommentsPageFilters
  };

})();
