import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import {
  getFirestore,
  collection,
  doc,
  onSnapshot,
  setDoc,
  deleteDoc,
  writeBatch,
  runTransaction,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";

/* --------------------------------------------------------------- config -- */
const firebaseConfig = {
  apiKey: "AIzaSyA_lq4rdu5-nvCCVEJuYUBaL3lv2ZZS4Wc",
  authDomain: "loanstatus-bc769.firebaseapp.com",
  projectId: "loanstatus-bc769",
  storageBucket: "loanstatus-bc769.firebasestorage.app",
  messagingSenderId: "380984135908",
  appId: "1:380984135908:web:a32ca743cd0c21ff8b5cf1",
};

let fbApp;
let auth;
let db;
try {
  fbApp = initializeApp(firebaseConfig);
  auth = getAuth(fbApp);
  db = getFirestore(fbApp);
} catch (error) {
  console.error("Firebase init failed", error);
  const boot = document.getElementById("boot");
  if (boot) {
    boot.innerHTML =
      '<div class="boot-mark">LT</div><p>Firebase tidak dapat dimulakan. Semak sambungan internet dan cuba muat semula.</p>';
  }
}

/* ------------------------------------------------------------ constants -- */
const STATUSES = ["Baru", "Dalam Proses", "Hantar Bank", "Diluluskan", "Ditolak", "Selesai"];
const PROCESS = new Set(["Baru", "Dalam Proses", "Hantar Bank"]);
const APPROVED = new Set(["Diluluskan", "Selesai"]);
const REJECTED = new Set(["Ditolak"]);
const BANKS = [
  "Maybank", "CIMB Bank", "Public Bank", "RHB Bank", "Hong Leong Bank",
  "AmBank", "Bank Islam", "Bank Rakyat", "BSN", "Affin Bank", "Alliance Bank",
  "MBSB Bank", "Bank Muamalat", "Agrobank", "OCBC Bank", "UOB Malaysia",
  "HSBC Malaysia", "Standard Chartered", "AEON Bank", "GXBank", "Boost Bank",
];
const STATUS_CLASS = {
  "Baru": "status-baru",
  "Dalam Proses": "status-proses",
  "Hantar Bank": "status-hantar",
  "Diluluskan": "status-lulus",
  "Ditolak": "status-tolak",
  "Selesai": "status-selesai",
};
const STATUS_BORDER = {
  "Baru": "status-baru-border",
  "Dalam Proses": "status-proses-border",
  "Hantar Bank": "status-hantar-border",
  "Diluluskan": "status-lulus-border",
  "Ditolak": "status-tolak-border",
  "Selesai": "status-selesai-border",
};
const STATUS_DOT = {
  "Baru": "#9AA9BC",
  "Dalam Proses": "#FBBF24",
  "Hantar Bank": "#818CF8",
  "Diluluskan": "#34D399",
  "Ditolak": "#FB7185",
  "Selesai": "#38BDF8",
};
const AVATAR_PALETTE = [
  ["#DBEAFE", "#1D4ED8"],
  ["#D1FAE5", "#047857"],
  ["#FEF3C7", "#B45309"],
  ["#FCE7F3", "#BE185D"],
  ["#E0E7FF", "#4338CA"],
  ["#CFFAFE", "#0E7490"],
  ["#F3E8FF", "#7E22CE"],
];
const MONTHS_SHORT = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun",
  "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"];
const MONTHS_LONG = ["Januari", "Februari", "Mac", "April", "Mei", "Jun",
  "Julai", "Ogos", "September", "Oktober", "November", "Disember"];
const DAYS_LONG = ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"];

/* ------------------------------------------------------------------ dom -- */
const $ = (selector, root = document) => root.querySelector(selector);
const el = {
  boot: $("#boot"),
  authScreen: $("#auth-screen"),
  appScreen: $("#app-screen"),
  authForm: $("#auth-form"),
  authEmail: $("#auth-email"),
  authPassword: $("#auth-password"),
  authError: $("#auth-error"),
  authSubmit: $("#auth-submit"),
  authTitle: $("#auth-title"),
  authSubtitle: $("#auth-subtitle"),
  authEyebrow: $("#auth-eyebrow"),
  authSwitch: $("#switch-auth"),
  forgotBtn: $("#forgot-btn"),
  togglePassword: $("#toggle-password"),
  navAll: $(".nav-item[data-filter='']"),
  countAll: $("#count-all"),
  navStatuses: $("#nav-statuses"),
  mobileFilters: $("#mobile-filters"),
  accountEmail: $("#account-email"),
  accountAvatar: $("#account-avatar"),
  logoutBtn: $("#logout-btn"),
  mobileLogout: $("#mobile-logout"),
  todayLabel: $("#today-label"),
  pageTitle: $("#page-title"),
  pageSubtitle: $("#page-subtitle"),
  statTotal: $("#stat-total"),
  statTotalCaption: $("#stat-total-caption"),
  statProcess: $("#stat-process"),
  statProcessCaption: $("#stat-process-caption"),
  statApproved: $("#stat-approved"),
  statApprovedCaption: $("#stat-approved-caption"),
  statRejected: $("#stat-rejected"),
  statRejectedCaption: $("#stat-rejected-caption"),
  countBadge: $("#count-badge"),
  searchInput: $("#search-input"),
  clearSearch: $("#clear-search"),
  loanList: $("#loan-list"),
  emptyState: $("#empty-state"),
  emptyTitle: $("#empty-title"),
  emptyBody: $("#empty-body"),
  emptyAction: $("#empty-action"),
  banner: $("#banner"),
  addBtn: $("#add-btn"),
  exportBtn: $("#export-btn"),
  projectLabel: $("#project-label"),
  dialog: $("#loan-dialog"),
  dialogForm: $("#loan-form"),
  dialogBody: $("#dialog-body"),
  dialogTitle: $("#dialog-title"),
  dialogSubtitle: $("#dialog-subtitle"),
  dialogClose: $("#dialog-close"),
  dialogCancel: $("#dialog-cancel"),
  dialogError: $("#dialog-error"),
  deleteBtn: $("#delete-btn"),
  saveBtn: $("#save-btn"),
  fName: $("#f-name"),
  fIc: $("#f-ic"),
  fCar: $("#f-car"),
  fBank: $("#f-bank"),
  fAmount: $("#f-amount"),
  fDate: $("#f-date"),
  dateHint: $("#date-hint"),
  fStatus: $("#f-status"),
  fNotes: $("#f-notes"),
  bankList: $("#bank-list"),
  historyPanel: $("#history-panel"),
  historyList: $("#history-list"),
  historyEmpty: $("#history-empty"),
  toast: $("#toast"),
  toastText: $("#toast-text"),
  toastCheck: $(".toast-check"),
};

