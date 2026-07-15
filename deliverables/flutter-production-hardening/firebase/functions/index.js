"use strict";

// ---------------------------------------------------------------------------
// Earn2Love Cloud Functions — entrypoint.
// All secure, server-authoritative logic is grouped by domain and re-exported
// here. The Flutter client must NEVER perform value operations directly.
// ---------------------------------------------------------------------------

const {setGlobalOptions} = require("firebase-functions/v2");
const admin = require("firebase-admin");

admin.initializeApp();
setGlobalOptions({maxInstances: 10, region: "us-central1"});

const payments = require("./payments");
const wallet = require("./wallet");
const calls = require("./calls");
const withdrawals = require("./withdrawals");
const adminActions = require("./admin");

// Payments & subscriptions
exports.createStripePaymentIntent = payments.createStripePaymentIntent;
exports.stripeWebhook = payments.stripeWebhook;
exports.confirmStripeTopupDev = payments.confirmStripeTopupDev; // dev-flag gated

// Wallet
exports.convertCoins = wallet.convertCoins;

// Calls
exports.generateAgoraToken = calls.generateAgoraToken;
exports.startCall = calls.startCall;
exports.endCall = calls.endCall;

// Withdrawals
exports.requestWithdrawal = withdrawals.requestWithdrawal;
exports.adminReviewWithdrawal = withdrawals.adminReviewWithdrawal;

// Admin & moderation
exports.adminSetAccountState = adminActions.adminSetAccountState;
exports.setAdminRole = adminActions.setAdminRole;
exports.onReportCreated = adminActions.onReportCreated;
