"use strict";

const {HttpsError} = require(
    "firebase-functions/v2/https",
);

const {
  db,
  timestamp,
  increment,
} = require("../call_util");

const {getAiConfig} = require("./ai_config");

/**
 * Returns a UTC daily usage key.
 *
 * @return {string} Daily key.
 */
function dailyKey() {
  return new Date()
      .toISOString()
      .slice(0, 10);
}

/**
 * Resolves the configured daily limit.
 *
 * @param {string} tier User tier or role.
 * @return {number} Daily request limit.
 */
function resolveDailyLimit(tier) {
  const config = getAiConfig();
  const normalized = String(
      tier || "casual",
  ).trim().toLowerCase();

  return Number(
      config.dailyLimits[normalized] ||
      config.dailyLimits.casual,
  );
}

/**
 * Reserves one daily AI request atomically.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} feature AI feature name.
 * @param {string} tier User tier or role.
 * @return {Promise<object>} Usage result.
 */
async function reserveAiUsage(
    uid,
    feature,
    tier,
) {
  const dateKey = dailyKey();
  const limit = resolveDailyLimit(tier);

  const reference = db()
      .collection("aiUsage")
      .doc(`${uid}_${dateKey}`);

  return db().runTransaction(
      async (transaction) => {
        const snapshot =
            await transaction.get(reference);

        const current =
            snapshot.exists ?
            Number(snapshot.data().total || 0) :
            0;

        if (current >= limit) {
          throw new HttpsError(
              "resource-exhausted",
              "Daily AI usage limit reached",
          );
        }

        transaction.set(
            reference,
            {
              uid,
              dateKey,
              total: increment(1),
              [`features.${feature}`]:
                  increment(1),
              updatedAt: timestamp(),
            },
            {merge: true},
        );

        return {
          used: current + 1,
          limit,
          remaining: Math.max(
              0,
              limit - current - 1,
          ),
        };
      },
  );
}

module.exports = {
  dailyKey,
  resolveDailyLimit,
  reserveAiUsage,
};
