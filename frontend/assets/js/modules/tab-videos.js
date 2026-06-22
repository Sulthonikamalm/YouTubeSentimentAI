/**
 * tab-videos.js — Logic for the Videos Tab
 */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, showToast, escapeHtml, formatNumber } = window.UI;

  async function loadVideoList() {
    try {
      const projectParam = window.MainState && window.MainState.selectedProjectId ? `?project_id=${window.MainState.selectedProjectId}` : "";
      const res = await apiFetch(`/videos${projectParam}`);
      renderVideoCards(res.videos || []);
    } catch (err) {
      console.error("Gagal memuat daftar video:", err);
      showToast("error", "Error", "Gagal memuat daftar video.");
    }
  }

  function renderVideoCards(videos) {
    const container = $("videoGridContainer");
    const emptyState = $("videoEmptyState");

    if (!videos || videos.length === 0) {
      if (container) container.innerHTML = "";
      if (emptyState) emptyState.classList.remove("hidden");
      return;
    }

    if (emptyState) emptyState.classList.add("hidden");
    
    if (container) {
      container.innerHTML = videos.map(v => {
        const isActive = v.monitoring_enabled;
        const statusClass = isActive ? "active" : "inactive";
        const statusText = isActive ? "Aktif" : "Nonaktif";
        
        const thumbnailUrl = `https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg`;
        const title = v.video_title || "Unknown Video Title";
        const channel = v.channel_title || "Unknown Channel";
        
        return `
          <div class="video-card">
            <div class="video-thumbnail">
              <img src="${thumbnailUrl}" alt="Thumbnail" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'video-thumbnail-placeholder\\'>No Thumbnail</div>';">
              <div class="video-status-badge ${statusClass}">
                <div class="dot"></div>
                ${statusText}
              </div>
            </div>
            <div class="video-info">
              <div class="video-title" title="${escapeHtml(title)}">${escapeHtml(title)}</div>
              <div class="video-channel">${escapeHtml(channel)}</div>
              <div class="video-metrics">
                <div class="video-metric">
                  <span class="video-metric-label">Total Komentar</span>
                  <span class="video-metric-value">${formatNumber(v.total_comments_collected || 0)}</span>
                </div>
                <div class="video-metric" style="margin-left: auto; text-align: right;">
                  <span class="video-metric-label">Didaftarkan</span>
                  <span class="video-metric-value" style="font-size:12px;font-weight:600;color:var(--color-text-muted);">${v.created_at ? new Date(v.created_at).toLocaleDateString("id-ID") : "-"}</span>
                </div>
              </div>
            </div>
            <div class="video-actions" style="flex-wrap: wrap;">
              <button class="btn btn-secondary btn-sm" onclick="window.crawlSingleVideo('${v.video_id}')" title="Tarik komentar baru hanya untuk video ini">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                Crawl
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.analyzeSingleVideo('${v.video_id}')" title="Analisis sentimen hanya untuk video ini">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z"/></svg>
                Analisis
              </button>
              <button class="btn btn-primary btn-sm" onclick="window.viewVideoAnalytics('${v.video_id}')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                Dashboard
              </button>
              <button class="btn btn-ghost btn-sm" onclick="window.toggleVideoMonitoring('${v.video_id}')" title="${isActive ? 'Nonaktifkan monitoring' : 'Aktifkan monitoring'}" style="flex: 0 0 auto;">
                ${isActive ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>' : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><polygon points="5 3 19 12 5 21 5 3"/></svg>'}
              </button>
              <button class="btn btn-ghost btn-sm" onclick="window.deleteVideo('${v.video_id}')" style="color:var(--color-danger); flex: 0 0 auto;" title="Hapus Video">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        `;
      }).join("");
    }
  }

  window.openAddVideoModal = function() {
    $("inputVideoUrl").value = "";
    $("addVideoModal").classList.add("open");
  };

  window.closeAddVideoModal = function() {
    $("addVideoModal").classList.remove("open");
  };

  window.toggleVideoMonitoring = async function(videoId) {
    try {
      const res = await apiFetch(`/videos/${videoId}/toggle`, { method: "POST" });
      if (res.success) {
        loadVideoList(); 
      }
    } catch (err) {
      showToast("error", "Error", err.message);
    }
  };

  window.deleteVideo = async function(videoId) {
    if (!confirm("Apakah Anda yakin ingin menghapus video ini dari daftar pemantauan?")) return;
    try {
      const res = await apiFetch(`/videos/${videoId}`, { method: "DELETE" });
      if (res.success) {
        showToast("success", "Dihapus", "Video berhasil dihapus.");
        loadVideoList();
        if (window.MainState) {
          window.MainState.loadVideoFilter(); 
          if (window.MainState.selectedVideoId === videoId) {
            window.MainState.selectedVideoId = ""; 
            if ($("filterVideo")) $("filterVideo").value = "";
          }
        }
      }
    } catch (err) {
      showToast("error", "Error", err.message);
    }
  };

  window.viewVideoAnalytics = function(videoId) {
    if (window.MainState) {
      window.MainState.selectedVideoId = videoId;
      if ($("filterVideo")) $("filterVideo").value = videoId;
      window.MainState.switchView("dashboard");
    }
  };

  window.crawlSingleVideo = async function(videoId) {
    showToast("info", "Crawl Dimulai", `Menarik komentar untuk video ${videoId}...`);
    try {
      const r = await apiFetch(`/crawler/run?mode=crawl_only&video_id=${videoId}`, { method: "POST" });
      if (r.success) {
        showToast("success", "Crawl Berhasil", "Komentar baru berhasil ditarik.");
        loadVideoList();
      } else {
        showToast("warning", "Gagal", r.error || "Crawl gagal.");
      }
    } catch (err) {
      const msg = err.message === "crawl_already_running" ? "Sistem sedang bekerja di latar belakang. Harap tunggu sejenak." : err.message;
      showToast("error", "Error Crawl", msg);
    }
  };

  window.analyzeSingleVideo = async function(videoId) {
    showToast("info", "Analisis Dimulai", `Menganalisis komentar untuk video ${videoId}...`);
    try {
      const r = await apiFetch(`/crawler/run?mode=inference_only&video_id=${videoId}`, { method: "POST" });
      if (r.success) {
        showToast("success", "Analisis Selesai", "Komentar berhasil dianalisis.");
        loadVideoList();
      } else {
        showToast("warning", "Gagal", r.error || "Analisis gagal.");
      }
    } catch (err) {
      const msg = err.message === "crawl_already_running" ? "Sistem sedang bekerja di latar belakang. Harap tunggu sejenak." : err.message;
      showToast("error", "Error Analisis", msg);
    }
  };

  function initVideosEvents() {
    $("btnCancelAddVideo")?.addEventListener("click", window.closeAddVideoModal);
    $("addVideoModal")?.addEventListener("click", e => { if (e.target === $("addVideoModal")) window.closeAddVideoModal(); });
    $("btnSubmitAddVideo")?.addEventListener("click", async () => {
      const urlInput = $("inputVideoUrl");
      const projectInput = $("inputVideoProject");
      const btn = $("btnSubmitAddVideo");
      const val = urlInput?.value.trim();
      const projId = projectInput?.value;
      
      if (!val) { showToast("warning", "Peringatan", "URL tidak boleh kosong"); return; }
      if (!projId) { showToast("warning", "Peringatan", "Silakan pilih Project terlebih dahulu"); return; }
      
      btn.disabled = true; btn.textContent = "Memproses...";
      try {
        const res = await apiFetch("/videos", {
          method: "POST",
          body: JSON.stringify({ url: val, project_id: projId })
        });
        if (res.success) {
          showToast("success", "Video Ditambahkan", "Video berhasil ditambahkan ke daftar pantauan.");
          window.closeAddVideoModal();
          loadVideoList();
          if (window.MainState) window.MainState.loadVideoFilter(); 
        } else {
          showToast("error", "Gagal", res.error || "Gagal menambahkan video.");
        }
      } catch (err) {
        showToast("error", "Error", err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "Tambahkan";
      }
    });
  }

  // Expose
  window.TabVideos = {
    loadVideoList,
    initVideosEvents
  };

})();
