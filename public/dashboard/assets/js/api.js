/**
 * api.js — API fetch wrapper for Pantausentimen dashboard.
 * Loaded before dashboard.js. Exposes window.API for use across modules.
 */

(() => {
  "use strict";

  const API_BASE = "/api";

  function getMockData(path) {
    // Auth
    if (path.includes("/auth/me")) {
      return { id: 1, username: "demo", display_name: "Demo User" };
    }
    // Projects (periksa sebelum /dashboard agar tidak terjadi false match)
    if (path.includes("/projects")) {
      return {
        projects: [
          {
            id: 1,
            name: "Untold Story Analysis",
            description: "Analisis sentimen komentar Untold Story Part 1 & 2.",
          },
        ],
      };
    }
    // Videos
    if (path.includes("/videos")) {
      return {
        videos: [
          { video_id: "demoVid1", video_title: "Untold Story Part 1" },
          { video_id: "demoVid2", video_title: "Untold Story Part 2" },
        ],
      };
    }
    // Dashboard endpoints
    if (path.includes("/dashboard/summary")) {
      return {
        total_videos: 2,
        total_comments: 1250,
        analyzed_comments: 1180,
        new_comments_24h: 47,
        positive_percentage: 62,
        negative_percentage: 18,
        neutral_percentage: 20,
        quota_used: 2100,
        quota_limit: 10000,
        last_crawl: new Date(Date.now() - 3600000).toISOString(),
      };
    }
    if (path.includes("/dashboard/distributions")) {
      return {
        sentiment: { positive: 775, neutral: 250, negative: 225 },
        issue: [
          { issue: "Kondisi Ekonomi", count: 420 },
          { issue: "Hukum & Keadilan", count: 310 },
          { issue: "Politik & Pemerintahan", count: 280 },
          { issue: "Kebebasan Berpendapat", count: 195 },
          { issue: "Lainnya", count: 45 },
        ],
        stance: [
          { stance: "Dukung Konten", count: 680 },
          { stance: "Kritik Pemerintah", count: 340 },
          { stance: "Netral", count: 230 },
        ],
        action_intent: [
          { intent: "Ekspresi Dukungan", count: 520 },
          { intent: "Menuntut Akuntabilitas", count: 310 },
          { intent: "Berbagi Informasi", count: 420 },
        ],
        wordcloud: [
          { text: "Indonesia", value: 200 },
          { text: "Rakyat", value: 180 },
          { text: "Pemerintah", value: 160 },
          { text: "Keadilan", value: 140 },
          { text: "Korupsi", value: 120 },
          { text: "Harapan", value: 100 },
          { text: "Perubahan", value: 90 },
          { text: "Ekonomi", value: 85 },
          { text: "Demokrasi", value: 80 },
          { text: "Fakta", value: 75 },
        ],
      };
    }
    if (path.includes("/dashboard/timeline")) {
      return {
        labels: ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
        datasets: [
          { label: "Positif", data: [95, 140, 115, 170, 190, 240, 200] },
          { label: "Negatif", data: [25, 35, 20, 30, 45, 40, 30] },
          { label: "Netral", data: [45, 55, 38, 50, 65, 75, 60] },
        ],
      };
    }
    // Periksa representative-comments SEBELUM /comments (substring match)
    if (path.includes("/dashboard/representative-comments")) {
      return {
        comments: [
          {
            author_name: "Ahmad R.",
            published_at: new Date(Date.now() - 7200000).toISOString(),
            text_original:
              "Akhirnya ada yang berani bahas ini secara terbuka. Salut!",
            sentiment: "positive",
            issue_label: "Kebebasan Berpendapat",
            stance_label: "Dukung Konten",
            interpretation_short:
              "Apresiasi terhadap keberanian pembuat konten.",
          },
          {
            author_name: "Siti N.",
            published_at: new Date(Date.now() - 14400000).toISOString(),
            text_original:
              "Faktanya memang begitu, sudah lama rakyat tau tapi siapa yang berani ngomong?",
            sentiment: "positive",
            issue_label: "Politik & Pemerintahan",
            stance_label: "Kritik Pemerintah",
            interpretation_short: "Dukungan terhadap transparansi informasi.",
          },
          {
            author_name: "Budi P.",
            published_at: new Date(Date.now() - 21600000).toISOString(),
            text_original:
              "Hati-hati, data yang dipakai belum tentu akurat semua.",
            sentiment: "neutral",
            issue_label: "Lainnya",
            stance_label: "Netral",
            interpretation_short: "Imbauan untuk verifikasi data lebih lanjut.",
          },
          {
            author_name: "Dewi K.",
            published_at: new Date(Date.now() - 28800000).toISOString(),
            text_original:
              "Ekonomi makin susah, ini yang jarang dibahas di media mainstream.",
            sentiment: "negative",
            issue_label: "Kondisi Ekonomi",
            stance_label: "Kritik Pemerintah",
            interpretation_short:
              "Keluhan terhadap kondisi ekonomi yang tidak banyak diliput.",
          },
        ],
      };
    }
    if (path.includes("/dashboard/interpretation")) {
      return {
        interpretation:
          "Dari 1.250 komentar yang dianalisis, mayoritas (62%) merespons secara positif terhadap konten Untold Story. Isu utama yang paling sering diangkat adalah kondisi ekonomi dan hukum. Dominasi stance Dukung Konten menunjukkan audiens secara umum mengapresiasi narasi video ini.",
      };
    }
    if (path.includes("/dashboard/realtime")) {
      return {
        new_comments: 12,
        analyzed: 12,
        sentiment_breakdown: { positive: 8, neutral: 3, negative: 1 },
      };
    }
    // Crawler
    if (path.includes("/crawler/logs")) {
      return {
        logs: [
          "[INFO] Sistem berjalan dalam mode demo.",
          "[INFO] Data yang ditampilkan adalah simulasi.",
          "[INFO] Untuk analisis nyata, jalankan backend lokal.",
          "[INFO] Kunjungi README untuk panduan setup lengkap.",
        ],
      };
    }
    if (path.includes("/crawler/status")) {
      return {
        is_running: false,
        scheduler_active: false,
        recent_runs: [
          {
            status: "completed",
            started_at: new Date(Date.now() - 3600000).toISOString(),
            comments_fetched: 47,
          },
        ],
      };
    }
    if (path.includes("/crawler")) {
      return {
        success: true,
        message: "Mode demo aktif. Crawler tidak berjalan.",
      };
    }
    // Settings
    if (path.includes("/settings/ollama-status")) {
      return {
        server_online: false,
        model_loaded: false,
        model_name: "Demo Mode",
        base_url: "N/A",
        error:
          "Mode demo aktif. Jalankan backend lokal untuk menggunakan Ollama.",
      };
    }
    // Comments (setelah representative-comments)
    if (path.includes("/comments")) {
      return { comments: [], total: 0 };
    }
    return {};
  }

  async function apiFetch(path, options = {}) {
    // AUTO DEMO MODE FOR VERCEL
    if (
      window.location.hostname.includes("vercel.app") ||
      window.location.hostname.includes("github.io")
    ) {
      console.log("[Demo Mode] Mocking API request to:", path);
      // Simulate network delay
      await new Promise((resolve) => setTimeout(resolve, 500));
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
