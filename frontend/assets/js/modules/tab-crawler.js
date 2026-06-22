/**
 * tab-crawler.js — Modul untuk halaman konfigurasi crawler.
 */
(() => {
  "use strict";

  const { $, showToast } = window.UI;
  const { apiFetch } = window.API;

  window.TabCrawler = {
    loadConfig: async function() {
      const wrap = $("crawlerConfigFormWrap");
      const loading = $("crawlerConfigLoading");
      
      if (wrap) wrap.style.display = "none";
      if (loading) loading.style.display = "flex";

      try {
        const data = await apiFetch("/crawler/config");
        if (data && !data.error) {
          if ($("inputYoutubeApiKey")) $("inputYoutubeApiKey").value = data.youtube_api_key || "";
          if ($("inputCrawlerInterval")) $("inputCrawlerInterval").value = data.interval_minutes || 10;
          if ($("inputCrawlerMaxComments")) $("inputCrawlerMaxComments").value = data.max_comments || 100;
        }
      } catch (err) {
        showToast("error", "Gagal Memuat", err.message);
      } finally {
        if (loading) loading.style.display = "none";
        if (wrap) wrap.style.display = "block";
      }
    },
    
    saveConfig: async function() {
      const btn = $("btnSaveCrawlerConfig");
      if (!btn) return;

      const apiKey = $("inputYoutubeApiKey").value;
      const interval = $("inputCrawlerInterval").value;
      const maxComments = $("inputCrawlerMaxComments").value;

      btn.disabled = true;
      btn.innerHTML = `<span class="pulse-indicator white" style="display:inline-block;margin-right:6px;width:12px;height:12px;"></span> Menyimpan...`;

      try {
        const payload = {
          interval_minutes: interval,
          max_comments: maxComments
        };
        // Hanya kirim API key jika diubah (tidak mengandung ...)
        if (apiKey && !apiKey.includes("...")) {
          payload.youtube_api_key = apiKey;
        }

        const data = await apiFetch("/crawler/config", {
          method: "POST",
          body: payload
        });

        if (data && data.success) {
          showToast("success", "Tersimpan", "Konfigurasi crawler berhasil diperbarui.");
          this.loadConfig(); // Reload to get masked key if updated
        }
      } catch (err) {
        showToast("error", "Gagal Menyimpan", err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          Simpan Konfigurasi
        `;
      }
    },

    initEvents: function() {
      const btnSave = $("btnSaveCrawlerConfig");
      if (btnSave) {
        btnSave.addEventListener("click", () => this.saveConfig());
      }

      const btnToggle = $("btnToggleApiKey");
      const inputApi = $("inputYoutubeApiKey");
      if (btnToggle && inputApi) {
        btnToggle.addEventListener("click", () => {
          if (inputApi.type === "password") {
            inputApi.type = "text";
            btnToggle.innerHTML = `
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            `;
          } else {
            inputApi.type = "password";
            btnToggle.innerHTML = `
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            `;
          }
        });
      }
    }
  };

  document.addEventListener("DOMContentLoaded", () => {
    if (window.TabCrawler && window.TabCrawler.initEvents) {
      window.TabCrawler.initEvents();
    }
  });

})();
