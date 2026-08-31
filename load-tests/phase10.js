import http from "k6/http";
import ws from "k6/ws";
import { check, fail, sleep } from "k6";
import { Rate } from "k6/metrics";

const API_BASE = (__ENV.BASE_URL || "http://127.0.0.1:8001/api").replace(/\/$/, "");
const TEST_SUITE = (__ENV.TEST_SUITE || "public-read").toLowerCase();
const LOAD_PROFILE = (__ENV.LOAD_PROFILE || "smoke").toLowerCase();
const THINK_SECONDS = Number(__ENV.THINK_SECONDS || "1");
const REMOTE_APPROVAL = "TAILORAHUB_APPROVED_LOAD_TEST";
const WRITE_APPROVAL = "TAILORAHUB_APPROVED_SYNTHETIC_WRITES";
const PAYMENT_APPROVAL = "TAILORAHUB_APPROVED_SANDBOX_PAYMENTS";
const businessErrors = new Rate("business_errors");

const suiteFunctions = {
  "public-read": "publicRead",
  "customer-read": "customerRead",
  "tailor-read": "tailorRead",
  "admin-read": "adminRead",
  auth: "authentication",
  booking: "bookingWrite",
  "tailor-stage": "tailorStageWrite",
  notifications: "notificationWrite",
  media: "mediaTransfer",
  websocket: "websocketTrack",
  payment: "sandboxPayment",
};

const profiles = {
  smoke: [
    { duration: "5s", target: 1 },
    { duration: "30s", target: 1 },
    { duration: "5s", target: 0 },
  ],
  baseline: [
    { duration: "30s", target: 50 },
    { duration: "2m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  normal: [
    { duration: "1m", target: 100 },
    { duration: "4m", target: 100 },
    { duration: "1m", target: 0 },
  ],
  growth: [
    { duration: "2m", target: 250 },
    { duration: "8m", target: 250 },
    { duration: "2m", target: 0 },
  ],
  release: [
    { duration: "3m", target: 500 },
    { duration: "12m", target: 500 },
    { duration: "3m", target: 0 },
  ],
  high: [
    { duration: "5m", target: 1000 },
    { duration: "15m", target: 1000 },
    { duration: "5m", target: 0 },
  ],
  spike: [
    { duration: "1m", target: 50 },
    { duration: "20s", target: 500 },
    { duration: "2m", target: 500 },
    { duration: "30s", target: 50 },
    { duration: "1m", target: 0 },
  ],
  soak: [
    { duration: "2m", target: Number(__ENV.SOAK_VUS || "100") },
    { duration: __ENV.SOAK_DURATION || "4h", target: Number(__ENV.SOAK_VUS || "100") },
    { duration: "2m", target: 0 },
  ],
};

if (!suiteFunctions[TEST_SUITE]) {
  throw new Error(`Unknown TEST_SUITE '${TEST_SUITE}'.`);
}
if (!profiles[LOAD_PROFILE]) {
  throw new Error(`Unknown LOAD_PROFILE '${LOAD_PROFILE}'.`);
}

const remoteTarget = !/^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:\/|$)/i.test(API_BASE);
if (remoteTarget && __ENV.PHASE10_REMOTE_APPROVAL !== REMOTE_APPROVAL) {
  throw new Error("Remote load tests require PHASE10_REMOTE_APPROVAL=TAILORAHUB_APPROVED_LOAD_TEST.");
}

const writeSuites = new Set(["booking", "tailor-stage", "notifications", "media", "payment"]);
if (writeSuites.has(TEST_SUITE) && __ENV.PHASE10_WRITE_APPROVAL !== WRITE_APPROVAL) {
  throw new Error("Write suites require PHASE10_WRITE_APPROVAL=TAILORAHUB_APPROVED_SYNTHETIC_WRITES.");
}
if (TEST_SUITE === "payment" && (__ENV.PAYMENT_PROVIDER_MODE || "").toLowerCase() !== "sandbox") {
  throw new Error("Payment load tests require PAYMENT_PROVIDER_MODE=sandbox.");
}
if (TEST_SUITE === "payment" && __ENV.PHASE10_PAYMENT_APPROVAL !== PAYMENT_APPROVAL) {
  throw new Error("Payment load tests require PHASE10_PAYMENT_APPROVAL=TAILORAHUB_APPROVED_SANDBOX_PAYMENTS.");
}

export const options = {
  discardResponseBodies: true,
  scenarios: {
    [TEST_SUITE.replace(/-/g, "_")]: {
      executor: "ramping-vus",
      exec: suiteFunctions[TEST_SUITE],
      startVUs: 0,
      stages: profiles[LOAD_PROFILE],
      gracefulRampDown: "30s",
      tags: { suite: TEST_SUITE, profile: LOAD_PROFILE },
    },
  },
  thresholds: {
    business_errors: ["rate<0.01"],
    http_req_failed: ["rate<0.01"],
    "http_req_duration{operation:read}": ["p(95)<500"],
    "http_req_duration{operation:write}": ["p(95)<1000"],
    checks: ["rate>0.99"],
    iterations: ["count>0"],
  },
};

