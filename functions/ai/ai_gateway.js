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
