"use strict";

const {
  generateStructuredResponse,
} = require("./openai_provider");

const {
  PlayPromptSchema,
  HostReactionSchema,
} = require("./ai_schemas");

const {
  getExperienceProfile,
} = require("./play_experience_profiles");

/**
 * Builds a dynamic Play Together prompt.
 *
 * @param {object} context Prompt context.
 * @return {Promise<object>} Structured prompt.
 */
async function generatePlayPrompt(context) {
  const profile = getExperienceProfile(
      context.experienceId,
  );

  const usedPrompts = Array.isArray(
      context.usedPromptTexts,
  ) ?
      context.usedPromptTexts.slice(-20) :
      [];

  const systemPrompt = [
    "You are an AI host for Earn2Love Play Together.",
    `Your host name is ${profile.hostName}.`,
    `Personality: ${profile.personality}.`,
    `Experience objective: ${profile.objective}.`,
    "Generate exactly one engaging shared round.",
    "Write naturally in the requested language.",
    "Do not repeat any supplied previous prompt.",
    "Never pressure either player to answer or act.",
    "Every player may answer, skip, replace or leave.",
    "Do not request passwords, financial details,",
    "precise addresses, government IDs or contact details.",
    "For mature mode, keep the prompt consent-first",
    "and suitable only for mutually consenting adults.",
    "Do not provide medical or psychological diagnosis.",
  ].join(" ");

  const userPrompt = JSON.stringify({
    experienceId: context.experienceId,
    experienceTitle: context.experienceTitle,
    language: context.language || "en",
    comfortLevel: context.comfortLevel || "standard",
    currentRound: context.currentRound || 1,
    maximumRounds: context.maximumRounds || 10,
    preferredRoundTypes:
        profile.preferredRoundTypes,
    previousPrompts: usedPrompts,
    requestedVisualTheme:
        profile.visualTheme,
  });

  return generateStructuredResponse({
    schemaName: "play_prompt",
    schema: PlayPromptSchema,
    systemPrompt,
    userPrompt,
  });
}

/**
 * Generates an AI-host reaction after both responses.
 *
 * @param {object} context Reaction context.
 * @return {Promise<object>} Structured host reaction.
 */
async function generateHostReaction(context) {
  const profile = getExperienceProfile(
      context.experienceId,
  );

  const systemPrompt = [
    "You are an entertaining Earn2Love AI host.",
    `Your name is ${profile.hostName}.`,
    "React warmly and briefly to both responses.",
    "Do not judge, diagnose or declare compatibility.",
    "Respect skipped responses.",
    "Write in the requested language.",
  ].join(" ");

  const userPrompt = JSON.stringify({
    experienceId: context.experienceId,
    language: context.language || "en",
    prompt: context.prompt,
    firstResponse: context.firstResponse,
    secondResponse: context.secondResponse,
  });

  return generateStructuredResponse({
    schemaName: "play_host_reaction",
    schema: HostReactionSchema,
    systemPrompt,
    userPrompt,
  });
}

module.exports = {
  generatePlayPrompt,
  generateHostReaction,
};
