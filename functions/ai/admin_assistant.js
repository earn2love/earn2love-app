"use strict";

const {
  generateStructuredResponse,
} = require("./openai_provider");

const {
  AdminAssistantSchema,
} = require("./ai_schemas");

/**
 * Creates an administrative analysis or recommendation.
 *
 * @param {object} context Approved administrative context.
 * @return {Promise<object>} Structured admin assistance.
 */
async function generateAdminAssistance(context) {
  const systemPrompt = [
    "You are the Earn2Love administrative copilot.",
    "Analyse only the supplied authorised context.",
    "Clearly separate facts from recommendations.",
    "Never execute or claim to execute an admin action.",
    "Sensitive actions require an authorised human",
    "administrator to review and confirm.",
  ].join(" ");

  return generateStructuredResponse({
    schemaName: "admin_assistant_result",
    schema: AdminAssistantSchema,
    systemPrompt,
    userPrompt: JSON.stringify(context),
  });
}

module.exports = {
  generateAdminAssistance,
};
