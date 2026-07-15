"use strict";

const {onCall, HttpsError} = require("firebase-functions/v2/https");
const admin = require("firebase-admin");

const {WITHDRAWAL_MIN, CONVERSION_RATES} = require("./config");
const {db, ts, inc, assertAuth, assertAccountUsable, assertAdmin, writeAudit, walletHistoryEntry} = require("./util");

// --------------------------------------------------------------------------
// requestWithdrawal — user submits a withdrawal. Locks the diamond amount and
// creates a walletHistory record with status 'requested'. No money moves here;
// a finance admin must approve, and a real payout provider must confirm 'paid'.
// --------------------------------------------------------------------------
exports.requestWithdrawal = onCall(async (request) => {
  const uid = assertAuth(request);
  const {diamondAmount} = request.data || {};
  const amt = Number(diamondAmount);
  if (!Number.isFinite(amt) || amt <= 0) {
    throw new HttpsError("invalid-argument", "Enter a valid diamond amount");
  }

  const u = await assertAccountUsable(uid, {requireWallet: true});

  // Love tier + verified identity required.
  if ((u.tier || "casual") !== "love") {
    throw new HttpsError("failed-precondition", "Withdrawals require the Love membership");
  }
  const vs = (u.verificationStatus || "").toString().toLowerCase();
  if (!["approved", "verified"].includes(vs) && u.livenessVerifiedAt == null) {
    throw new HttpsError("failed-precondition", "Identity/liveness verification required");
  }

  const region = (u.country === "UK" || u.pricingRegion === "UK") ? "UK" : "IN";
  const rates = CONVERSION_RATES[region];
  const minCfg = WITHDRAWAL_MIN[region];
  const cashValue = amt * rates.diamondCashUnit; // diamonds -> local currency
  if (cashValue < minCfg.min) {
    throw new HttpsError("failed-precondition",
        `Minimum withdrawal is ${minCfg.min} ${minCfg.currency.toUpperCase()}`);
  }

  const userRef = db().collection("users").doc(uid);
  const result = await db().runTransaction(async (tx) => {
    const snap = await tx.get(userRef);
    const cur = snap.data() || {};
    const bal = Number(cur.diamondBalance || 0);
    if (bal < amt) throw new HttpsError("failed-precondition", "Not enough Diamonds");

    // One pending withdrawal at a time.
    if (cur.pendingWithdrawalId) {
      throw new HttpsError("failed-precondition", "You already have a pending withdrawal");
    }

    // Lock the diamonds (move to locked balance).
    tx.update(userRef, {
      diamondBalance: inc(-amt),
      lockedDiamond: inc(amt),
      updatedAt: ts(),
    });
    const id = walletHistoryEntry(tx, uid, {
      type: "withdraw", title: "Withdraw request",
      fromCoin: "Diamond", fromAmount: amt, toCoin: "Cash", toAmount: cashValue,
      country: region, currencyCode: rates.currency, cashValue,
      status: "requested",
    });
    tx.update(userRef, {pendingWithdrawalId: id});
    return {id, cashValue};
  });

  return {ok: true, withdrawalId: result.id, cashValue: result.cashValue, currency: rates.currency};
});

// --------------------------------------------------------------------------
// adminReviewWithdrawal — finance admin approves/rejects. On reject the locked
// diamonds are returned. 'paid' must be set only after a real payout confirms.
// --------------------------------------------------------------------------
exports.adminReviewWithdrawal = onCall(async (request) => {
  const {decision, uid, withdrawalId, reason} = request.data || {};
  const action = decision === "approve" ? "approve_withdrawal" : "reject_withdrawal";
  const adminCtx = assertAdmin(request, action);
  if (!uid || !withdrawalId) throw new HttpsError("invalid-argument", "uid and withdrawalId required");

  const userRef = db().collection("users").doc(uid);
  const whRef = userRef.collection("walletHistory").doc(withdrawalId);

  await db().runTransaction(async (tx) => {
    const whSnap = await tx.get(whRef);
    if (!whSnap.exists) throw new HttpsError("not-found", "Withdrawal not found");
    const wh = whSnap.data();
    if (!["requested", "under_review"].includes(wh.status)) {
      throw new HttpsError("failed-precondition", `Cannot review a '${wh.status}' withdrawal`);
    }
    const amt = Number(wh.fromAmount || 0);

    if (decision === "approve") {
      tx.update(whRef, {status: "approved", reviewedAt: ts(), reviewedBy: adminCtx.email});
      // locked diamonds stay locked until payout marks it 'paid'.
    } else {
      // reject -> return locked diamonds
      tx.update(userRef, {diamondBalance: inc(amt), lockedDiamond: inc(-amt), pendingWithdrawalId: admin.firestore.FieldValue.delete(), updatedAt: ts()});
      tx.update(whRef, {status: "rejected", rejectionReason: reason || "", reviewedAt: ts(), reviewedBy: adminCtx.email});
    }
  });

  await writeAudit({
    adminUid: adminCtx.uid, adminEmail: adminCtx.email, adminRole: adminCtx.role,
    action, module: "withdrawals", targetId: uid, reason: reason || "",
    new: decision === "approve" ? "approved" : "rejected",
  });
  return {ok: true};
});
