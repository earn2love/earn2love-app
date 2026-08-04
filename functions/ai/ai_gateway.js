"use strict";

const {onCall} = require(
    "firebase-functions/v2/https",
);

const {
  assertAccountUsable,
} = require("../call_util");

const {
  requireAuthenticatedUser,
  requireAdminRole,
} = require("./ai_permissions");

const {
  reserveAiUsage,
} = require("./ai_usage_limits");

const {
  generateUserSupportAnswer,
} = require("./user_support");

const {
  generateAdminAssistance,
} = require("./admin_assistant");

const {
  generateMeeraAssistance,
} = require("./meera_assistant");

exports.askMeeraAssistant = onCall(
    {
      secrets: ["OPENAI_API_KEY"],
      timeoutSeconds: 45,
      memory: "256MiB",
    },
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      const account =
          await assertAccountUsable(uid);

      const accountData =
          account.data || {};

      const tier = String(
          accountData.tier ||
          accountData.subTier ||
          "casual",
      ).trim().toLowerCase();

      const usage = await reserveAiUsage(
          uid,
          "meeraAssistant",
          tier,
      );

      const data = request.data || {};

      const message =
          String(data.message || "")
              .trim()
              .slice(0, 3000);

      if (!message) {
        const {HttpsError} = require(
            "firebase-functions/v2/https",
        );

        throw new HttpsError(
            "invalid-argument",
            "A message is required",
        );
      }

      const result =
          await generateMeeraAssistance({
            message,
            history: data.history,
            currentScreen:
                data.currentScreen,
            language: {
              languageMode:
                  data.languageMode ||
                  accountData
                      .meeraLanguageMode ||
                  "auto",
              requestedLanguage:
                  data.requestedLanguage,
              preferredLanguage:
                  accountData
                      .meeraPreferredLanguage ||
                  accountData.appLanguage ||
                  "",
              appLanguage:
                  accountData.appLanguage ||
                  "en",
              secondaryLanguage:
                  accountData
                      .meeraSecondaryLanguage ||
                  "",
              scriptPreference:
                  accountData
                      .meeraScriptPreference ||
                  "natural",
              tonePreference:
                  accountData
                      .meeraTonePreference ||
                  "friendly",
              allowMixedLanguage:
                  accountData
                      .meeraAllowMixedLanguage !==
                  false,
            },
            verifiedUserContext: {
              tier,
              subscriptionStatus:
                  accountData
                      .subscriptionStatus ||
                  null,
              accountStatus:
                  accountData
                      .accountStatus ||
                  "active",
              appLanguage:
                  accountData.appLanguage ||
                  "en",
              matchLanguage:
                  accountData.matchLanguage ||
                  null,
              interests:
                  Array.isArray(
                      accountData.interests,
                  ) ?
                    accountData.interests
                        .slice(0, 20) :
                    [],
              profileCompletion:
                  Number(
                      accountData
                          .profileCompletion ||
                      0,
                  ),
              country:
                  accountData.country ||
                  null,
            },
          });

      return {
        ...result,
        usage,
      };
    },
);

exports.askUserSupportAssistant = onCall(
    {
      secrets: ["OPENAI_API_KEY"],
      timeoutSeconds: 30,
      memory: "256MiB",
    },
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      const account =
          await assertAccountUsable(uid);

      const tier = String(
          account.data.tier ||
          account.data.subTier ||
          "casual",
      ).toLowerCase();

      const usage = await reserveAiUsage(
          uid,
          "userSupport",
          tier,
      );

      const data = request.data || {};

      const result =
          await generateUserSupportAnswer({
            language:
                data.language ||
                account.data.appLanguage ||
                "en",
            question:
                String(data.question || "")
                    .trim()
                    .slice(0, 2000),
            verifiedAccountContext: {
              tier,
              subscriptionStatus:
                  account.data.subscriptionStatus ||
                  null,
              accountStatus:
                  account.data.accountStatus ||
                  "active",
            },
          });

      return {
        ...result,
        usage,
      };
    },
);

exports.askAdminAssistant = onCall(
    {
      secrets: ["OPENAI_API_KEY"],
      timeoutSeconds: 30,
      memory: "256MiB",
    },
    async (request) => {
      const admin = requireAdminRole(
          request,
          [
            "super_admin",
            "moderator",
            "support_agent",
            "finance_admin",
            "hr_admin",
            "hr_manager",
          ],
      );

      const usage = await reserveAiUsage(
          admin.uid,
          "adminAssistant",
          "admin",
      );

      const data = request.data || {};

      const result =
          await generateAdminAssistance({
            role: admin.role,
            request:
                String(data.request || "")
                    .trim()
                    .slice(0, 3000),
            authorisedContext:
                data.authorisedContext || {},
          });

      return {
        ...result,
        usage,
      };
    },
);
