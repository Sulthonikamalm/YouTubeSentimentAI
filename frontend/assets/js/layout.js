/**
 * layout.js — Dynamic HTML layout injector for Pantausentimen dashboard.
 * Injects sidebar and modal templates into the DOM before dashboard.js initializes.
 */

(() => {
  "use strict";

  // 1. Inject Sidebar and Sidebar Overlay into #appShell
  const appShell = document.getElementById("appShell");
  if (appShell) {
    const sidebarHtml = `
      <div class="sidebar-overlay" id="sidebarOverlay"></div>
      <aside class="sidebar" id="sidebar">
        <!-- Brand -->
        <div class="sidebar-brand">
          <div class="sidebar-brand-logo-title">
            <div class="sidebar-brand-icon" title="Pantausentimen" style="background: transparent;">
              <img src="assets/logo.png" alt="Pantausentimen Logo" style="width: 100%; height: 100%; object-fit: contain; border-radius: 8px;">
            </div>
            <span class="sidebar-brand-text">Pantausentimen</span>
          </div>
          <!-- Collapse Toggle -->
          <button class="sidebar-collapse-btn" id="sidebarCollapseBtn" title="Perkecil sidebar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
        </div>

        <!-- Navigation -->
        <nav class="sidebar-nav">
          <div class="sidebar-section-label">Menu Utama</div>

          <a href="#" class="sidebar-link active" data-page="dashboard" title="Dashboard">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>
            <span>Dashboard</span>
          </a>

          <a href="#" class="sidebar-link" data-page="monitoring" title="Monitoring">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
            <span>Monitoring</span>
          </a>

          <a href="#" class="sidebar-link" data-page="komentar" title="Komentar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>
            <span>Komentar</span>
          </a>

          <a href="#" class="sidebar-link" data-page="video" title="Video">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            <span>Video</span>
          </a>

          <div class="sidebar-section-label">Sistem</div>

          <a href="#" class="sidebar-link" data-page="crawler" title="Crawler">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span>Crawler</span>
          </a>

          <a href="#" class="sidebar-link" data-page="taxonomy" title="Taxonomy AI">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
            <span>Taxonomy AI</span>
          </a>

          <a href="#" class="sidebar-link" data-page="ollama_status" title="Status Ollama">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
            <span>Status Ollama</span>
          </a>
        </nav>

        <!-- Footer -->
        <div class="sidebar-footer">
          <span class="sidebar-footer-version">Sistem v2.1.0</span>
          <span class="sidebar-footer-status">
            <span class="dot"></span>
            <span class="status-text">Online</span>
          </span>
          <span class="sidebar-footer-copy">&copy; 2025 Pantausentimen</span>
        </div>
      </aside>
    `;
    appShell.insertAdjacentHTML("afterbegin", sidebarHtml);
  }

  // 2. Inject Modal templates into the end of body
  const modalsHtml = `
    <!-- Correction Modal (Human-in-the-Loop) -->
    <div class="modal-overlay" id="correctionModal">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">Koreksi Analisis Komentar</h3>
          <button class="modal-close-btn" id="btnCancelCorrection">&times;</button>
        </div>
        <div class="modal-body">
          <div class="comment-preview-box">
            <p class="comment-preview-label">Komentar Asli:</p>
            <p class="comment-preview-text" id="correctionCommentText">...</p>
          </div>
          <form id="correctionForm" style="display:flex;flex-direction:column;gap:12px;">
            <input type="hidden" id="correctionCommentId">
            
            <div class="form-group">
              <label class="form-label" for="correctSentiment">Sentimen:</label>
              <select class="form-select" id="correctSentiment" required>
                <option value="positive">Positif</option>
                <option value="neutral">Netral</option>
                <option value="negative">Negatif</option>
              </select>
            </div>
            
            <div class="form-group">
              <label class="form-label" for="correctIssue">Isu Dominan:</label>
              <select class="form-select" id="correctIssue" required>
                <option value="ekonomi_rakyat">Ekonomi Rakyat</option>
                <option value="kepercayaan_publik">Kepercayaan Publik</option>
                <option value="pemerintahan_kebijakan">Pemerintahan & Kebijakan</option>
                <option value="hukum_korupsi">Hukum & Korupsi</option>
                <option value="elite_politik">Elite Politik</option>
                <option value="geopolitik_keamanan">Geopolitik & Keamanan</option>
                <option value="media_narasi">Media & Narasi</option>
                <option value="demokrasi_aksi_publik">Demokrasi & Aksi Publik</option>
                <option value="feedback_video">Feedback Video</option>
                <option value="lainnya">Lainnya</option>
              </select>
            </div>
            
            <div class="form-group">
              <label class="form-label" for="correctStance">Sikap (Stance):</label>
              <select class="form-select" id="correctStance" required>
                <option value="kritik_pemerintah">Kritik Pemerintah</option>
                <option value="dukung_pemerintah">Dukung Pemerintah</option>
                <option value="dukung_video">Dukung Video</option>
                <option value="kritik_video">Kritik Video</option>
                <option value="sinis_tidak_percaya">Sinis / Tidak Percaya</option>
                <option value="netral_informatif">Netral / Informatif</option>
                <option value="debat_antar_pengguna">Debat Antar Pengguna</option>
                <option value="tidak_terdeteksi">Tidak Terdeteksi</option>
              </select>
            </div>
            
            <div class="form-group">
              <label class="form-label" for="correctAction">Niat Tindakan (Action Intent):</label>
              <select class="form-select" id="correctAction" required>
                <option value="menuntut_akuntabilitas">Menuntut Akuntabilitas</option>
                <option value="dorongan_aksi_publik">Dorongan Aksi Publik</option>
                <option value="perubahan_elektoral">Perubahan Elektoral</option>
                <option value="menyebarkan_kesadaran">Menyebarkan Kesadaran</option>
                <option value="harapan_doa">Harapan & Doa</option>
                <option value="menunggu_mengamati">Menunggu & Mengamati</option>
                <option value="apatis_sinis">Apatis / Sinis</option>
                <option value="tidak_terdeteksi">Tidak Terdeteksi</option>
              </select>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="btnDismissCorrection">Batal</button>
          <button class="btn btn-primary" id="btnSaveCorrection">Simpan Koreksi</button>
        </div>
      </div>
    </div>

    <!-- Ollama Status Modal -->
    <div class="modal-overlay" id="settingsModal">
      <div class="modal-card" style="max-width: 500px;">
        <div class="modal-header">
          <h3 class="modal-title">Status Ollama (Sahabat-AI)</h3>
          <button class="modal-close-btn" id="btnCancelSettings">&times;</button>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 12px; color: var(--text-secondary); font-size: 14px;">
            Sistem menggunakan model Sahabat-AI 8B via Ollama lokal untuk analisis sentimen komentar YouTube.
          </p>
          
          <div id="ollamaStatusContainer" style="display:flex; flex-direction:column; gap:12px;">
            <span style="color:var(--text-muted); font-size:13px;">Memeriksa koneksi Ollama...</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="btnCancelSettingsSave">Tutup</button>
          <button class="btn btn-primary" id="btnRefreshOllamaStatus">Refresh Status</button>
        </div>
      </div>
    </div>

    <!-- Modal: Reset Confirmation -->
    <div class="modal-overlay" id="resetModal">
      <div class="modal-card" style="max-width: 400px;">
        <div class="modal-header">
          <h3 class="modal-title" style="color: var(--color-warning);">Reset Data Analisis</h3>
          <button class="modal-close-btn" onclick="document.getElementById('resetModal').classList.remove('open')">&times;</button>
        </div>
        <div class="modal-body">
          <p style="font-size: 14px; color: var(--color-text-secondary); margin: 0 0 10px 0;">
            Apakah Anda yakin ingin me-reset seluruh hasil analisis AI?
          </p>
          <p style="font-size: 13px; color: var(--color-text-muted); margin: 0;">
            Komentar <strong>tidak akan dihapus</strong>, tetapi statusnya akan dikembalikan ke 'pending' untuk dianalisis ulang.
          </p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="document.getElementById('resetModal').classList.remove('open')">Batal</button>
          <button class="btn btn-primary" id="btnConfirmReset" style="background: var(--color-warning); border-color: var(--color-warning);">Ya, Reset Data</button>
        </div>
      </div>
    </div>

    <!-- Modal: Delete Confirmation -->
    <div class="modal-overlay" id="deleteModal">
      <div class="modal-card" style="max-width: 420px;">
        <div class="modal-header">
          <h3 class="modal-title" style="color: var(--color-danger);">Hapus Semua Data</h3>
          <button class="modal-close-btn" onclick="document.getElementById('deleteModal').classList.remove('open')">&times;</button>
        </div>
        <div class="modal-body">
          <p style="font-size: 14px; color: var(--color-text-secondary); margin: 0 0 16px 0;">
            <strong>PERINGATAN:</strong> Tindakan ini akan menghapus <strong>SELURUH</strong> data komentar dari database secara permanen.
          </p>
          <div class="form-group">
            <label class="form-label" for="deleteConfirmInput">Ketik "HAPUS" untuk melanjutkan:</label>
            <input type="text" id="deleteConfirmInput" class="form-select" placeholder="HAPUS" autocomplete="off" style="border: 1px solid var(--color-danger); color: var(--color-danger); font-weight: bold; text-align: center;">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="document.getElementById('deleteModal').classList.remove('open')">Batal</button>
          <button class="btn btn-primary" id="btnConfirmDelete" style="background: var(--color-danger); border-color: var(--color-danger);" disabled>Hapus Permanen</button>
        </div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML("beforeend", modalsHtml);
})();