function required(name) {
  const value = __ENV[name];
  if (!value) fail(`${name} is required for the ${TEST_SUITE} suite.`);
  return value;
}

function parseJsonEnv(name) {
  try {
    return JSON.parse(required(name));
  } catch (error) {
    fail(`${name} must contain valid JSON: ${error.message}`);
  }
}

function bearer(token) {
  return { Authorization: `Bearer ${token}` };
}

function request(method, path, body, token, name, operation = "read", captureBody = false, extraHeaders = {}) {
  const params = {
    headers: { Accept: "application/json", ...extraHeaders, ...(token ? bearer(token) : {}) },
    tags: { name, operation },
    responseType: captureBody ? "text" : "none",
    timeout: __ENV.REQUEST_TIMEOUT || "15s",
  };
  if (body !== null && body !== undefined) params.headers["Content-Type"] = "application/json";
  const response = http.request(method, `${API_BASE}${path}`, body === null || body === undefined ? null : JSON.stringify(body), params);
  const ok = check(response, { [`${name} succeeds`]: (r) => r.status >= 200 && r.status < 300 });
  businessErrors.add(!ok, { name, operation });
  return response;
}

function customerToken() {
  return required("CUSTOMER_TOKEN");
}

function pause() {
  if (THINK_SECONDS > 0) sleep(THINK_SECONDS);
}

export function publicRead() {
  request("GET", "/health", null, null, "health", "read");
  request("GET", "/tailors?limit=20&offset=0", null, null, "public-tailors", "read");
  if (__ENV.PUBLIC_TAILOR_ID) {
    request("GET", `/v1/tailors/${encodeURIComponent(__ENV.PUBLIC_TAILOR_ID)}/services?limit=20&offset=0`, null, null, "public-tailor-services", "read");
  }
  pause();
}

export function customerRead() {
  const token = customerToken();
  const query = encodeURIComponent(__ENV.SEARCH_QUERY || "blouse");
  request("GET", `/customer/tailors?q=${query}&limit=20&offset=0`, null, token, "customer-tailors", "read");
  request("GET", "/customer/favorites?limit=20&offset=0", null, token, "customer-favorites", "read");
  request("GET", "/customer/bookings?limit=20&offset=0", null, token, "customer-bookings", "read");
  if (__ENV.PUBLIC_TAILOR_ID) {
    request("GET", `/customer/tailors/${encodeURIComponent(__ENV.PUBLIC_TAILOR_ID)}`, null, token, "customer-tailor-profile", "read");
  }
  pause();
}

export function tailorRead() {
  const token = required("TAILOR_TOKEN");
  request("GET", "/tailor/dashboard?limit=20&offset=0", null, token, "tailor-dashboard", "read");
  request("GET", "/v1/tailors/me/services?limit=20&offset=0", null, token, "tailor-services", "read");
  request("GET", "/v1/tailors/me/waiting-list?limit=20&offset=0", null, token, "tailor-waiting-list", "read");
  pause();
}

export function adminRead() {
  const token = required("ADMIN_TOKEN");
  request("GET", "/admin/metrics", null, token, "admin-metrics", "read");
  request("GET", "/admin/orders?limit=20&offset=0", null, token, "admin-orders", "read");
  request("GET", "/admin/tailors?limit=20&offset=0", null, token, "admin-tailors", "read");
  request("GET", "/admin/support-tickets?limit=20&offset=0", null, token, "admin-support", "read");
  pause();
}

export function authentication() {
  const users = parseJsonEnv("AUTH_USERS_JSON");
  if (!Array.isArray(users) || users.length === 0) fail("AUTH_USERS_JSON must be a non-empty array of synthetic users.");
  const account = users[(__VU - 1) % users.length];
  const role = account.role === "tailor" ? "tailor" : "customer";
  const path = role === "tailor" ? "/v1/auth/login" : "/v1/auth/customer-login";
  const login = request("POST", path, { identifier: account.identifier, password: account.password, mode: "password" }, null, `${role}-login`, "write", true);
  if (login.status >= 200 && login.status < 300) {
    const payload = login.json();
    const refreshToken = payload.refreshToken || payload.refresh_token;
    if (refreshToken) request("POST", "/v1/auth/refresh", { refreshToken }, null, `${role}-refresh`, "write");
    else businessErrors.add(true, { name: `${role}-refresh-token-missing`, operation: "write" });
  }
  pause();
}