const state = {
  user: null,
  loans: [],
  loaded: false,
  filter: "",
  search: "",
  unsub: null,
  editingId: null,
  saving: false,
  searchTimer: null,
  toastTimer: null,
};

/* -------------------------------------------------------------- helpers -- */
const pad2 = (n) => String(n).padStart(2, "0");

function localIso() {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T` +
    `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function todayLabel() {
  const d = new Date();
  return `${DAYS_LONG[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}`;
}

function dateFromIso(value) {
  if (!value) return null;
  const parts = String(value).slice(0, 10).split("-").map(Number);
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) return null;
  const d = new Date(parts[0], parts[1] - 1, parts[2]);
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtDate(value, long = false) {
  const d = dateFromIso(value);
  if (!d) return "—";
  const months = long ? MONTHS_LONG : MONTHS_SHORT;
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

function fmtDateTime(value) {
  if (!value) return "—";
  const d = new Date(String(value));
  if (Number.isNaN(d.getTime())) return String(value);
  return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()} · ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function relativeDays(value) {
  const d = dateFromIso(value);
  if (!d) return "";
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((today.getTime() - d.getTime()) / 86400000);
  if (days <= 0) return "Hari ini";
  if (days === 1) return "Semalam";
  return `${days} hari lalu`;
}

function formatIc(value) {
  const digits = String(value || "").replace(/\D/g, "");
  if (digits.length === 12) {
    return `${digits.slice(0, 6)}-${digits.slice(6, 8)}-${digits.slice(8)}`;
  }
  return String(value || "");
}

function icDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function fmtNumber(value) {
  return Number(value || 0).toLocaleString("en-MY");
}

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `RM ${number.toLocaleString("en-MY", { maximumFractionDigits: 0 })}`;
}

function fmtCompact(value) {
  const number = Number(value || 0);
  if (number >= 1000000) {
    return `RM ${(number / 1000000).toFixed(2).replace(/\.?0+$/, "")}j`;
  }
  if (number >= 1000) {
    const amount = number >= 10000 ? Math.round(number / 1000) :
      (number / 1000).toFixed(1).replace(/\.0$/, "");
    return `RM ${amount}k`;
  }
  return `RM ${fmtNumber(number)}`;
}

function initials(name) {
  const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function hashIndex(text, length) {
  let total = 0;
  for (const ch of String(text || "")) total += ch.charCodeAt(0);
  return total % length;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function generateId() {
  if (window.crypto?.randomUUID) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function statusClass(status) {
  return STATUS_CLASS[status] || STATUS_CLASS.Baru;
}

function normalizeHistory(history) {
  if (!Array.isArray(history)) return [];
  return history
    .filter((entry) => entry && typeof entry === "object" && STATUSES.includes(entry.to_status))
    .map((entry) => ({
      from_status: entry.from_status && STATUSES.includes(entry.from_status) ? entry.from_status : null,
      to_status: entry.to_status,
      note: typeof entry.note === "string" ? entry.note : "",
      changed_at: typeof entry.changed_at === "string" ? entry.changed_at : "",
    }))
    .sort((a, b) => String(a.changed_at).localeCompare(String(b.changed_at)));
}

function normalizeLoan(id, data) {
  if (!data || typeof data !== "object" || data._deleted === true) return null;
  const status = STATUSES.includes(data.status) ? data.status : "Baru";
  const amountValue = data.amount === null || data.amount === undefined || data.amount === ""
    ? null : Number(data.amount);
  return {
    id,
    cloud_id: typeof data.cloud_id === "string" && data.cloud_id ? data.cloud_id : id,
    name: typeof data.name === "string" ? data.name : "",
    ic: typeof data.ic === "string" ? data.ic : String(data.ic || ""),
    car: typeof data.car === "string" ? data.car : "",
    bank: typeof data.bank === "string" ? data.bank : "",
    amount: amountNumber(amountValue),
    applied_date: typeof data.applied_date === "string" ? data.applied_date : "",
    status,
    notes: typeof data.notes === "string" ? data.notes : "",
    created_at: typeof data.created_at === "string" ? data.created_at : "",
    updated_at: typeof data.updated_at === "string" ? data.updated_at : "",
    history: normalizeHistory(data.history),
  };
}

function amountNumber(value) {
  return Number.isFinite(value) ? value : null;
}

function sortLoans(a, b) {
  const byDate = String(b.applied_date || "").localeCompare(String(a.applied_date || ""));
  if (byDate !== 0) return byDate;
  const byCreated = String(b.created_at || "").localeCompare(String(a.created_at || ""));
  if (byCreated !== 0) return byCreated;
  return String(b.id).localeCompare(String(a.id));
}

/* --------------------------------------------------------------- toast --- */
function showToast(message, kind = "success") {
  el.toastText.textContent = message;
  el.toast.hidden = false;
  const isError = kind === "error";
  el.toast.classList.toggle("is-error", isError);
  el.toastCheck.textContent = isError ? "!" : "✓";
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    el.toast.hidden = true;
  }, 3400);
}

function showBanner(message) {
  el.banner.textContent = message;
  el.banner.hidden = false;
}

function hideBanner() {
  el.banner.hidden = true;
}

/* --------------------------------------------------------------- auth ---- */
let authMode = "login";

function setAuthMode(mode) {
  authMode = mode;
  const isLogin = mode === "login";
  el.authEyebrow.textContent = isLogin ? "SELAMAT KEMBALI" : "MULA DI SINI";
  el.authTitle.textContent = isLogin ? "Log masuk" : "Daftar akaun";
  el.authSubtitle.textContent = isLogin
    ? "Akses rekod pinjaman anda."
    : "Cipta akaun untuk mula memantau pinjaman.";
  el.authSubmit.textContent = isLogin ? "Log masuk" : "Daftar akaun";
  el.authSwitch.textContent = isLogin ? "Daftar akaun baharu" : "Sudah ada akaun? Log masuk";
  el.forgotBtn.hidden = !isLogin;
  el.authPassword.autocomplete = isLogin ? "current-password" : "new-password";
  el.authError.hidden = true;
  el.authPassword.value = "";
}

function authErrorMessage(error) {
  const code = error?.code || "";
  switch (code) {
    case "auth/invalid-credential":
    case "auth/wrong-password":
    case "auth/user-not-found":
      return "Email atau kata laluan tidak betul.";
    case "auth/invalid-email":
      return "Format email tidak sah.";
    case "auth/missing-password":
      return "Sila masukkan kata laluan.";
    case "auth/email-already-in-use":
      return "Email ini sudah didaftarkan. Sila log masuk.";
    case "auth/weak-password":
      return "Kata laluan terlalu lemah. Gunakan sekurang-kurangnya 6 aksara.";
    case "auth/operation-not-allowed":
      return "Log masuk Email/Password belum diaktifkan dalam Firebase Console.";
    case "auth/user-disabled":
      return "Akaun ini telah dinyahdayakan.";
    case "auth/too-many-requests":
      return "Terlalu banyak percubaan. Cuba lagi sebentar nanti.";
    case "auth/network-request-failed":
      return "Tidak dapat menghubungi Firebase. Semak sambungan internet anda.";
    case "auth/unauthorized-domain":
      return "Domain ini tidak dibenarkan dalam Firebase Authentication.";
    default:
      return "Ralat: " + (error?.message || "Cuba lagi.");
  }
}

function setAuthBusy(busy) {
  el.authSubmit.disabled = busy;
  el.authSubmit.textContent = busy
    ? (authMode === "login" ? "Menyambung…" : "Mendaftar…")
    : (authMode === "login" ? "Log masuk" : "Daftar akaun");
}

el.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fbApp) return;
  const email = el.authEmail.value.trim();
  const password = el.authPassword.value;
  el.authError.hidden = true;
  if (!email || !email.includes("@")) {
    el.authError.textContent = "Sila masukkan alamat email yang sah.";
    el.authError.hidden = false;
    el.authEmail.focus();
    return;
  }
  if (!password) {
    el.authError.textContent = "Sila masukkan kata laluan.";
    el.authError.hidden = false;
    el.authPassword.focus();
    return;
  }
  if (authMode === "register" && password.length < 6) {
    el.authError.textContent = "Kata laluan mesti sekurang-kurangnya 6 aksara.";
    el.authError.hidden = false;
    el.authPassword.focus();
    return;
  }
  setAuthBusy(true);
  try {
    if (authMode === "login") {
      await signInWithEmailAndPassword(auth, email, password);
    } else {
      await createUserWithEmailAndPassword(auth, email, password);
    }
  } catch (error) {
    console.error(error);
    el.authError.textContent = authErrorMessage(error);
    el.authError.hidden = false;
  } finally {
    setAuthBusy(false);
  }
});

