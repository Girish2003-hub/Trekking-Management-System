import { api } from "../api.js";
import { store, homeFor } from "../store.js";
import { StatusBadge, TrekFilters, queryString } from "../components.js";

// Trek catalogue: used by guests (view only) and trekkers (can book).
export const TrekBrowse = {
  components: { StatusBadge, TrekFilters },
  data: () => ({ store, treks: [], loading: true, error: "", participants: {}, busy: null }),
  async mounted() { await this.load({}); },
  methods: {
    async load(filters) {
      this.loading = true; this.error = "";
      try { this.treks = (await api("/treks" + queryString(filters))).treks; }
      catch (e) { this.error = e.message; }
      this.loading = false;
    },
    async book(trek) {
      const count = Number(this.participants[trek.id] || 1);
      if (!confirm(`Book ${trek.name} for ${count} participant(s)?`)) return;
      this.busy = trek.id;
      try {
        await api("/bookings", { method: "POST", body: { trek_id: trek.id, participants: count } });
        store.notify(`Booked ${trek.name}! You can pay from your dashboard.`);
        trek.available_slots -= count;
      } catch (e) { store.notify(e.message, "danger"); }
      this.busy = null;
    },
  },
  template: `
    <div class="container py-4">
      <h1 class="h3 mb-3">Find a Trek</h1>
      <trek-filters @search="load"></trek-filters>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <div v-if="loading" class="text-center py-5"><div class="spinner-border text-success"></div></div>
      <p v-else-if="!treks.length" class="text-muted">No treks match your filters.</p>
      <div class="row g-3">
        <div v-for="t in treks" :key="t.id" class="col-12 col-sm-6 col-lg-4">
          <div class="card trek-card h-100 border-0 shadow-sm">
            <div class="card-body d-flex flex-column">
              <div class="d-flex justify-content-between align-items-start">
                <h2 class="h5 card-title mb-1">{{ t.name }}</h2>
                <status-badge :status="t.status"></status-badge>
              </div>
              <p class="text-muted small mb-2">{{ t.location }}</p>
              <ul class="list-unstyled small mb-3">
                <li>Difficulty: <span class="text-capitalize">{{ t.difficulty }}</span></li>
                <li>Duration: {{ t.duration_days }} day(s)</li>
                <li>Dates: {{ t.start_date }} to {{ t.end_date }}</li>
                <li>Slots left: <strong>{{ t.available_slots }}</strong> / {{ t.total_slots }}</li>
                <li v-if="t.assigned_staff_name">Guide: {{ t.assigned_staff_name }}</li>
              </ul>
              <div class="mt-auto">
                <template v-if="store.user && store.user.role === 'user'">
                  <div v-if="t.status === 'open' && t.available_slots > 0" class="input-group">
                    <input v-model="participants[t.id]" type="number" min="1" :max="Math.min(10, t.available_slots)"
                           class="form-control" placeholder="1" aria-label="Participants">
                    <button class="btn btn-success" :disabled="busy === t.id" @click="book(t)">Book</button>
                  </div>
                  <button v-else class="btn btn-outline-secondary w-100" disabled>
                    {{ t.status === 'open' ? 'Fully booked' : 'Bookings not open yet' }}
                  </button>
                </template>
                <router-link v-else-if="!store.user" to="/login" class="btn btn-outline-success w-100">Login to book</router-link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>`,
};

