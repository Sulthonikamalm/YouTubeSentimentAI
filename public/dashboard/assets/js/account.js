/* account.js — Menu akun di dashboard: tampilkan user, logout, tambah sidik jari.
 * Self-contained (helper base64url sendiri) agar tidak bergantung pada auth.js
 * yang khusus halaman login.
 */
(function () {
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

  async function loadMe() {
    try {
      const me = await (await fetch("/api/auth/me")).json();
      const el = document.getElementById("currentUserName");
      if (el && me.display_name) el.textContent = me.display_name || me.username;
    } catch (e) {
      /* abaikan */
    }
  }

  async function doLogout(e) {
    if (e) e.preventDefault();
    try {
      await postJSON("/api/auth/logout", {});
    } catch (_) {}
    window.location.href = "/login";
  }

  async function doAddFingerprint(e) {
    if (e) e.preventDefault();
    try {
      let options = await postJSON("/api/auth/credentials/add/begin", {});
      options.challenge = b64urlToBuf(options.challenge);
      options.user.id = b64urlToBuf(options.user.id);
      if (options.excludeCredentials) {
        options.excludeCredentials = options.excludeCredentials.map((c) => ({
          ...c,
          id: b64urlToBuf(c.id),
        }));
      }
      const cred = await navigator.credentials.create({ publicKey: options });
      await postJSON("/api/auth/credentials/add/finish", {
        credential: {
          id: cred.id,
          rawId: bufToB64url(cred.rawId),
          type: cred.type,
          response: {
            clientDataJSON: bufToB64url(cred.response.clientDataJSON),
            attestationObject: bufToB64url(cred.response.attestationObject),
          },
          clientExtensionResults: cred.getClientExtensionResults(),
        },
        device_label: navigator.platform || "Laptop",
      });
      alert("Sidik jari baru berhasil ditambahkan.");
    } catch (err) {
      alert("Gagal menambah sidik jari: " + (err.message || err));
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadMe();
    const logout = document.getElementById("btnMenuLogout");
    if (logout) logout.addEventListener("click", doLogout);
    const addFp = document.getElementById("btnMenuAddFingerprint");
    if (addFp) addFp.addEventListener("click", doAddFingerprint);
  });
})();
