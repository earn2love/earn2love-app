"use strict";

const {
  generateStructuredResponse,
} = require("./openai_provider");

const {
  SupportAnswerSchema,
} = require("./ai_schemas");

/**
 * Creates a multilingual customer-support response.
 *
 * @param {object} context Support context.
 * @return {Promise<object>} Structured support response.
 */
async function generateUserSupportAnswer(context) {
  const systemPrompt = [
    "You are the Earn2Love customer support assistant.",
    "Give accurate, concise and friendly guidance.",
    "Use only the supplied product and account context.",
    "Never claim that a payment, refund, withdrawal,",
    "subscription, KYC decision or account action occurred",
    "unless the supplied verified context confirms it.",
    "Escalate payment disputes, bans, KYC, withdrawals,",
    "harassment reports and security incidents to a human.",
    "Write in the requested language.",
  ].join(" ");

  return generateStructuredResponse({
    schemaName: "user_support_answer",
    schema: SupportAnswerSchema,
    systemPrompt,
    userPrompt: JSON.stringify(context),
  });
}

module.exports = {
  generateUserSupportAnswer,
};
