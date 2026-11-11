// Shared state for the whole app: who is logged in, plus a flash message.
// Vue.reactive() means any component that reads store.user re-renders when it changes.
import { api, setToken } from "./api.js";

export const store = Vue.reactive({
  user: null,
  loaded: false,
  flash: null, // { type: "success" | "danger" | "warning", text: "..." }

  notify(text, type = "success") {
    this.flash = { text, type };
    clearTimeout(this._timer);
    this._timer = setTimeout(() => { this.flash = null; }, 4000);
  },

  // Asks Flask "who am I?" once per page load (needs your GET /api/auth/me).
  async loadUser() {
    if (this.loaded) return this.user;
    try {
      this.user = (await api("/auth/me")).user;
    } catch {
      this.user = null;
    }
    this.loaded = true;
    return this.user;
  },

  async login(email, password) {
    const data = await api("/auth/login", { method: "POST", body: { email, password } });
    if (data.token) setToken(data.token);
    this.user = data.user;
    this.loaded = true;
    return data.user;
  },

  async logout() {
    try { await api("/auth/logout", { method: "POST" }); } catch { /* already logged out */ }
    setToken(null);
    this.user = null;
  },
});

// Where each role lands after login.
export function homeFor(user) {
  if (!user) return "/";
  return { admin: "/admin", staff: "/staff", user: "/dashboard" }[user.role] || "/";
}