el.authSwitch.addEventListener("click", () => {
  setAuthMode(authMode === "login" ? "register" : "login");
  el.authEmail.focus();
});

el.forgotBtn.addEventListener("click", async () => {
  const email = el.authEmail.value.trim();
  el.authError.hidden = true;
  if (!email || !email.includes("@")) {
    el.authError.textContent = "Masukkan email anda dahulu untuk set semula kata laluan.";
    el.authError.hidden = false;
    el.authEmail.focus();
    return;
  }
  el.forgotBtn.disabled = true;
  try {
    await sendPasswordResetEmail(auth, email);
    showToast("Pautan set semula kata laluan telah dihantar ke email anda.");
  } catch (error) {
    console.error(error);
    el.authError.textContent = authErrorMessage(error);
    el.authError.hidden = false;
  } finally {
    el.forgotBtn.disabled = false;
  }
});

el.togglePassword.addEventListener("click", () => {
  const isPassword = el.authPassword.type === "password";
  el.authPassword.type = isPassword ? "text" : "password";
  el.togglePassword.textContent = isPassword ? "Sembunyi" : "Tunjuk";
  el.togglePassword.setAttribute(
    "aria-label",
    isPassword ? "Sembunyi kata laluan" : "Tunjuk kata laluan"
  );
});

