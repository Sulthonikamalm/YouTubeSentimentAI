/**
 * tab-taxonomy.js — Logic for Taxonomy AI view
 */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, $$, showToast, escapeHtml } = window.UI;

  async function loadTaxonomy() {
    const pid = window.MainState?.selectedProjectId;
    if (!pid) {
      $("taxonomyEmptyState").style.display = "block";
      $("taxonomyContent").style.display = "none";
      return;
    }
    
    $("taxonomyEmptyState").style.display = "none";
    $("taxonomyContent").style.display = "block";
    
    // Load Project details for sample count
    try {
      const pRes = await apiFetch(`/projects/${pid}`);
      const sampleCount = pRes.project.valid_sample_count || 0;
      
      const infoEl = $("taxonomySampleInfo");
      if (sampleCount < 20) {
        infoEl.innerHTML = `<span style="color:var(--color-warning);">⚠️ Project ini baru memiliki ${sampleCount} komentar valid. Dibutuhkan minimal 20 komentar untuk membuat taxonomy otomatis.</span>`;
        $("btnGenerateTaxonomy").disabled = true;
      } else {
        infoEl.innerHTML = `<span style="color:var(--color-success);">✓ Project memiliki ${sampleCount} komentar valid (cukup untuk ditarik sampel).</span>`;
        $("btnGenerateTaxonomy").disabled = false;
      }
      
      // Load Versions
      const vRes = await apiFetch(`/projects/${pid}/taxonomy/versions`);
      const versions = vRes.versions || [];
      
      const activeVersion = versions.find(v => v.status === "active");
      const draftVersion = versions.find(v => v.status === "draft");
      
      if (activeVersion) {
        $("taxonomyActiveSection").style.display = "block";
        renderActiveTaxonomy(activeVersion);
      } else {
        $("taxonomyActiveSection").style.display = "none";
      }
      
      if (draftVersion) {
        // Show draft edit form
        renderDraftTaxonomy(draftVersion);
      } else {
        // Hide draft form if no draft
        const oldDraft = $("taxonomyDraftEditor");
        if (oldDraft) oldDraft.remove();
      }
      
    } catch (err) {
      showToast("error", "Error Memuat Taxonomy", err.message);
    }
  }

  function formatLabels(jsonStr) {
    if (!jsonStr) return "";
    try {
      const arr = JSON.parse(jsonStr);
      return arr.map(l => `<span style="display:inline-block;background:var(--color-border);padding:2px 6px;border-radius:4px;margin:2px;" title="${escapeHtml(l.description || '')}">${escapeHtml(l.name || l.key)}</span>`).join("");
    } catch(e) {
      return jsonStr.split(",").map(l => `<span style="display:inline-block;background:var(--color-border);padding:2px 6px;border-radius:4px;margin:2px;">${escapeHtml(l)}</span>`).join("");
    }
  }

  function renderActiveTaxonomy(v) {
    const container = $("taxonomyActiveSection");
    container.innerHTML = `
      <div style="border:1px solid var(--color-border); border-radius:8px; overflow:hidden;">
        <div style="background:var(--color-bg); padding:12px 16px; border-bottom:1px solid var(--color-border); display:flex; justify-content:space-between; align-items:center;">
          <div>
            <h4 style="margin:0; font-size:14px;">Taxonomy Aktif</h4>
            <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">Versi: ${v.version_id} • Dibuat: ${new Date(v.created_at).toLocaleString()}</div>
          </div>
          <span style="background:var(--color-success); color:#fff; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:600;">ACTIVE</span>
        </div>
        <div style="padding:16px;">
          <div style="margin-bottom:12px;">
            <div style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Prompt Context</div>
            <div style="background:var(--color-bg); padding:10px; border-radius:6px; font-family:monospace; font-size:12px; white-space:pre-wrap;">${escapeHtml(v.prompt_context || "-")}</div>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
            <div>
              <div style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Issues</div>
              <div style="background:var(--color-bg); padding:10px; border-radius:6px; font-size:12px;">${formatLabels(v.issue_labels)}</div>
            </div>
            <div>
              <div style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Stances</div>
              <div style="background:var(--color-bg); padding:10px; border-radius:6px; font-size:12px;">${formatLabels(v.stance_labels)}</div>
            </div>
            <div>
              <div style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Actions</div>
              <div style="background:var(--color-bg); padding:10px; border-radius:6px; font-size:12px;">${formatLabels(v.action_labels)}</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function renderDraftTaxonomy(v) {
    try {
      if (v.issue_labels && !v.issue_labels.startsWith("[")) {
        v.issue_labels = JSON.stringify(v.issue_labels.split(",").map(k => ({key: k, name: k, description: ""})));
      }
      if (v.stance_labels && !v.stance_labels.startsWith("[")) {
        v.stance_labels = JSON.stringify(v.stance_labels.split(",").map(k => ({key: k, name: k, description: ""})));
      }
      if (v.action_labels && !v.action_labels.startsWith("[")) {
        v.action_labels = JSON.stringify(v.action_labels.split(",").map(k => ({key: k, name: k, description: ""})));
      }
      // Pretty print JSON for textarea
      v.issue_labels = JSON.stringify(JSON.parse(v.issue_labels), null, 2);
      v.stance_labels = JSON.stringify(JSON.parse(v.stance_labels), null, 2);
      v.action_labels = JSON.stringify(JSON.parse(v.action_labels), null, 2);
    } catch(e) {}

    let oldDraft = $("taxonomyDraftEditor");
    if (oldDraft) oldDraft.remove();
    
    const container = document.createElement("div");
    container.id = "taxonomyDraftEditor";
    container.style = "border:1px solid var(--color-warning); border-radius:8px; overflow:hidden; margin-top:20px;";
    
    container.innerHTML = `
      <div style="background:#fffbeb; padding:12px 16px; border-bottom:1px solid var(--color-warning); display:flex; justify-content:space-between; align-items:center;">
        <div>
          <h4 style="margin:0; font-size:14px; color:#b45309;">Draft Review (Belum Aktif)</h4>
          <div style="font-size:12px; color:#b45309; margin-top:4px;">Versi: ${v.version_id}</div>
        </div>
        <button class="btn btn-sm" id="btnActivateDraft" style="background:var(--color-warning); color:#fff; border:none;">Aktifkan Draft Ini</button>
      </div>
      <div style="padding:16px;">
        <div class="form-group" style="margin-bottom:12px;">
          <label style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Prompt Context & Definitions</label>
          <textarea id="editDraftPrompt" class="form-control" rows="8" style="font-family:monospace; font-size:12px;">${escapeHtml(v.prompt_context || "")}</textarea>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:16px;">
          <div class="form-group">
            <label style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Issues (JSON)</label>
            <textarea id="editDraftIssues" class="form-control" rows="6" style="font-family:monospace; font-size:11px;">${escapeHtml(v.issue_labels || "")}</textarea>
          </div>
          <div class="form-group">
            <label style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Stances (JSON)</label>
            <textarea id="editDraftStances" class="form-control" rows="6" style="font-family:monospace; font-size:11px;">${escapeHtml(v.stance_labels || "")}</textarea>
          </div>
          <div class="form-group">
            <label style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px;">Actions (JSON)</label>
            <textarea id="editDraftActions" class="form-control" rows="6" style="font-family:monospace; font-size:11px;">${escapeHtml(v.action_labels || "")}</textarea>
          </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; gap:8px;">
            <input type="text" id="regenerateInstructions" class="form-control" style="width:300px; font-size:13px;" placeholder="Instruksi perbaikan ke AI (opsional)">
            <button class="btn btn-secondary btn-sm" id="btnRegenerateDraft">Regenerate</button>
          </div>
          <button class="btn btn-primary btn-sm" id="btnSaveDraftManual">Simpan Editan</button>
        </div>
      </div>
    `;
    
    $("taxonomyGenerateSection").after(container);
    
    // Bind events
    $("btnSaveDraftManual").addEventListener("click", async () => {
      try {
        await apiFetch(`/projects/${window.MainState.selectedProjectId}/taxonomy/versions/${v.version_id}`, {
          method: "PATCH",
          body: JSON.stringify({
            prompt_context: $("editDraftPrompt").value,
            issue_labels: $("editDraftIssues").value,
            stance_labels: $("editDraftStances").value,
            action_labels: $("editDraftActions").value
          })
        });
        showToast("success", "Disimpan", "Draft berhasil diperbarui.");
        loadTaxonomy();
      } catch (err) {
        showToast("error", "Gagal", err.message);
      }
    });
    
    $("btnActivateDraft").addEventListener("click", async () => {
      if (confirm("Aktifkan taxonomy ini? Komentar yang sudah dianalisis sebelumnya mungkin akan di-reset untuk dianalisis ulang dengan taxonomy baru.")) {
        try {
          await apiFetch(`/projects/${window.MainState.selectedProjectId}/taxonomy/versions/${v.version_id}/activate`, {
            method: "POST",
            body: JSON.stringify({ reprocess_all: true })
          });
          showToast("success", "Diaktifkan", "Taxonomy baru sekarang aktif.");
          loadTaxonomy();
        } catch (err) {
          showToast("error", "Gagal", err.message);
        }
      }
    });
    
    $("btnRegenerateDraft").addEventListener("click", () => {
      generateTaxonomy($("regenerateInstructions").value);
    });
  }

  async function generateTaxonomy(instructions = "") {
    const pid = window.MainState?.selectedProjectId;
    if (!pid) return;
    
    const btn = $("btnGenerateTaxonomy");
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner" style="width:14px;height:14px;border-width:2px;"></span> Memproses...`;
    btn.disabled = true;
    
    try {
      const r = await apiFetch(`/projects/${pid}/taxonomy/generate`, {
        method: "POST",
        body: JSON.stringify({ instructions })
      });
      if (r.success) {
        showToast("success", "Selesai", r.cache_hit ? "Memuat draft dari cache." : "Draft berhasil digenerate.");
        loadTaxonomy();
      }
    } catch (err) {
      showToast("error", "Gagal", err.message);
    } finally {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  }

  function initEvents() {
    $("btnGenerateTaxonomy")?.addEventListener("click", () => generateTaxonomy());
  }

  window.TabTaxonomy = {
    loadTaxonomy,
    initEvents
  };

})();
