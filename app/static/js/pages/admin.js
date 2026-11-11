import { api } from "../api.js";
import { store } from "../store.js";
import { StatCard, StatusBadge, queryString } from "../components.js";

const STATUSES = ["pending", "approved", "open", "closed", "ongoing", "completed"];

// ------------------------------------------------------------------ dashboard + charts
export const AdminDashboard = {
  components: { StatCard },
  data: () => ({ s: null, error: "" }),
  async mounted() {
    try { this.s = await api("/admin/stats"); } catch (e) { this.error = e.message; return; }
    await this.$nextTick(); // wait until the <canvas> elements exist
    this.charts = [
      this.draw("popular", "bar", this.s.charts.popular_treks, "Participants"),
      this.draw("monthly", "line", this.s.charts.bookings_per_month, "Bookings"),
      this.draw("status", "doughnut", Object.entries(this.s.charts.treks_by_status)),
      this.draw("bookings", "pie", Object.entries(this.s.charts.bookings_by_status)),
    ];
  },
  beforeUnmount() { (this.charts || []).forEach((c) => c && c.destroy()); },
  methods: {
    // pairs: [["Hampta Pass", 12], ["Kedarkantha", 8]]
    draw(ref, type, pairs, label) {
      if (!window.Chart || !pairs.length) return null;
      const round = type === "doughnut" || type === "pie";
      return new Chart(this.$refs[ref], {
        type,
        data: {
          labels: pairs.map((p) => p[0]),
          datasets: [{
            label, data: pairs.map((p) => p[1]), borderWidth: round ? 1 : 2,
            backgroundColor: round ? ["#198754", "#0d6efd", "#ffc107", "#dc3545", "#6c757d", "#212529"] : "#198754",
            borderColor: round ? "#fff" : "#198754", tension: 0.3,
          }],
        },
        options: {
          maintainAspectRatio: false,
          plugins: { legend: { display: round } },
          scales: round ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    },
  },
  template: `
    <div class="container py-4">
      <h1 class="h3 mb-3">Admin dashboard</h1>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-if="s">
        <div class="row g-3 mb-4">
          <div class="col-6 col-lg-3"><stat-card label="Total treks" :value="s.counts.treks"></stat-card></div>
          <div class="col-6 col-lg-3"><stat-card label="Trekkers" :value="s.counts.users" color="success"></stat-card></div>
          <div class="col-6 col-lg-3"><stat-card label="Staff" :value="s.counts.staff" color="primary"></stat-card></div>
          <div class="col-6 col-lg-3"><stat-card label="Bookings" :value="s.counts.bookings" color="success"></stat-card></div>
          <div class="col-6 col-lg-4"><stat-card label="Active bookings" :value="s.counts.active_bookings"></stat-card></div>
          <div class="col-6 col-lg-4"><stat-card label="Treks completed" :value="s.counts.completed_treks"></stat-card></div>
          <div class="col-12 col-lg-4"><stat-card label="Treks awaiting approval" :value="s.counts.pending_treks" color="warning"></stat-card></div>
        </div>
        <div class="row g-3">
          <div class="col-lg-6"><div class="card border-0 shadow-sm"><div class="card-body">
            <h2 class="h6">Most popular treks (participants)</h2>
            <div class="chart-box"><canvas ref="popular"></canvas></div>
            <p v-if="!s.charts.popular_treks.length" class="text-muted small">No bookings yet.</p></div></div></div>
          <div class="col-lg-6"><div class="card border-0 shadow-sm"><div class="card-body">
            <h2 class="h6">Bookings per month</h2>
            <div class="chart-box"><canvas ref="monthly"></canvas></div></div></div></div>
          <div class="col-lg-6"><div class="card border-0 shadow-sm"><div class="card-body">
            <h2 class="h6">Treks by status</h2>
            <div class="chart-box"><canvas ref="status"></canvas></div></div></div></div>
          <div class="col-lg-6"><div class="card border-0 shadow-sm"><div class="card-body">
            <h2 class="h6">Bookings by status</h2>
            <div class="chart-box"><canvas ref="bookings"></canvas></div></div></div></div>
        </div>
      </template>
    </div>`,
};

// ------------------------------------------------------------------ treks
const emptyTrek = () => ({ name: "", location: "", difficulty: "easy", start_date: "", end_date: "", total_slots: 10 });

export const AdminTreks = {
  components: { StatusBadge },
  data: () => ({
    treks: [], staff: [], filters: { q: "", status: "" }, form: emptyTrek(), editingId: null,
    showForm: false, formError: "", statuses: STATUSES,
  }),
  computed: {
    activeStaff() { return this.staff.filter((s) => s.is_active && !s.is_blacklisted); },
  },
  async mounted() {
    await Promise.all([this.load(), this.loadStaff()]);
  },
  methods: {
    async load() { this.treks = (await api("/admin/treks" + queryString(this.filters))).treks; },
    async loadStaff() { this.staff = (await api("/admin/staff")).staff; },
    openCreate() { this.form = emptyTrek(); this.editingId = null; this.formError = ""; this.showForm = true; },
    openEdit(t) {
      this.form = { name: t.name, location: t.location, difficulty: t.difficulty,
                    start_date: t.start_date, end_date: t.end_date, total_slots: t.total_slots };
      this.editingId = t.id; this.formError = ""; this.showForm = true;
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    async save() {
      this.formError = "";
      if (this.form.end_date < this.form.start_date) { this.formError = "End date cannot be before start date"; return; }
      try {
        if (this.editingId) await api(`/admin/treks/${this.editingId}`, { method: "PUT", body: this.form });
        else await api("/admin/treks", { method: "POST", body: this.form });
        store.notify(this.editingId ? "Trek updated" : "Trek created (status: pending)");
        this.showForm = false; this.load();
      } catch (e) { this.formError = e.message; }
    },
    async act(request, message) {
      try { await request; store.notify(message); } catch (e) { store.notify(e.message, "danger"); }
      this.load();
    },
    setStatus(t, status) { this.act(api(`/admin/treks/${t.id}/status`, { method: "PATCH", body: { status } }), `Status: ${status}`); },
    assign(t, staffId) {
      this.act(api(`/admin/treks/${t.id}/assign`, { method: "PUT", body: { staff_id: staffId ? Number(staffId) : null } }), "Staff assignment saved");
    },
    remove(t) {
      if (!confirm(`Delete ${t.name}?`)) return;
      this.act(api(`/admin/treks/${t.id}`, { method: "DELETE" }), "Trek deleted");
    },
  },
  template: `
    <div class="container py-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h1 class="h3 mb-0">Treks</h1>
        <button class="btn btn-success" @click="openCreate">+ New trek</button>
      </div>

      <div v-if="showForm" class="card border-0 shadow-sm mb-4"><div class="card-body">
        <h2 class="h5">{{ editingId ? "Edit trek" : "New trek" }}</h2>
        <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
        <form class="row g-2" @submit.prevent="save">
          <div class="col-md-4"><label class="form-label small">Name</label>
            <input v-model.trim="form.name" class="form-control" required minlength="3" maxlength="120"></div>
          <div class="col-md-4"><label class="form-label small">Location</label>
            <input v-model.trim="form.location" class="form-control" required minlength="2" maxlength="120"></div>
          <div class="col-md-4"><label class="form-label small">Difficulty</label>
            <select v-model="form.difficulty" class="form-select" required>
              <option value="easy">Easy</option><option value="moderate">Moderate</option><option value="hard">Hard</option></select></div>
          <div class="col-6 col-md-4"><label class="form-label small">Start date</label>
            <input v-model="form.start_date" type="date" class="form-control" required></div>
          <div class="col-6 col-md-4"><label class="form-label small">End date</label>
            <input v-model="form.end_date" type="date" class="form-control" :min="form.start_date" required></div>
          <div class="col-md-4"><label class="form-label small">Total slots</label>
            <input v-model.number="form.total_slots" type="number" min="1" max="500" class="form-control" required></div>
          <div class="col-12 d-flex gap-2 mt-2">
            <button class="btn btn-success">Save</button>
            <button type="button" class="btn btn-outline-secondary" @click="showForm = false">Cancel</button>
          </div>
        </form>
        <p class="small text-muted mt-2 mb-0">Duration is calculated from the dates.</p>
      </div></div>

      <form class="row g-2 mb-3" @submit.prevent="load">
        <div class="col-8 col-md-5"><input v-model.trim="filters.q" class="form-control" placeholder="Search name or location"></div>
        <div class="col-4 col-md-3"><select v-model="filters.status" class="form-select" @change="load">
          <option value="">All statuses</option><option v-for="s in statuses" :key="s" :value="s">{{ s }}</option></select></div>
        <div class="col-12 col-md-2"><button class="btn btn-outline-success w-100">Filter</button></div>
      </form>

      <div class="table-responsive">
        <table class="table bg-white shadow-sm">
          <thead><tr><th>Trek</th><th>Dates</th><th>Slots</th><th>Status</th><th>Assigned staff</th><th></th></tr></thead>
          <tbody>
            <tr v-for="t in treks" :key="t.id">
              <td>{{ t.name }}<div class="small text-muted">{{ t.location }} &middot; {{ t.difficulty }} &middot; {{ t.duration_days }}d</div></td>
              <td class="small">{{ t.start_date }}<br>{{ t.end_date }}</td>
              <td>{{ t.available_slots }} / {{ t.total_slots }}</td>
              <td style="min-width: 130px">
                <select class="form-select form-select-sm" :value="t.status" @change="setStatus(t, $event.target.value)" aria-label="Status">
                  <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option></select>
              </td>
              <td style="min-width: 160px">
                <select class="form-select form-select-sm" :value="t.assigned_staff_id || ''" :disabled="t.status === 'completed'"
                        @change="assign(t, $event.target.value)" aria-label="Assigned staff">
                  <option value="">Unassigned</option>
                  <option v-for="s in activeStaff" :key="s.id" :value="s.id">{{ s.name }}</option>
                  <option v-if="t.assigned_staff_id && !activeStaff.some(s => s.id === t.assigned_staff_id)"
                          :value="t.assigned_staff_id">{{ t.assigned_staff_name }}</option>
                </select>
              </td>
              <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-primary me-1" :disabled="t.status === 'completed'" @click="openEdit(t)">Edit</button>
                <button class="btn btn-sm btn-outline-danger" @click="remove(t)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!treks.length" class="text-muted">No treks found.</p>
      </div>
    </div>`,
};

// ------------------------------------------------------------------ account actions (shared)
const AccountActions = {
  props: ["account"],
  emits: ["changed"],
  methods: {
    async act(action) {
      if (action === "blacklist" && !confirm(`Blacklist ${this.account.name}?`)) return;
      try {
        await api(`/admin/accounts/${this.account.id}`, { method: "PATCH", body: { action } });
        store.notify(`${this.account.name}: ${action}d`);
        this.$emit("changed");
      } catch (e) { store.notify(e.message, "danger"); }
    },
  },
  template: `
    <div class="btn-group btn-group-sm">
      <button v-if="account.is_active" class="btn btn-outline-warning" @click="act('deactivate')">Deactivate</button>
      <button v-else class="btn btn-outline-success" @click="act('activate')">Activate</button>
      <button v-if="!account.is_blacklisted" class="btn btn-outline-danger" @click="act('blacklist')">Blacklist</button>
      <button v-else class="btn btn-outline-secondary" @click="act('unblacklist')">Unblacklist</button>
    </div>`,
};

const AccountState = {
  props: ["account"],
  template: `
    <span v-if="account.is_blacklisted" class="badge text-bg-danger">Blacklisted</span>
    <span v-else-if="!account.is_active" class="badge text-bg-warning">Inactive</span>
    <span v-else class="badge text-bg-success">Active</span>`,
};

// ------------------------------------------------------------------ staff
const emptyStaff = () => ({ name: "", email: "", password: "", contact: "", phone: "", experience_years: 0, specialization: "" });

export const AdminStaff = {
  components: { AccountActions, AccountState },
  data: () => ({ staff: [], q: "", form: emptyStaff(), showForm: false, formError: "" }),
  async mounted() { await this.load(); },
  methods: {
    async load() { this.staff = (await api("/admin/staff" + queryString({ q: this.q }))).staff; },
    async create() {
      this.formError = "";
      try {
        await api("/admin/staff", { method: "POST", body: this.form });
        store.notify(`Staff account created for ${this.form.email}`);
        this.form = emptyStaff(); this.showForm = false; this.load();
      } catch (e) { this.formError = e.message; }
    },
  },
  template: `
    <div class="container py-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h1 class="h3 mb-0">Trek staff</h1>
        <button class="btn btn-success" @click="showForm = !showForm">+ Add staff</button>
      </div>
      <div v-if="showForm" class="card border-0 shadow-sm mb-4"><div class="card-body">
        <h2 class="h5">New staff member</h2>
        <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
        <form class="row g-2" @submit.prevent="create">
          <div class="col-md-4"><label class="form-label small">Name</label>
            <input v-model.trim="form.name" class="form-control" required minlength="2" maxlength="120"></div>
          <div class="col-md-4"><label class="form-label small">Email (login)</label>
            <input v-model.trim="form.email" type="email" class="form-control" required></div>
          <div class="col-md-4"><label class="form-label small">Temporary password</label>
            <input v-model="form.password" type="text" class="form-control" required minlength="6"></div>
          <div class="col-md-3"><label class="form-label small">Phone</label>
            <input v-model.trim="form.phone" type="tel" class="form-control" pattern="\\+?[0-9]{7,15}" title="7-15 digits"></div>
          <div class="col-md-3"><label class="form-label small">Experience (years)</label>
            <input v-model.number="form.experience_years" type="number" min="0" max="60" class="form-control"></div>
          <div class="col-md-6"><label class="form-label small">Specialization</label>
            <input v-model.trim="form.specialization" class="form-control" maxlength="120" placeholder="e.g. High altitude, first aid"></div>
          <div class="col-12"><button class="btn btn-success mt-2">Create staff account</button></div>
        </form>
      </div></div>
      <form class="d-flex gap-2 mb-3" @submit.prevent="load">
        <input v-model.trim="q" class="form-control" placeholder="Search name or email">
        <button class="btn btn-outline-success">Search</button>
      </form>
      <div class="table-responsive">
        <table class="table bg-white shadow-sm">
          <thead><tr><th>Name</th><th>Phone</th><th>Experience</th><th>Assigned treks</th><th>Status</th><th></th></tr></thead>
          <tbody>
            <tr v-for="s in staff" :key="s.id">
              <td>{{ s.name }}<div class="small text-muted">{{ s.email }}</div></td>
              <td>{{ s.phone || '-' }}</td>
              <td>{{ s.experience_years }} yr<div class="small text-muted">{{ s.specialization }}</div></td>
              <td class="small">{{ s.assigned_treks.map(t => t.name).join(', ') || '-' }}</td>
              <td><account-state :account="s"></account-state></td>
              <td class="text-end"><account-actions :account="s" @changed="load"></account-actions></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!staff.length" class="text-muted">No staff found.</p>
      </div>
    </div>`,
};

// ------------------------------------------------------------------ users
export const AdminUsers = {
  components: { AccountActions, AccountState },
  data: () => ({ users: [], q: "" }),
  async mounted() { await this.load(); },
  methods: {
    async load() { this.users = (await api("/admin/users" + queryString({ q: this.q }))).users; },
  },
  template: `
    <div class="container py-4">
      <h1 class="h3 mb-3">Trekkers</h1>
      <form class="d-flex gap-2 mb-3" @submit.prevent="load">
        <input v-model.trim="q" class="form-control" placeholder="Search name or email">
        <button class="btn btn-outline-success">Search</button>
      </form>
      <div class="table-responsive">
        <table class="table bg-white shadow-sm">
          <thead><tr><th>Name</th><th>Contact</th><th>Joined</th><th>Bookings</th><th>Status</th><th></th></tr></thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.name }}<div class="small text-muted">{{ u.email }}</div></td>
              <td>{{ u.contact || '-' }}</td><td class="small">{{ u.created_at.slice(0, 10) }}</td>
              <td>{{ u.booking_count }}</td>
              <td><account-state :account="u"></account-state></td>
              <td class="text-end"><account-actions :account="u" @changed="load"></account-actions></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!users.length" class="text-muted">No users found.</p>
      </div>
    </div>`,
};

// ------------------------------------------------------------------ bookings
export const AdminBookings = {
  components: { StatusBadge },
  data: () => ({ bookings: [], status: "" }),
  async mounted() { await this.load(); },
  methods: {
    async load() { this.bookings = (await api("/admin/bookings" + queryString({ status: this.status }))).bookings; },
  },
  template: `
    <div class="container py-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h1 class="h3 mb-0">All bookings</h1>
        <select v-model="status" class="form-select w-auto" @change="load">
          <option value="">All</option><option value="booked">Booked</option>
          <option value="completed">Completed</option><option value="cancelled">Cancelled</option></select>
      </div>
      <div class="table-responsive">
        <table class="table bg-white shadow-sm">
          <thead><tr><th>#</th><th>Trekker</th><th>Trek</th><th>Trek dates</th><th>Booked on</th><th>People</th><th>Status</th><th>Payment</th></tr></thead>
          <tbody>
            <tr v-for="b in bookings" :key="b.id">
              <td>{{ b.id }}</td><td>{{ b.user_name }}<div class="small text-muted">{{ b.user_email }}</div></td>
              <td>{{ b.trek_name }}<div class="small text-muted">{{ b.location }}</div></td>
              <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
              <td class="small">{{ b.booking_date.slice(0, 10) }}</td><td>{{ b.participants }}</td>
              <td><status-badge :status="b.status"></status-badge></td>
              <td><status-badge :status="b.payment_status"></status-badge></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!bookings.length" class="text-muted">No bookings.</p>
      </div>
    </div>`,
};

// ------------------------------------------------------------------ search
export const AdminSearch = {
  components: { StatusBadge, AccountState },
  data: () => ({ q: "", type: "all", r: null, error: "" }),
  methods: {
    async search() {
      this.error = "";
      try { this.r = await api("/admin/search" + queryString({ q: this.q, type: this.type })); }
      catch (e) { this.error = e.message; }
    },
  },
  template: `
    <div class="container py-4">
      <h1 class="h3 mb-3">Search</h1>
      <form class="row g-2 mb-3" @submit.prevent="search">
        <div class="col-12 col-md-7"><input v-model.trim="q" class="form-control" placeholder="Name, email or location" required></div>
        <div class="col-6 col-md-3"><select v-model="type" class="form-select">
          <option value="all">Everything</option><option value="users">Users</option>
          <option value="staff">Staff</option><option value="treks">Treks</option></select></div>
        <div class="col-6 col-md-2"><button class="btn btn-success w-100">Search</button></div>
      </form>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-if="r">
        <div v-if="r.users" class="mb-4"><h2 class="h5">Users ({{ r.users.length }})</h2>
          <ul class="list-group">
            <li v-for="u in r.users" :key="u.id" class="list-group-item d-flex justify-content-between">
              <span>{{ u.name }} <span class="text-muted small">{{ u.email }}</span></span><account-state :account="u"></account-state></li>
          </ul></div>
        <div v-if="r.staff" class="mb-4"><h2 class="h5">Staff ({{ r.staff.length }})</h2>
          <ul class="list-group">
            <li v-for="s in r.staff" :key="s.id" class="list-group-item d-flex justify-content-between">
              <span>{{ s.name }} <span class="text-muted small">{{ s.email }}</span></span><account-state :account="s"></account-state></li>
          </ul></div>
        <div v-if="r.treks"><h2 class="h5">Treks ({{ r.treks.length }})</h2>
          <ul class="list-group">
            <li v-for="t in r.treks" :key="t.id" class="list-group-item d-flex justify-content-between">
              <span>{{ t.name }} <span class="text-muted small">{{ t.location }} &middot; {{ t.start_date }}</span></span>
              <status-badge :status="t.status"></status-badge></li>
          </ul></div>
      </template>
    </div>`,
};