/* ------------------------------------------------------------- auth/app -- */
function accountInitials(email) {
  const local = String(email || "").split("@")[0] || "?";
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function showAuthScreen() {
  el.boot.hidden = true;
  el.appScreen.hidden = true;
  el.authScreen.hidden = false;
  setAuthMode("login");
}

function showAppScreen(user) {
  el.boot.hidden = true;
  el.authScreen.hidden = true;
  el.appScreen.hidden = false;
  el.accountEmail.textContent = user.email || "Akaun Firebase";
  el.accountAvatar.textContent = accountInitials(user.email);
  el.todayLabel.textContent = todayLabel();
  el.projectLabel.textContent = firebaseConfig.projectId;
  el.authPassword.value = "";
}

function enterApp(user) {
  state.user = user;
  showAppScreen(user);
  startLoans(user.uid);
  renderAll();
}

function leaveApp() {
  stopLoans();
  state.user = null;
  state.loans = [];
  state.loaded = false;
  state.filter = "";
  state.search = "";
  el.searchInput.value = "";
  if (el.dialog.open) el.dialog.close();
  renderAll();
  showAuthScreen();
}

if (auth) {
  onAuthStateChanged(auth, (user) => {
    if (user) {
      enterApp(user);
    } else {
      leaveApp();
    }
  });
}

async function logout() {
  if (!confirm("Log keluar daripada akaun LoanTrack?")) return;
  try {
    await signOut(auth);
  } catch (error) {
    showToast("Tidak dapat log keluar. Cuba lagi.", "error");
  }
}

el.logoutBtn.addEventListener("click", logout);
el.mobileLogout.addEventListener("click", logout);

/* -------------------------------------------------------------- data ----- */
function startLoans(uid) {
  stopLoans();
  state.loaded = false;
  const loansRef = collection(db, "users", uid, "loans");
  state.unsub = onSnapshot(
    loansRef,
    (snapshot) => {
      state.loans = snapshot.docs
        .map((d) => normalizeLoan(d.id, d.data()))
        .filter(Boolean)
        .sort(sortLoans);
      state.loaded = true;
      hideBanner();
      renderAll();
    },
    (error) => {
      console.error(error);
      state.loaded = true;
      showBanner(firestoreErrorMessage(error));
      renderAll();
    }
  );
}

function stopLoans() {
  if (state.unsub) {
    try { state.unsub(); } catch (_) { /* noop */ }
    state.unsub = null;
  }
}

function firestoreErrorMessage(error) {
  const code = error?.code || "";
  switch (code) {
    case "permission-denied":
      return "Akses Firestore ditolak. Pastikan Rules Firestore sudah di-publish.";
    case "unavailable":
      return "Tidak dapat menyambung ke Firestore. Rekod mungkin tidak dikemas kini sehingga sambungan pulih.";
    case "failed-precondition":
      return "Firestore memerlukan konfigurasi tambahan. Semak Firebase Console.";
    case "unauthenticated":
      return "Sesi tamat. Sila log masuk semula.";
    default:
      return "Ralat Firestore: " + (error?.message || "Cuba lagi.");
  }
}

/* ------------------------------------------------------------ filtering -- */
function filteredLoans() {
  const query = state.search.trim().toLowerCase();
  const digits = query.replace(/\D/g, "");
  return state.loans.filter((loan) => {
    if (state.filter && loan.status !== state.filter) return false;
    if (!query) return true;
    const haystack = [loan.name, loan.car, loan.bank, loan.notes, loan.status]
      .join(" ").toLowerCase();
    if (haystack.includes(query)) return true;
    return digits.length >= 4 && icDigits(loan.ic).includes(digits);
  });
}

function setFilter(filter) {
  state.filter = filter || "";
  renderAll();
}

/* -------------------------------------------------------------- render --- */
function renderAll() {
  if (!state.user) return;
  renderNav();
  renderStats();
  renderHeader();
  renderList();
}

function updateCounts() {
  const counts = { "": state.loans.length };
  for (const status of STATUSES) counts[status] = 0;
  for (const loan of state.loans) {
    if (counts[loan.status] === undefined) counts[loan.status] = 0;
    counts[loan.status] += 1;
  }
  return counts;
}

function renderNav() {
  const counts = updateCounts();
  el.countAll.textContent = counts[""];
  el.navAll.classList.toggle("is-active", state.filter === "");

  el.navStatuses.innerHTML = STATUSES.map((status) => `
    <button class="nav-item ${state.filter === status ? "is-active" : ""}"
            data-filter="${escapeHtml(status)}" type="button">
      <span class="nav-dot" style="background:${STATUS_DOT[status]}"></span>
      <span class="nav-label">${escapeHtml(status)}</span>
      <span class="nav-count">${counts[status] || 0}</span>
    </button>
  `).join("");

  el.mobileFilters.innerHTML = [
    `<button class="filter-chip ${state.filter === "" ? "is-active" : ""}"
             data-filter="" type="button">Semua
       <span class="chip-count">${counts[""]}</span>
     </button>`,
    ...STATUSES.map((status) => `
      <button class="filter-chip ${state.filter === status ? "is-active" : ""}"
              data-filter="${escapeHtml(status)}" type="button">${escapeHtml(status)}
        <span class="chip-count">${counts[status] || 0}</span>
      </button>
    `),
  ].join("");
}

function renderStats() {
  const loans = state.loans;
  const total = loans.length;
  const processing = loans.filter((l) => PROCESS.has(l.status)).length;
  const approved = loans.filter((l) => APPROVED.has(l.status)).length;
  const rejected = loans.filter((l) => REJECTED.has(l.status)).length;
  const totalValue = loans.reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
  const approvedValue = loans
    .filter((l) => APPROVED.has(l.status))
    .reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
  const rejectedPct = total ? Math.round((rejected / total) * 100) : 0;

  el.statTotal.textContent = fmtNumber(total);
  el.statTotalCaption.textContent = total
    ? `${fmtCompact(totalValue)} jumlah nilai`
    : "Belum ada rekod";
  el.statProcess.textContent = fmtNumber(processing);
  el.statProcessCaption.textContent = processing
    ? "Menunggu keputusan"
    : "Tiada tindakan tertunggak";
  el.statApproved.textContent = fmtNumber(approved);
  el.statApprovedCaption.textContent = approved
    ? `${fmtCompact(approvedValue)} nilai diluluskan`
    : "Belum ada kelulusan";
  el.statRejected.textContent = fmtNumber(rejected);
  el.statRejectedCaption.textContent = total
    ? `${rejectedPct}% kadar penolakan`
    : "—";
}

function renderHeader() {
  const rows = filteredLoans();
  const title = state.filter || "Semua Pinjaman";
  el.pageTitle.textContent = title;
  if (rows.length) {
    const value = rows.reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
    el.pageSubtitle.textContent =
      `${fmtNumber(rows.length)} rekod · ${fmtCompact(value)} jumlah nilai`;
  } else {
    el.pageSubtitle.textContent = state.loaded
      ? "Tiada rekod untuk dipaparkan"
      : "Memuatkan rekod…";
  }
  el.countBadge.textContent = fmtNumber(rows.length);
}

function avatarFor(loan) {
  const [bg, fg] = AVATAR_PALETTE[hashIndex(loan.ic || loan.name, AVATAR_PALETTE.length)];
  return { bg, fg };
}

function renderList() {
  const rows = filteredLoans();
  if (!state.loaded) {
    el.loanList.innerHTML = Array.from({ length: 4 }, () => `
      <div class="skeleton-row" aria-hidden="true">
        <div class="skeleton skeleton-avatar"></div>
        <div class="skeleton-lines">
          <div class="skeleton skeleton-line"></div>
          <div class="skeleton skeleton-line short"></div>
        </div>
        <div class="skeleton skeleton-cell"></div>
        <div class="skeleton skeleton-cell"></div>
      </div>
    `).join("");
    el.emptyState.hidden = true;
    return;
  }
  if (!rows.length) {
    el.loanList.innerHTML = "";
    showEmptyState();
    return;
  }
  el.emptyState.hidden = true;
  el.loanList.innerHTML = rows.map((loan) => {
    const avatar = avatarFor(loan);
    const name = escapeHtml(loan.name || "Tanpa nama");
    return `
      <div class="loan-row" role="listitem" tabindex="0" data-id="${escapeHtml(loan.id)}"
           aria-label="Buka butiran ${name}">
        <div class="cell identity">
          <div class="avatar" style="background:${avatar.bg};color:${avatar.fg}">
            ${escapeHtml(initials(loan.name))}
          </div>
          <div class="identity-copy">
            <div class="loan-name">${name}</div>
            <div class="loan-car">${escapeHtml(loan.car || "—")}</div>
          </div>
        </div>
        <div class="cell ic">${escapeHtml(formatIc(loan.ic) || "—")}</div>
        <div class="cell bank">${escapeHtml(loan.bank || "—")}</div>
        <div class="cell amount">${fmtMoney(loan.amount)}</div>
        <div class="cell date">
          <div class="date-copy">
            <span class="date-main">${fmtDate(loan.applied_date)}</span>
            <span class="date-age">${escapeHtml(relativeDays(loan.applied_date))}</span>
          </div>
        </div>
        <div class="cell status">
          <span class="pill ${statusClass(loan.status)}">${escapeHtml(loan.status)}</span>
        </div>
        <div class="cell chevron" aria-hidden="true">›</div>
      </div>
    `;
  }).join("");
}

function showEmptyState() {
  el.emptyState.hidden = false;
  const hasLoans = state.loans.length > 0;
  const isFiltered = Boolean(state.filter || state.search.trim());
  if (hasLoans && isFiltered) {
    el.emptyTitle.textContent = "Tiada rekod ditemui";
    el.emptyBody.textContent = "Cuba tukar kata kunci carian atau tapis status yang lain.";
    el.emptyAction.textContent = "Set Semula Tapisan";
    el.emptyAction.dataset.action = "reset";
  } else {
    el.emptyTitle.textContent = "Belum ada rekod pinjaman";
    el.emptyBody.textContent = "Tambah rekod pertama anda untuk mula memantau status pinjaman.";
    el.emptyAction.textContent = "+ Tambah Pinjaman";
    el.emptyAction.dataset.action = "add";
  }
}

/* ------------------------------------------------------------- nav events */
el.navAll.addEventListener("click", () => setFilter(""));
el.navStatuses.addEventListener("click", (event) => {
  const button = event.target.closest("[data-filter]");
  if (button) setFilter(button.dataset.filter);
});
el.mobileFilters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-filter]");
  if (button) setFilter(button.dataset.filter);
});

