const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:9000/api").replace(/\/+$/, "");
const API_ORIGIN = API_BASE.replace(/\/api$/, "");
const SESSION_STORAGE_VERSION = "2026-08-12-session-referral-v2";
export const SESSION_TIMEOUT_MS = 5 * 60 * 1000;
const LAST_ACTIVE_KEY = "tl_last_active_at";
const AUTH_STORAGE_KEYS = ["tl_token", "tl_admin_token", "tl_role", "tl_refresh_token", LAST_ACTIVE_KEY];

function removeAuthKeys(storage) {
  AUTH_STORAGE_KEYS.forEach((key) => storage.removeItem(key));
}

if (localStorage.getItem("tl_session_storage_version") !== SESSION_STORAGE_VERSION) {
  removeAuthKeys(localStorage);
  localStorage.setItem("tl_session_storage_version", SESSION_STORAGE_VERSION);
}

removeAuthKeys(localStorage);

let token = sessionStorage.getItem("tl_token") || "";
let role = sessionStorage.getItem("tl_role") || "";
let refreshToken = sessionStorage.getItem("tl_refresh_token") || "";
let refreshInFlight = null;
let sessionClearNotified = false;

export function setSession(nextToken, nextRole, nextRefreshToken = "") {
  token = nextToken || "";
  role = nextRole || "";
  refreshToken = nextRefreshToken || "";
  if (token) sessionClearNotified = false;
  removeAuthKeys(localStorage);
  if (token) sessionStorage.setItem("tl_token", token);
  else sessionStorage.removeItem("tl_token");
  if (role) sessionStorage.setItem("tl_role", role);
  else sessionStorage.removeItem("tl_role");
  if (refreshToken) sessionStorage.setItem("tl_refresh_token", refreshToken);
  else sessionStorage.removeItem("tl_refresh_token");
  sessionStorage.removeItem("tl_admin_token");
  if (token) markSessionActive();
  else sessionStorage.removeItem(LAST_ACTIVE_KEY);
}

export function clearSession() {
  setSession("", "");
  if (!sessionClearNotified) {
    sessionClearNotified = true;
    window.dispatchEvent(new Event("tailorahub:session-cleared"));
  }
}

export function getToken() {
  return token;
}

export function getRole() {
  return role;
}

export function getRefreshToken() {
  return refreshToken;
}

export function markSessionActive(now = Date.now()) {
  if (!token) return;
  sessionStorage.setItem(LAST_ACTIVE_KEY, String(now));
}

export function getSessionLastActive() {
  const value = Number(sessionStorage.getItem(LAST_ACTIVE_KEY) || 0);
  return Number.isFinite(value) ? value : 0;
}

export function isSessionExpired(now = Date.now()) {
  if (!token) return false;
  const lastActive = getSessionLastActive();
  if (!lastActive) {
    return true;
  }
  return now - lastActive > SESSION_TIMEOUT_MS;
}

export function hasValidStoredSession() {
  if (!token || !role) return false;
  if (isSessionExpired()) {
    clearSession();
    return false;
  }
  markSessionActive();
  return true;
}

export function assetUrl(path) {
  if (!path) return "";
  if (/^(data:|https?:\/\/)/.test(path)) return path;
  return path.startsWith("/") ? API_ORIGIN + path : path;
}

