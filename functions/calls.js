"use strict";

const {
  onCall,
  HttpsError,
} = require("firebase-functions/v2/https");

const {
  defineSecret,
} = require("firebase-functions/params");

const {
  RtcRole,
  RtcTokenBuilder,
} = require("agora-token");

const {
  loadCallConfig,
  saveCallConfig,
} = require("./call_config");

const {
  db,
  timestamp,
  increment,
  assertAuth,
  assertAccountUsable,
  walletHistoryEntry,
} = require("./call_util");

const AGORA_APP_ID = defineSecret("AGORA_APP_ID");
const AGORA_APP_CERTIFICATE =
    defineSecret("AGORA_APP_CERTIFICATE");

const TOKEN_VALIDITY_SECONDS = 60 * 60;

/**
 * Converts an arbitrary value to a trimmed string.
 * @param {*} value Input value.
 * @return {string} Trimmed string.
 */
function asString(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * Converts a value to a non-negative integer.
 * @param {*} value Input value.
 * @return {number} Safe integer.
 */
function asPositiveInteger(value) {
  const number = Number(value);

  if (!Number.isFinite(number) || number < 0) {
    return 0;
  }

  return Math.floor(number);
}

exports.generateAgoraToken = onCall(
    {
      secrets: [
        AGORA_APP_ID,
        AGORA_APP_CERTIFICATE,
      ],
    },
    async (request) => {
      assertAuth(request);

      const appId = asString(AGORA_APP_ID.value());
      const appCertificate =
          asString(AGORA_APP_CERTIFICATE.value());

      if (!appId || !appCertificate) {
        throw new HttpsError(
            "failed-precondition",
            "Agora is not configured",
        );
      }

      const channelName =
          asString((request.data && request.data.channelName));

      if (!channelName) {
        throw new HttpsError(
            "invalid-argument",
            "channelName required",
        );
      }

      const agoraUid =
          asPositiveInteger((request.data && request.data.agoraUid));

      const nowSeconds =
          Math.floor(Date.now() / 1000);

      const expiresAt =
          nowSeconds + TOKEN_VALIDITY_SECONDS;

      const token =
          RtcTokenBuilder.buildTokenWithUid(
              appId,
              appCertificate,
              channelName,
              agoraUid,
              RtcRole.PUBLISHER,
              expiresAt,
              expiresAt,
          );

      return {
        token,
        appId,
        channelName,
        uid: agoraUid,
        expiresAt,
      };
    },
);

exports.startCall = onCall(
    async (request) => {
      const callerUid = assertAuth(request);

      const calleeUid =
          asString((request.data && request.data.calleeUid));

      const type =
          asString((request.data && request.data.type)).toLowerCase();

      if (!calleeUid ||
          !["audio", "video"].includes(type)) {
        throw new HttpsError(
            "invalid-argument",
            "calleeUid and valid type required",
        );
      }

      if (calleeUid === callerUid) {
        throw new HttpsError(
            "invalid-argument",
            "Cannot call yourself",
        );
      }

      const callerAccount =
          await assertAccountUsable(
              callerUid,
              {requireWallet: true},
          );

      await assertAccountUsable(calleeUid);

      const callerRawBalance =
          callerAccount.data.silverBalance !== undefined &&
          callerAccount.data.silverBalance !== null ?
          callerAccount.data.silverBalance :
          callerAccount.data.silverCoins;

      const callerBalance = Number(
          callerRawBalance !== undefined &&
          callerRawBalance !== null ?
          callerRawBalance :
          0,
      );

      const config = await loadCallConfig();

      if (!config.enabled) {
        throw new HttpsError(
            "failed-precondition",
            "Calls are currently disabled",
        );
      }

      const typeConfig = config[type];

      if (callerBalance <
          typeConfig.callerPerMinute) {
        throw new HttpsError(
            "failed-precondition",
            "Insufficient Silver to start this call",
        );
      }

      const pricingSnapshot = {
        callerPerMinute:
            typeConfig.callerPerMinute,
        receiverRewardPercent:
            typeConfig.receiverRewardPercent,
        billingIncrementSeconds:
            config.billingIncrementSeconds,
        minimumBillableSeconds:
            config.minimumBillableSeconds,
      };

      const channelName =
          `call_${callerUid}_${Date.now()}`;

      const callReference =
          await db().collection("calls").add({
            callerUid,
            calleeUid,
            type,
            channelName,
            status: "ringing",
            charged: false,
            pricingSnapshot,
            createdAt: timestamp(),
            updatedAt: timestamp(),
          });

      return {
        callId: callReference.id,
        channelName,
        type,
        ratePerMin:
            pricingSnapshot.callerPerMinute,
        receiverRewardPercent:
            pricingSnapshot.receiverRewardPercent,
        billingIncrementSeconds:
            pricingSnapshot.billingIncrementSeconds,
        minimumBillableSeconds:
            pricingSnapshot.minimumBillableSeconds,
      };
    },
);

exports.endCall = onCall(
    async (request) => {
      const currentUid = assertAuth(request);

      const callId =
          asString((request.data && request.data.callId));

      if (!callId) {
        throw new HttpsError(
            "invalid-argument",
            "callId required",
        );
      }

      const durationSeconds =
          asPositiveInteger(
              (request.data && request.data.durationSeconds),
          );

      const callReference =
          db().collection("calls").doc(callId);

      return db().runTransaction(
          async (transaction) => {
            const callSnapshot =
                await transaction.get(callReference);

            if (!callSnapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Call not found",
              );
            }

            const call = callSnapshot.data() || {};

            if (call.callerUid !== currentUid &&
                call.calleeUid !== currentUid) {
              throw new HttpsError(
                  "permission-denied",
                  "Not a call participant",
              );
            }

            if (call.charged === true) {
              return {
                ok: true,
                alreadyCharged: true,
              };
            }

            const callType =
                ["audio", "video"].includes(call.type) ?
                call.type :
                "audio";

            const liveConfig =
                await loadCallConfig();

            const fallbackTypeConfig =
                liveConfig[callType];

            const storedPricing =
                call.pricingSnapshot || {};

            const callerPerMinute = Number(
                storedPricing.callerPerMinute ||
                fallbackTypeConfig.callerPerMinute,
            );

            const receiverRewardPercent = Number(
                storedPricing.receiverRewardPercent !==
                        undefined ?
                storedPricing.receiverRewardPercent :
                fallbackTypeConfig.receiverRewardPercent,
            );

            const billingIncrementSeconds = Number(
                storedPricing.billingIncrementSeconds ||
                liveConfig.billingIncrementSeconds,
            );

            const minimumBillableSeconds = Number(
                storedPricing.minimumBillableSeconds !==
                        undefined ?
                storedPricing.minimumBillableSeconds :
                liveConfig.minimumBillableSeconds,
            );

            const callerReference =
                db().collection("users")
                    .doc(call.callerUid);

            const calleeReference =
                db().collection("users")
                    .doc(call.calleeUid);

            const callerSnapshot =
                await transaction.get(
                    callerReference,
                );

            const callerData =
                callerSnapshot.data() || {};

            const callerRawBalance =
                callerData.silverBalance !== undefined &&
                callerData.silverBalance !== null ?
                callerData.silverBalance :
                callerData.silverCoins;

            const callerBalance = Number(
                callerRawBalance !== undefined &&
                callerRawBalance !== null ?
                callerRawBalance :
                0,
            );

            const shouldBill =
                durationSeconds >=
                minimumBillableSeconds;

            const requestedBillingUnits =
                shouldBill ?
                Math.ceil(
                    durationSeconds /
                    billingIncrementSeconds,
                ) :
                0;

            const maximumAffordableUnits =
                Math.floor(
                    callerBalance /
                    callerPerMinute,
                );

            const billedUnits =
                Math.min(
                    requestedBillingUnits,
                    maximumAffordableUnits,
                );

            const charge =
                billedUnits *
                callerPerMinute;

            const reward =
                Math.floor(
                    charge *
                    receiverRewardPercent /
                    100,
                );

            const billedSeconds =
                billedUnits *
                billingIncrementSeconds;

            const billedMinutes =
                Math.ceil(
                    billedSeconds / 60,
                );

            if (charge > 0) {
              transaction.set(
                  callerReference,
                  {
                    silverBalance:
                        increment(-charge),
                    updatedAt: timestamp(),
                  },
                  {merge: true},
              );

              walletHistoryEntry(
                  transaction,
                  call.callerUid,
                  {
                    type: "call_spend",
                    title:
                        `${callType} call`,
                    fromCoin: "Silver",
                    fromAmount: charge,
                    callId,
                    minutes: billedMinutes,
                  },
              );
            }

            if (reward > 0) {
              transaction.set(
                  calleeReference,
                  {
                    silverBalance:
                        increment(reward),
                    updatedAt: timestamp(),
                  },
                  {merge: true},
              );

              walletHistoryEntry(
                  transaction,
                  call.calleeUid,
                  {
                    type: "call_earning",
                    title:
                        `${callType} call reward`,
                    toCoin: "Silver",
                    toAmount: reward,
                    callId,
                    minutes: billedMinutes,
                  },
              );
            }

            transaction.set(
                callReference,
                {
                  status: "ended",
                  charged: true,
                  durationSeconds,
                  billedMinutes,
                  billedUnits,
                  billedSeconds,
                  charge,
                  reward,
                  pricingSnapshot: {
                    callerPerMinute,
                    receiverRewardPercent,
                    billingIncrementSeconds,
                    minimumBillableSeconds,
                  },
                  endedBy: currentUid,
                  endedAt: timestamp(),
                  updatedAt: timestamp(),
                },
                {merge: true},
            );

            return {
              ok: true,
              charge,
              reward,
              billedMinutes,
            };
          },
      );
    },
);

