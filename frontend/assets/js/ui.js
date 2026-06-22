/**
 * ui.js — UI utilities for Pantausentimen dashboard.
 * Toast notifications, DOM helpers, formatters. Loaded before dashboard.js.
 */

(() => {
  "use strict";

  const TOAST_DURATION_MS = 4000;

  // DOM helpers
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  // Formatters
  function formatNumber(n) {
    if (n == null) return "-";
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
    return n.toLocaleString("id-ID");
  }

  function formatDateTime(iso) {
    if (!iso) return "-";
    try {
      const d = new Date(iso);
      return d.toLocaleString("id-ID", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit",
      });
    } catch { return iso; }
  }

  function formatTimeAgo(iso) {
    if (!iso) return "-";
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return `${diff} detik lalu`;
    if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
    return `${Math.floor(diff / 86400)} hari lalu`;
  }

  function capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
  }

  function sentimentChipClass(s) {
    if (!s) return "neutral";
    const lower = s.toLowerCase();
    if (lower.includes("positif") || lower === "positive") return "positive";
    if (lower.includes("negatif") || lower === "negative") return "negative";
    return "neutral";
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Toast notification system
  function showToast(type, title, message) {
    const container = $("toastContainer");
    if (!container) return;

    const iconPaths = {
      success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
      info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    };

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-icon">${iconPaths[type] || iconPaths.info}</div>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-message">${message}</div>` : ""}
      </div>
      <button class="toast-close" aria-label="Tutup">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;

    toast.querySelector(".toast-close").addEventListener("click", () => removeToast(toast));
    container.appendChild(toast);
    setTimeout(() => removeToast(toast), TOAST_DURATION_MS);
  }

  function removeToast(el) {
    if (!el || el.classList.contains("removing")) return;
    el.classList.add("removing");
    el.addEventListener("animationend", () => el.remove());
  }

  // Skeleton loader
  function showKPISkeleton() {
    const grid = $("kpiGrid");
    if (!grid) return;
    grid.innerHTML = Array(6).fill(0).map(() => `
      <div class="kpi-card">
        <div class="kpi-card-header">
          <div class="skeleton" style="width:34px;height:34px;border-radius:8px;"></div>
        </div>
        <div class="skeleton skeleton-text w-50"></div>
        <div class="skeleton skeleton-number"></div>
        <div class="skeleton skeleton-text w-70"></div>
      </div>`).join("");
  }

  // Expose globally
  window.UI = {
    $, $$,
    formatNumber, formatDateTime, formatTimeAgo,
    capitalize, sentimentChipClass, escapeHtml,
    showToast, removeToast, showKPISkeleton,
  };
})();
