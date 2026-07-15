"use strict";

const {HttpsError} = require("firebase-functions/v2/https");
const admin = require("firebase-admin");
const {ADMIN_ROLES, ADMIN_ACTION_ROLES} = require("./config");

const db = () => admin.firestore();
const ts = () => admin.firestore.FieldValue.serverTimestamp();
const inc = (n) => admin.firestore.FieldValue.increment(n);

// ---- Auth guards ----------------------------------------------------------

function assertAuth(request) {
  if (!request.auth || !request.auth.uid) {
    throw new HttpsError("unauthenticated", "Login required");
  }
  return request.auth.uid;
}

// Requires an admin custom-claim role. Optionally gate by a specific action.
function assertAdmin(request, action) {
  assertAuth(request);
  const role = request.auth.token && request.auth.token.role;
  if (!ADMIN_ROLES.includes(role)) {
    throw new HttpsError("permission-denied", "Admin role required");
  }
  if (action) {
    const allowed = ADMIN_ACTION_ROLES[action] || [];
    if (!allowed.includes(role)) {
      throw new HttpsError("permission-denied", `Role '${role}' cannot perform '${action}'`);
    }
  }
  return {uid: request.auth.uid, role, email: request.auth.token.email || ""};
}

// ---- Account-state enforcement -------------------------------------------

// Reads users/{uid} and throws if the account cannot perform value actions
// (spend coins, call, convert, withdraw, message). Server is the source of truth.
async function assertAccountUsable(uid, {requireWallet = false} = {}) {
  const snap = await db().collection("users").doc(uid).get();
  if (!snap.exists) throw new HttpsError("not-found", "User profile not found");
  const u = snap.data() || {};
  const status = (u.accountStatus || u.status || "Active").toString().toLowerCase();
  if (u.banned === true || status === "banned") {
    throw new HttpsError("permission-denied", "Account banned");
  }
  if (u.frozen === true || status === "frozen") {
    throw new HttpsError("permission-denied", "Account frozen");
  }
  if (status === "deleted" || u.deleted === true) {
    throw new HttpsError("permission-denied", "Account deleted");
  }
  if (requireWallet && u.walletFrozen === true) {
    throw new HttpsError("permission-denied", "Wallet is frozen");
  }
  return u;
}

// ---- Audit logging (mirrors admin panel adminAuditLogs schema) ------------

async function writeAudit(entry) {
  await db().collection("adminAuditLogs").add({
    adminUid: entry.adminUid || "system",
    adminEmail: entry.adminEmail || "system",
    adminRole: entry.adminRole || "system",
    action: entry.action,
    module: entry.module || "",
    target: entry.target || "",
    targetId: entry.targetId || "",
    prev: entry.prev === undefined ? null : entry.prev,
    new: entry.new === undefined ? null : entry.new,
    reason: entry.reason || "",
    source: entry.source || "cloud_function",
    timestamp: ts(),
  });
}

// ---- Wallet history (users/{uid}/walletHistory) ---------------------------
// Single canonical transaction store used by the app AND the admin panel
// (admin reads it via the walletHistory collectionGroup).

function walletHistoryEntry(tx, uid, data) {
  const ref = db().collection("users").doc(uid).collection("walletHistory").doc();
  tx.set(ref, Object.assign({createdAt: ts()}, data));
  return ref.id;
}

module.exports = {
  db,
  ts,
  inc,
  assertAuth,
  assertAdmin,
  assertAccountUsable,
  writeAudit,
  walletHistoryEntry,
};