/* ------------------------------------------------------------ search ----- */
el.searchInput.addEventListener("input", () => {
  state.search = el.searchInput.value;
  el.clearSearch.hidden = !state.search;
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(renderAll, 70);
});

el.searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Escape") clearSearch();
});

function clearSearch() {
  state.search = "";
  el.searchInput.value = "";
  el.clearSearch.hidden = true;
  renderAll();
}

el.clearSearch.addEventListener("click", clearSearch);

/* ------------------------------------------------------------ list events */
el.loanList.addEventListener("click", (event) => {
  const row = event.target.closest(".loan-row");
  if (row) openEdit(row.dataset.id);
});
el.loanList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const row = event.target.closest(".loan-row");
  if (!row) return;
  event.preventDefault();
  openEdit(row.dataset.id);
});

el.emptyAction.addEventListener("click", () => {
  if (el.emptyAction.dataset.action === "reset") {
    state.filter = "";
    state.search = "";
    el.searchInput.value = "";
    el.clearSearch.hidden = true;
    renderAll();
  } else {
    openAdd();
  }
});

el.addBtn.addEventListener("click", openAdd);

/* -------------------------------------------------------------- dialog --- */
function resetDialogErrors() {
  el.dialogError.hidden = true;
  el.dialogError.textContent = "";
  for (const field of el.dialogForm.querySelectorAll(".invalid")) {
    field.classList.remove("invalid");
  }
}