export const HomePage = {
  data: () => ({ store }),
  computed: { home() { return homeFor(store.user); } },
  template: `
    <div class="container py-4">
      <div class="hero p-4 p-md-5 mb-4">
        <h1 class="display-5 fw-bold">Plan, book and run treks in one place</h1>
        <p class="lead col-lg-8">Browse open treks, book your slot, and track your trekking history.
          Staff manage their groups and admins oversee everything.</p>
        <div class="d-flex flex-wrap gap-2">
          <router-link to="/treks" class="btn btn-light btn-lg">Browse treks</router-link>
          <router-link v-if="!store.user" to="/register" class="btn btn-outline-light btn-lg">Create account</router-link>
          <router-link v-else :to="home" class="btn btn-outline-light btn-lg">Go to dashboard</router-link>
        </div>
      </div>
      <div class="row g-3 text-center">
        <div class="col-md-4"><div class="card border-0 shadow-sm h-100"><div class="card-body">
          <h2 class="h5">Search &amp; filter</h2><p class="text-muted mb-0">By difficulty, location and duration.</p></div></div></div>
        <div class="col-md-4"><div class="card border-0 shadow-sm h-100"><div class="card-body">
          <h2 class="h5">Live slots</h2><p class="text-muted mb-0">No overbooking and no duplicate bookings.</p></div></div></div>
        <div class="col-md-4"><div class="card border-0 shadow-sm h-100"><div class="card-body">
          <h2 class="h5">Your history</h2><p class="text-muted mb-0">Every trek you booked, cancelled or completed.</p></div></div></div>
      </div>
    </div>`,
};

export const LoginPage = {
  data: () => ({ email: "", password: "", error: "", busy: false }),
  methods: {
    async submit() {
      this.error = ""; this.busy = true;
      try {
        const user = await store.login(this.email, this.password);
        store.notify(`Welcome, ${user.name}`);
        this.$router.push(this.$route.query.next || homeFor(user));
      } catch (e) { this.error = e.message; }
      this.busy = false;
    },
  },
  template: `
    <div class="container py-5" style="max-width: 440px">
      <div class="card border-0 shadow-sm"><div class="card-body p-4">
        <h1 class="h4 mb-3">Login</h1>
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="mb-3">
            <label class="form-label" for="email">Email</label>
            <input id="email" v-model.trim="email" type="email" class="form-control" required autocomplete="username">
          </div>
          <div class="mb-3">
            <label class="form-label" for="pw">Password</label>
            <input id="pw" v-model="password" type="password" class="form-control" required autocomplete="current-password">
          </div>
          <button class="btn btn-success w-100" :disabled="busy">{{ busy ? "Logging in..." : "Login" }}</button>
        </form>
        <p class="small text-muted mt-3 mb-0">Trekker without an account?
          <router-link to="/register">Register</router-link>. Staff accounts are created by the admin.</p>
      </div></div>
    </div>`,
};

export const RegisterPage = {
  data: () => ({ f: { name: "", email: "", contact: "", password: "", confirm: "" }, error: "", busy: false }),
  methods: {
    async submit() {
      this.error = "";
      if (this.f.password !== this.f.confirm) { this.error = "Passwords do not match"; return; }
      this.busy = true;
      try {
        const { confirm, ...body } = this.f;
        await api("/auth/register", { method: "POST", body });
        store.notify("Account created. Please log in.");
        this.$router.push("/login");
      } catch (e) { this.error = e.message; }
      this.busy = false;
    },
  },
  template: `
    <div class="container py-5" style="max-width: 480px">
      <div class="card border-0 shadow-sm"><div class="card-body p-4">
        <h1 class="h4 mb-3">Create trekker account</h1>
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <form @submit.prevent="submit">
          <div class="mb-3"><label class="form-label">Full name</label>
            <input v-model.trim="f.name" class="form-control" required minlength="2" maxlength="120"></div>
          <div class="mb-3"><label class="form-label">Email</label>
            <input v-model.trim="f.email" type="email" class="form-control" required></div>
          <div class="mb-3"><label class="form-label">Contact number</label>
            <input v-model.trim="f.contact" type="tel" class="form-control" pattern="\\+?[0-9]{7,15}"
                   title="7-15 digits"></div>
          <div class="mb-3"><label class="form-label">Password</label>
            <input v-model="f.password" type="password" class="form-control" required minlength="6"></div>
          <div class="mb-3"><label class="form-label">Confirm password</label>
            <input v-model="f.confirm" type="password" class="form-control" required minlength="6"></div>
          <button class="btn btn-success w-100" :disabled="busy">Register</button>
        </form>
      </div></div>
    </div>`,
};

export const NotFoundPage = {
  template: `<div class="container py-5 text-center"><h1 class="h3">Page not found</h1>
    <router-link to="/" class="btn btn-success mt-3">Go home</router-link></div>`,
};