exports.acceptCall = onCall(
    async (request) => {
      const currentUid = assertAuth(request);
      const callId = asString(
          request.data && request.data.callId,
      );

      if (!callId) {
        throw new HttpsError(
            "invalid-argument",
            "callId required",
        );
      }

      const callReference =
          db().collection("calls").doc(callId);

      return db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(callReference);

            if (!snapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Call not found",
              );
            }

            const call = snapshot.data() || {};

            if (call.calleeUid !== currentUid) {
              throw new HttpsError(
                  "permission-denied",
                  "Only the receiver can accept this call",
              );
            }

            if (call.status === "accepted" ||
                call.status === "connected") {
              return {
                ok: true,
                alreadyAccepted: true,
                callId,
                channelName: call.channelName,
                type: call.type,
                callerUid: call.callerUid,
                calleeUid: call.calleeUid,
              };
            }

            if (call.status !== "ringing") {
              throw new HttpsError(
                  "failed-precondition",
                  "Call is no longer available",
              );
            }

            transaction.set(
                callReference,
                {
                  status: "accepted",
                  acceptedBy: currentUid,
                  acceptedAt: timestamp(),
                  updatedAt: timestamp(),
                },
                {merge: true},
            );

            return {
              ok: true,
              alreadyAccepted: false,
              callId,
              channelName: call.channelName,
              type: call.type,
              callerUid: call.callerUid,
              calleeUid: call.calleeUid,
            };
          },
      );
    },
);