function setDialogError(message, field = null) {
  el.dialogError.textContent = message;
  el.dialogError.hidden = false;
  if (field) {
    field.classList.add("invalid");
    field.focus();
    field.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function populateDialogOptions() {
  el.fStatus.innerHTML = STATUSES
    .map((status) => `<option value="${escapeHtml(status)}">${escapeHtml(status)}</option>`)
    .join("");
  el.bankList.innerHTML = BANKS
    .map((bank) => `<option value="${escapeHtml(bank)}"></option>`)
    .join("");
}

function updateDateHint() {
  el.dateHint.textContent = el.fDate.value
    ? fmtDate(el.fDate.value, true)
    : "Pilih tarikh permohonan.";
}

function openAdd() {
  if (!state.user) return;
  state.editingId = null;
  el.dialog.classList.add("is-new");
  el.dialogTitle.textContent = "Tambah Pinjaman Baharu";
  el.dialogSubtitle.textContent = "Masukkan butiran permohonan pelanggan.";
  el.saveBtn.textContent = "Simpan";
  el.deleteBtn.hidden = true;
  el.dialogForm.reset();
  el.fStatus.value = "Baru";
  el.fDate.value = todayIso();
  updateDateHint();
  resetDialogErrors();
  el.historyList.innerHTML = "";
  el.historyEmpty.hidden = false;
  el.historyEmpty.textContent = "Sejarah akan direkodkan selepas rekod disimpan.";
  el.dialogBody.scrollTop = 0;
  el.dialog.showModal();
  setTimeout(() => el.fName.focus(), 60);
}

function openEdit(id) {
  if (!state.user) return;
  const loan = state.loans.find((item) => item.id === id);
  if (!loan) return;
  state.editingId = id;
  el.dialog.classList.remove("is-new");
  el.dialogTitle.textContent = "Butiran Pinjaman";
  el.dialogSubtitle.textContent = "Kemas kini maklumat dan pantau sejarah status.";
  el.saveBtn.textContent = "Simpan Perubahan";
  el.deleteBtn.hidden = false;
  el.deleteBtn.disabled = false;
  el.deleteBtn.textContent = "Padam";
  el.fName.value = loan.name;
  el.fIc.value = formatIc(loan.ic);
  el.fCar.value = loan.car;
  el.fBank.value = loan.bank;
  el.fAmount.value = loan.amount ?? "";
  el.fDate.value = loan.applied_date || todayIso();
  updateDateHint();
  el.fStatus.value = loan.status;
  el.fNotes.value = loan.notes;
  resetDialogErrors();
  renderHistory(loan.history);
  el.dialogBody.scrollTop = 0;
  el.dialog.showModal();
  setTimeout(() => el.fName.focus(), 60);
}

function renderHistory(history) {
  const rows = (history || []).slice().sort((a, b) =>
    String(a.changed_at).localeCompare(String(b.changed_at))
  ).reverse();
  if (!rows.length) {
    el.historyList.innerHTML = "";
    el.historyEmpty.hidden = false;
    el.historyEmpty.textContent = "Tiada sejarah direkodkan.";
    return;
  }
  el.historyEmpty.hidden = true;
  el.historyList.innerHTML = rows.map((entry) => {
    const note = entry.note && entry.note !== "Status dikemas kini"
      ? `<div class="history-note">${escapeHtml(entry.note)}</div>` : "";
    const from = entry.from_status
      ? ` · daripada ${escapeHtml(entry.from_status)}` : "";
    return `
      <div class="history-item ${STATUS_BORDER[entry.to_status] || ""}">
        <span class="pill ${statusClass(entry.to_status)}">${escapeHtml(entry.to_status)}</span>
        <div class="history-meta">${escapeHtml(fmtDateTime(entry.changed_at))}${from}</div>
        ${note}
      </div>
    `;
  }).join("");
}

function closeDialog() {
  if (state.saving) return;
  if (el.dialog.open) el.dialog.close();
}

el.dialogClose.addEventListener("click", closeDialog);
el.dialogCancel.addEventListener("click", closeDialog);
el.dialog.addEventListener("click", (event) => {
  if (event.target === el.dialog) closeDialog();
});
el.dialog.addEventListener("cancel", (event) => {
  if (state.saving) event.preventDefault();
});
el.dialog.addEventListener("close", () => {
  state.editingId = null;
  resetDialogErrors();
});

el.dialogForm.addEventListener("input", (event) => {
  if (event.target.matches("input, select, textarea")) {
    event.target.classList.remove("invalid");
    if (!el.dialogError.hidden) {
      el.dialogError.hidden = true;
      el.dialogError.textContent = "";
    }
  }
});

el.fIc.addEventListener("blur", () => {
  const digits = icDigits(el.fIc.value);
  if (digits.length === 12) el.fIc.value = formatIc(digits);
});

el.fDate.addEventListener("change", updateDateHint);
el.fDate.addEventListener("input", updateDateHint);

function validateForm() {
  const name = el.fName.value.trim();
  if (name.length < 2) {
    setDialogError("Sila masukkan nama penuh pemohon.", el.fName);
    return null;
  }
  const digits = icDigits(el.fIc.value);
  if (digits.length !== 12) {
    setDialogError("No. IC mesti mengandungi 12 digit (cth. 900101-14-5678).", el.fIc);
    return null;
  }
  const car = el.fCar.value.trim();
  if (!car) {
    setDialogError("Sila masukkan jenis atau model kereta.", el.fCar);
    return null;
  }
  const bank = el.fBank.value.trim();
  if (!bank) {
    setDialogError("Sila pilih atau masukkan nama bank.", el.fBank);
    return null;
  }
  const rawAmount = el.fAmount.value.trim();
  let amount = null;
  if (rawAmount !== "") {
    amount = Number(rawAmount);
    if (!Number.isFinite(amount) || amount < 0) {
      setDialogError("Jumlah pinjaman tidak sah. Masukkan nombor sahaja.", el.fAmount);
      return null;
    }
  }
  const applied = el.fDate.value;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(applied)) {
    setDialogError("Sila masukkan tarikh permohonan.", el.fDate);
    return null;
  }
  const status = el.fStatus.value;
  if (!STATUSES.includes(status)) {
    setDialogError("Sila pilih status pinjaman.", el.fStatus);
    return null;
  }
  return {
    name,
    ic: digits,
    car,
    bank,
    amount,
    applied_date: applied,
    status,
    notes: el.fNotes.value.trim(),
  };
}

el.dialogForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.saving || !state.user) return;
  resetDialogErrors();
  const values = validateForm();
  if (!values) return;

  state.saving = true;
  el.saveBtn.disabled = true;
  el.deleteBtn.disabled = true;
  el.saveBtn.textContent = state.editingId ? "Menyimpan…" : "Menyimpan…";

  try {
    if (!state.editingId) {
      const id = generateId();
      const now = localIso();
      const payload = {
        cloud_id: id,
        name: values.name,
        ic: values.ic,
        car: values.car,
        bank: values.bank,
        amount: values.amount,
        applied_date: values.applied_date,
        status: values.status,
        notes: values.notes,
        created_at: now,
        updated_at: now,
        schema_version: 1,
        history: [{
          from_status: null,
          to_status: values.status,
          note: "Rekod dicipta",
          changed_at: now,
        }],
      };
      await setDoc(doc(db, "users", state.user.uid, "loans", id), payload);
      state.filter = "";
      state.search = "";
      el.searchInput.value = "";
      el.clearSearch.hidden = true;
      el.dialog.close();
      renderAll();
      showToast("Rekod baharu disimpan.");
    } else {
      const now = localIso();
      const reference = doc(db, "users", state.user.uid, "loans", state.editingId);
      await runTransaction(db, async (transaction) => {
        const snapshot = await transaction.get(reference);
        if (!snapshot.exists()) {
          const missing = new Error("Rekod tidak lagi wujud.");
          missing.code = "not-found";
          throw missing;
        }
        const current = snapshot.data();
        const history = Array.isArray(current.history) ? current.history.slice() : [];
        if (current.status !== values.status) {
          history.push({
            from_status: current.status || null,
            to_status: values.status,
            note: "Status dikemas kini",
            changed_at: now,
          });
        }
        transaction.update(reference, {
          name: values.name,
          ic: values.ic,
          car: values.car,
          bank: values.bank,
          amount: values.amount,
          applied_date: values.applied_date,
          status: values.status,
          notes: values.notes,
          updated_at: now,
          history,
        });
      });
      el.dialog.close();
      showToast("Rekod dikemas kini.");
    }
  } catch (error) {
    console.error(error);
    if (error?.code === "permission-denied") {
      setDialogError("Akses ditolak oleh Firestore. Semak Firestore Rules.");
    } else if (error?.code === "not-found" || error?.message === "Rekod tidak lagi wujud.") {
      setDialogError("Rekod ini telah dipadam oleh peranti lain.");
    } else if (error?.code === "unavailable") {
      setDialogError("Tiada sambungan ke Firestore. Cuba lagi selepas sambungan pulih.");
    } else {
      setDialogError("Rekod tidak dapat disimpan. " + (error?.message || "Cuba lagi."));
    }
  } finally {
    state.saving = false;
    el.saveBtn.disabled = false;
    el.deleteBtn.disabled = false;
    if (el.dialog.open && state.editingId) {
      el.saveBtn.textContent = "Simpan Perubahan";
    } else if (el.dialog.open) {
      el.saveBtn.textContent = "Simpan";
    }
  }
});