async function refreshAccessToken() {
  if (!refreshToken) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const res = await fetch(API_BASE + "/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) return false;
      setSession(data.token || data.access_token, data.role || role, data.refreshToken || data.refresh_token || refreshToken);
      return true;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function fieldLabel(field) {
  const labels = {
    title: "Offer title",
    body: "Offer details",
    discount: "Discount / label",
    expiresAt: "Valid until",
    expires_at: "Valid until",
    otp: "OTP",
    trackerStage: "Order status",
    tracker_stage: "Order status",
  };
  return labels[field] || String(field || "This field").replace(/_/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2");
}

function formatValidationIssue(issue) {
  if (!issue || typeof issue !== "object") return String(issue || "Please check the highlighted field.");
  const loc = Array.isArray(issue.loc) ? issue.loc.filter((part) => part !== "body") : [];
  const field = fieldLabel(loc[loc.length - 1]);
  const type = String(issue.type || "");
  const msg = String(issue.msg || "Please check this value.");
  const input = issue.input;
  const minLength = issue.ctx?.min_length;
  const maxLength = issue.ctx?.max_length;
  if (type.includes("missing")) return `${field} is required. Please enter a value.`;
  if (type.includes("string_too_short")) {
    const length = typeof input === "string" ? input.trim().length : 0;
    return `${field} is too short. You entered ${length} character${length === 1 ? "" : "s"}; minimum required is ${minLength || "more"}.`;
  }
  if (type.includes("string_too_long")) return `${field} is too long. Maximum allowed is ${maxLength || "less"} characters.`;
  if (type.includes("date") || type.includes("datetime")) return `${field} has an invalid date. Please choose a valid date.`;
  if (type.includes("int") || type.includes("float") || type.includes("decimal")) return `${field} must be a valid number.`;
  return `${field} is invalid. ${msg}`;
}

function formatApiError(data, fallback) {
  const detail = data?.detail ?? data?.error ?? data?.message;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(formatValidationIssue).join(" ");
  if (typeof detail === "object") {
    if (typeof detail.message === "string") return detail.message;
    if (typeof detail.error === "string") return detail.error;
    return Object.entries(detail)
      .map(([key, value]) => `${fieldLabel(key)}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
      .join(" ");
  }
  return String(detail || fallback);
}

async function request(path, options = {}, retried = false) {
  if (!path.includes("/auth/refresh")) {
    if (isSessionExpired()) {
      clearSession();
      throw new Error("Session expired. Please log in again.");
    }
  }
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API_BASE + path, { ...options, headers });
  const data = await res.json().catch(() => null);
  if (res.status === 401 && refreshToken && !retried && !path.includes("/auth/refresh")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request(path, options, true);
    clearSession();
  }
  if (res.status === 401 && token) clearSession();
  if (!res.ok) throw new Error(formatApiError(data, `Request failed (${res.status})`));
  return data;
}

async function requestText(path, options = {}, retried = false) {
  if (!path.includes("/auth/refresh")) {
    if (isSessionExpired()) {
      clearSession();
      throw new Error("Session expired. Please log in again.");
    }
  }
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API_BASE + path, { ...options, headers });
  const text = await res.text();
  if (res.status === 401 && refreshToken && !retried && !path.includes("/auth/refresh")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return requestText(path, options, true);
    clearSession();
  }
  if (res.status === 401 && token) clearSession();
  if (!res.ok) {
    let message = text;
    try {
      const data = JSON.parse(text);
      message = formatApiError(data, message);
    } catch {}
    throw new Error(message || `Request failed (${res.status})`);
  }
  return text;
}

function qs(params) {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, value);
  });
  const out = search.toString();
  return out ? `?${out}` : "";
}

export const api = {
  base: API_BASE,
  login: (roleName, identifier, password) => request("/auth/login", { method: "POST", body: JSON.stringify({ role: roleName, identifier, password }) }),
  adminLogin: (username, password) => request("/auth/admin/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  requestOtp: (email) => request("/auth/otp/request", { method: "POST", body: JSON.stringify({ email }) }),
  verifyOtp: (email, otp) => request("/auth/otp/verify", { method: "POST", body: JSON.stringify({ email, otp }) }),
  register: (payload) => request("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  tailorV1Login: (payload) => request("/v1/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  customerV1Login: (payload) => request("/v1/auth/customer-login", { method: "POST", body: JSON.stringify(payload) }),
  tailorForgotPassword: (identifier) => request("/v1/auth/forgot-password", { method: "POST", body: JSON.stringify({ identifier }) }),
  tailorResetPassword: (payload) => request("/v1/auth/reset-password", { method: "POST", body: JSON.stringify(payload) }),
  customerForgotPassword: (identifier) => request("/v1/auth/customer-forgot-password", { method: "POST", body: JSON.stringify({ identifier }) }),
  customerResetPassword: (payload) => request("/v1/auth/customer-reset-password", { method: "POST", body: JSON.stringify(payload) }),
  refreshSession: (refreshTokenValue = refreshToken) => request("/v1/auth/refresh", { method: "POST", body: JSON.stringify({ refreshToken: refreshTokenValue }) }),
  refreshLegacySession: (refreshTokenValue = refreshToken) => request("/auth/refresh", { method: "POST", body: JSON.stringify({ refreshToken: refreshTokenValue }) }),
  registerTailor: (payload) => request("/v1/tailors/register", { method: "POST", body: JSON.stringify(payload) }),
  registerCustomer: (payload) => request("/v1/customers/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/me"),
  reference: () => request("/reference"),

  // Purpose-scoped OTP (registration_phone / registration_email / login / forgot_password / delivery)
  sendPurposeOtp: (target, purpose) => request("/v1/otp/send", { method: "POST", body: JSON.stringify({ target, purpose }) }),
  verifyPurposeOtp: (target, purpose, otp) => request("/v1/otp/verify", { method: "POST", body: JSON.stringify({ target, purpose, otp }) }),
  checkAvailability: (field, value) => request("/v1/tailors/check-availability", { method: "POST", body: JSON.stringify({ field, value }) }),
  checkCustomerAvailability: (field, value) => request("/v1/customers/check-availability", { method: "POST", body: JSON.stringify({ field, value }) }),
  verifyTailorAadhaar: (payload) => request("/v1/tailors/verify-aadhaar", { method: "POST", body: JSON.stringify(payload) }),
  setV1TailorLocation: (payload) => request("/v1/tailors/me/location", { method: "POST", body: JSON.stringify(payload) }),
  updateV1TailorLocation: (payload) => request("/v1/tailors/me/location", { method: "PATCH", body: JSON.stringify(payload) }),
  walletMe: () => request("/v1/wallet/me"),
  setWalletUpi: (upiId) => request("/v1/wallet/set-upi", { method: "POST", body: JSON.stringify({ upi_id: upiId }) }),
  sendWithdrawOtp: () => request("/v1/wallet/withdraw/send-otp", { method: "POST" }),
  withdrawWallet: (payload) => request("/v1/wallet/withdraw", { method: "POST", body: JSON.stringify(payload) }),
  payWalletQr: (payload) => request("/v1/payments/pay", { method: "POST", body: JSON.stringify(payload) }),
  myReferralCode: () => request("/v1/referrals/my-code"),
  myReferralCount: () => request("/v1/referrals/my-count"),
  adminReferralTree: (tailorId) => request(`/v1/admin/referrals/tree/${encodeURIComponent(tailorId)}`),
  adminCustomerReferralTree: (customerId) => request(`/v1/admin/customer-referrals/tree/${encodeURIComponent(customerId)}`),
  adminDisputes: () => request("/v1/admin/disputes"),
  patchAdminDispute: (id, payload) => request(`/v1/admin/disputes/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  adminPaymentIntents: () => request("/v1/admin/payment-intents"),
  verifyPaymentIntent: (id, payload) => request(`/v1/admin/payment-intents/${encodeURIComponent(id)}/verify`, { method: "POST", body: JSON.stringify(payload) }),
  rejectPaymentIntent: (id, payload) => request(`/v1/admin/payment-intents/${encodeURIComponent(id)}/reject`, { method: "POST", body: JSON.stringify(payload || {}) }),
  adminWithdrawalRequests: () => request("/v1/admin/withdrawal-requests"),
  approveWithdrawalRequest: (id, payload) => request(`/v1/admin/withdrawal-requests/${encodeURIComponent(id)}/approve`, { method: "POST", body: JSON.stringify(payload || {}) }),
  rejectWithdrawalRequest: (id, payload) => request(`/v1/admin/withdrawal-requests/${encodeURIComponent(id)}/reject`, { method: "POST", body: JSON.stringify(payload || {}) }),
  adminFinanceSettings: () => request("/v1/admin/finance/settings"),
  updateAdminFinanceSettings: (payload) => request("/v1/admin/finance/settings", { method: "PATCH", body: JSON.stringify(payload) }),
  adminFinanceWallet: (params) => request(`/v1/admin/finance/wallet${qs(params)}`),
  exportAdminFinanceWallet: (params) => requestText(`/v1/admin/finance/wallet/export${qs(params)}`),
  tailorProfile: () => request("/tailor/me"),
  updateTailorProfile: (payload) => request("/tailor/me", { method: "PATCH", body: JSON.stringify(payload) }),
  setTailorLocation: (payload) => request("/tailor/me/location", { method: "POST", body: JSON.stringify(payload) }),
  updateTailorLocation: (payload) => request("/tailor/me/location", { method: "PATCH", body: JSON.stringify(payload) }),
  myServices: () => request("/v1/tailors/me/services"),
  createService: (payload) => request("/v1/tailors/me/services", { method: "POST", body: JSON.stringify(payload) }),
  updateService: (id, payload) => request(`/v1/tailors/me/services/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteService: (id) => request(`/v1/tailors/me/services/${encodeURIComponent(id)}`, { method: "DELETE" }),
  publicTailorServices: (tailorId) => request(`/v1/tailors/${encodeURIComponent(tailorId)}/services`),

  metrics: () => request("/admin/metrics"),
  customers: () => request("/admin/customers"),
  tailors: () => request("/admin/tailors"),
  bookingRequests: () => request("/admin/booking-requests"),
  orders: () => request("/admin/orders"),
  payments: () => request("/admin/payments"),
  reviews: () => request("/admin/reviews"),
  complaints: () => request("/admin/complaints"),
  supportTickets: () => request("/admin/support-tickets"),
  audit: () => request("/admin/audit"),
  patchCustomer: (id, payload) => request(`/admin/customers/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  customerDeleteCheck: (id) => request(`/admin/customers/${id}/delete-check`),
  deleteCustomer: (id, reason) => request(`/admin/customers/${id}?reason=${encodeURIComponent(reason || "Admin deletion")}`, { method: "DELETE" }),
  approveTailor: (id) => request(`/admin/tailors/${id}/approve`, { method: "POST" }),
  rejectTailor: (id, reason) => request(`/admin/tailors/${id}/reject?reason=${encodeURIComponent(reason || "Documents incomplete")}`, { method: "POST" }),
  patchTailor: (id, payload) => request(`/admin/tailors/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  tailorDeleteCheck: (id) => request(`/admin/tailors/${id}/delete-check`),
  deleteTailor: (id, reason) => request(`/admin/tailors/${id}?reason=${encodeURIComponent(reason || "Admin deletion")}`, { method: "DELETE" }),
  patchOrder: (id, payload) => request(`/admin/orders/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  cancelOrder: (id, reason) => request(`/admin/orders/${id}/cancel?reason=${encodeURIComponent(reason || "Cancelled by admin")}`, { method: "POST" }),
  patchReview: (id, payload) => request(`/admin/reviews/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  patchComplaint: (id, payload) => request(`/admin/complaints/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  patchSupportTicket: (id, payload) => request(`/admin/support-tickets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  replySupportTicket: (id, body) => request(`/admin/support-tickets/${id}/messages`, { method: "POST", body: JSON.stringify({ body }) }),

  customerTailors: (params) => request(`/customer/tailors${qs(params)}`),
  nearbyTailors: (params) => request(`/v1/customers/nearby-tailors${qs(params)}`),
  customerTailor: (id) => request(`/customer/tailors/${id}`),
  customerFavorites: () => request("/customer/favorites"),
  favoriteTailor: (id) => request(`/customer/tailors/${id}/favorite`, { method: "POST" }),
  unfavoriteTailor: (id) => request(`/customer/tailors/${id}/favorite`, { method: "DELETE" }),
  followTailor: (id) => request(`/customer/tailors/${id}/follow`, { method: "POST" }),
  unfollowTailor: (id) => request(`/customer/tailors/${id}/follow`, { method: "DELETE" }),
  createBooking: (payload) => request("/v1/bookings", { method: "POST", body: JSON.stringify(payload) }),
  createLegacyBooking: (payload) => request("/customer/booking-requests", { method: "POST", body: JSON.stringify(payload) }),
  customerBookings: () => request("/customer/bookings"),
  markCustomerNotificationsRead: () => request("/customer/notifications/read", { method: "POST" }),
  customerWallet: () => request("/v1/customers/me/wallet"),
  customerReferralCode: () => request("/v1/customers/me/referral-code"),
  customerReferralCount: () => request("/v1/customers/me/referral-count"),
  customerSupportTickets: () => request("/customer/support/tickets"),
  createCustomerSupportTicket: (payload) => request("/customer/support/tickets", { method: "POST", body: JSON.stringify(payload) }),
  customerSupportTicket: (id) => request(`/customer/support/tickets/${id}`),
  replyCustomerSupportTicket: (id, body) => request(`/customer/support/tickets/${id}/messages`, { method: "POST", body: JSON.stringify({ body }) }),
  closeCustomerSupportTicket: (id) => request(`/customer/support/tickets/${id}/close`, { method: "POST" }),
  payOrder: (id, payload) => request(`/customer/orders/${id}/pay`, { method: "POST", body: JSON.stringify(payload || {}) }),
  payBooking: (id, payload) => request(`/v1/bookings/${encodeURIComponent(id)}/pay`, { method: "POST", body: JSON.stringify(payload || {}) }),
  bookingPaymentBreakdown: (id) => request(`/v1/bookings/${encodeURIComponent(id)}/payment-breakdown`),
  reviewOrder: (id, payload) => request(`/customer/orders/${id}/review`, { method: "POST", body: JSON.stringify(payload) }),
  orderTimeline: (id) => request(`/customer/orders/${id}/timeline`),
  bookingStatus: (id) => request(`/v1/bookings/${encodeURIComponent(id)}/status`),
  updateCustomerBooking: (id, payload) => request(`/v1/bookings/${encodeURIComponent(id)}/customer-update`, { method: "PATCH", body: JSON.stringify(payload) }),
  cancelCustomerBooking: (id, payload) => request(`/v1/bookings/${encodeURIComponent(id)}/customer-cancel`, { method: "POST", body: JSON.stringify(payload || {}) }),
  raiseDispute: (id, payload) => request(`/v1/bookings/${encodeURIComponent(id)}/raise-dispute`, { method: "POST", body: JSON.stringify(payload) }),

  tailorDashboard: () => request("/tailor/dashboard"),
  tailorWaitingList: () => request("/v1/tailors/me/waiting-list"),
  tailorConfirmBooking: (id) => request(`/v1/bookings/${encodeURIComponent(id)}/tailor-confirm`, { method: "POST" }),
  measurementDone: (id) => request(`/v1/bookings/${encodeURIComponent(id)}/measurement-done`, { method: "POST" }),
  updateBookingStage: (id, payload) => request(`/v1/bookings/${encodeURIComponent(id)}/stage`, { method: "PATCH", body: JSON.stringify(payload) }),
  tailorSupportTickets: () => request("/tailor/support/tickets"),
  createTailorSupportTicket: (payload) => request("/tailor/support/tickets", { method: "POST", body: JSON.stringify(payload) }),
  tailorSupportTicket: (id) => request(`/tailor/support/tickets/${id}`),
  replyTailorSupportTicket: (id, body) => request(`/tailor/support/tickets/${id}/messages`, { method: "POST", body: JSON.stringify({ body }) }),
  closeTailorSupportTicket: (id) => request(`/tailor/support/tickets/${id}/close`, { method: "POST" }),
  updateAvailability: (payload) => request("/tailor/availability", { method: "PATCH", body: JSON.stringify(payload) }),
  uploadTailorProfileImage: (payload) => request("/tailor/profile-image", { method: "POST", body: JSON.stringify(payload) }),
  deleteTailorProfileImage: () => request("/tailor/profile-image", { method: "DELETE" }),
  uploadTailorMedia: (payload) => request("/tailor/media", { method: "POST", body: JSON.stringify(payload) }),
  deleteTailorMedia: (index) => request(`/tailor/media/${index}`, { method: "DELETE" }),
  createTailorOffer: (payload) => request("/tailor/offers", { method: "POST", body: JSON.stringify(payload) }),
  deleteTailorOffer: (id) => request(`/tailor/offers/${id}`, { method: "DELETE" }),
  markTailorNotificationsRead: () => request("/tailor/notifications/read", { method: "POST" }),
  acceptRequest: (id) => request(`/tailor/requests/${id}/accept`, { method: "POST" }),
  rejectRequest: (id, reason) => request(`/tailor/requests/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  updateTailorOrder: (id, payload) => request(`/tailor/orders/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  addCharge: (id, payload) => request(`/tailor/orders/${id}/charges`, { method: "POST", body: JSON.stringify(payload) }),
  deliveryOtp: (id) => request(`/tailor/orders/${id}/delivery-otp`, { method: "POST" }),
  sendDeliveryOtp: (id) => request(`/v1/bookings/${encodeURIComponent(id)}/send-delivery-otp`, { method: "POST" }),
  verifyDelivery: (id, otp) => request(`/tailor/orders/${id}/verify-delivery`, { method: "POST", body: JSON.stringify({ otp }) }),
  verifyDeliveryOtp: (id, otp) => request(`/v1/bookings/${encodeURIComponent(id)}/verify-delivery-otp`, { method: "POST", body: JSON.stringify({ otp }) }),
};
