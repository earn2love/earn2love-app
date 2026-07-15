"use strict";

const {onCall, onRequest, HttpsError} = require("firebase-functions/v2/https");
const {defineSecret} = require("firebase-functions/params");
const Stripe = require("stripe");

const {TOPUP_PACKS, SUBSCRIPTION_PLANS, FLAGS} = require("./config");
const {db, ts, inc, assertAuth, walletHistoryEntry} = require("./util");

const STRIPE_SECRET_KEY = defineSecret("STRIPE_SECRET_KEY");
const STRIPE_WEBHOOK_SECRET = defineSecret("STRIPE_WEBHOOK_SECRET");

// --------------------------------------------------------------------------
// createStripePaymentIntent — creates a real PaymentIntent for a Silver pack
// OR a subscription plan. Records a pending paymentIntents doc for reconcile.
// Coins/subscription are credited ONLY by the verified webhook, never here.
// --------------------------------------------------------------------------
exports.createStripePaymentIntent = onCall({secrets: [STRIPE_SECRET_KEY]}, async (request) => {
  const uid = assertAuth(request);
  const {packId, planId} = request.data || {};

  let intentMeta;
  if (packId) {
    const pack = TOPUP_PACKS[packId];
    if (!pack) throw new HttpsError("invalid-argument", "Invalid packId");
    intentMeta = {
      kind: "silver_topup", amount: pack.amount, currency: pack.currency,
      silver: pack.silver, packId, region: pack.region,
    };
  } else if (planId) {
    const plan = SUBSCRIPTION_PLANS[planId];
    if (!plan) throw new HttpsError("invalid-argument", "Invalid planId");
    intentMeta = {
      kind: "subscription", amount: plan.amount, currency: plan.currency,
      tier: plan.tier, planId, region: plan.region,
    };
  } else {
    throw new HttpsError("invalid-argument", "packId or planId required");
  }

  const stripe = new Stripe(STRIPE_SECRET_KEY.value());
  const paymentIntent = await stripe.paymentIntents.create({
    amount: intentMeta.amount,
    currency: intentMeta.currency,
    automatic_payment_methods: {enabled: true},
    metadata: Object.assign({uid, type: intentMeta.kind}, intentMeta.silver ?
      {packId: intentMeta.packId, silver: String(intentMeta.silver)} :
      {planId: intentMeta.planId, tier: intentMeta.tier}),
  });

  await db().collection("paymentIntents").doc(paymentIntent.id).set({
    uid,
    provider: "stripe",
    status: "created",
    createdAt: ts(),
    ...intentMeta,
  });

  return {clientSecret: paymentIntent.client_secret, paymentIntentId: paymentIntent.id};
});

// --------------------------------------------------------------------------
// stripeWebhook — the ONLY place that credits Silver / activates a plan.
// Verifies the Stripe signature and processes each event exactly once.
// --------------------------------------------------------------------------
exports.stripeWebhook = onRequest(
    {secrets: [STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET]},
    async (req, res) => {
      const sig = req.headers["stripe-signature"];
      const stripe = new Stripe(STRIPE_SECRET_KEY.value());
      let event;
      try {
        event = stripe.webhooks.constructEvent(
            req.rawBody, sig, STRIPE_WEBHOOK_SECRET.value());
      } catch (err) {
        console.error("Webhook signature verification failed", err.message);
        res.status(400).send(`Webhook Error: ${err.message}`);
        return;
      }

      // Idempotency: record processed event ids.
      const evtRef = db().collection("stripeEvents").doc(event.id);
      const evtSnap = await evtRef.get();
      if (evtSnap.exists) {
        res.json({received: true, duplicate: true});
        return;
      }

      try {
        if (event.type === "payment_intent.succeeded") {
          await handlePaymentSucceeded(event.data.object);
        } else if (event.type === "payment_intent.payment_failed") {
          await markIntent(event.data.object.id, "failed");
        } else if (event.type === "charge.refunded") {
          await markIntent(event.data.object.payment_intent, "refunded");
        }
        await evtRef.set({type: event.type, processedAt: ts()});
        res.json({received: true});
      } catch (err) {
        console.error("Webhook handler error", err);
        res.status(500).send("handler_error");
      }
    });

async function markIntent(paymentIntentId, status) {
  if (!paymentIntentId) return;
  await db().collection("paymentIntents").doc(paymentIntentId)
      .set({status, updatedAt: ts()}, {merge: true});
}

async function handlePaymentSucceeded(pi) {
  const piRef = db().collection("paymentIntents").doc(pi.id);

  await db().runTransaction(async (tx) => {
    const snap = await tx.get(piRef);
    if (!snap.exists) return; // unknown intent, ignore
    const rec = snap.data();
    if (rec.status === "credited") return; // already processed
    const uid = rec.uid;
    const userRef = db().collection("users").doc(uid);

    if (rec.kind === "silver_topup") {
      tx.update(userRef, {silverBalance: inc(rec.silver), updatedAt: ts()});
      walletHistoryEntry(tx, uid, {
        type: "topup", title: "Silver top-up", provider: "stripe",
        paymentIntentId: pi.id, toCoin: "Silver", toAmount: rec.silver,
        amount: rec.amount, currency: rec.currency, status: "paid",
      });
    } else if (rec.kind === "subscription") {
      tx.update(userRef, {
        tier: rec.tier,
        subscriptionPlan: rec.planId,
        subscriptionStatus: "active",
        subscriptionActivatedAt: ts(),
        updatedAt: ts(),
      });
      walletHistoryEntry(tx, uid, {
        type: "subscription", title: `Subscription: ${rec.tier}`, provider: "stripe",
        paymentIntentId: pi.id, amount: rec.amount, currency: rec.currency, status: "paid",
      });
    }
    tx.update(piRef, {status: "credited", creditedAt: ts()});
  });
}

// --------------------------------------------------------------------------
// confirmStripeTopupDev — DEV ONLY. Disabled unless ALLOW_DEV_STRIPE_CONFIRM
// env flag is "true". Never enable in production; the webhook is authoritative.
// --------------------------------------------------------------------------
exports.confirmStripeTopupDev = onCall(async (request) => {
  if (!FLAGS.allowDevStripeConfirm) {
    throw new HttpsError("failed-precondition",
        "Dev confirm disabled. Payments are credited by the Stripe webhook.");
  }
  const uid = assertAuth(request);
  const {paymentIntentId} = request.data || {};
  if (!paymentIntentId) throw new HttpsError("invalid-argument", "paymentIntentId required");

  const piRef = db().collection("paymentIntents").doc(paymentIntentId);
  const piSnap = await piRef.get();
  if (!piSnap.exists) throw new HttpsError("not-found", "Payment not found");
  const pi = piSnap.data();
  if (pi.uid !== uid) throw new HttpsError("permission-denied", "Not your payment");
  if (pi.status === "credited") return {ok: true, alreadyCredited: true};

  await handlePaymentSucceeded({id: paymentIntentId});
  return {ok: true, dev: true};
});
