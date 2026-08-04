"use strict";

const {HttpsError} = require(
    "firebase-functions/v2/https",
);

const {
  db,
  timestamp,
} = require("./call_util");

const DEFAULT_CALL_CONFIG = Object.freeze({
  enabled: true,
  audio: Object.freeze({
    callerPerMinute: 10,
    receiverRewardPercent: 20,
  }),
  video: Object.freeze({
    callerPerMinute: 25,
    receiverRewardPercent: 20,
  }),
  billingIncrementSeconds: 60,
  minimumBillableSeconds: 1,
});

function asNumber(value, fallback) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return fallback;
  }

  return number;
}

function clampInteger(
    value,
    fallback,
    minimum,
    maximum,
) {
  const number = Math.floor(
      asNumber(value, fallback),
  );

  return Math.min(
      maximum,
      Math.max(minimum, number),
  );
}

function sanitizeCallConfig(raw) {
  const source = raw || {};
  const audio = source.audio || {};
  const video = source.video || {};

  return {
    enabled: source.enabled !== false,
    audio: {
      callerPerMinute: clampInteger(
          audio.callerPerMinute,
          DEFAULT_CALL_CONFIG.audio.callerPerMinute,
          1,
          100000,
      ),
      receiverRewardPercent: clampInteger(
          audio.receiverRewardPercent,
          DEFAULT_CALL_CONFIG.audio.receiverRewardPercent,
          0,
          100,
      ),
    },
    video: {
      callerPerMinute: clampInteger(
          video.callerPerMinute,
          DEFAULT_CALL_CONFIG.video.callerPerMinute,
          1,
          100000,
      ),
      receiverRewardPercent: clampInteger(
          video.receiverRewardPercent,
          DEFAULT_CALL_CONFIG.video.receiverRewardPercent,
          0,
          100,
      ),
    },
    billingIncrementSeconds: clampInteger(
        source.billingIncrementSeconds,
        DEFAULT_CALL_CONFIG.billingIncrementSeconds,
        1,
        3600,
    ),
    minimumBillableSeconds: clampInteger(
        source.minimumBillableSeconds,
        DEFAULT_CALL_CONFIG.minimumBillableSeconds,
        0,
        3600,
    ),
  };
}

async function loadCallConfig() {
  const reference = db()
      .collection("appConfig")
      .doc("calls");

  const snapshot = await reference.get();

  if (!snapshot.exists) {
    const initial = sanitizeCallConfig(
        DEFAULT_CALL_CONFIG,
    );

    await reference.set({
      ...initial,
      createdAt: timestamp(),
      updatedAt: timestamp(),
      updatedBy: "system",
    });

    return initial;
  }

  return sanitizeCallConfig(
      snapshot.data(),
  );
}

function assertSuperAdmin(request) {
  const token = request.auth && request.auth.token;
  const role = token && token.role;

  const isSuperAdmin =
      role === "super_admin" ||
      (token && token.super_admin === true);

  if (!isSuperAdmin) {
    throw new HttpsError(
        "permission-denied",
        "Super admin access required",
    );
  }

  return request.auth.uid;
}

async function saveCallConfig(
    request,
    rawConfig,
) {
  const adminUid = assertSuperAdmin(request);

  const config = sanitizeCallConfig(
      rawConfig,
  );

  await db()
      .collection("appConfig")
      .doc("calls")
      .set({
        ...config,
        updatedAt: timestamp(),
        updatedBy: adminUid,
      }, {
        merge: true,
      });

  return config;
}

module.exports = {
  DEFAULT_CALL_CONFIG,
  sanitizeCallConfig,
  loadCallConfig,
  saveCallConfig,
};
