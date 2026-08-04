"use strict";

const DEFAULT_AI_CONFIG = Object.freeze({
  enabled: true,
  meeraAssistantEnabled: true,
  multilingualEnabled: true,
  playTogetherEnabled: true,
  userSupportEnabled: true,
  adminAssistantEnabled: true,
  supportCopilotEnabled: true,

  model: "gpt-5.6-luna",

  requestTimeoutMs: 15000,
  maximumPromptCharacters: 12000,
  maximumAnswerCharacters: 1000,

  dailyLimits: Object.freeze({
    casual: 20,
    friendship: 60,
    love: 150,
    employee: 50,
    hr: 100,
    admin: 200,
  }),
});

/**
 * Returns the production AI configuration.
 *
 * @return {object} AI configuration.
 */
function getAiConfig() {
  return {
    ...DEFAULT_AI_CONFIG,
    dailyLimits: {
      ...DEFAULT_AI_CONFIG.dailyLimits,
    },
  };
}

module.exports = {
  DEFAULT_AI_CONFIG,
  getAiConfig,
};
