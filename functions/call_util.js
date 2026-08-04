"use strict";

const {HttpsError} = require("firebase-functions/v2/https");
const admin = require("firebase-admin");

/**
 * Returns the Firestore database instance.
 * @return {FirebaseFirestore.Firestore} Firestore instance.
 */
function db() {
  return admin.firestore();
}

/**
 * Returns a server timestamp sentinel.
 * @return {FirebaseFirestore.FieldValue} Server timestamp value.
 */
function timestamp() {
  return admin.firestore.FieldValue.serverTimestamp();
}

/**
 * Returns an atomic Firestore increment sentinel.
 * @param {number} value Increment value.
 * @return {FirebaseFirestore.FieldValue} Increment value.
 */
function increment(value) {
  return admin.firestore.FieldValue.increment(value);
}

/**
 * Verifies that a callable request is authenticated.
 * @param {object} request Firebase callable request.
 * @return {string} Authenticated Firebase user ID.
 */
function assertAuth(request) {
  const uid = request.auth && request.auth.uid;

  if (!uid) {
    throw new HttpsError(
        "unauthenticated",
        "Login required",
    );
  }

  return uid;
}

/**
 * Loads and validates a user account.
 * @param {string} uid Firebase user ID.
 * @param {object} options Validation options.
 * @return {Promise<object>} User document reference and data.
 */
async function assertAccountUsable(
    uid,
    {requireWallet = false} = {},
) {
  const reference = db().collection("users").doc(uid);
  const snapshot = await reference.get();

  if (!snapshot.exists) {
    throw new HttpsError(
        "not-found",
        "User account not found",
    );
  }

  const data = snapshot.data() || {};

  if (data.isBanned === true ||
      data.banned === true ||
      data.accountStatus === "banned") {
    throw new HttpsError(
        "permission-denied",
        "Account is banned",
    );
  }

  if (data.isFrozen === true ||
      data.frozen === true ||
      data.accountStatus === "frozen") {
    throw new HttpsError(
        "permission-denied",
        "Account is frozen",
    );
  }

  if (requireWallet) {
    const rawBalance =
        data.silverBalance !== undefined &&
        data.silverBalance !== null ?
        data.silverBalance :
        data.silverCoins;

    const balance = Number(
        rawBalance !== undefined &&
        rawBalance !== null ?
        rawBalance :
        0,
    );

    if (!Number.isFinite(balance)) {
      throw new HttpsError(
          "failed-precondition",
          "Wallet balance is invalid",
      );
    }
  }

  return {
    reference,
    data,
  };
}

/**
 * Creates a wallet-history record inside a transaction.
 * @param {FirebaseFirestore.Transaction} transaction Firestore transaction.
 * @param {string} uid Firebase user ID.
 * @param {object} payload Wallet-history values.
 * @return {void}
 */
function walletHistoryEntry(
    transaction,
    uid,
    payload,
) {
  const reference = db()
      .collection("users")
      .doc(uid)
      .collection("walletHistory")
      .doc();

  transaction.set(reference, {
    ...payload,
    createdAt: timestamp(),
  });
}

module.exports = {
  db,
  timestamp,
  increment,
  assertAuth,
  assertAccountUsable,
  walletHistoryEntry,
};
