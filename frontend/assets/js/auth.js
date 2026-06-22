/* auth.js — Login dashboard: sidik jari (WebAuthn/Windows Hello) + password.
 *
 * Mengonversi data base64url <-> ArrayBuffer karena browser WebAuthn memakai
 * ArrayBuffer, sedangkan server (Python) memakai string base64url.
 */

// --- Konversi base64url <-> ArrayBuffer ---
function b64urlToBuf(b64url) {
  const pad = "=".repeat((4 - (b64url.length % 4)) % 4);
  const b64 = (b64url + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

function bufToB64url(buf) {
  const bytes = new Uint8Array(buf);
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Terjadi kesalahan");
  return data;
}

// --- Status pesan ---
function setStatus(msg, type) {
  const el = document.getElementById("authStatus");
  if (!el) return;
  el.textContent = msg || "";
  el.className = "auth-status" + (type ? " auth-status--" + type : "");
}

// --- Cek dukungan Windows Hello / platform authenticator ---
async function hasPlatformAuthenticator() {
  if (!window.PublicKeyCredential) return false;
  try {
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch (e) {
    return false;
  }
}

// --- Terjemahkan error WebAuthn jadi pesan yang jelas (untuk diagnosa) ---
function webauthnErrorMessage(e) {
  const name = (e && e.name) || "Error";
  const detail = (e && e.message) ? ` (${e.message})` : "";
  switch (name) {
    case "NotAllowedError":
      return "Sidik jari dibatalkan atau waktu habis. Pastikan Windows Hello aktif lalu coba lagi.";
    case "InvalidStateError":
      return "Sidik jari ini sudah terdaftar di akun ini.";
    case "NotSupportedError":
      return "Browser/laptop tidak mendukung sidik jari (WebAuthn). Gunakan Chrome/Edge terbaru.";
    case "SecurityError":
      return "Konteks tidak aman. Buka lewat http://localhost:5000 (bukan IP/file).";
    case "AbortError":
      return "Proses sidik jari dibatalkan. Coba lagi.";
    default:
      return `Sidik jari gagal: ${name}${detail}. Anda tetap bisa masuk dengan password.`;
  }
}

// --- Serialisasi hasil ceremony untuk dikirim ke server ---
function serializeRegistration(cred) {
  return {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      clientDataJSON: bufToB64url(cred.response.clientDataJSON),
      attestationObject: bufToB64url(cred.response.attestationObject),
    },
    clientExtensionResults: cred.getClientExtensionResults(),
  };
}

function serializeAuthentication(cred) {
  return {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      clientDataJSON: bufToB64url(cred.response.clientDataJSON),
      authenticatorData: bufToB64url(cred.response.authenticatorData),
      signature: bufToB64url(cred.response.signature),
      userHandle: cred.response.userHandle ? bufToB64url(cred.response.userHandle) : null,
    },
    clientExtensionResults: cred.getClientExtensionResults(),
  };
}

// --- DAFTAR: buat akun + rekam sidik jari ---
async function doRegister() {
  const username = document.getElementById("regUsername").value.trim();
  const displayName = document.getElementById("regDisplayName").value.trim();
  const password = document.getElementById("regPassword").value;

  if (!username || !password) {
    setStatus("Isi nama pengguna dan password cadangan dulu.", "error");
    return;
  }

  setStatus("Membuat akun…");
  let options;
  try {
    options = await postJSON("/api/auth/register/begin", {
      username,
      display_name: displayName,
      password,
    });
  } catch (e) {
    setStatus(e.message, "error");
    return;
  }

  // Ubah field base64url menjadi ArrayBuffer untuk browser.
  options.challenge = b64urlToBuf(options.challenge);
  options.user.id = b64urlToBuf(options.user.id);
  if (options.excludeCredentials) {
    options.excludeCredentials = options.excludeCredentials.map((c) => ({
      ...c,
      id: b64urlToBuf(c.id),
    }));
  }

  setStatus("Sentuh sensor sidik jari di laptop Anda saat jendela Windows muncul…");
  let cred;
  try {
    cred = await navigator.credentials.create({ publicKey: options });
  } catch (e) {
    setStatus(webauthnErrorMessage(e), "error");
    return;
  }

  try {
    await postJSON("/api/auth/register/finish", {
      credential: serializeRegistration(cred),
      device_label: navigator.platform || "Laptop",
    });
  } catch (e) {
    setStatus(e.message, "error");
    return;
  }

  setStatus("Berhasil! Mengarahkan ke dashboard…", "success");
  window.location.href = "/dashboard";
}

// --- MASUK dengan sidik jari ---
async function doFingerprintLogin() {
  setStatus("Menyiapkan login sidik jari…");
  let options;
  try {
    options = await postJSON("/api/auth/login/begin", {});
  } catch (e) {
    setStatus(e.message, "error");
    return;
  }

  options.challenge = b64urlToBuf(options.challenge);
  if (options.allowCredentials) {
    options.allowCredentials = options.allowCredentials.map((c) => ({
      ...c,
      id: b64urlToBuf(c.id),
    }));
  }

  setStatus("Sentuh sensor sidik jari di laptop Anda…");
  let cred;
  try {
    cred = await navigator.credentials.get({ publicKey: options });
  } catch (e) {
    setStatus(webauthnErrorMessage(e), "error");
    return;
  }

  try {
    await postJSON("/api/auth/login/finish", {
      credential: serializeAuthentication(cred),
    });
  } catch (e) {
    setStatus(e.message, "error");
    return;
  }

  setStatus("Berhasil! Mengarahkan ke dashboard…", "success");
  window.location.href = "/dashboard";
}

// --- MASUK dengan password ---
async function doPasswordLogin() {
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;

  // AUTO DEMO MODE FOR VERCEL
  if (window.location.hostname.includes("vercel.app") || window.location.hostname.includes("github.io")) {
    setStatus("Demo Mode: Berhasil! Mengarahkan ke dashboard...", "success");
    window.location.href = "index.html";
    return;
  }

  if (!username || !password) {
    setStatus("Isi username dan password.", "error");
    return;
  }
  setStatus("Memeriksa…");
  try {
    await postJSON("/api/auth/login/password", { username, password });
  } catch (e) {
    setStatus(e.message, "error");
    return;
  }
  setStatus("Berhasil! Mengarahkan ke dashboard…", "success");
  window.location.href = "/dashboard";
}

// --- Inisialisasi halaman ---
document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("btnFingerprintLogin").addEventListener("click", doFingerprintLogin);
  document.getElementById("btnPasswordLogin").addEventListener("click", doPasswordLogin);
  document.getElementById("btnRegister").addEventListener("click", doRegister);

  // Tab Masuk <-> Daftar
  const tabs = document.querySelectorAll("[data-tab]");
  tabs.forEach((t) =>
    t.addEventListener("click", () => {
      tabs.forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      const target = t.getAttribute("data-tab");
      document.getElementById("panel-login").style.display = target === "login" ? "block" : "none";
      document.getElementById("panel-register").style.display = target === "register" ? "block" : "none";
      setStatus("");
    })
  );

  // Submit dengan tombol Enter
  document.getElementById("loginPassword").addEventListener("keydown", (e) => {
    if (e.key === "Enter") doPasswordLogin();
  });

  // Bila perangkat tak punya sensor sidik jari/Windows Hello, beri tahu user.
  const supported = await hasPlatformAuthenticator();
  if (!supported) {
    const note = document.getElementById("fingerprintNote");
    if (note) {
      note.textContent =
        "Laptop ini sepertinya belum punya sidik jari/Windows Hello aktif. Silakan masuk dengan password.";
      note.classList.add("auth-status--error");
    }
    document.getElementById("btnFingerprintLogin").disabled = true;
  }
});
