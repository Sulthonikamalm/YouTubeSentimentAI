/**
 * main.js — Entry point for the Dashboard.
 * Manages global state and global event listeners.
 */
(() => {
  "use strict";

  const { $, $$, showToast, escapeHtml } = window.UI;
  const { apiFetch } = window.API;

  window.MainState = {
    autoMonitor: false, 
    sidebarCollapsed: false, 
    crawlStep: "idle", 
    currentRunMode: "both",
    crawlRunning: false, 
    selectedDays: 30, 
    selectedVideoId: "", 
    selectedProjectId: "",
    selectedType: "all", 
    representativeComments: [],
    abortRequested: false,
    
    // Core routing method
    switchView: function(pageId) {
      $$(".view-content").forEach(el => el.classList.add("hidden"));

      if (window.TabDashboard) window.TabDashboard.stopRealtimePolling();

      $$(".sidebar-link").forEach(link => {
        if (link.dataset.page === pageId) {
          link.classList.add("active");
        } else {
          link.classList.remove("active");
        }
      });

      let targetView = null;
      let title = "Dashboard";
      if (pageId === "dashboard") {
        targetView = $("viewDashboard");
        title = "Dashboard";
        if (window.TabDashboard) window.TabDashboard.loadDashboard();
      } else if (pageId === "komentar") {
        targetView = $("viewComments");
        title = "Komentar Publik";
        if (window.TabComments) window.TabComments.loadCommentsPage();
      } else if (pageId === "monitoring") {
        targetView = $("viewMonitoring");
        title = "Monitoring Real-time";
        if (window.TabDashboard) window.TabDashboard.startRealtimePolling();
      } else if (pageId === "video") {
        targetView = $("viewVideo");
        title = "Manajemen Video Pantauan";
        if (window.TabVideos) window.TabVideos.loadVideoList();
      } else if (pageId === "crawler") {
        targetView = $("viewCrawler");
        title = "Konfigurasi Crawler";
        if (window.TabCrawler) window.TabCrawler.loadConfig();
      } else if (pageId === "taxonomy") {
        targetView = $("viewTaxonomy");
        title = "Konfigurasi Taxonomy AI";
        if (window.TabTaxonomy) window.TabTaxonomy.loadTaxonomy();
      }

      if (targetView) targetView.classList.remove("hidden");
      const topbarTitle = document.querySelector(".topbar-title");
      if (topbarTitle) topbarTitle.textContent = title;
    },

    loadVideoFilter: async function() {
      try {
        const projectParam = this.selectedProjectId ? `?project_id=${this.selectedProjectId}` : "";
        const data = await apiFetch(`/videos${projectParam}`);
        const select = $("filterVideo"); if (!select || !data.videos) return;
        select.innerHTML = '<option value="">Semua Video</option>';
        data.videos.forEach(v => { const o = document.createElement("option"); o.value = v.video_id; o.textContent = v.video_title || v.video_id; select.appendChild(o); });
      } catch { /* non-critical */ }
    }
  };

  async function openSettingsModal() {
    $("settingsModal").classList.add("open");
    $("ollamaStatusContainer").innerHTML = '<span style="color:var(--text-muted); font-size:13px;">Memeriksa koneksi Ollama...</span>';
    try {
      const data = await apiFetch("/settings/ollama-status");
      const serverColor = data.server_online ? "var(--color-success)" : "var(--color-danger)";
      const serverLabel = data.server_online ? "Online" : "Offline";
      const modelColor = data.model_loaded ? "var(--color-success)" : "var(--color-warning)";
      const modelLabel = data.model_loaded ? "Tersedia" : "Belum Dimuat";
      $("ollamaStatusContainer").innerHTML = `
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; background:var(--color-bg); padding:10px 14px; border-radius:8px; border:1px solid var(--color-border);">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="width:8px;height:8px;border-radius:50%;background:${serverColor};display:inline-block;"></span>
              <span style="font-size:13px; font-weight:600;">Server Ollama</span>
            </div>
            <span style="background:${serverColor}; color:white; font-size:11px; padding:2px 10px; border-radius:4px; font-weight:600;">${serverLabel}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; background:var(--color-bg); padding:10px 14px; border-radius:8px; border:1px solid var(--color-border);">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="width:8px;height:8px;border-radius:50%;background:${modelColor};display:inline-block;"></span>
              <span style="font-size:13px; font-weight:600;">Model AI</span>
            </div>
            <span style="background:${modelColor}; color:white; font-size:11px; padding:2px 10px; border-radius:4px; font-weight:600;">${modelLabel}</span>
          </div>
          <div style="background:var(--color-bg); padding:10px 14px; border-radius:8px; border:1px solid var(--color-border);">
            <div style="font-size:12px; color:var(--text-muted); margin-bottom:4px;">Model Name</div>
            <div style="font-family:monospace; font-size:13px;">${escapeHtml(data.model_name || "-")}</div>
          </div>
          <div style="background:var(--color-bg); padding:10px 14px; border-radius:8px; border:1px solid var(--color-border);">
            <div style="font-size:12px; color:var(--text-muted); margin-bottom:4px;">Base URL</div>
            <div style="font-family:monospace; font-size:13px;">${escapeHtml(data.base_url || "-")}</div>
          </div>
          ${data.error ? `<div style="background:var(--color-danger-light, #fef2f2); padding:10px 14px; border-radius:8px; border:1px solid var(--color-danger); color:var(--color-danger); font-size:13px;">⚠ ${escapeHtml(data.error)}</div>` : ""}
        </div>
      `;
    } catch (err) {
      $("ollamaStatusContainer").innerHTML = `<span style="color:var(--color-danger); font-size:13px;">Gagal memeriksa status Ollama: ${escapeHtml(err.message)}</span>`;
    }
  }

  function closeSettingsModal() { 
    $("settingsModal").classList.remove("open"); 
    $$(".sidebar-link").forEach(l => { if (l.dataset.page === "ollama_status") l.classList.remove("active"); }); 
  }

  function initSidebarCollapse() {
    const btn = $("sidebarCollapseBtn"), shell = $("appShell"), resize = () => setTimeout(() => { window.Charts.chartRefs.timeline?.resize(); window.Charts.chartRefs.sentiment?.resize(); }, 350);
    if (!btn || !shell) return;
    if (localStorage.getItem("sidebar_collapsed") === "true") { shell.classList.add("sidebar-collapsed"); window.MainState.sidebarCollapsed = true; }
    btn.addEventListener("click", e => { e.stopPropagation(); window.MainState.sidebarCollapsed = true; shell.classList.add("sidebar-collapsed"); localStorage.setItem("sidebar_collapsed", "true"); resize(); });
    $("sidebar")?.addEventListener("click", () => {
      if (shell.classList.contains("sidebar-collapsed")) { window.MainState.sidebarCollapsed = false; shell.classList.remove("sidebar-collapsed"); localStorage.setItem("sidebar_collapsed", "false"); resize(); }
    });
  }

  function initGlobalEventHandlers() {
    // Sidebar nav
    $$(".sidebar-link").forEach(link => link.addEventListener("click", e => {
      e.preventDefault();
      const p = link.dataset.page;
      if (p === "ollama_status") {
        openSettingsModal();
      } else {
        window.MainState.switchView(p);
      }
    }));

    // Mobile menu
    $("mobileMenuBtn")?.addEventListener("click", () => {
      const shell = $("appShell");
      if (shell && shell.classList.contains("sidebar-collapsed")) {
        window.MainState.sidebarCollapsed = false;
        shell.classList.remove("sidebar-collapsed");
        localStorage.setItem("sidebar_collapsed", "false");
      }
      $("sidebar")?.classList.toggle("open");
      $("sidebarOverlay")?.classList.toggle("open");
    });
    $("sidebarOverlay")?.addEventListener("click", () => { $("sidebar")?.classList.remove("open"); $("sidebarOverlay")?.classList.remove("open"); });

    // Dropdown
    const btnMore = $("btnMoreOptions"), dropdown = $("moreDropdown");
    if (btnMore && dropdown) {
      btnMore.addEventListener("click", e => { e.stopPropagation(); dropdown.classList.toggle("show"); });
      document.addEventListener("click", e => { if (!dropdown.contains(e.target) && e.target !== btnMore) dropdown.classList.remove("show"); });
    }

    $("btnMenuRefresh")?.addEventListener("click", e => { e.preventDefault(); dropdown?.classList.remove("show"); showToast("info", "Memuat ulang...", "Dashboard sedang diperbarui."); if (window.TabDashboard) window.TabDashboard.loadDashboard(); });
    $("btnMenuResetData")?.addEventListener("click", e => { e.preventDefault(); dropdown?.classList.remove("show"); $("resetModal")?.classList.add("open"); });

    $("btnConfirmReset")?.addEventListener("click", async () => {
      const btn = $("btnConfirmReset");
      btn.disabled = true;
      btn.textContent = "Memproses...";
      try {
        const r = await apiFetch("/comments/reset", { method: "POST" });
        if (r.success) {
          showToast("success", "Reset Berhasil", r.message);
          $("resetModal")?.classList.remove("open");
          if (window.TabDashboard) window.TabDashboard.loadDashboard();
        }
      } catch (err) {
        showToast("error", "Gagal Reset", err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "Ya, Reset Data";
      }
    });

    const delInput = $("deleteConfirmInput"), btnDel = $("btnConfirmDelete");
    $("btnMenuHapusData")?.addEventListener("click", e => { e.preventDefault(); dropdown?.classList.remove("show"); if (delInput) delInput.value = ""; if (btnDel) btnDel.disabled = true; $("deleteModal")?.classList.add("open"); });
    delInput?.addEventListener("input", e => { if (btnDel) btnDel.disabled = e.target.value !== "HAPUS"; });
    btnDel?.addEventListener("click", async () => {
      btnDel.disabled = true;
      btnDel.textContent = "Menghapus...";
      try {
        const r = await apiFetch("/comments/delete_all", { method: "POST" });
        if (r.success) {
          showToast("success", "Data Dihapus", r.message);
          $("deleteModal")?.classList.remove("open");
          if (window.TabDashboard) window.TabDashboard.loadDashboard();
        }
      } catch (err) {
        showToast("error", "Gagal Menghapus", err.message);
      } finally {
        btnDel.disabled = false;
        btnDel.textContent = "Hapus Permanen";
        if (delInput) delInput.value = "";
      }
    });

    $("globalProjectSelect")?.addEventListener("change", (e) => {
      window.MainState.selectedProjectId = e.target.value;
      window.MainState.selectedVideoId = ""; 
      const videoFilter = $("filterVideo");
      if (videoFilter) videoFilter.value = "";
      window.MainState.loadVideoFilter();
      if (window.TabDashboard) window.TabDashboard.loadDashboard();
      if ($("viewComments") && !$("viewComments").classList.contains("hidden")) {
        if (window.TabComments) window.TabComments.loadCommentsPage();
      }
      if ($("viewTaxonomy") && !$("viewTaxonomy").classList.contains("hidden")) {
        if (window.TabTaxonomy) window.TabTaxonomy.loadTaxonomy();
      }
    });

    // Time/type Filters
    $("filterTimeRange")?.addEventListener("click", e => {
      const btn = e.target.closest("button"); if (!btn) return;
      $$("#filterTimeRange button").forEach(b => b.classList.remove("active")); btn.classList.add("active");
      window.MainState.selectedDays = Number.isNaN(parseInt(btn.dataset.days, 10)) ? 30 : parseInt(btn.dataset.days, 10);
      const videoParam = window.MainState.selectedVideoId ? `&video_id=${window.MainState.selectedVideoId}` : "";
      const typeParam = window.MainState.selectedType !== "all" ? `&type=${window.MainState.selectedType}` : "";
      const projectParam = window.MainState.selectedProjectId ? `&project_id=${window.MainState.selectedProjectId}` : "";
      apiFetch(`/dashboard/timeline?days=${window.MainState.selectedDays}${videoParam}${typeParam}${projectParam}`).then(window.Charts.renderTimelineChart).catch(() => {});
    });
    
    $("filterType")?.addEventListener("click", e => { 
      const btn = e.target.closest("button"); if (!btn) return; 
      $$("#filterType button").forEach(b => b.classList.remove("active")); btn.classList.add("active"); 
      window.MainState.selectedType = btn.dataset.type || "all"; 
      if (window.TabDashboard) window.TabDashboard.loadDashboard(); 
    });
    
    $("filterVideo")?.addEventListener("change", e => { 
      window.MainState.selectedVideoId = e.target.value; 
      if (window.TabDashboard) window.TabDashboard.loadDashboard(); 
    });
    
    $("linkAllComments")?.addEventListener("click", e => { e.preventDefault(); window.MainState.switchView("komentar"); });

    // Modals
    ["btnCancelCorrection", "btnDismissCorrection"].forEach(id => $(id)?.addEventListener("click", window.closeCorrectionModal));
    $("btnSaveCorrection")?.addEventListener("click", window.saveCorrection);
    $("correctionModal")?.addEventListener("click", e => { if (e.target === $("correctionModal")) window.closeCorrectionModal(); });
    ["btnCancelSettings", "btnCancelSettingsSave"].forEach(id => $(id)?.addEventListener("click", closeSettingsModal));
    $("btnRefreshOllamaStatus")?.addEventListener("click", openSettingsModal);
    $("settingsModal")?.addEventListener("click", e => { if (e.target === $("settingsModal")) closeSettingsModal(); });

  }

  function init() {
    if (window.TabProjects) {
      window.TabProjects.loadProjects().then(() => {
        initSidebarCollapse();
        initGlobalEventHandlers();
        
        if (window.TabProjects.initProjectsEvents) window.TabProjects.initProjectsEvents();
        if (window.TabVideos && window.TabVideos.initVideosEvents) window.TabVideos.initVideosEvents();
        if (window.TabComments && window.TabComments.initCommentsPageFilters) window.TabComments.initCommentsPageFilters();
        if (window.CrawlerFeed && window.CrawlerFeed.initCrawlerFeedEvents) window.CrawlerFeed.initCrawlerFeedEvents();
        if (window.TabTaxonomy && window.TabTaxonomy.initEvents) window.TabTaxonomy.initEvents();
        
        window.MainState.loadVideoFilter(); 
        if (window.TabDashboard) {
          window.TabDashboard.loadDashboard(); 
          window.TabDashboard.startAutoRefresh(); 
        }
        if (window.CrawlerFeed) window.CrawlerFeed.pollCrawlerLogs();
      });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

})();
