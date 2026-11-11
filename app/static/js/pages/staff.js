import { api } from "../api.js";
import { store } from "../store.js";
import { StatCard, StatusBadge } from "../components.js";

export const StaffDashboard = {
  components: { StatCard, StatusBadge },
  data: () => ({ d: null, error: "" }),
  async mounted() {
    try { this.d = await api("/staff/dashboard"); } catch (e) { this.error = e.message; }
  },
  template: `
    <div class="container py-4">
      <h1 class="h3 mb-3">My assigned treks</h1>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-if="d">
        <div class="row g-3 mb-4">
          <div class="col-6 col-md"><stat-card label="Assigned" :value="d.counts.assigned"></stat-card></div>
          <div class="col-6 col-md"><stat-card label="Open" :value="d.counts.open" color="success"></stat-card></div>
          <div class="col-6 col-md"><stat-card label="Ongoing" :value="d.counts.ongoing" color="primary"></stat-card></div>
          <div class="col-6 col-md"><stat-card label="Completed" :value="d.counts.completed"></stat-card></div>
          <div class="col-12 col-md"><stat-card label="Participants" :value="d.counts.participants" color="success"></stat-card></div>
        </div>
        <p v-if="!d.treks.length" class="text-muted">The admin has not assigned you any treks yet.</p>
        <div v-else class="table-responsive">
          <table class="table bg-white shadow-sm">
            <thead><tr><th>Trek</th><th>Dates</th><th>Registered</th><th>Slots left</th><th>Status</th><th></th></tr></thead>
            <tbody>
              <tr v-for="t in d.treks" :key="t.id">
                <td>{{ t.name }}<div class="small text-muted">{{ t.location }}</div></td>
                <td class="small">{{ t.start_date }} to {{ t.end_date }}</td>
                <td>{{ t.booked_count }}</td>
                <td>{{ t.available_slots }} / {{ t.total_slots }}</td>
                <td><status-badge :status="t.status"></status-badge></td>
                <td class="text-end"><router-link :to="'/staff/treks/' + t.id" class="btn btn-sm btn-success">Manage</router-link></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>`,
};

export const StaffTrek = {
  components: { StatusBadge },
  props: ["id"],
  data: () => ({ trek: null, participants: [], allowed: [], slots: 0, error: "" }),
  computed: {
    locked() { return this.trek && ["ongoing", "completed"].includes(this.trek.status); },
  },
  async mounted() { await this.load(); },
  methods: {
    async load() {
      try {
        const d = await api(`/staff/treks/${this.id}`);
        this.trek = d.trek; this.participants = d.participants; this.allowed = d.allowed_statuses;
        this.slots = d.trek.total_slots;
      } catch (e) { this.error = e.message; }
    },
    async run(request, message) {
      try { await request; store.notify(message); await this.load(); }
      catch (e) { store.notify(e.message, "danger"); }
    },
    saveSlots() {
      this.run(api(`/staff/treks/${this.id}`, { method: "PATCH", body: { total_slots: this.slots } }), "Slots updated");
    },
    setStatus(status) {
      if (status === "completed" && !confirm("Mark this trek as completed? This cannot be undone.")) return;
      this.run(api(`/staff/treks/${this.id}`, { method: "PATCH", body: { status } }), `Trek is now ${status}`);
    },
    setParticipant(b, status) {
      this.run(api(`/staff/bookings/${b.id}`, { method: "PATCH", body: { status } }), "Participant updated");
    },
  },
  template: `
    <div class="container py-4">
      <router-link to="/staff" class="small">&larr; Back</router-link>
      <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
      <template v-if="trek">
        <div class="d-flex flex-wrap align-items-center gap-2 my-2">
          <h1 class="h3 mb-0">{{ trek.name }}</h1><status-badge :status="trek.status"></status-badge>
        </div>
        <p class="text-muted">{{ trek.location }} &middot; <span class="text-capitalize">{{ trek.difficulty }}</span>
          &middot; {{ trek.start_date }} to {{ trek.end_date }}</p>

        <div class="row g-3 mb-4">
          <div class="col-md-6"><div class="card border-0 shadow-sm h-100"><div class="card-body">
            <h2 class="h6">Slots</h2>
            <p class="mb-2">{{ trek.booked_count }} booked &middot; {{ trek.available_slots }} available</p>
            <form class="input-group" @submit.prevent="saveSlots">
              <input v-model.number="slots" type="number" :min="Math.max(1, trek.booked_count)" class="form-control"
                     :disabled="locked" required aria-label="Total slots">
              <button class="btn btn-success" :disabled="locked">Update total</button>
            </form>
          </div></div></div>
          <div class="col-md-6"><div class="card border-0 shadow-sm h-100"><div class="card-body">
            <h2 class="h6">Status</h2>
            <p v-if="!allowed.length" class="text-muted mb-0">
              {{ trek.status === 'pending' ? 'Waiting for admin approval.' : 'No further changes possible.' }}</p>
            <div class="d-flex flex-wrap gap-2">
              <button v-for="s in allowed" :key="s" class="btn btn-outline-primary text-capitalize" @click="setStatus(s)">
                {{ s === 'ongoing' ? 'Mark started' : s === 'completed' ? 'Mark completed' : 'Set ' + s }}</button>
            </div>
          </div></div></div>
        </div>

        <h2 class="h5">Participants ({{ participants.length }})</h2>
        <p v-if="!participants.length" class="text-muted">No bookings yet.</p>
        <div v-else class="table-responsive">
          <table class="table bg-white shadow-sm">
            <thead><tr><th>Name</th><th>Contact</th><th>People</th><th>Booked on</th><th>Status</th><th>Payment</th><th></th></tr></thead>
            <tbody>
              <tr v-for="b in participants" :key="b.id">
                <td>{{ b.user_name }}<div class="small text-muted">{{ b.user_email }}</div></td>
                <td>{{ b.user_contact || '-' }}</td><td>{{ b.participants }}</td>
                <td class="small">{{ b.booking_date.slice(0, 10) }}</td>
                <td><status-badge :status="b.status"></status-badge></td>
                <td><status-badge :status="b.payment_status"></status-badge></td>
                <td class="text-end">
                  <template v-if="!locked">
                    <button v-if="b.status === 'booked'" class="btn btn-sm btn-outline-danger" @click="setParticipant(b, 'cancelled')">Remove</button>
                    <button v-else-if="b.status === 'cancelled'" class="btn btn-sm btn-outline-success" @click="setParticipant(b, 'booked')">Restore</button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>`,
};