el.deleteBtn.addEventListener("click", async () => {
  if (!state.user || !state.editingId || state.saving) return;
  const loan = state.loans.find((item) => item.id === state.editingId);
  if (!loan) return;
  const confirmed = confirm(
    `Padam rekod untuk ${loan.name || "rekod ini"}?\n\n` +
    "Semua sejarah status juga akan dipadam. Tindakan ini tidak boleh dibatalkan."
  );
  if (!confirmed) return;
  state.saving = true;
  el.deleteBtn.disabled = true;
  el.saveBtn.disabled = true;
  el.deleteBtn.textContent = "Memadam…";
  try {
    const now = localIso();
    const cloudId = loan.cloud_id || loan.id;
    const batch = writeBatch(db);
    batch.set(
      doc(db, "users", state.user.uid, "tombstones", cloudId),
      { cloud_id: cloudId, deleted_at: now, updated_at: now }
    );
    batch.delete(doc(db, "users", state.user.uid, "loans", loan.id));
    await batch.commit();
    el.dialog.close();
    showToast("Rekod dipadam.");
  } catch (error) {
    console.error(error);
    setDialogError(
      error?.code === "permission-denied"
        ? "Akses ditolak oleh Firestore. Semak Firestore Rules."
        : "Rekod tidak dapat dipadam. " + (error?.message || "Cuba lagi.")
    );
    el.deleteBtn.textContent = "Padam";
  } finally {
    state.saving = false;
    el.deleteBtn.disabled = false;
    el.saveBtn.disabled = false;
    if (el.dialog.open) el.deleteBtn.textContent = "Padam";
  }
});

