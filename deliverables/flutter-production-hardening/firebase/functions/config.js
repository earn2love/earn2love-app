"use strict";

// ---------------------------------------------------------------------------
// Central server-side configuration for Earn2Love Cloud Functions.
// Business rules live here so they are defined ONCE and enforced server-side.
// Do NOT duplicate these values in the Flutter client for security decisions.
// ---------------------------------------------------------------------------

const REGION = "us-central1";

// Canonical coin balance fields on users/{uid} (matches the Flutter app + admin panel).
const COIN_FIELDS = {
  Silver: "silverBalance",
  Gold: "goldBalance",
  Diamond: "diamondBalance",
};

// Silver top-up packs (real money -> Silver). amount is in the smallest
// currency unit (pence / paise). Silver credited only after verified payment.
const TOPUP_PACKS = {
  uk_199: {amount: 199, currency: "gbp", silver: 100, region: "UK", label: "£1.99 Silver Pack"},
  uk_499: {amount: 499, currency: "gbp", silver: 280, region: "UK", label: "£4.99 Silver Pack"},
  uk_999: {amount: 999, currency: "gbp", silver: 620, region: "UK", label: "£9.99 Silver Pack"},
  in_99: {amount: 9900, currency: "inr", silver: 100, region: "IN", label: "₹99 Silver Pack"},
  in_299: {amount: 29900, currency: "inr", silver: 280, region: "IN", label: "₹299 Silver Pack"},
  in_499: {amount: 49900, currency: "inr", silver: 620, region: "IN", label: "₹499 Silver Pack"},
};

// Membership / subscription plans. Prices come from here, never hardcoded per screen.
const SUBSCRIPTION_PLANS = {
  friendship_uk: {tier: "friendship", amount: 499, currency: "gbp", region: "UK", label: "Friendship (UK)"},
  friendship_in: {tier: "friendship", amount: 9900, currency: "inr", region: "IN", label: "Friendship (India)"},
  love_uk: {tier: "love", amount: 999, currency: "gbp", region: "UK", label: "Love (UK)"},
  love_in: {tier: "love", amount: 49900, currency: "inr", region: "IN", label: "Love (India)"},
};

// Coin conversion rates by region.
//  IN: 3 Silver -> 2 Gold, 3 Gold -> 2 Diamond
//  UK: 3 Silver -> 2.5 Gold, 3 Gold -> 2.5 Diamond
const CONVERSION_RATES = {
  IN: {silverToGold: 2 / 3, goldToDiamond: 2 / 3, diamondCashUnit: 0.01, currency: "inr"},
  UK: {silverToGold: 2.5 / 3, goldToDiamond: 2.5 / 3, diamondCashUnit: 0.01, currency: "gbp"},
};

// Cooldown between conversions (seconds). Configurable; 0 disables.
const CONVERSION_COOLDOWN_SECONDS = 60;

// Call pricing (Silver per minute) — server is the source of truth.
const CALL_COSTS = {
  audio: {callerPerMin: 10, receiverPerMin: 2},
  video: {callerPerMin: 25, receiverPerMin: 5},
};

// Withdrawal minimums (in local currency units, NOT smallest unit).
const WITHDRAWAL_MIN = {
  UK: {currency: "gbp", min: 150},
  IN: {currency: "inr", min: 10000},
};

// Withdrawal state machine.
const WITHDRAWAL_STATES = [
  "requested", "under_review", "approved", "processing", "paid", "rejected", "cancelled", "failed",
];

// Admin roles (mirror the admin panel custom claims).
const ADMIN_ROLES = ["super_admin", "moderator", "support_agent", "finance_admin", "verification_agent"];

// Which roles may perform which admin account action.
const ADMIN_ACTION_ROLES = {
  freeze: ["super_admin", "moderator"],
  unfreeze: ["super_admin", "moderator"],
  ban: ["super_admin", "moderator"],
  unban: ["super_admin", "moderator"],
  force_logout: ["super_admin", "moderator"],
  request_liveness: ["super_admin", "moderator", "verification_agent"],
  reset_liveness: ["super_admin", "verification_agent"],
  set_verification: ["super_admin", "verification_agent"],
  freeze_wallet: ["super_admin", "finance_admin"],
  unfreeze_wallet: ["super_admin", "finance_admin"],
  reset_reports: ["super_admin", "moderator"],
  approve_withdrawal: ["super_admin", "finance_admin"],
  reject_withdrawal: ["super_admin", "finance_admin"],
};

// Reports threshold that triggers auto 24h freeze + liveness review.
const REPORTS_FREEZE_THRESHOLD = 3;
const AUTO_FREEZE_HOURS = 24;

// Feature flags — external-dependent features stay OFF until keys/console are configured.
// Read from env so ops can enable per environment without code changes.
const FLAGS = {
  // Dev-only Stripe confirm (credits without webhook). NEVER true in production.
  allowDevStripeConfirm: process.env.ALLOW_DEV_STRIPE_CONFIRM === "true",
  // Ads reward crediting requires a verified ad-network callback.
  adsRewardEnabled: process.env.ADS_REWARD_ENABLED === "true",
  // Real-money withdrawal payout provider (manual admin payout until true).
  autoPayoutEnabled: process.env.AUTO_PAYOUT_ENABLED === "true",
};

module.exports = {
  REGION,
  COIN_FIELDS,
  TOPUP_PACKS,
  SUBSCRIPTION_PLANS,
  CONVERSION_RATES,
  CONVERSION_COOLDOWN_SECONDS,
  CALL_COSTS,
  WITHDRAWAL_MIN,
  WITHDRAWAL_STATES,
  ADMIN_ROLES,
  ADMIN_ACTION_ROLES,
  REPORTS_FREEZE_THRESHOLD,
  AUTO_FREEZE_HOURS,
  FLAGS,
};
