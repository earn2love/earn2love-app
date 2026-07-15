"use strict";

const {onCall, HttpsError} = require("firebase-functions/v2/https");

const {COIN_FIELDS, CONVERSION_RATES, CONVERSION_COOLDOWN_SECONDS} = require("./config");
const {db, ts, inc, assertAuth, assertAccountUsable, walletHistoryEntry} = require("./util");

// Allowed conversion pairs. Direct Silver -> Diamond is NOT allowed.
const PAIRS = {
  "Silver>Gold": (r) => r.silverToGold,
  "Gold>Diamond": (r) => r.goldToDiamond,
  "Gold>Silver": (r) => 1 / r.silverToGold,
  "Diamond>Gold": (r) => 1 / r.goldToDiamond,
};

// --------------------------------------------------------------------------
// convertCoins — atomic, server-authoritative coin conversion.
// Client can NEVER change balances directly; this is the only path.
// --------------------------------------------------------------------------
exports.convertCoins = onCall(async (request) => {
  const uid = assertAuth(request);
  const {from, to, amount, bonusPct} = request.data || {};

  const amt = Number(amount);
  if (!Number.isFinite(amt) || amt <= 0) {
    throw new HttpsError("invalid-argument", "Enter a valid amount");
  }
  if (from === to) throw new HttpsError("invalid-argument", "From and To cannot be same");
  const key = `${from}>${to}`;
  if (!PAIRS[key]) {
    throw new HttpsError("failed-precondition", "Conversion pair not allowed");
  }

  await assertAccountUsable(uid, {requireWallet: true});

  const userRef = db().collection("users").doc(uid);
  const result = await db().runTransaction(async (tx) => {
    const snap = await tx.get(userRef);
    const u = snap.data() || {};

    // Cooldown check (server-enforced).
    if (CONVERSION_COOLDOWN_SECONDS > 0) {
      const last = u.lastConversionAt;
      if (last && last.toMillis) {
        const elapsed = (Date.now() - last.toMillis()) / 1000;
        if (elapsed < CONVERSION_COOLDOWN_SECONDS) {
          throw new HttpsError("resource-exhausted",
              `Please wait ${Math.ceil(CONVERSION_COOLDOWN_SECONDS - elapsed)}s before converting again`);
        }
      }
    }

    const region = (u.country === "UK" || u.pricingRegion === "UK") ? "UK" : "IN";
    const rates = CONVERSION_RATES[region];

    const fromField = COIN_FIELDS[from];
    const toField = COIN_FIELDS[to];
    if (!fromField || !toField) throw new HttpsError("invalid-argument", "Unknown coin");

    const fromBal = Number(u[fromField] || 0);
    if (fromBal < amt) throw new HttpsError("failed-precondition", `Not enough ${from}`);

    let out = amt * PAIRS[key](rates);

    // Streak bonus applies only to Silver -> Gold; clamp to server-stored value.
    if (key === "Silver>Gold") {
      const serverBonus = Math.max(0, Math.min(10, Number(u.streakBonusPct || 0)));
      const requested = Math.max(0, Math.min(10, Number(bonusPct || 0)));
      const applied = Math.min(serverBonus, requested || serverBonus);
      out = out + out * (applied / 100);
    }

    // Store whole coins only to avoid floating-point drift.
    out = Math.floor(out);
    if (out <= 0) throw new HttpsError("failed-precondition", "Amount too small to convert");

    tx.update(userRef, {
      [fromField]: inc(-amt),
      [toField]: inc(out),
      lastConversionAt: ts(),
      updatedAt: ts(),
    });
    walletHistoryEntry(tx, uid, {
      type: "conversion", title: "Conversion",
      fromCoin: from, fromAmount: amt, toCoin: to, toAmount: out,
      region, status: "completed",
    });
    return {out};
  });

  return {ok: true, from, to, spent: amt, received: result.out};
});
