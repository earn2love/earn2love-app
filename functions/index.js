/* eslint-disable max-len */
const {setGlobalOptions} = require("firebase-functions");
const {onCall, HttpsError} = require("firebase-functions/v2/https");
const admin = require("firebase-admin");
const Stripe = require("stripe");
const calls = require("./calls");
const playTogether = require("./play_together");

admin.initializeApp();
setGlobalOptions({maxInstances: 10});

const db = admin.firestore();

const TOPUP_PACKS = {
  uk_199: {amount: 199, currency: "gbp", silver: 100, label: "£1.99 Silver Pack"},
  uk_499: {amount: 499, currency: "gbp", silver: 280, label: "£4.99 Silver Pack"},
  uk_999: {amount: 999, currency: "gbp", silver: 620, label: "£9.99 Silver Pack"},
  in_99: {amount: 9900, currency: "inr", silver: 100, label: "₹99 Silver Pack"},
  in_299: {amount: 29900, currency: "inr", silver: 280, label: "₹299 Silver Pack"},
  in_499: {amount: 49900, currency: "inr", silver: 620, label: "₹499 Silver Pack"},
};

exports.createStripePaymentIntent = onCall({secrets: ["STRIPE_SECRET_KEY"]}, async (request) => {
  if (!request.auth) {
    throw new HttpsError("unauthenticated", "Login required");
  }

  const {packId} = request.data || {};
  const pack = TOPUP_PACKS[packId];

  if (!pack) {
    throw new HttpsError("invalid-argument", "Invalid packId");
  }

  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

  const paymentIntent = await stripe.paymentIntents.create({
    amount: pack.amount,
    currency: pack.currency,
    automatic_payment_methods: {enabled: true},
    metadata: {
      uid: request.auth.uid,
      packId,
      silver: String(pack.silver),
      type: "silver_topup",
    },
  });

  await db.collection("paymentIntents").doc(paymentIntent.id).set({
    uid: request.auth.uid,
    packId,
    amount: pack.amount,
    currency: pack.currency,
    silver: pack.silver,
    status: "created",
    provider: "stripe",
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
  });

  return {
    clientSecret: paymentIntent.client_secret,
    paymentIntentId: paymentIntent.id,
  };
});

exports.confirmStripeTopupDev = onCall(async (request) => {
  if (!request.auth) {
    throw new HttpsError("unauthenticated", "Login required");
  }

  const {paymentIntentId} = request.data || {};
  if (!paymentIntentId) {
    throw new HttpsError("invalid-argument", "paymentIntentId required");
  }

  const piRef = db.collection("paymentIntents").doc(paymentIntentId);
  const piSnap = await piRef.get();

  if (!piSnap.exists) {
    throw new HttpsError("not-found", "Payment not found");
  }

  const pi = piSnap.data();

  if (pi.uid !== request.auth.uid) {
    throw new HttpsError("permission-denied", "Not your payment");
  }

  if (pi.status === "credited") {
    return {ok: true, alreadyCredited: true};
  }

  const userRef = db.collection("users").doc(request.auth.uid);

  await db.runTransaction(async (tx) => {
    tx.update(userRef, {
      silverCoins: admin.firestore.FieldValue.increment(pi.silver),
      updatedAt: admin.firestore.FieldValue.serverTimestamp(),
    });

    tx.update(piRef, {
      status: "credited",
      creditedAt: admin.firestore.FieldValue.serverTimestamp(),
    });

    tx.set(db.collection("walletTransactions").doc(), {
      uid: request.auth.uid,
      type: "silver_topup",
      provider: "stripe",
      paymentIntentId,
      silver: pi.silver,
      amount: pi.amount,
      currency: pi.currency,
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
    });
  });

  return {ok: true, silverAdded: pi.silver};
});

// Agora calls
exports.generateAgoraToken =
    calls.generateAgoraToken;
exports.startCall = calls.startCall;
exports.endCall = calls.endCall;

exports.acceptCall = calls.acceptCall;
exports.rejectCall = calls.rejectCall;
exports.cancelCall = calls.cancelCall;
exports.getCallConfig = calls.getCallConfig;
exports.updateCallConfig = calls.updateCallConfig;

// Play Together
exports.getPlayExperiences =
    playTogether.getPlayExperiences;
exports.createPlaySession =
    playTogether.createPlaySession;
exports.joinPlaySession =
    playTogether.joinPlaySession;
exports.setPlayReady =
    playTogether.setPlayReady;
exports.getPlaySession =
    playTogether.getPlaySession;
exports.leavePlaySession =
    playTogether.leavePlaySession;
