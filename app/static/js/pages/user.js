import { api } from "../api.js";
import { store } from "../store.js";
import { StatCard, StatusBadge } from "../components.js";

export const UserDashboard = {
  components: { StatCard, StatusBadge },
  data: () => ({ store, d: null, error: "", exporting: false }),
  async mounted() { await this.load(); },
  methods: {
    async load() {
      try { this.d = await api("/user/dashboard"); } catch (e) { this.error = e.message; }
    },
    async cancel(b) {
      if (!confirm(`Cancel your booking for ${b.trek_name}?`)) return;
      try { await api(`/bookings/${b.id}/cancel`, { method: "PATCH" }); store.notify("Booking cancelled", "warning"); this.load(); }
      catch (e) { store.notify(e.message, "danger"); }
    },
    async pay(b) {
      try { await api(`/bookings/${b.id}/pay`, { method: "POST" }); store.notify("Payment successful (simulated)"); this.load(); }
      catch (e) { store.notify(e.message, "danger"); }
    },
    // Calls YOUR Celery-backed endpoint (POST /api/user/export). See README.
    async exportCsv() {
      this.exporting = true;
      try {
        const res = await api("/user/export", { method: "POST" });
        store.notify(res.message || "Export started. You will be alerted when the CSV is ready.");
      } catch (e) {
        store.notify(e.status === 404 ? "CSV export job is not implemented yet." : e.message, "warning");
      }
      this.exporting = false;
    },
  },
  template: `
    <div class="container py-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h1 class="h3 mb-0">Hello, {{ store.user.name }}</h1>
        <button class="btn btn-outline-success" :disabled="exporting" @click="exportCsv">
          {{ exporting ? "Starting export..." : "Export history (CSV)" }}</button>
      </div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-if="d">
        <div class="row g-3 mb-4">
          <div class="col-6 col-md-3"><stat-card label="Total bookings" :value="d.counts.total"></stat-card></div>
          <div class="col-6 col-md-3"><stat-card label="Active" :value="d.counts.active" color="success"></stat-card></div>
          <div class="col-6 col-md-3"><stat-card label="Completed" :value="d.counts.completed" color="primary"></stat-card></div>
          <div class="col-6 col-md-3"><stat-card label="Cancelled" :value="d.counts.cancelled" color="danger"></stat-card></div>
        </div>

        <h2 class="h5">My upcoming treks</h2>
        <p v-if="!d.upcoming.length" class="text-muted">No upcoming bookings. <router-link to="/treks">Find a trek</router-link></p>
        <div v-else class="table-responsive mb-4">
          <table class="table bg-white shadow-sm">
            <thead><tr><th>Trek</th><th>Dates</th><th>People</th><th>Trek status</th><th>Payment</th><th></th></tr></thead>
            <tbody>
              <tr v-for="b in d.upcoming" :key="b.id">
                <td>{{ b.trek_name }}<div class="small text-muted">{{ b.location }}</div></td>
                <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
                <td>{{ b.participants }}</td>
                <td><status-badge :status="b.trek_status"></status-badge></td>
                <td><status-badge :status="b.payment_status"></status-badge></td>
                <td class="text-end text-nowrap">
                  <button v-if="b.payment_status === 'pending'" class="btn btn-sm btn-success me-1" @click="pay(b)">Pay</button>
                  <button v-if="b.trek_status !== 'ongoing'" class="btn btn-sm btn-outline-danger" @click="cancel(b)">Cancel</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 class="h5">Available treks</h2>
        <div class="row g-3">
          <div v-for="t in d.available_treks" :key="t.id" class="col-12 col-md-6 col-lg-4">
            <div class="card border-0 shadow-sm h-100"><div class="card-body">
              <div class="d-flex justify-content-between"><strong>{{ t.name }}</strong><status-badge :status="t.status"></status-badge></div>
              <div class="small text-muted">{{ t.location }} &middot; {{ t.duration_days }} day(s) &middot; {{ t.start_date }}</div>
              <div class="small">Slots left: {{ t.available_slots }}</div>
            </div></div>
          </div>
        </div>
        <router-link to="/treks" class="btn btn-success mt-3">Search &amp; book treks</router-link>
      </template>
    </div>`,
};

export const UserHistory = {
  components: { StatusBadge },
  data: () => ({ bookings: [], status: "", error: "" }),
  async mounted() { await this.load(); },
  methods: {
    async load() {
      try { this.bookings = (await api("/bookings" + (this.status ? "?status=" + this.status : ""))).bookings; }
      catch (e) { this.error = e.message; }
    },
  },
  template: `
    <div class="container py-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h1 class="h3 mb-0">Trekking history</h1>
        <select v-model="status" class="form-select w-auto" @change="load">
          <option value="">All</option><option value="booked">Booked</option>
          <option value="completed">Completed</option><option value="cancelled">Cancelled</option>
        </select>
      </div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <p v-if="!bookings.length" class="text-muted">Nothing here yet.</p>
      <div v-else class="table-responsive">
        <table class="table bg-white shadow-sm">
          <thead><tr><th>#</th><th>Trek</th><th>Location</th><th>Trek dates</th><th>Booked on</th><th>People</th><th>Status</th><th>Payment</th></tr></thead>
          <tbody>
            <tr v-for="b in bookings" :key="b.id">
              <td>{{ b.id }}</td><td>{{ b.trek_name }}</td><td>{{ b.location }}</td>
              <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
              <td class="small">{{ b.booking_date.slice(0, 10) }}</td><td>{{ b.participants }}</td>
              <td><status-badge :status="b.status"></status-badge></td>
              <td><status-badge :status="b.payment_status"></status-badge></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>`,
};

export const ProfilePage = {
  data: () => ({ f: { name: "", contact: "" }, email: "", error: "", busy: false }),
  async mounted() {
    const { user } = await api("/user/profile");
    this.f = { name: user.name, contact: user.contact || "" };
    this.email = user.email;
  },
  methods: {
    async save() {
      this.error = ""; this.busy = true;
      try {
        const { user } = await api("/user/profile", { method: "PUT", body: this.f });
        store.user.name = user.name;
        store.notify("Profile updated");
      } catch (e) { this.error = e.message; }
      this.busy = false;
    },
  },
  template: `
    <div class="container py-4" style="max-width: 520px">
      <h1 class="h3 mb-3">My profile</h1>
      <div class="card border-0 shadow-sm"><div class="card-body">
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <form @submit.prevent="save">
          <div class="mb-3"><label class="form-label">Email</label>
            <input :value="email" class="form-control" disabled></div>
          <div class="mb-3"><label class="form-label">Name</label>
            <input v-model.trim="f.name" class="form-control" required minlength="2" maxlength="120"></div>
          <div class="mb-3"><label class="form-label">Contact</label>
            <input v-model.trim="f.contact" type="tel" class="form-control" pattern="\\+?[0-9]{7,15}" title="7-15 digits"></div>
          <button class="btn btn-success" :disabled="busy">Save</button>
        </form>
      </div></div>
    </div>`,
};
