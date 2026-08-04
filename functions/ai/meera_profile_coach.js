"use strict";

const {
  generateStructuredResponse,
} = require("./openai_provider");

const {
  MeeraProfileCoachSchema,
} = require("./ai_schemas");

const {
  resolveLanguageContext,
} = require("./ai_language");

/**
 * Creates a safe profile-coach analysis.
 *
 * @param {object} context Verified profile context.
 * @return {Promise<object>} Structured analysis.
 */
async function generateProfileCoaching(
    context,
) {
  const language = resolveLanguageContext(
      context.language || {},
  );

  const profile = context.profile || {};

  const systemPrompt = [
    "You are Meera, Earn2Love's profile coach.",
    "Analyse only the verified profile fields supplied.",
    "Be helpful, encouraging and specific.",
    "Do not make attractiveness judgements.",
    "Do not infer race, religion, health, sexuality,",
    "income, personality disorders or other sensitive",
    "attributes.",
    "Do not identify people from photographs.",
    "Photo guidance must concern presentation quality",
    "only, such as lighting, clarity, framing and",
    "variety.",
    "Never claim a profile change has been applied.",
    "Bio suggestions must be no longer than 140",
    "characters and must not include phone numbers,",
    "social-media handles, addresses or contact details.",
    "Suggested interests must be realistic and based",
    "only on supplied interests or user goals.",
    language.autoDetect ?
      "Reply in the user's app language." :
      `Reply in ${language.targetName}.`,
  ].join(" ");

  const userPrompt = JSON.stringify({
    profile: {
      displayName:
          String(profile.displayName || "")
              .trim()
              .slice(0, 80),
      bio:
          String(profile.bio || "")
              .trim()
              .slice(0, 300),
      interests:
          Array.isArray(profile.interests) ?
            profile.interests
                .map((item) =>
                  String(item || "")
                      .trim()
                      .slice(0, 60))
                .filter(Boolean)
                .slice(0, 30) :
            [],
      languages:
          Array.isArray(profile.languages) ?
            profile.languages
                .map((item) =>
                  String(item || "")
                      .trim()
                      .slice(0, 60))
                .filter(Boolean)
                .slice(0, 20) :
            [],
      hasProfilePhoto:
          profile.hasProfilePhoto === true,
      mediaPhotoCount:
          Math.max(
              0,
              Number(profile.mediaPhotoCount || 0),
          ),
      mediaVideoCount:
          Math.max(
              0,
              Number(profile.mediaVideoCount || 0),
          ),
      country:
          String(profile.country || "")
              .trim()
              .slice(0, 80),
      profileCompletion:
          Math.max(
              0,
              Math.min(
                  100,
                  Number(
                      profile.profileCompletion || 0,
                  ),
              ),
          ),
    },
    language,
  });

  return generateStructuredResponse({
    schemaName: "meera_profile_coach_result",
    schema: MeeraProfileCoachSchema,
    systemPrompt,
    userPrompt,
  });
}

module.exports = {
  generateProfileCoaching,
};