export function bookingWrite() {
  const payload = parseJsonEnv("BOOKING_PAYLOAD");
  const token = customerToken();
  request("POST", "/v1/bookings/preview", payload, token, "booking-preview", "write");
  const key = `${required("BOOKING_IDEMPOTENCY_PREFIX")}-${__VU}-${__ITER}`.slice(0, 100);
  const headers = { "Idempotency-Key": key };
  const first = request("POST", "/v1/bookings", { ...payload, idempotencyKey: key }, token, "booking-create", "write", true, headers);
  const second = request("POST", "/v1/bookings", { ...payload, idempotencyKey: key }, token, "booking-duplicate", "write", true, headers);
  if (first.status >= 200 && first.status < 300 && second.status >= 200 && second.status < 300) {
    const duplicate = second.json().duplicate === true;
    const ok = check(second, { "duplicate booking is deduplicated": () => duplicate });
    businessErrors.add(!ok, { name: "booking-idempotency", operation: "write" });
  }
  pause();
}

export function tailorStageWrite() {
  request("PATCH", `/v1/bookings/${encodeURIComponent(required("STAGE_BOOKING_ID"))}/stage`, parseJsonEnv("STAGE_PAYLOAD"), required("TAILOR_TOKEN"), "booking-stage", "write");
  pause();
}

export function notificationWrite() {
  const role = (__ENV.NOTIFICATION_ROLE || "customer").toLowerCase();
  const token = role === "tailor" ? required("TAILOR_TOKEN") : customerToken();
  request("POST", `/${role}/notifications/read`, {}, token, `${role}-notifications-read`, "write");
  pause();
}

export function mediaTransfer() {
  const downloadUrl = required("MEDIA_DOWNLOAD_URL");
  const read = http.get(downloadUrl, { tags: { name: "media-download", operation: "read" }, responseType: "none" });
  const readOk = check(read, { "media download succeeds": (r) => r.status >= 200 && r.status < 300 });
  businessErrors.add(!readOk, { name: "media-download", operation: "read" });
  const upload = http.put(required("MEDIA_UPLOAD_URL"), __ENV.MEDIA_UPLOAD_BODY || "tailorahub-phase10-synthetic-media", {
    headers: { "Content-Type": __ENV.MEDIA_CONTENT_TYPE || "text/plain" },
    tags: { name: "media-upload", operation: "write" },
    responseType: "none",
  });
  const uploadOk = check(upload, { "media upload succeeds": (r) => r.status >= 200 && r.status < 300 });
  businessErrors.add(!uploadOk, { name: "media-upload", operation: "write" });
  pause();
}

export function websocketTrack() {
  const bookingId = required("TRACK_BOOKING_ID");
  const ticketResponse = request("POST", `/v1/bookings/${encodeURIComponent(bookingId)}/track-ticket`, {}, customerToken(), "tracker-ticket", "write", true);
  if (ticketResponse.status < 200 || ticketResponse.status >= 300) return;
  const ticket = ticketResponse.json().ticket;
  const wsBase = (__ENV.WS_BASE_URL || API_BASE.replace(/^http/i, "ws")).replace(/\/$/, "");
  const response = ws.connect(`${wsBase}/v1/bookings/${encodeURIComponent(bookingId)}/track?ticket=${encodeURIComponent(ticket)}`, { tags: { name: "booking-websocket" } }, (socket) => {
    let pong = false;
    socket.on("open", () => socket.send("ping"));
    socket.on("message", (message) => {
      if (String(message).includes("pong")) {
        pong = true;
        socket.close();
      }
    });
    socket.setTimeout(() => {
      const ok = check(pong, { "websocket receives pong": (value) => value === true });
      businessErrors.add(!ok, { name: "booking-websocket", operation: "read" });
      socket.close();
    }, Number(__ENV.WS_SESSION_MS || "10000"));
  });
  const connected = check(response, { "websocket connects": (r) => r && r.status === 101 });
  businessErrors.add(!connected, { name: "booking-websocket", operation: "read" });
  pause();
}

export function sandboxPayment() {
  const bookingId = required("PAYMENT_BOOKING_ID");
  const action = (__ENV.PAYMENT_ACTION || "create").toLowerCase();
  if (action === "verify") {
    request("POST", `/v1/bookings/${encodeURIComponent(bookingId)}/razorpay/verify`, parseJsonEnv("PAYMENT_VERIFY_PAYLOAD"), customerToken(), "sandbox-payment-verify", "write", true);
    pause();
    return;
  }
  if (action !== "create") fail("PAYMENT_ACTION must be create or verify.");
  const key = `${required("PAYMENT_IDEMPOTENCY_PREFIX")}-${__VU}-${__ITER}`.slice(0, 100);
  request("POST", `/v1/bookings/${encodeURIComponent(bookingId)}/pay`, { ...parseJsonEnv("PAYMENT_PAYLOAD"), idempotencyKey: key }, customerToken(), "sandbox-payment", "write", true, { "Idempotency-Key": key });
  pause();
}

export function handleSummary(data) {
  const output = JSON.stringify(data, null, 2);
  const destination = __ENV.REPORT_PATH || "load-test-results/phase10-summary.json";
  return { stdout: `\nPhase 10 summary written to ${destination}\n`, [destination]: output };
}
