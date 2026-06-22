/** Project taxonomy generation, review, manual editing, and activation. */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, showToast, escapeHtml } = window.UI;
  let currentDraft = null;

  const parseLabels = value => {
    if (Array.isArray(value)) return value;
    if (!value) return [];
    try { return JSON.parse(value); } catch { return String(value).split(",").filter(Boolean).map(key => ({ key, name: key, description: "", examples: [] })); }
  };

  const displayDate = value => value ? new Date(value).toLocaleString("id-ID") : "-";

  function labelPills(labels) {
    return parseLabels(labels).map(label => `
      <span title="${escapeHtml(label.description || "")}" style="display:inline-block;background:var(--color-border);padding:4px 7px;border-radius:5px;margin:2px;font-size:11px;">
        ${escapeHtml(label.name || label.key)}
      </span>`).join("");
  }

  function renderActive(version) {
    const root = $("taxonomyActiveSection");
    if (!version) { root.style.display = "none"; root.innerHTML = ""; return; }
    root.style.display = "block";
    root.innerHTML = `
      <div style="border:1px solid var(--color-border);border-radius:8px;overflow:hidden;">
        <div style="display:flex;justify-content:space-between;gap:16px;padding:13px 16px;background:var(--color-bg);border-bottom:1px solid var(--color-border);">
          <div><strong>Taxonomy Aktif</strong><div class="help-text">${escapeHtml(version.version_id)} · ${displayDate(version.activated_at || version.created_at)}</div></div>
          <span style="align-self:center;color:var(--color-success);font-size:12px;font-weight:700;">AKTIF</span>
        </div>
        <div style="padding:16px;">
          <div class="form-group"><label>Konteks</label><p style="white-space:pre-wrap;margin:6px 0 16px;">${escapeHtml(version.prompt_context || "-")}</p></div>
          <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;">
            <div><strong style="font-size:12px;">Issue</strong><div>${labelPills(version.issue_labels)}</div></div>
            <div><strong style="font-size:12px;">Stance</strong><div>${labelPills(version.stance_labels)}</div></div>
            <div><strong style="font-size:12px;">Action</strong><div>${labelPills(version.action_labels)}</div></div>
          </div>
        </div>
      </div>`;
  }

  function labelRows(axis, labels) {
    return parseLabels(labels).map((label, index) => `
      <div class="taxonomy-label-row" data-axis="${axis}" data-index="${index}" style="display:grid;grid-template-columns:150px 170px minmax(220px,1fr) 170px 34px;gap:8px;align-items:start;margin-bottom:8px;">
        <input class="form-control label-key" value="${escapeHtml(label.key || "")}" placeholder="key_label">
        <input class="form-control label-name" value="${escapeHtml(label.name || "")}" placeholder="Nama label">
        <input class="form-control label-description" value="${escapeHtml(label.description || "")}" placeholder="Kapan label ini digunakan">
        <input class="form-control label-examples" value="${escapeHtml((label.examples || []).join("; "))}" placeholder="contoh 1; contoh 2">
        <button type="button" class="btn btn-ghost btn-remove-label" title="Hapus label" style="color:var(--color-danger);padding:8px;">×</button>
      </div>`).join("");
  }

  function axisEditor(axis, title, labels) {
    return `
      <section style="margin-top:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <div><strong>${title}</strong><span class="help-text" style="margin-left:8px;">key, nama, deskripsi, dan contoh</span></div>
          <button type="button" class="btn btn-secondary btn-sm btn-add-label" data-axis="${axis}">+ Tambah</button>
        </div>
        <div id="taxonomyRows-${axis}">${labelRows(axis, labels)}</div>
      </section>`;
  }

  function collectAxis(axis) {
    return Array.from(document.querySelectorAll(`.taxonomy-label-row[data-axis="${axis}"]`)).map(row => ({
      key: row.querySelector(".label-key").value.trim(),
      name: row.querySelector(".label-name").value.trim(),
      description: row.querySelector(".label-description").value.trim(),
      examples: row.querySelector(".label-examples").value.split(";").map(item => item.trim()).filter(Boolean),
    }));
  }

  function bindEditorRows() {
    document.querySelectorAll(".btn-remove-label").forEach(button => button.addEventListener("click", () => button.closest(".taxonomy-label-row").remove()));
    document.querySelectorAll(".btn-add-label").forEach(button => button.addEventListener("click", () => {
      const axis = button.dataset.axis;
      const holder = $(`taxonomyRows-${axis}`);
      const wrapper = document.createElement("div");
      wrapper.innerHTML = labelRows(axis, [{ key: "", name: "", description: "", examples: [] }]);
      holder.appendChild(wrapper.firstElementChild);
      bindEditorRows();
    }));
  }

  function diffSummary(previous, next) {
    if (!previous || previous.version_id === next.version_id) return "";
    const changes = [];
    [["issue_labels", "issue"], ["stance_labels", "stance"], ["action_labels", "action"]].forEach(([field, name]) => {
      const before = new Set(parseLabels(previous[field]).map(item => item.key));
      const after = new Set(parseLabels(next[field]).map(item => item.key));
      const added = [...after].filter(key => !before.has(key));
      const removed = [...before].filter(key => !after.has(key));
      if (added.length) changes.push(`${name} ditambah: ${added.join(", ")}`);
      if (removed.length) changes.push(`${name} dihapus: ${removed.join(", ")}`);
    });
    return changes.length ? `<div class="alert alert-info" style="margin-bottom:14px;"><strong>Perubahan draft terbaru</strong><br>${changes.map(escapeHtml).join("<br>")}</div>` : "";
  }

  function renderDraft(version, previousDraft) {
    document.getElementById("taxonomyDraftEditor")?.remove();
    currentDraft = version;
    if (!version) return;

    const root = document.createElement("div");
    root.id = "taxonomyDraftEditor";
    root.style = "border:1px solid var(--color-warning);border-radius:8px;margin-top:20px;padding:16px;overflow:auto;";
    root.innerHTML = `
      ${diffSummary(previousDraft, version)}
      <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;">
        <div><h3 style="margin:0 0 4px;font-size:16px;">Review Draft</h3><div class="help-text">${escapeHtml(version.version_id)} · belum memengaruhi analisis</div></div>
        <button class="btn btn-primary btn-sm" id="btnSaveDraftManual">Simpan edit</button>
      </div>
      <div class="form-group" style="margin-top:16px;"><label>Konteks project</label><textarea id="editDraftPrompt" class="form-control" rows="5">${escapeHtml(version.prompt_context || "")}</textarea></div>
      ${axisEditor("issues", "Issue", version.issue_labels)}
      ${axisEditor("stances", "Stance", version.stance_labels)}
      ${axisEditor("actions", "Action intent", version.action_labels)}
      <div style="display:grid;grid-template-columns:minmax(220px,1fr) auto;gap:8px;margin-top:20px;">
        <input id="regenerateInstructions" class="form-control" placeholder="Contoh: pisahkan harga pangan dan lapangan kerja">
        <button class="btn btn-secondary" id="btnRegenerateDraft">Generate ulang penuh</button>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;padding-top:16px;border-top:1px solid var(--color-border);">
        <button class="btn btn-primary" id="btnActivateNewOnly">Aktifkan untuk komentar baru</button>
        <button class="btn btn-secondary" id="btnActivateReprocess">Aktifkan & analisis ulang</button>
      </div>`;
    $("taxonomyGenerateSection").after(root);
    bindEditorRows();

    $("btnSaveDraftManual").addEventListener("click", saveDraft);
    $("btnRegenerateDraft").addEventListener("click", () => generateTaxonomy($("regenerateInstructions").value));
    $("btnActivateNewOnly").addEventListener("click", () => activateDraft(false));
    $("btnActivateReprocess").addEventListener("click", () => activateDraft(true));
  }

  async function saveDraft() {
    try {
      await apiFetch(`/projects/${window.MainState.selectedProjectId}/taxonomy/versions/${currentDraft.version_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          prompt_context: $("editDraftPrompt").value,
          issue_labels: collectAxis("issues"),
          stance_labels: collectAxis("stances"),
          action_labels: collectAxis("actions"),
        }),
      });
      showToast("success", "Draft disimpan", "Perubahan manual telah disimpan.");
      loadTaxonomy();
    } catch (error) { showToast("error", "Draft tidak valid", error.message); }
  }

  async function activateDraft(reprocess) {
    const message = reprocess
      ? "Aktifkan taxonomy dan antrekan ulang seluruh komentar yang belum dikoreksi manual?"
      : "Aktifkan taxonomy hanya untuk analisis berikutnya?";
    if (!confirm(message)) return;
    try {
      const result = await apiFetch(`/projects/${window.MainState.selectedProjectId}/taxonomy/versions/${currentDraft.version_id}/activate`, {
        method: "POST", body: JSON.stringify({ reprocess_all: reprocess }),
      });
      showToast("success", "Taxonomy aktif", reprocess ? `${result.comments_queued || 0} komentar masuk antrean ulang.` : "Komentar lama tidak diubah.");
      loadTaxonomy();
    } catch (error) { showToast("error", "Aktivasi gagal", error.message); }
  }

  async function generateTaxonomy(instructions = "") {
    const projectId = window.MainState?.selectedProjectId;
    if (!projectId) return;
    const button = $("btnGenerateTaxonomy");
    const oldHtml = button.innerHTML;
    button.disabled = true;
    button.textContent = "Menyusun draft...";
    try {
      const result = await apiFetch(`/projects/${projectId}/taxonomy/generate`, {
        method: "POST", body: JSON.stringify({ instructions }),
      });
      showToast("success", "Draft tersedia", result.cache_hit ? "Draft identik dimuat dari cache." : "Gemini membuat draft baru.");
      loadTaxonomy();
    } catch (error) { showToast("error", "Generate gagal", error.message); }
    finally { button.innerHTML = oldHtml; button.disabled = false; }
  }

  const manualTemplate = {
    prompt_context: "Kelompokkan komentar berdasarkan tujuan project. Gunakan konteks video dan isi komentar tanpa mengarang maksud yang tidak dinyatakan.",
    issue_labels: [
      { key: "topik_utama", name: "Topik Utama", description: "Pembahasan langsung mengenai topik utama video.", examples: [] },
      { key: "keluhan", name: "Keluhan", description: "Masalah atau pengalaman negatif yang disampaikan komentator.", examples: [] },
      { key: "saran", name: "Saran", description: "Usulan perbaikan atau kebutuhan yang disampaikan komentator.", examples: [] },
      { key: "pertanyaan", name: "Pertanyaan", description: "Permintaan informasi atau klarifikasi dari komentator.", examples: [] },
      { key: "lainnya", name: "Lainnya", description: "Topik lain yang tidak sesuai dengan issue khusus.", examples: [] },
    ],
    stance_labels: [
      { key: "mendukung", name: "Mendukung", description: "Komentator menunjukkan dukungan yang dapat dikenali.", examples: [] },
      { key: "menolak", name: "Menolak", description: "Komentator menunjukkan penolakan atau kritik yang dapat dikenali.", examples: [] },
      { key: "tidak_terdeteksi", name: "Tidak Terdeteksi", description: "Posisi komentator tidak dapat ditentukan.", examples: [] },
    ],
    action_labels: [
      { key: "keluhan", name: "Keluhan", description: "Komentator menyampaikan masalah yang dialami atau diamati.", examples: [] },
      { key: "saran", name: "Saran", description: "Komentator mengusulkan tindakan atau perbaikan.", examples: [] },
      { key: "ajakan_aksi", name: "Ajakan Aksi", description: "Komentator mengajak pihak lain melakukan tindakan tertentu.", examples: [] },
      { key: "tidak_terdeteksi", name: "Tidak Terdeteksi", description: "Niat tindakan tidak dapat ditentukan.", examples: [] },
    ],
  };

  async function createManualDraft() {
    const projectId = window.MainState?.selectedProjectId;
    if (!projectId) return;
    const button = $("btnCreateManualTaxonomy");
    button.disabled = true;
    try {
      await apiFetch(`/projects/${projectId}/taxonomy/versions`, {
        method: "POST", body: JSON.stringify(manualTemplate),
      });
      showToast("success", "Draft manual tersedia", "Label awal dapat langsung Anda ubah sebelum diaktifkan.");
      loadTaxonomy();
    } catch (error) { showToast("error", "Draft gagal dibuat", error.message); }
    finally { button.disabled = false; }
  }

  async function loadTaxonomy() {
    const projectId = window.MainState?.selectedProjectId;
    if (!projectId) {
      $("taxonomyEmptyState").style.display = "block";
      $("taxonomyContent").style.display = "none";
      return;
    }
    $("taxonomyEmptyState").style.display = "none";
    $("taxonomyContent").style.display = "block";
    try {
      const [projectResult, versionsResult] = await Promise.all([
        apiFetch(`/projects/${projectId}`),
        apiFetch(`/projects/${projectId}/taxonomy/versions`),
      ]);
      const count = projectResult.project.valid_sample_count || 0;
      const generateButton = $("btnGenerateTaxonomy");
      generateButton.disabled = count < 20;
      $("taxonomySampleInfo").textContent = count < 20
        ? `${count}/20 komentar valid. Jalankan crawl terlebih dahulu.`
        : `${count} komentar valid tersedia; maksimal 100 akan dijadikan sampel.`;

      const versions = versionsResult.versions || [];
      const active = versions.find(version => version.status === "active");
      const drafts = versions.filter(version => version.status === "draft");
      renderActive(active);
      renderDraft(drafts[0], drafts[1]);
    } catch (error) { showToast("error", "Gagal memuat taxonomy", error.message); }
  }

  function initEvents() {
    $("btnGenerateTaxonomy")?.addEventListener("click", () => generateTaxonomy());
    $("btnCreateManualTaxonomy")?.addEventListener("click", createManualDraft);
  }

  window.TabTaxonomy = { loadTaxonomy, initEvents };
})();
