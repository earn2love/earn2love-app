"use strict";

const SUPPORTED_LANGUAGE_MODES =
    Object.freeze([
      "auto",
      "app_language",
      "fixed",
      "bilingual",
    ]);

const LANGUAGE_ALIASES =
    Object.freeze({
      "en": "English",
      "en-GB": "British English",
      "en-IN": "Indian English",
      "te": "Telugu",
      "hi": "Hindi",
      "ta": "Tamil",
      "kn": "Kannada",
      "ml": "Malayalam",
      "bn": "Bengali",
      "pa": "Punjabi",
      "ur": "Urdu",
      "gu": "Gujarati",
      "mr": "Marathi",
      "es": "Spanish",
      "fr": "French",
      "de": "German",
      "pt": "Portuguese",
      "ar": "Arabic",
      "it": "Italian",
      "nl": "Dutch",
      "pl": "Polish",
      "tr": "Turkish",
      "ru": "Russian",
      "ja": "Japanese",
      "ko": "Korean",
      "zh": "Chinese",
    });
/**
 * Normalises a language value.
 *
 * @param {*} value Raw language value.
 * @param {string} fallback Fallback language.
 * @return {string} Normalised language code or name.
 */
function normalizeLanguage(
    value,
    fallback = "auto",
) {
  const language = String(
      value || "",
  ).trim();

  if (!language) {
    return fallback;
  }

  return language.slice(0, 60);
}

/**
 * Normalises the configured language mode.
 *
 * @param {*} value Raw language mode.
 * @return {string} Supported mode.
 */
function normalizeLanguageMode(value) {
  const mode = String(
      value || "auto",
  ).trim().toLowerCase();

  return SUPPORTED_LANGUAGE_MODES.includes(
      mode,
  ) ?
      mode :
      "auto";
}

/**
 * Resolves multilingual instructions.
 *
 * @param {object} input Language inputs.
 * @return {object} Resolved language context.
 */
function resolveLanguageContext(input = {}) {
  const mode = normalizeLanguageMode(
      input.languageMode,
  );

  const requestedLanguage =
      normalizeLanguage(
          input.requestedLanguage,
          "",
      );

  const preferredLanguage =
      normalizeLanguage(
          input.preferredLanguage,
          "",
      );

  const appLanguage =
      normalizeLanguage(
          input.appLanguage,
          "en",
      );

  const secondaryLanguage =
      normalizeLanguage(
          input.secondaryLanguage,
          "",
      );

  let targetLanguage = "auto";

  if (requestedLanguage) {
    targetLanguage = requestedLanguage;
  } else if (
    mode === "fixed" &&
    preferredLanguage
  ) {
    targetLanguage = preferredLanguage;
  } else if (
    mode === "app_language"
  ) {
    targetLanguage = appLanguage;
  } else if (
    preferredLanguage &&
    mode !== "auto"
  ) {
    targetLanguage = preferredLanguage;
  }

  const targetName =
      LANGUAGE_ALIASES[targetLanguage] ||
      targetLanguage;

  return {
    mode,
    targetLanguage,
    targetName,
    preferredLanguage,
    appLanguage,
    secondaryLanguage,
    autoDetect:
        targetLanguage === "auto",
    allowMixedLanguage:
        input.allowMixedLanguage !== false,
    scriptPreference:
        normalizeLanguage(
            input.scriptPreference,
            "natural",
        ),
    tonePreference:
        normalizeLanguage(
            input.tonePreference,
            "friendly",
        ),
  };
}

/**
 * Sanitises recent conversational context.
 *
 * @param {*} rawHistory Raw history.
 * @return {object[]} Safe recent history.
 */
function sanitizeConversationHistory(
    rawHistory,
) {
  if (!Array.isArray(rawHistory)) {
    return [];
  }

  return rawHistory
      .slice(-12)
      .map((entry) => {
        const role =
            entry &&
            entry.role === "assistant" ?
              "assistant" :
              "user";

        const content = String(
            entry && entry.content || "",
        )
            .trim()
            .slice(0, 1500);

        return {
          role,
          content,
        };
      })
      .filter(
          (entry) => entry.content.length > 0,
      );
}

module.exports = {
  SUPPORTED_LANGUAGE_MODES,
  LANGUAGE_ALIASES,
  normalizeLanguage,
  normalizeLanguageMode,
  resolveLanguageContext,
  sanitizeConversationHistory,
};