exports.rejectCall = onCall(
    async (request) => {
      const currentUid = assertAuth(request);
      const callId = asString(
          request.data && request.data.callId,
      );

      if (!callId) {
        throw new HttpsError(
            "invalid-argument",
            "callId required",
        );
      }

      const callReference =
          db().collection("calls").doc(callId);

      return db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(callReference);

            if (!snapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Call not found",
              );
            }

            const call = snapshot.data() || {};

            if (call.calleeUid !== currentUid) {
              throw new HttpsError(
                  "permission-denied",
                  "Only the receiver can reject this call",
              );
            }

            if (call.status !== "ringing") {
              return {
                ok: true,
                alreadyHandled: true,
              };
            }

            transaction.set(
                callReference,
                {
                  status: "rejected",
                  rejectedBy: currentUid,
                  rejectedAt: timestamp(),
                  updatedAt: timestamp(),
                },
                {merge: true},
            );

            return {
              ok: true,
              alreadyHandled: false,
            };
          },
      );
    },
);

exports.cancelCall = onCall(
    async (request) => {
      const currentUid = assertAuth(request);
      const callId = asString(
          request.data && request.data.callId,
      );

      if (!callId) {
        throw new HttpsError(
            "invalid-argument",
            "callId required",
        );
      }

      const callReference =
          db().collection("calls").doc(callId);

      return db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(callReference);

            if (!snapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Call not found",
              );
            }

            const call = snapshot.data() || {};

            if (call.callerUid !== currentUid) {
              throw new HttpsError(
                  "permission-denied",
                  "Only the caller can cancel this call",
              );
            }

            if (call.status !== "ringing") {
              return {
                ok: true,
                alreadyHandled: true,
              };
            }

            transaction.set(
                callReference,
                {
                  status: "cancelled",
                  cancelledBy: currentUid,
                  cancelledAt: timestamp(),
                  updatedAt: timestamp(),
                },
                {merge: true},
            );

            return {
              ok: true,
              alreadyHandled: false,
            };
          },
      );
    },
);

exports.getCallConfig = onCall(
    async (request) => {
      assertAuth(request);
      return loadCallConfig();
    },
);

exports.updateCallConfig = onCall(
    async (request) => {
      assertAuth(request);

      const config = await saveCallConfig(
          request,
          request.data || {},
      );

      return {
        ok: true,
        config,
      };
    },
);
