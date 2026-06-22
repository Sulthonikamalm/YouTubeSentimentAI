/**
 * api.js — API fetch wrapper for Pantausentimen dashboard.
 * Loaded before dashboard.js. Exposes window.API for use across modules.
 */

(() => {
  "use strict";

  const API_BASE = "/api";

  function getMockData(path) {
    if (path.includes('/dashboard/summary')) {
      return { total_videos: 5, total_comments: 1250, analyzed_comments: 1250, positive_percentage: 65, negative_percentage: 15 };
    }
    if (path.includes('/dashboard/distributions')) {
      return {
        sentiment: { positive: 812, neutral: 250, negative: 188 },
        issue: [{issue: "Pelayanan", count: 400}, {issue: "Harga", count: 350}, {issue: "Kualitas", count: 500}],
        stance: [{stance: "Dukung", count: 700}, {stance: "Kritik", count: 300}],
        action_intent: [{intent: "Rekomendasi", count: 600}, {intent: "Boikot", count: 50}],
        wordcloud: [{text: "Bagus", value: 100}, {text: "Keren", value: 80}, {text: "Mahal", value: 30}]
      };
    }
    if (path.includes('/dashboard/timeline')) {
      return {
        labels: ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
        datasets: [
          { label: "Positif", data: [100, 150, 120, 180, 200, 250, 210] },
          { label: "Negatif", data: [20, 30, 15, 25, 40, 35, 25] },
          { label: "Netral", data: [50, 60, 40, 55, 70, 80, 65] }
        ]
      };
    }
    if (path.includes('/dashboard/interpretation')) {
      return { interpretation: "Berdasarkan data dummy, audiens merespons sangat positif terhadap konten Anda dengan fokus utama pada kualitas dan pelayanan." };
    }
    if (path.includes('/crawler/status')) {
      return { is_running: false, recent_runs: [{status: "completed", started_at: new Date().toISOString()}] };
    }
    if (path.includes('/dashboard/representative-comments')) {
      return { comments: [
        { author_name: "Budi", published_at: new Date().toISOString(), text_original: "Wah keren banget videonya!", sentiment: "positive", issue: "Kualitas", stance: "Dukung", action_intent: "Rekomendasi" },
        { author_name: "Siti", published_at: new Date().toISOString(), text_original: "Harganya kemahalan sih menurutku.", sentiment: "negative", issue: "Harga", stance: "Kritik", action_intent: "Komplain" }
      ]};
    }
    if (path.includes('/projects')) {
      return { projects: [{id: 1, name: "Demo Project Vercel", description: "Proyek simulasi demo."}] };
    }
    return {}; // Default fallback
  }

  async function apiFetch(path, options = {}) {
    // AUTO DEMO MODE FOR VERCEL
    if (window.location.hostname.includes("vercel.app") || window.location.hostname.includes("github.io")) {
      console.log("[Demo Mode] Mocking API request to:", path);
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 500));
      return getMockData(path);
    }

    try {
      const resp = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${resp.status}`);
      }
      return await resp.json();
    } catch (err) {
      console.error(`API Error [${path}]:`, err);
      throw err;
    }
  }

  // Expose globally
  window.API = { apiFetch };
})();
