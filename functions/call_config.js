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
    enabled: true,
    callerPerMinute: 10,
    receiverRewardPercent: 20,
  }),
  video: Object.freeze({
    enabled: true,
    callerPerMinute: 25,
    receiverRewardPercent: 20,
  }),
  billingIncrementSeconds: 60,
  minimumBillableSeconds: 1,
});

/**
 * Convert a value to a finite number.
 *
 * @param {*} value Raw value.
 * @param {number} fallback Fallback value.
 * @return {number} Parsed or fallback number.
 */
function asNumber(value, fallback) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return fallback;
  }

  return number;
}

/**
 * Clamp an integer to an allowed range.
 *
 * @param {*} value Raw value.
 * @param {number} fallback Fallback value.
 * @param {number} minimum Minimum value.
 * @param {number} maximum Maximum value.
 * @return {number} Sanitized integer.
 */
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

/**
 * Sanitize the complete call configuration.
 *
 * @param {Object=} raw Raw configuration.
 * @return {Object} Sanitized configuration.
 */
function sanitizeCallConfig(raw) {
  const source = raw || {};
  const audio = source.audio || {};
  const video = source.video || {};

  return {
    enabled: source.enabled !== false,
    audio: {
      enabled: audio.enabled !== false,
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
      enabled: video.enabled !== false,
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

/**
 * Load or seed the call configuration.
 *
 * @return {Promise<Object>} Current configuration.
 */
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

/**
 * Require a super-admin callable request.
 *
 * @param {Object} request Callable request.
 * @return {string} Authenticated admin UID.
 */
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

/**
 * Validate and save call configuration.
 *
 * @param {Object} request Callable request.
 * @param {Object} rawConfig Raw configuration.
 * @return {Promise<Object>} Saved configuration.
 */
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
