/**
 * tab-projects.js — Logic for the Projects Tab/Modal
 */
(() => {
  "use strict";

  const { apiFetch } = window.API;
  const { $, $$, showToast, escapeHtml } = window.UI;

  async function loadProjects() {
    try {
      const data = await apiFetch("/projects");
      const globalSelect = $("globalProjectSelect");
      const videoSelect = $("inputVideoProject");
      const listContainer = $("projectListContainer");

      if (globalSelect) {
        const prevGlobalVal = globalSelect.value;
        globalSelect.innerHTML = '<option value="">Semua Project</option>';
        data.projects.forEach(p => {
          const opt = document.createElement("option");
          opt.value = p.project_id;
          opt.textContent = p.project_name;
          globalSelect.appendChild(opt);
        });
        if (prevGlobalVal && data.projects.some(p => p.project_id === prevGlobalVal)) {
          globalSelect.value = prevGlobalVal;
          if (window.MainState) window.MainState.selectedProjectId = prevGlobalVal;
        }
      }
      
      if (videoSelect) {
        videoSelect.innerHTML = '';
        data.projects.forEach(p => {
          const opt = document.createElement("option");
          opt.value = p.project_id;
          opt.textContent = p.project_name;
          videoSelect.appendChild(opt);
        });
      }

      if (listContainer) {
        listContainer.innerHTML = data.projects.map(p => `
          <div style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; font-size: 14px;">${escapeHtml(p.project_name)}</div>
              <div style="font-size: 12px; color: var(--text-muted);">${escapeHtml(p.project_id)}</div>
            </div>
            <button class="btn btn-ghost btn-sm btn-delete-project" data-id="${escapeHtml(p.project_id)}" style="color: var(--color-danger); padding: 4px;">Hapus</button>
          </div>
        `).join('');

        $$(".btn-delete-project").forEach(btn => {
          btn.addEventListener("click", async (e) => {
            if (confirm("Apakah Anda yakin ingin menghapus project ini?")) {
              try {
                const r = await apiFetch(`/projects/${e.target.dataset.id}`, { method: "DELETE" });
                if (r.success) { showToast("success", "Project Dihapus", "Project berhasil dihapus."); loadProjects(); }
              } catch(err) { showToast("error", "Gagal Menghapus", err.message); }
            }
          });
        });
      }
      return data;
    } catch (err) {
      console.error("Gagal memuat projects:", err);
      throw err;
    }
  }

  function initProjectsEvents() {
    $("btnManageProjects")?.addEventListener("click", () => {
      loadProjects();
      $("manageProjectsModal").classList.add("open");
    });
    
    $("btnCloseManageProjects")?.addEventListener("click", () => {
      $("manageProjectsModal").classList.remove("open");
    });
    $("manageProjectsModal")?.addEventListener("click", e => {
      if (e.target === $("manageProjectsModal")) $("manageProjectsModal").classList.remove("open");
    });

    $("btnSubmitAddProject")?.addEventListener("click", async () => {
      const pname = $("newProjectName").value.trim();
      const goalType = $("newProjectGoalType").value;
      
      if (!pname || !goalType) {
        showToast("warning", "Peringatan", "Nama Project dan Tujuan Utama wajib diisi."); return;
      }
      
      const payload = {
        project_name: pname,
        description: $("newProjectDesc").value.trim(),
        goal_type: goalType,
        goal_text: $("newProjectGoalText").value.trim()
      };
      
      const btn = $("btnSubmitAddProject");
      btn.disabled = true;
      try {
        const r = await apiFetch("/projects", { method: "POST", body: JSON.stringify(payload) });
        if (r.success) {
          showToast("success", "Sukses", "Project draf berhasil ditambahkan.");
          $("newProjectName").value = "";
          $("newProjectDesc").value = "";
          $("newProjectGoalType").value = "";
          $("newProjectGoalText").value = "";
          await loadProjects();
          if (window.MainState) window.MainState.selectedProjectId = r.project_id;
          if ($("globalProjectSelect")) $("globalProjectSelect").value = r.project_id;
          if ($("inputVideoProject")) $("inputVideoProject").value = r.project_id;
          $("manageProjectsModal").classList.remove("open");
          window.openAddVideoModal?.();
        }
      } catch(err) {
        showToast("error", "Gagal", err.message);
      } finally {
        btn.disabled = false;
      }
    });
  }

  // Expose
  window.TabProjects = {
    loadProjects,
    initProjectsEvents
  };

})();
