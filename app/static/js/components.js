// Small reusable components used by many pages.
import { store, homeFor } from "./store.js";

export const StatusBadge = {
  props: ["status"],
  computed: {
    color() {
      return {
        pending: "secondary", approved: "info", open: "success", closed: "warning",
        ongoing: "primary", completed: "dark", booked: "success", cancelled: "danger",
        paid: "success", refunded: "warning",
      }[this.status] || "secondary";
    },
  },
  template: `<span class="badge text-capitalize" :class="'text-bg-' + color">{{ status }}</span>`,
};

export const StatCard = {
  props: ["label", "value", "color"],
  template: `
    <div class="card stat-card border-0 shadow-sm h-100">
      <div class="card-body">
        <div class="text-muted small">{{ label }}</div>
        <div class="display-6" :class="'text-' + (color || 'dark')">{{ value }}</div>
      </div>
    </div>`,
};

export const FlashMessage = {
  data: () => ({ store }),
  template: `
    <div v-if="store.flash" class="container mt-3">
      <div class="alert alert-dismissible mb-0" :class="'alert-' + store.flash.type">
        {{ store.flash.text }}
        <button type="button" class="btn-close" @click="store.flash = null"></button>
      </div>
    </div>`,
};

export const AppNavbar = {
  data: () => ({ store }),
  computed: {
    links() {
      const role = store.user && store.user.role;
      if (role === "admin") return [
        ["/admin", "Dashboard"], ["/admin/treks", "Treks"], ["/admin/staff", "Staff"],
        ["/admin/users", "Users"], ["/admin/bookings", "Bookings"], ["/admin/search", "Search"],
      ];
      if (role === "staff") return [["/staff", "My Treks"], ["/profile", "Profile"]];
      if (role === "user") return [
        ["/dashboard", "Dashboard"], ["/treks", "Find Treks"], ["/history", "History"], ["/profile", "Profile"],
      ];
      return [["/", "Home"], ["/treks", "Treks"]];
    },
    home() { return homeFor(store.user); },
  },
  methods: {
    async logout() {
      await store.logout();
      store.notify("Logged out");
      this.$router.push("/login");
    },
  },
  template: `
    <nav class="navbar navbar-expand-lg navbar-dark bg-success shadow-sm">
      <div class="container">
        <router-link class="navbar-brand fw-semibold" :to="home">TrekManager</router-link>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div id="nav" class="collapse navbar-collapse">
          <ul class="navbar-nav me-auto">
            <li v-for="[to, label] in links" :key="to" class="nav-item">
              <router-link class="nav-link" :to="to" exact-active-class="active">{{ label }}</router-link>
            </li>
          </ul>
          <div v-if="store.user" class="d-flex align-items-center gap-2">
            <span class="text-white-50 small">{{ store.user.name }} ({{ store.user.role }})</span>
            <button class="btn btn-outline-light btn-sm" @click="logout">Logout</button>
          </div>
          <div v-else class="d-flex gap-2">
            <router-link class="btn btn-outline-light btn-sm" to="/login">Login</router-link>
            <router-link class="btn btn-light btn-sm" to="/register">Register</router-link>
          </div>
        </div>
      </div>
    </nav>`,
};

// Search + filter bar for treks. Emits "search" with the filter object.
export const TrekFilters = {
  emits: ["search"],
  data: () => ({ f: { q: "", difficulty: "", location: "", min_days: "", max_days: "" } }),
  methods: {
    submit() { this.$emit("search", { ...this.f }); },
    reset() { this.f = { q: "", difficulty: "", location: "", min_days: "", max_days: "" }; this.submit(); },
  },
  template: `
    <form class="row g-2 align-items-end mb-3" @submit.prevent="submit">
      <div class="col-12 col-md-3">
        <label class="form-label small">Search</label>
        <input v-model.trim="f.q" class="form-control" placeholder="Name or location" maxlength="60">
      </div>
      <div class="col-6 col-md-2">
        <label class="form-label small">Difficulty</label>
        <select v-model="f.difficulty" class="form-select">
          <option value="">Any</option><option value="easy">Easy</option>
          <option value="moderate">Moderate</option><option value="hard">Hard</option>
        </select>
      </div>
      <div class="col-6 col-md-2">
        <label class="form-label small">Location</label>
        <input v-model.trim="f.location" class="form-control" maxlength="60">
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label small">Min days</label>
        <input v-model="f.min_days" type="number" min="1" class="form-control">
      </div>
      <div class="col-6 col-md-1">
        <label class="form-label small">Max days</label>
        <input v-model="f.max_days" type="number" min="1" class="form-control">
      </div>
      <div class="col-12 col-md-3 d-flex gap-2">
        <button class="btn btn-success flex-fill">Search</button>
        <button type="button" class="btn btn-outline-secondary" @click="reset">Reset</button>
      </div>
    </form>`,
};

export function queryString(obj) {
  const params = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => { if (v !== "" && v != null) params.set(k, v); });
  const s = params.toString();
  return s ? "?" + s : "";
}
