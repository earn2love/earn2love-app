"use strict";

const {onCall, HttpsError} = require("firebase-functions/v2/https");
const {defineSecret} = require("firebase-functions/params");

const {CALL_COSTS} = require("./config");
const {db, ts, inc, assertAuth, assertAccountUsable, walletHistoryEntry} = require("./util");

const AGORA_APP_ID = defineSecret("AGORA_APP_ID");
const AGORA_APP_CERTIFICATE = defineSecret("AGORA_APP_CERTIFICATE");

// --------------------------------------------------------------------------
// generateAgoraToken — mints a short-lived Agora RTC token server-side.
// DISABLED (failed-precondition) until AGORA_APP_ID + AGORA_APP_CERTIFICATE
// secrets are configured. The certificate must NEVER ship in the client.
// --------------------------------------------------------------------------
exports.generateAgoraToken = onCall(
    {secrets: [AGORA_APP_ID, AGORA_APP_CERTIFICATE]},
    async (request) => {
      assertAuth(request);
      const appId = AGORA_APP_ID.value();
      const appCert = AGORA_APP_CERTIFICATE.value();
      if (!appId || !appCert) {
        throw new HttpsError("failed-precondition",
            "Calls are not available yet (Agora not configured).");
      }
      const {channelName, agoraUid} = request.data || {};
      if (!channelName) throw new HttpsError("invalid-argument", "channelName required");

      // Lazy require so the function still deploys before the dep is installed.
      let RtcTokenBuilder; let RtcRole;
      try {
        ({RtcTokenBuilder, RtcRole} = require("agora-token"));
      } catch (e) {
        throw new HttpsError("failed-precondition", "agora-token package not installed");
      }

      const numericUid = Number(agoraUid) || 0;
      const expireSeconds = 3600;
      const privilegeExpire = Math.floor(Date.now() / 1000) + expireSeconds;
      const token = RtcTokenBuilder.buildTokenWithUid(
          appId, appCert, channelName, numericUid,
          RtcRole.PUBLISHER, privilegeExpire, privilegeExpire);

      return {token, appId, channelName, uid: numericUid, expiresAt: privilegeExpire};
    });

// --------------------------------------------------------------------------
// startCall — validates eligibility & balance, creates the call record.
// --------------------------------------------------------------------------
exports.startCall = onCall(async (request) => {
  const callerUid = assertAuth(request);
  const {calleeUid, type} = request.data || {};
  if (!calleeUid || !["audio", "video"].includes(type)) {
    throw new HttpsError("invalid-argument", "calleeUid and valid type required");
  }
  if (calleeUid === callerUid) throw new HttpsError("invalid-argument", "Cannot call yourself");

  const caller = await assertAccountUsable(callerUid, {requireWallet: true});
  await assertAccountUsable(calleeUid); // callee must not be banned/frozen

  const cost = CALL_COSTS[type];
  const balance = Number(caller.silverBalance || 0);
  if (balance < cost.callerPerMin) {
    throw new HttpsError("failed-precondition", "Insufficient Silver to start this call");
  }

  const channelName = `call_${callerUid}_${Date.now()}`;
  const ref = await db().collection("calls").add({
    callerUid, calleeUid, type, channelName,
    status: "ringing", charged: false,
    createdAt: ts(),
  });
  return {callId: ref.id, channelName, type, ratePerMin: cost.callerPerMin};
});

// --------------------------------------------------------------------------
// endCall — server computes final charge & receiver reward, applies atomically.
// Idempotent: a call can be charged only once.
// --------------------------------------------------------------------------
exports.endCall = onCall(async (request) => {
  const uid = assertAuth(request);
  const {callId, durationSeconds} = request.data || {};
  if (!callId) throw new HttpsError("invalid-argument", "callId required");
  const secs = Math.max(0, Number(durationSeconds) || 0);
  const minutes = Math.ceil(secs / 60);

  const callRef = db().collection("calls").doc(callId);

  return db().runTransaction(async (tx) => {
    const snap = await tx.get(callRef);
    if (!snap.exists) throw new HttpsError("not-found", "Call not found");
    const call = snap.data();
    if (call.callerUid !== uid && call.calleeUid !== uid) {
      throw new HttpsError("permission-denied", "Not a participant");
    }
    if (call.charged === true) {
      return {ok: true, alreadyCharged: true};
    }

    const cost = CALL_COSTS[call.type] || CALL_COSTS.audio;
    const callerRef = db().collection("users").doc(call.callerUid);
    const calleeRef = db().collection("users").doc(call.calleeUid);
    const callerSnap = await tx.get(callerRef);
    const callerBal = Number((callerSnap.data() || {}).silverBalance || 0);

    // Charge only what the caller can afford (never negative balance).
    const wantCharge = cost.callerPerMin * minutes;
    const charge = Math.min(wantCharge, callerBal);
    const billedMinutes = Math.floor(charge / cost.callerPerMin);
    const reward = cost.receiverPerMin * billedMinutes;

    if (charge > 0) {
      tx.update(callerRef, {silverBalance: inc(-charge), updatedAt: ts()});
      walletHistoryEntry(tx, call.callerUid, {
        type: "call_spend", title: `${call.type} call`,
        fromCoin: "Silver", fromAmount: charge, callId, minutes: billedMinutes,
      });
    }
    if (reward > 0) {
      tx.update(calleeRef, {silverBalance: inc(reward), updatedAt: ts()});
      walletHistoryEntry(tx, call.calleeUid, {
        type: "call_earning", title: `${call.type} call reward`,
        toCoin: "Silver", toAmount: reward, callId, minutes: billedMinutes,
      });
    }
    tx.update(callRef, {
      status: "ended", charged: true, durationSeconds: secs,
      billedMinutes, charge, reward, endedAt: ts(),
    });
    return {ok: true, charge, reward, billedMinutes};
  });
});
