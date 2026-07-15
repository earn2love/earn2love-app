"use strict";

const {onCall, HttpsError} = require("firebase-functions/v2/https");
const {onDocumentCreated} = require("firebase-functions/v2/firestore");
const admin = require("firebase-admin");

const {ADMIN_ROLES, REPORTS_FREEZE_THRESHOLD} = require("./config");
const {db, ts, assertAdmin, writeAudit} = require("./util");

// Maps an admin action to the users/{uid} field mutations (mirrors admin panel).
function stateUpdateFor(action, value) {
  switch (action) {
    case "freeze": return {accountStatus: "Frozen", frozen: true};
    case "unfreeze": return {accountStatus: "Active", frozen: false};
    case "ban": return {accountStatus: "Banned", banned: true};
    case "unban": return {accountStatus: "Active", banned: false};
    case "reset_reports": return {reportsCount: 0};
    case "freeze_wallet": return {walletFrozen: true};
    case "unfreeze_wallet": return {walletFrozen: false};
    case "request_liveness": return {verificationStatus: "Pending", livenessRequired: true};
    case "reset_liveness": return {verificationStatus: "Needs Review", livenessRequired: true};
    case "set_verification": return {verificationStatus: value || "Pending"};
    case "force_logout": return {activeSessionId: admin.firestore.FieldValue.delete(), forceLogoutAt: ts()};
    default: return null;
  }
}

// --------------------------------------------------------------------------
// adminSetAccountState — single authoritative entry for account actions.
// Requires the right admin role and writes an audit-log entry.
// --------------------------------------------------------------------------
exports.adminSetAccountState = onCall(async (request) => {
  const {action, targetUid, value, reason} = request.data || {};
  if (!action || !targetUid) throw new HttpsError("invalid-argument", "action and targetUid required");
  const adminCtx = assertAdmin(request, action);

  const update = stateUpdateFor(action, value);
  if (!update) throw new HttpsError("invalid-argument", `Unknown action '${action}'`);

  const userRef = db().collection("users").doc(targetUid);
  const before = (await userRef.get()).data() || {};
  await userRef.set(Object.assign({updatedAt: ts()}, update), {merge: true});

  // Auth-level enforcement.
  const auth = admin.auth();
  try {
    if (action === "ban") {
      await auth.updateUser(targetUid, {disabled: true});
      await auth.revokeRefreshTokens(targetUid);
    } else if (action === "unban") {
      await auth.updateUser(targetUid, {disabled: false});
    } else if (action === "force_logout") {
      await auth.revokeRefreshTokens(targetUid);
    }
  } catch (e) {
    console.warn("auth enforcement failed", action, e.message);
  }

  await writeAudit({
    adminUid: adminCtx.uid, adminEmail: adminCtx.email, adminRole: adminCtx.role,
    action, module: "users", targetId: targetUid, reason: reason || "",
    prev: before.accountStatus || null, new: update.accountStatus || value || true,
  });
  return {ok: true, action, targetUid};
});

// --------------------------------------------------------------------------
// setAdminRole — super_admin only; assigns an admin custom claim to a user.
// --------------------------------------------------------------------------
exports.setAdminRole = onCall(async (request) => {
  const adminCtx = assertAdmin(request);
  if (adminCtx.role !== "super_admin") {
    throw new HttpsError("permission-denied", "Only super_admin can assign roles");
  }
  const {targetUid, role} = request.data || {};
  if (!targetUid || (role && !ADMIN_ROLES.includes(role))) {
    throw new HttpsError("invalid-argument", "Valid targetUid and role required");
  }
  await admin.auth().setCustomUserClaims(targetUid, role ? {role} : {});
  await writeAudit({
    adminUid: adminCtx.uid, adminEmail: adminCtx.email, adminRole: adminCtx.role,
    action: "set_role", module: "admins", targetId: targetUid, new: role || "revoked",
  });
  return {ok: true};
});

// --------------------------------------------------------------------------
// onReportCreated — auto-moderation. After REPORTS_FREEZE_THRESHOLD distinct
// reports against a user, apply a 24h freeze + liveness review (admin can undo).
// --------------------------------------------------------------------------
exports.onReportCreated = onDocumentCreated("reports/{reportId}", async (event) => {
  const report = event.data && event.data.data();
  if (!report) return;
  const targetUid = report.targetUid || report.reportedUid || report.reported_user;
  if (!targetUid) return;

  const snap = await db().collection("reports")
      .where("targetUid", "==", targetUid).get();
  const count = snap.size;

  const userRef = db().collection("users").doc(targetUid);
  await userRef.set({reportsCount: count, updatedAt: ts()}, {merge: true});

  if (count >= REPORTS_FREEZE_THRESHOLD) {
    const u = (await userRef.get()).data() || {};
    if (u.banned === true || (u.accountStatus === "Frozen")) return; // already actioned
    await userRef.set({
      accountStatus: "Frozen",
      frozen: true,
      verificationStatus: "Needs Review",
      livenessRequired: true,
      autoFrozenAt: ts(),
      updatedAt: ts(),
    }, {merge: true});
    await writeAudit({
      action: "auto_freeze", module: "users", targetId: targetUid,
      reason: `Auto freeze after ${count} reports`, new: "Frozen",
    });
  }
});