/* --------------------------------------------------------------- export -- */
function csvCell(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

el.exportBtn.addEventListener("click", () => {
  const rows = filteredLoans();
  if (!rows.length) {
    showToast("Tiada rekod untuk dieksport.", "error");
    return;
  }
  const headers = [
    "Nama", "No. IC", "Jenis Kereta", "Bank", "Jumlah Pinjaman (RM)",
    "Tarikh Mohon", "Status", "Catatan", "Dikemas Kini",
  ];
  const lines = [headers.map(csvCell).join(",")];
  for (const loan of rows) {
    lines.push([
      loan.name,
      formatIc(loan.ic),
      loan.car,
      loan.bank,
      loan.amount === null ? "" : Number(loan.amount).toFixed(2),
      fmtDate(loan.applied_date, true),
      loan.status,
      loan.notes,
      fmtDateTime(loan.updated_at),
    ].map(csvCell).join(","));
  }
  const blob = new Blob(["﻿" + lines.join("\r\n")], {
    type: "text/csv;charset=utf-8",
  });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `pinjaman_${todayIso()}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
  showToast(`${rows.length} rekod dieksport ke CSV.`);
});

/* --------------------------------------------------------------- online -- */
window.addEventListener("offline", () => {
  showBanner("Tiada sambungan internet. Paparan mungkin tidak terkini sehingga sambungan pulih.");
});
window.addEventListener("online", () => {
  hideBanner();
});

/* ---------------------------------------------------------------- init --- */
populateDialogOptions();
el.todayLabel.textContent = todayLabel();
el.projectLabel.textContent = firebaseConfig.projectId;
el.clearSearch.hidden = true;

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && state.user && state.loaded) renderAll();
});
