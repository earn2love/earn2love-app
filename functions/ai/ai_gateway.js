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

const {
  generateProfileCoaching,
} = require("./meera_profile_coach");

const {
  createConversation,
  ensureConversation,
  saveConversationMessage,
  listConversations,
  getConversation,
  loadRecentHistory,
  renameConversation,
  deleteConversation,
  saveMemory,
  listMemories,
  loadMemoriesForContext,
  deleteMemory,
  clearMemories,
} = require("./meera_persistence");

exports.analyseMeeraProfile = onCall(
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
          "profileCoach",
          tier,
      );

      const mediaSnapshot =
          await account.reference
              .collection("media")
              .limit(100)
              .get();

      let photoCount = 0;
      let videoCount = 0;

      for (const document of mediaSnapshot.docs) {
        const media = document.data() || {};

        if (media.type === "photo") {
          photoCount += 1;
        } else if (media.type === "video") {
          videoCount += 1;
        }
      }

      const interests =
          Array.isArray(accountData.interests) ?
            accountData.interests :
            [];

      const languages =
          Array.isArray(accountData.languages) ?
            accountData.languages :
            [];

      const result =
          await generateProfileCoaching({
            profile: {
              displayName:
                  accountData.displayName ||
                  accountData.name ||
                  "",
              bio:
                  accountData.bio || "",
              interests,
              languages,
              hasProfilePhoto:
                  Boolean(
                      accountData.photoUrl ||
                      accountData.profilePhoto,
                  ),
              mediaPhotoCount: photoCount,
              mediaVideoCount: videoCount,
              country:
                  accountData.country || "",
              profileCompletion:
                  Number(
                      accountData
                          .profileCompletion ||
                      0,
                  ),
            },
            language: {
              languageMode:
                  request.data &&
                  request.data.languageMode ||
                  accountData
                      .meeraLanguageMode ||
                  "auto",
              requestedLanguage:
                  request.data &&
                  request.data.requestedLanguage,
              preferredLanguage:
                  accountData
                      .meeraPreferredLanguage ||
                  accountData.appLanguage ||
                  "",
              appLanguage:
                  accountData.appLanguage ||
                  "en",
              allowMixedLanguage:
                  accountData
                      .meeraAllowMixedLanguage !==
                  false,
              tonePreference:
                  accountData
                      .meeraTonePreference ||
                  "friendly",
              scriptPreference:
                  accountData
                      .meeraScriptPreference ||
                  "natural",
            },
          });

      return {
        ...result,
        usage,
      };
    },
);

exports.createMeeraConversation = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      return createConversation(
          uid,
          request.data || {},
      );
    },
);

exports.listMeeraConversations = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      return {
        conversations:
            await listConversations(
                uid,
                request.data &&
                request.data.limit,
            ),
      };
    },
);

exports.getMeeraConversation = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      const data = request.data || {};

      return getConversation(
          uid,
          data.conversationId,
          data.limit,
      );
    },
);

exports.renameMeeraConversation = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      const data = request.data || {};

      return renameConversation(
          uid,
          data.conversationId,
          data.title,
      );
    },
);

exports.deleteMeeraConversation = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      const data = request.data || {};

      return deleteConversation(
          uid,
          data.conversationId,
      );
    },
);

exports.saveMeeraMemory = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      return saveMemory(
          uid,
          request.data || {},
      );
    },
);

exports.listMeeraMemories = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      return {
        memories:
            await listMemories(
                uid,
                request.data &&
                request.data.limit,
            ),
      };
    },
);

exports.deleteMeeraMemory = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      const data = request.data || {};

      return deleteMemory(
          uid,
          data.memoryId,
      );
    },
);

exports.clearMeeraMemories = onCall(
    async (request) => {
      const uid =
          requireAuthenticatedUser(request);

      await assertAccountUsable(uid);

      return clearMemories(uid);
    },
);

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

      const conversation =
          await ensureConversation(
              uid,
              data.conversationId,
              {
                title: data.conversationTitle,
                initialMessage: message,
                languageMode:
                    data.languageMode,
                requestedLanguage:
                    data.requestedLanguage,
              },
          );

      await saveConversationMessage(
          uid,
          conversation.id,
          {
            role: "user",
            content: message,
          },
      );

      const persistentHistory =
          await loadRecentHistory(
              uid,
              conversation.id,
              12,
          );

      const memories =
          await loadMemoriesForContext(uid);

      const result =
          await generateMeeraAssistance({
            message,
            history: persistentHistory
                .slice(0, -1),
            memories,
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

      await saveConversationMessage(
          uid,
          conversation.id,
          {
            role: "assistant",
            content: result.answer,
            detectedLanguage:
                result.detectedLanguage,
            responseLanguage:
                result.responseLanguage,
            category: result.category,
            requiresHumanSupport:
                result.requiresHumanSupport,
          },
      );

      return {
        ...result,
        conversationId:
            conversation.id,
        conversationCreated:
            conversation.created,
        conversationTitle:
            conversation.title || null,
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
