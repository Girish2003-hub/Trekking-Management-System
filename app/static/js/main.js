// Entry point: builds the router, guards routes by role, mounts the app.
import { store, homeFor } from "./store.js";
import { AppNavbar, FlashMessage } from "./components.js";
import { HomePage, LoginPage, RegisterPage, TrekBrowse, NotFoundPage } from "./pages/public.js";
import { UserDashboard, UserHistory, ProfilePage } from "./pages/user.js";
import { StaffDashboard, StaffTrek } from "./pages/staff.js";
import {
  AdminDashboard, AdminTreks, AdminStaff, AdminUsers, AdminBookings, AdminSearch,
} from "./pages/admin.js";

const routes = [
  { path: "/", component: HomePage },
  { path: "/treks", component: TrekBrowse },
  { path: "/login", component: LoginPage, meta: { guestOnly: true } },
  { path: "/register", component: RegisterPage, meta: { guestOnly: true } },

  { path: "/dashboard", component: UserDashboard, meta: { roles: ["user"] } },
  { path: "/history", component: UserHistory, meta: { roles: ["user"] } },
  { path: "/profile", component: ProfilePage, meta: { roles: ["user", "staff", "admin"] } },

  { path: "/staff", component: StaffDashboard, meta: { roles: ["staff"] } },
  { path: "/staff/treks/:id", component: StaffTrek, props: true, meta: { roles: ["staff"] } },

  { path: "/admin", component: AdminDashboard, meta: { roles: ["admin"] } },
  { path: "/admin/treks", component: AdminTreks, meta: { roles: ["admin"] } },
  { path: "/admin/staff", component: AdminStaff, meta: { roles: ["admin"] } },
  { path: "/admin/users", component: AdminUsers, meta: { roles: ["admin"] } },
  { path: "/admin/bookings", component: AdminBookings, meta: { roles: ["admin"] } },
  { path: "/admin/search", component: AdminSearch, meta: { roles: ["admin"] } },

  { path: "/:pathMatch(.*)*", component: NotFoundPage },
];

const router = VueRouter.createRouter({
  history: VueRouter.createWebHistory(),
  routes,
});

// Runs before every page change. This is only for UX - the real security
// check is @role_required on the Flask side.
router.beforeEach(async (to) => {
  const user = await store.loadUser();
  if (to.meta.guestOnly && user) return homeFor(user);
  if (to.meta.roles) {
    if (!user) return { path: "/login", query: { next: to.fullPath } };
    if (!to.meta.roles.includes(user.role)) return homeFor(user);
  }
  return true;
});

const App = {
  components: { AppNavbar, FlashMessage },
  template: `
    <app-navbar></app-navbar>
    <flash-message></flash-message>
    <main><router-view :key="$route.fullPath"></router-view></main>
    <footer class="text-center text-muted small py-4">Trekking Management Application &middot; V2</footer>`,
};

Vue.createApp(App).use(router).mount("#app");
