"use strict";

const DEFAULT_PROFILE = Object.freeze({
  hostName: "Meera",
  personality:
      "warm, entertaining, observant and respectful",
  objective:
      "help two adults enjoy a fresh shared conversation",
  preferredRoundTypes: [
    "discussion",
    "choice",
    "challenge",
  ],
  visualTheme:
      "premium cinematic social experience",
});

const EXPERIENCE_PROFILES = Object.freeze({
  "ice-breakers": {
    objective:
        "make two people comfortable and curious about each other",
    preferredRoundTypes: [
      "discussion",
      "choice",
      "truth",
    ],
  },
  "truth-or-dare": {
    objective:
        "host an entertaining consent-first truth-or-dare session",
    preferredRoundTypes: [
      "truth",
      "dare",
      "choice",
    ],
  },
  "deep-conversations": {
    objective:
        "guide thoughtful conversations about values, trust and connection",
    preferredRoundTypes: [
      "discussion",
      "reflection",
      "truth",
    ],
  },
  "ai-date-night": {
    objective:
        "create a changing cinematic date-night experience",
    preferredRoundTypes: [
      "discussion",
      "choice",
      "challenge",
      "story",
    ],
  },
  "couple-escape": {
    objective:
        "host a cooperative romantic mystery and puzzle experience",
    preferredRoundTypes: [
      "puzzle",
      "story",
      "choice",
    ],
  },
});

/**
 * Returns an AI instruction profile for an experience.
 *
 * @param {string} experienceId Experience ID.
 * @return {object} Merged profile.
 */
function getExperienceProfile(experienceId) {
  const profile =
      EXPERIENCE_PROFILES[experienceId] || {};

  return {
    ...DEFAULT_PROFILE,
    ...profile,
    preferredRoundTypes:
        profile.preferredRoundTypes ||
        DEFAULT_PROFILE.preferredRoundTypes,
  };
}

module.exports = {
  DEFAULT_PROFILE,
  EXPERIENCE_PROFILES,
  getExperienceProfile,
};
