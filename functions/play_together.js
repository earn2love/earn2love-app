"use strict";

const crypto = require("crypto");
const {onCall, HttpsError} = require(
    "firebase-functions/v2/https",
);

const {
  db,
  timestamp,
  assertAuth,
  assertAccountUsable,
} = require("./call_util");

const {
  generatePlayPrompt,
  generateHostReaction,
} = require("./ai/play_prompts");

const {
  reserveAiUsage,
} = require("./ai/ai_usage_limits");

const TIER_RANK = Object.freeze({
  casual: 0,
  friendship: 1,
  love: 2,
});

const COMFORT_RANK = Object.freeze({
  standard: 0,
  romantic: 1,
  mature: 2,
});

const PROMPT_BANK = Object.freeze({
  standard: [
    {
      type: "discussion",
      text: "What is something small that always improves your day?",
    },
    {
      type: "choice",
      text: "Choose together: mountains, beach, city or countryside?",
    },
    {
      type: "truth",
      text: "What is one talent you wish you had?",
    },
    {
      type: "challenge",
      text: "Describe your mood using only three emojis.",
    },
    {
      type: "discussion",
      text: "What is one place you would love to visit together?",
    },
    {
      type: "truth",
      text: "What is something people often misunderstand about you?",
    },
    {
      type: "choice",
      text: "Would you prefer a surprise adventure or a perfectly planned day?",
    },
    {
      type: "challenge",
      text: "Give the other player a genuine compliment.",
    },
    {
      type: "discussion",
      text: "What makes a conversation unforgettable for you?",
    },
    {
      type: "truth",
      text: "What is one memory that always makes you smile?",
    },
    {
      type: "choice",
      text: "Choose one: movie night, road trip, cooking together or dancing?",
    },
    {
      type: "challenge",
      text: "Invent a funny nickname for the other player.",
    },
  ],
  romantic: [
    {
      type: "discussion",
      text: "What makes you feel genuinely appreciated by someone?",
    },
    {
      type: "truth",
      text: "What was your first impression of the other player?",
    },
    {
      type: "choice",
      // eslint-disable-next-line max-len
      text: "Choose your ideal date: rooftop dinner, beach walk, cabin or city lights?",
    },
    {
      type: "challenge",
      text: "Describe the other player using three affectionate words.",
    },
    {
      type: "discussion",
      text: "What does emotional closeness mean to you?",
    },
    {
      type: "truth",
      text: "What quality do you find most attractive in a partner?",
    },
    {
      type: "choice",
      // eslint-disable-next-line max-len
      text: "Would you rather receive a thoughtful message or a surprise visit?",
    },
    {
      type: "challenge",
      text: "Complete this sentence: I feel closest to someone when...",
    },
    {
      type: "discussion",
      text: "What kind of future experience would you love to share together?",
    },
    {
      type: "truth",
      text: "What is one romantic moment you would love to experience?",
    },
    {
      type: "choice",
      // eslint-disable-next-line max-len
      text: "Choose one: slow dance, long drive, candlelight dinner or stargazing?",
    },
    {
      type: "challenge",
      text: "Tell the other player one thing that makes them memorable.",
    },
  ],
  mature: [
    {
      type: "discussion",
      text: "What helps you feel safe when discussing intimacy and boundaries?",
    },
    {
      type: "truth",
      text: "What kind of affection makes you feel most desired?",
    },
    {
      type: "choice",
      // eslint-disable-next-line max-len
      text: "Choose the mood you prefer: playful, romantic, confident or mysterious?",
    },
    {
      type: "challenge",
      text: "Share one flirty compliment, or choose Skip.",
    },
    {
      type: "discussion",
      // eslint-disable-next-line max-len
      text: "How should two adults communicate when one person feels uncomfortable?",
    },
    {
      type: "truth",
      text: "What creates strong chemistry for you beyond physical attraction?",
    },
    {
      type: "choice",
      text: "Would you prefer a bold confession or a slow romantic build-up?",
    },
    {
      type: "challenge",
      // eslint-disable-next-line max-len
      text: "Describe your ideal romantic atmosphere without naming a location.",
    },
    {
      type: "discussion",
      // eslint-disable-next-line max-len
      text: "Which personal boundaries are most important for a partner to respect?",
    },
    {
      type: "truth",
      // eslint-disable-next-line max-len
      text: "What is something intimate you would only discuss after building trust?",
    },
    {
      type: "choice",
      // eslint-disable-next-line max-len
      text: "Choose one: teasing conversation, deep eye contact, affectionate touch or words?",
    },
    {
      type: "challenge",
      // eslint-disable-next-line max-len
      text: "Ask one personal question. The other player may answer, replace or skip.",
    },
  ],
});

const EXPERIENCES = Object.freeze([
  // Casual — 7
  {
    id: "ice-breakers",
    title: "Ice Breakers",
    tier: "casual",
    category: "casual",
    icon: "❄️",
    description: "Fresh questions that make starting a conversation easy.",
    theme: "friendly",
    estimatedMinutes: 10,
  },
  {
    id: "emoji-challenge",
    title: "Emoji Challenge",
    tier: "casual",
    category: "casual",
    icon: "😄",
    description: "Communicate stories, moods and answers using emojis.",
    theme: "fun",
    estimatedMinutes: 8,
  },
  {
    id: "this-or-that",
    title: "This or That",
    tier: "casual",
    category: "casual",
    icon: "⚖️",
    description: "Fast choices that reveal preferences and personality.",
    theme: "fun",
    estimatedMinutes: 10,
  },
  {
    id: "quick-choices",
    title: "Quick Choices",
    tier: "casual",
    category: "casual",
    icon: "⚡",
    description: "Answer before time runs out and compare your choices.",
    theme: "energetic",
    estimatedMinutes: 8,
  },
  {
    id: "guess-my-answer",
    title: "Guess My Answer",
    tier: "casual",
    category: "casual",
    icon: "🎯",
    description: "Guess what the other player would choose.",
    theme: "playful",
    estimatedMinutes: 12,
  },
  {
    id: "story-starter",
    title: "AI Story Starter",
    tier: "casual",
    category: "casual",
    icon: "📖",
    description: "Create a surprising story together one choice at a time.",
    theme: "creative",
    estimatedMinutes: 15,
  },
  {
    id: "daily-fun",
    title: "Daily Fun Challenge",
    tier: "casual",
    category: "casual",
    icon: "🌞",
    description: "A different shared challenge every day.",
    theme: "daily",
    estimatedMinutes: 7,
  },

  // Friendship — 10
  {
    id: "would-you-rather",
    title: "Would You Rather",
    tier: "friendship",
    category: "friendship",
    icon: "🤔",
    description: "Unexpected choices followed by deeper discussion.",
    theme: "discussion",
    estimatedMinutes: 15,
  },
  {
    id: "friend-adventure",
    title: "AI Adventure",
    tier: "friendship",
    category: "friendship",
    icon: "🗺️",
    description: "Make decisions together inside a changing adventure.",
    theme: "adventure",
    estimatedMinutes: 20,
  },
  {
    id: "mystery-box",
    title: "Mystery Box",
    tier: "friendship",
    category: "friendship",
    icon: "🎁",
    description: "Open unpredictable challenges, questions and surprises.",
    theme: "mystery",
    estimatedMinutes: 15,
  },
  {
    id: "personality-match",
    title: "Personality Match",
    tier: "friendship",
    category: "friendship",
    icon: "🧩",
    description: "Explore similarities and differences without judgement.",
    theme: "personality",
    estimatedMinutes: 18,
  },
  {
    id: "best-friend-quiz",
    title: "Best Friend Quiz",
    tier: "friendship",
    category: "friendship",
    icon: "🏆",
    description: "Find out how well you understand one another.",
    theme: "quiz",
    estimatedMinutes: 15,
  },
  {
    id: "draw-together",
    title: "Draw Together",
    tier: "friendship",
    category: "friendship",
    icon: "🎨",
    description: "Create, describe and guess drawings together.",
    theme: "creative",
    estimatedMinutes: 20,
  },
  {
    id: "build-a-story",
    title: "Build a Story",
    tier: "friendship",
    category: "friendship",
    icon: "✍️",
    description: "Take turns shaping characters, twists and endings.",
    theme: "story",
    estimatedMinutes: 20,
  },
  {
    id: "memory-lane",
    title: "Memory Lane",
    tier: "friendship",
    category: "friendship",
    icon: "🧠",
    description: "Share memorable moments and discover new stories.",
    theme: "memory",
    estimatedMinutes: 18,
  },
  {
    id: "team-escape",
    title: "Team Escape",
    tier: "friendship",
    category: "friendship",
    icon: "🔐",
    description: "Solve a cooperative AI-hosted escape challenge.",
    theme: "puzzle",
    estimatedMinutes: 25,
  },
  {
    id: "challenge-arena",
    title: "Challenge Arena",
    tier: "friendship",
    category: "friendship",
    icon: "🔥",
    description: "Compete through quick social and creative rounds.",
    theme: "competitive",
    estimatedMinutes: 20,
  },

  // Love — 20
  {
    id: "ai-date-night",
    title: "AI Date Night",
    tier: "love",
    category: "love",
    icon: "🌹",
    description: "A changing AI-hosted date with questions and challenges.",
    theme: "romantic",
    estimatedMinutes: 30,
  },
  {
    id: "truth-or-dare",
    title: "Truth or Dare AI",
    tier: "love",
    category: "love",
    icon: "🎭",
    description: "Consent-based truth or dare with adjustable depth.",
    theme: "flirty",
    estimatedMinutes: 25,
    adultEligible: true,
  },
  {
    id: "deep-conversations",
    title: "Deep Conversations",
    tier: "love",
    category: "love",
    icon: "🌙",
    description: "Explore feelings, values, memories and hopes together.",
    theme: "deep",
    estimatedMinutes: 30,
    adultEligible: true,
  },
  {
    id: "love-compatibility",
    title: "Love Compatibility",
    tier: "love",
    category: "love",
    icon: "💞",
    description: "Compare perspectives across real relationship situations.",
    theme: "compatibility",
    estimatedMinutes: 25,
  },
  {
    id: "our-love-story",
    title: "Our Love Story",
    tier: "love",
    category: "love",
    icon: "📕",
    description: "Build a personalised story inspired by both players.",
    theme: "story",
    estimatedMinutes: 30,
  },
  {
    id: "future-together",
    title: "Dream Future Together",
    tier: "love",
    category: "love",
    icon: "🌅",
    description: "Imagine future adventures, goals and shared plans.",
    theme: "future",
    estimatedMinutes: 25,
  },
  {
    id: "virtual-date",
    title: "Virtual Date",
    tier: "love",
    category: "love",
    icon: "🥂",
    description: "Enter a changing virtual location and enjoy a guided date.",
    theme: "date",
    estimatedMinutes: 30,
  },
  {
    id: "relationship-challenge",
    title: "Relationship Challenge",
    tier: "love",
    category: "love",
    icon: "🤝",
    description: "Complete communication and understanding challenges.",
    theme: "relationship",
    estimatedMinutes: 25,
  },
  {
    id: "secret-thoughts",
    title: "Secret Thoughts",
    tier: "love",
    category: "love",
    icon: "🔮",
    description: "Share thoughts only when you feel comfortable.",
    theme: "intimate",
    estimatedMinutes: 25,
    adultEligible: true,
  },
  {
    id: "guess-my-feelings",
    title: "Guess My Feelings",
    tier: "love",
    category: "love",
    icon: "💭",
    description: "Guess and discuss how the other person might feel.",
    theme: "emotional",
    estimatedMinutes: 20,
  },
  {
    id: "couple-decisions",
    title: "Couple Decisions",
    tier: "love",
    category: "love",
    icon: "🛤️",
    description:
        "Make shared choices inside realistic and fictional scenarios.",
    theme: "decisions",
    estimatedMinutes: 25,
  },
  {
    id: "romantic-adventure",
    title: "Romantic Adventure",
    tier: "love",
    category: "love",
    icon: "🏰",
    description: "A cooperative romance adventure with changing outcomes.",
    theme: "adventure",
    estimatedMinutes: 35,
  },
  {
    id: "bucket-list",
    title: "Bucket List Together",
    tier: "love",
    category: "love",
    icon: "📝",
    description: "Create and explore a shared list of future experiences.",
    theme: "future",
    estimatedMinutes: 20,
  },
  {
    id: "dream-home",
    title: "Dream Home Builder",
    tier: "love",
    category: "love",
    icon: "🏡",
    description: "Design a fictional dream home through shared choices.",
    theme: "creative",
    estimatedMinutes: 25,
  },
  {
    id: "future-family",
    title: "Future Family",
    tier: "love",
    category: "love",
    icon: "🌳",
    description: "Discuss future values and lifestyle choices respectfully.",
    theme: "future",
    estimatedMinutes: 25,
  },
  {
    id: "couple-escape",
    title: "Couple Escape Room",
    tier: "love",
    category: "love",
    icon: "🗝️",
    description: "Solve an AI-generated romantic mystery together.",
    theme: "mystery",
    estimatedMinutes: 35,
  },
  {
    id: "love-journey",
    title: "Love Journey RPG",
    tier: "love",
    category: "love",
    icon: "🧭",
    description: "Play as partners inside an evolving interactive journey.",
    theme: "rpg",
    estimatedMinutes: 40,
  },
  {
    id: "ai-movie-night",
    title: "AI Movie Night",
    tier: "love",
    category: "love",
    icon: "🎬",
    description: "Star together in a changing interactive movie scenario.",
    theme: "cinematic",
    estimatedMinutes: 30,
  },
  {
    id: "relationship-reflection",
    title: "Relationship Reflection",
    tier: "love",
    category: "love",
    icon: "🪞",
    description: "Reflect on communication and shared strengths for fun.",
    theme: "reflection",
    estimatedMinutes: 25,
  },
  {
    id: "surprise-me",
    title: "Surprise Me",
    tier: "love",
    category: "love",
    icon: "✨",
    description: "Let the AI host choose a completely unexpected experience.",
    theme: "surprise",
    estimatedMinutes: 25,
    adultEligible: true,
  },
]);

/**
 * Normalizes a subscription tier.
 *
 * @param {*} value Raw tier.
 * @return {string} Supported tier.
 */
function normalizeTier(value) {
  const tier = String(value || "")
      .trim()
      .toLowerCase();

  return Object.prototype.hasOwnProperty.call(
      TIER_RANK,
      tier,
  ) ? tier : "casual";
}

/**
 * Returns whether a user tier can access an experience.
 *
 * @param {string} userTier User tier.
 * @param {string} requiredTier Required tier.
 * @return {boolean} Access result.
 */
function hasTierAccess(userTier, requiredTier) {
  return TIER_RANK[normalizeTier(userTier)] >=
      TIER_RANK[normalizeTier(requiredTier)];
}

/**
 * Normalizes a comfort level.
 *
 * @param {*} value Raw comfort level.
 * @return {string} Supported comfort level.
 */
function normalizeComfort(value) {
  const comfort = String(value || "")
      .trim()
      .toLowerCase();

  return Object.prototype.hasOwnProperty.call(
      COMFORT_RANK,
      comfort,
  ) ? comfort : "standard";
}

/**
 * Finds the lowest mutually accepted comfort level.
 *
 * @param {string} first First comfort level.
 * @param {string} second Second comfort level.
 * @param {boolean} adultEligible Whether mature mode is allowed.
 * @return {string} Effective comfort level.
 */
function effectiveComfort(
    first,
    second,
    adultEligible,
) {
  const firstLevel = normalizeComfort(first);
  const secondLevel = normalizeComfort(second);

  const rank = Math.min(
      COMFORT_RANK[firstLevel],
      COMFORT_RANK[secondLevel],
  );

  if (rank >= COMFORT_RANK.mature &&
      adultEligible !== true) {
    return "romantic";
  }

  return Object.keys(COMFORT_RANK).find(
      (key) => COMFORT_RANK[key] === rank,
  ) || "standard";
}

/**
 * Creates a new server-selected prompt.
 *
 * @param {Object} session Current session.
 * @return {Object} Prompt payload.
 */
function createPrompt(session) {
  const comfort = normalizeComfort(
      session.effectiveComfort,
  );

  const bank = PROMPT_BANK[comfort] ||
      PROMPT_BANK.standard;

  const usedPromptIds =
      Array.isArray(session.usedPromptIds) ?
      session.usedPromptIds :
      [];

  const available = bank
      .map((prompt, index) => ({
        ...prompt,
        sourceIndex: index,
      }))
      .filter((prompt) =>
        !usedPromptIds.includes(
            `${comfort}_${prompt.sourceIndex}`,
        ),
      );

  const candidates =
      available.length > 0 ? available : bank.map(
          (prompt, index) => ({
            ...prompt,
            sourceIndex: index,
          }),
      );

  const selected = candidates[
      crypto.randomInt(0, candidates.length)
  ];

  return {
    id: `${comfort}_${selected.sourceIndex}`,
    type: selected.type,
    text: selected.text,
    comfort,
    language: session.language || "en",
    source: "curated_v1",
    createdAt: Date.now(),
  };
}

/**
 * Returns the tier used for AI request limits.
 *
 * @param {Object} account Account data.
 * @return {string} Supported usage tier.
 */
function resolveAiTier(account) {
  return normalizeTier(
      account.tier ||
      account.subTier ||
      account.subscriptionPlan,
  );
}

/**
 * Creates an OpenAI prompt or a curated fallback.
 *
 * The OpenAI request is intentionally executed outside Firestore
 * transactions. Any provider, schema, timeout or usage-limit error
 * falls back to the existing curated prompt engine.
 *
 * @param {Object} options Prompt-generation options.
 * @param {Object} options.session Current Play Together session.
 * @param {string} options.uid User requesting generation.
 * @param {string} options.tier User subscription tier.
 * @param {number} options.targetRound Target round number.
 * @return {Promise<Object>} Stored prompt payload.
 */
async function buildPromptWithFallback({
  session,
  uid,
  tier,
  targetRound,
}) {
  try {
    await reserveAiUsage(
        uid,
        "playTogetherPrompt",
        tier,
    );

    const generated = await generatePlayPrompt({
      experienceId: session.experienceId,
      experienceTitle: session.experienceTitle,
      language: session.language || "en",
      comfortLevel:
          session.effectiveComfort || "standard",
      currentRound: targetRound,
      maximumRounds:
          Number(session.maxRounds || 10),
      usedPromptTexts:
          Array.isArray(session.usedPromptTexts) ?
          session.usedPromptTexts :
          [],
    });

    return {
      id: `ai_${crypto.randomUUID()}`,
      type: generated.type,
      text: generated.text,
      comfort:
          session.effectiveComfort || "standard",
      language: session.language || "en",
      source: "openai",
      hostIntroduction:
          generated.hostIntroduction || "",
      followUpHint:
          generated.followUpHint || "",
      visualTheme:
          generated.visualTheme || "",
      consentReminder:
          generated.consentReminder || "",
      createdAt: Date.now(),
    };
  } catch (error) {
    console.warn(
        "Play Together AI prompt fallback:",
        error && error.message ?
        error.message :
        String(error),
    );

    const fallback = createPrompt(session);

    return {
      ...fallback,
      id: `fallback_${crypto.randomUUID()}`,
      source: "curated_fallback",
    };
  }
}

/**
 * Generates an optional reaction to both player responses.
 *
 * A failed reaction must never prevent the next game round.
 *
 * @param {Object} options Reaction options.
 * @param {Object} options.session Current session.
 * @param {string} options.uid Requesting user ID.
 * @param {string} options.tier User tier.
 * @return {Promise<Object|null>} AI reaction or null.
 */
async function buildHostReaction({
  session,
  uid,
  tier,
}) {
  try {
    await reserveAiUsage(
        uid,
        "playTogetherReaction",
        tier,
    );

    const hostResponse =
        session.hostResponse || {};

    const guestResponse =
        session.guestResponse || {};

    return await generateHostReaction({
      experienceId: session.experienceId,
      language: session.language || "en",
      prompt:
          session.currentPrompt &&
          session.currentPrompt.text ?
          session.currentPrompt.text :
          "",
      firstResponse: hostResponse.skipped === true ?
          "Skipped" :
          String(hostResponse.text || ""),
      secondResponse: guestResponse.skipped === true ?
          "Skipped" :
          String(guestResponse.text || ""),
    });
  } catch (error) {
    console.warn(
        "Play Together AI reaction skipped:",
        error && error.message ?
        error.message :
        String(error),
    );

    return null;
  }
}

/**
 * Returns whether an abandoned generation lock can be reclaimed.
 *
 * @param {Object} session Session data.
 * @return {boolean} Whether the lock is stale.
 */
function generationLockExpired(session) {
  const startedAt = Number(
      session.generationStartedAtMs || 0,
  );

  if (startedAt <= 0) {
    return true;
  }

  return Date.now() - startedAt > 45000;
}

/**
 * Finds an experience.
 *
 * @param {string} experienceId Experience ID.
 * @return {Object|null} Experience or null.
 */
function findExperience(experienceId) {
  return EXPERIENCES.find(
      (experience) => experience.id === experienceId,
  ) || null;
}

/**
 * Creates a short invitation code.
 *
 * @return {string} Invitation code.
 */
function createInviteCode() {
  return crypto.randomBytes(4)
      .toString("hex")
      .toUpperCase();
}

/**
 * Returns a safe public session payload.
 *
 * @param {string} sessionId Session ID.
 * @param {Object} session Session data.
 * @return {Object} Public session.
 */
function publicSession(sessionId, session) {
  return {
    sessionId,
    experienceId: session.experienceId,
    experienceTitle: session.experienceTitle,
    status: session.status,
    hostUid: session.hostUid,
    guestUid: session.guestUid || null,
    inviteCode: session.inviteCode,
    language: session.language,
    comfortLevel: session.comfortLevel,
    hostComfort: session.hostComfort || "standard",
    guestComfort: session.guestComfort || "standard",
    effectiveComfort:
        session.effectiveComfort || "standard",
    adultEligible: session.adultEligible === true,
    hostReady: session.hostReady === true,
    guestReady: session.guestReady === true,
    currentRound: Number(session.currentRound || 0),
    maxRounds: Number(session.maxRounds || 10),
    currentPrompt: session.currentPrompt || null,
    hostResponse: session.hostResponse || null,
    guestResponse: session.guestResponse || null,
    replacementCount:
        Number(session.replacementCount || 0),
    hostReaction: session.hostReaction || null,
    generationState:
        session.status === "generating" ?
        "generating" :
        "idle",
    createdAt: session.createdAt || null,
  };
}

exports.getPlayExperiences = onCall(
    async (request) => {
      const uid = assertAuth(request);

      const account = await assertAccountUsable(uid);
      const userTier = normalizeTier(
          account.data.tier ||
          account.data.subTier ||
          account.data.subscriptionPlan,
      );

      return {
        userTier,
        total: EXPERIENCES.length,
        experiences: EXPERIENCES.map((experience) => ({
          ...experience,
          accessible: hasTierAccess(
              userTier,
              experience.tier,
          ),
        })),
      };
    },
);

exports.createPlaySession = onCall(
    async (request) => {
      const hostUid = assertAuth(request);
      const account = await assertAccountUsable(hostUid);

      const data = request.data || {};
      const experienceId = String(
          data.experienceId || "",
      ).trim();

      const experience = findExperience(experienceId);

      if (!experience) {
        throw new HttpsError(
            "not-found",
            "Play experience not found",
        );
      }

      const userTier = normalizeTier(
          account.data.tier ||
          account.data.subTier ||
          account.data.subscriptionPlan,
      );

      if (!hasTierAccess(userTier, experience.tier)) {
        throw new HttpsError(
            "permission-denied",
            `${experience.tier} plan required`,
        );
      }

      const language = String(
          data.language ||
          account.data.appLanguage ||
          "en",
      ).trim().toLowerCase();

      const comfortLevel = String(
          data.comfortLevel || "standard",
      ).trim().toLowerCase();

      const inviteCode = createInviteCode();

      const sessionReference = db()
          .collection("playSessions")
          .doc();

      const session = {
        experienceId: experience.id,
        experienceTitle: experience.title,
        experienceTier: experience.tier,
        hostUid,
        guestUid: null,
        participants: [hostUid],
        inviteCode,
        language,
        comfortLevel,
        hostComfort: comfortLevel,
        guestComfort: "standard",
        effectiveComfort: "standard",
        adultEligible: experience.adultEligible === true,
        status: "waiting",
        hostReady: false,
        guestReady: false,
        currentRound: 0,
        maxRounds: 10,
        currentPrompt: null,
        hostResponse: null,
        guestResponse: null,
        replacementCount: 0,
        usedPromptIds: [],
        usedPromptTexts: [],
        hostReaction: null,
        generationToken: null,
        generationStartedAtMs: null,
        promptVersion: 0,
        createdAt: timestamp(),
        updatedAt: timestamp(),
      };

      await sessionReference.set(session);

      return publicSession(
          sessionReference.id,
          session,
      );
    },
);

exports.joinPlaySession = onCall(
    async (request) => {
      const guestUid = assertAuth(request);
      const account = await assertAccountUsable(guestUid);

      const inviteCode = String(
          request.data && request.data.inviteCode || "",
      ).trim().toUpperCase();

      if (!inviteCode) {
        throw new HttpsError(
            "invalid-argument",
            "Invite code required",
        );
      }

      const query = await db()
          .collection("playSessions")
          .where("inviteCode", "==", inviteCode)
          .limit(1)
          .get();

      if (query.empty) {
        throw new HttpsError(
            "not-found",
            "Play session not found",
        );
      }

      const snapshot = query.docs[0];
      const reference = snapshot.ref;

      await db().runTransaction(async (transaction) => {
        const currentSnapshot =
            await transaction.get(reference);

        const session =
            currentSnapshot.data() || {};

        if (session.hostUid === guestUid) {
          return;
        }

        if (session.status !== "waiting") {
          throw new HttpsError(
              "failed-precondition",
              "Session is no longer accepting players",
          );
        }

        if (session.guestUid &&
            session.guestUid !== guestUid) {
          throw new HttpsError(
              "already-exists",
              "Session already has two players",
          );
        }

        const guestTier = normalizeTier(
            account.data.tier ||
            account.data.subTier ||
            account.data.subscriptionPlan,
        );

        if (!hasTierAccess(
            guestTier,
            session.experienceTier,
        )) {
          throw new HttpsError(
              "permission-denied",
              `${session.experienceTier} plan required`,
          );
        }

        transaction.update(reference, {
          guestUid,
          participants: [
            session.hostUid,
            guestUid,
          ],
          guestReady: false,
          guestComfort: normalizeComfort(
              request.data &&
              request.data.comfortLevel,
          ),
          updatedAt: timestamp(),
        });
      });

      const updated = await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.setPlayReady = onCall(
    {
      secrets: ["OPENAI_API_KEY"],
      timeoutSeconds: 30,
      memory: "256MiB",
    },
    async (request) => {
      const uid = assertAuth(request);
      const account =
          await assertAccountUsable(uid);

      const tier = resolveAiTier(account.data);

      const sessionId = String(
          request.data &&
          request.data.sessionId ||
          "",
      ).trim();

      const ready =
          request.data &&
          request.data.ready === true;

      if (!sessionId) {
        throw new HttpsError(
            "invalid-argument",
            "sessionId required",
        );
      }

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      const generationToken =
          crypto.randomUUID();

      let generationSession = null;

      await db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(reference);

            if (!snapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Play session not found",
              );
            }

            const session =
                snapshot.data() || {};

            const isHost =
                session.hostUid === uid;

            const isGuest =
                session.guestUid === uid;

            if (!isHost && !isGuest) {
              throw new HttpsError(
                  "permission-denied",
                  "You are not part of this session",
              );
            }

            const update = {
              updatedAt: timestamp(),
            };

            if (isHost) {
              update.hostReady = ready;
            }

            if (isGuest) {
              update.guestReady = ready;
            }

            const hostReady = isHost ?
              ready :
              session.hostReady === true;

            const guestReady = isGuest ?
              ready :
              session.guestReady === true;

            if (!ready) {
              update.status = "waiting";
              update.generationToken = null;
              update.generationStartedAtMs = null;

              transaction.update(
                  reference,
                  update,
              );
              return;
            }

            const canGenerate =
                session.guestUid &&
                hostReady &&
                guestReady &&
                (
                  session.status === "waiting" ||
                  (
                    session.status === "generating" &&
                    generationLockExpired(session)
                  )
                );

            if (!canGenerate) {
              transaction.update(
                  reference,
                  update,
              );
              return;
            }

            const effective = effectiveComfort(
                session.hostComfort,
                session.guestComfort,
                session.adultEligible === true,
            );

            generationSession = {
              ...session,
              hostReady,
              guestReady,
              effectiveComfort: effective,
            };

            update.status = "generating";
            update.effectiveComfort = effective;
            update.generationToken =
                generationToken;
            update.generationStartedAtMs =
                Date.now();

            transaction.update(
                reference,
                update,
            );
          },
      );

      if (generationSession) {
        const targetRound =
            Number(
                generationSession.currentRound || 0,
            ) + 1;

        const prompt =
            await buildPromptWithFallback({
              session: generationSession,
              uid,
              tier,
              targetRound,
            });

        await db().runTransaction(
            async (transaction) => {
              const snapshot =
                  await transaction.get(reference);

              if (!snapshot.exists) {
                return;
              }

              const current =
                  snapshot.data() || {};

              if (
                current.status !== "generating" ||
                current.generationToken !==
                    generationToken
              ) {
                return;
              }

              transaction.update(reference, {
                status: "playing",
                currentRound: targetRound,
                currentPrompt: prompt,
                usedPromptIds: [
                  ...(current.usedPromptIds || []),
                  prompt.id,
                ],
                usedPromptTexts: [
                  ...(current.usedPromptTexts || []),
                  prompt.text,
                ].slice(-50),
                hostResponse: null,
                guestResponse: null,
                hostReaction: null,
                generationToken: null,
                generationStartedAtMs: null,
                startedAt:
                    current.startedAt ||
                    timestamp(),
                promptVersion:
                    Number(
                        current.promptVersion || 0,
                    ) + 1,
                updatedAt: timestamp(),
              });
            },
        );
      }

      const updated =
          await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.getPlaySession = onCall(
    async (request) => {
      const uid = assertAuth(request);
      const sessionId = String(
          request.data && request.data.sessionId || "",
      ).trim();

      const snapshot = await db()
          .collection("playSessions")
          .doc(sessionId)
          .get();

      if (!snapshot.exists) {
        throw new HttpsError(
            "not-found",
            "Play session not found",
        );
      }

      const session = snapshot.data() || {};
      const participants =
          Array.isArray(session.participants) ?
          session.participants :
          [];

      if (!participants.includes(uid)) {
        throw new HttpsError(
            "permission-denied",
            "You are not part of this session",
        );
      }

      return publicSession(snapshot.id, session);
    },
);


exports.setPlayComfort = onCall(
    async (request) => {
      const uid = assertAuth(request);
      const sessionId = String(
          request.data && request.data.sessionId || "",
      ).trim();

      const comfort = normalizeComfort(
          request.data && request.data.comfortLevel,
      );

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      await db().runTransaction(async (transaction) => {
        const snapshot =
            await transaction.get(reference);

        if (!snapshot.exists) {
          throw new HttpsError(
              "not-found",
              "Play session not found",
          );
        }

        const session = snapshot.data() || {};
        const isHost = session.hostUid === uid;
        const isGuest = session.guestUid === uid;

        if (!isHost && !isGuest) {
          throw new HttpsError(
              "permission-denied",
              "You are not part of this session",
          );
        }

        if (session.status === "playing") {
          throw new HttpsError(
              "failed-precondition",
              "Comfort level cannot change after play begins",
          );
        }

        transaction.update(reference, {
          [isHost ? "hostComfort" : "guestComfort"]:
              comfort,
          [isHost ? "hostReady" : "guestReady"]:
              false,
          status: "waiting",
          updatedAt: timestamp(),
        });
      });

      const updated = await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.submitPlayResponse = onCall(
    async (request) => {
      const uid = assertAuth(request);
      const data = request.data || {};
      const sessionId = String(
          data.sessionId || "",
      ).trim();

      const response = String(
          data.response || "",
      ).trim();

      if (!response) {
        throw new HttpsError(
            "invalid-argument",
            "Response required",
        );
      }

      if (response.length > 1000) {
        throw new HttpsError(
            "invalid-argument",
            "Response is too long",
        );
      }

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      await db().runTransaction(async (transaction) => {
        const snapshot =
            await transaction.get(reference);

        if (!snapshot.exists) {
          throw new HttpsError(
              "not-found",
              "Play session not found",
          );
        }

        const session = snapshot.data() || {};
        const isHost = session.hostUid === uid;
        const isGuest = session.guestUid === uid;

        if (!isHost && !isGuest) {
          throw new HttpsError(
              "permission-denied",
              "You are not part of this session",
          );
        }

        if (session.status !== "playing") {
          throw new HttpsError(
              "failed-precondition",
              "Session is not currently playing",
          );
        }

        transaction.update(reference, {
          [isHost ? "hostResponse" : "guestResponse"]: {
            text: response,
            skipped: false,
            submittedAt: Date.now(),
          },
          updatedAt: timestamp(),
        });
      });

      const updated = await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.skipPlayPrompt = onCall(
    async (request) => {
      const uid = assertAuth(request);
      const sessionId = String(
          request.data && request.data.sessionId || "",
      ).trim();

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      await db().runTransaction(async (transaction) => {
        const snapshot =
            await transaction.get(reference);

        if (!snapshot.exists) {
          throw new HttpsError(
              "not-found",
              "Play session not found",
          );
        }

        const session = snapshot.data() || {};
        const isHost = session.hostUid === uid;
        const isGuest = session.guestUid === uid;

        if (!isHost && !isGuest) {
          throw new HttpsError(
              "permission-denied",
              "You are not part of this session",
          );
        }

        transaction.update(reference, {
          [isHost ? "hostResponse" : "guestResponse"]: {
            text: "",
            skipped: true,
            submittedAt: Date.now(),
          },
          updatedAt: timestamp(),
        });
      });

      const updated = await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.replacePlayPrompt = onCall(
    {
      secrets: ["OPENAI_API_KEY"],
      timeoutSeconds: 30,
      memory: "256MiB",
    },
    async (request) => {
      const uid = assertAuth(request);
      const account =
          await assertAccountUsable(uid);

      const tier = resolveAiTier(account.data);

      const sessionId = String(
          request.data &&
          request.data.sessionId ||
          "",
      ).trim();

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      const generationToken =
          crypto.randomUUID();

      let generationSession = null;

      await db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(reference);

            if (!snapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Play session not found",
              );
            }

            const session =
                snapshot.data() || {};

            const participants =
                Array.isArray(session.participants) ?
                session.participants :
                [];

            if (!participants.includes(uid)) {
              throw new HttpsError(
                  "permission-denied",
                  "You are not part of this session",
              );
            }

            if (session.status !== "playing") {
              throw new HttpsError(
                  "failed-precondition",
                  "Session is not currently playing",
              );
            }

            const replacementCount =
                Number(
                    session.replacementCount || 0,
                );

            if (replacementCount >= 5) {
              throw new HttpsError(
                  "resource-exhausted",
                  "Replacement limit reached",
              );
            }

            generationSession = session;

            transaction.update(reference, {
              status: "generating",
              generationToken,
              generationStartedAtMs:
                  Date.now(),
              updatedAt: timestamp(),
            });
          },
      );

      const prompt =
          await buildPromptWithFallback({
            session: generationSession,
            uid,
            tier,
            targetRound:
                Number(
                    generationSession.currentRound || 1,
                ),
          });

      await db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(reference);

            if (!snapshot.exists) {
              return;
            }

            const current =
                snapshot.data() || {};

            if (
              current.status !== "generating" ||
              current.generationToken !==
                  generationToken
            ) {
              return;
            }

            transaction.update(reference, {
              status: "playing",
              currentPrompt: prompt,
              usedPromptIds: [
                ...(current.usedPromptIds || []),
                prompt.id,
              ],
              usedPromptTexts: [
                ...(current.usedPromptTexts || []),
                prompt.text,
              ].slice(-50),
              hostResponse: null,
              guestResponse: null,
              hostReaction: null,
              replacementCount:
                  Number(
                      current.replacementCount || 0,
                  ) + 1,
              generationToken: null,
              generationStartedAtMs: null,
              promptVersion:
                  Number(
                      current.promptVersion || 0,
                  ) + 1,
              updatedAt: timestamp(),
            });
          },
      );

      const updated =
          await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.nextPlayPrompt = onCall(
    {
      secrets: ["OPENAI_API_KEY"],
      timeoutSeconds: 30,
      memory: "256MiB",
    },
    async (request) => {
      const uid = assertAuth(request);
      const account =
          await assertAccountUsable(uid);

      const tier = resolveAiTier(account.data);

      const sessionId = String(
          request.data &&
          request.data.sessionId ||
          "",
      ).trim();

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      const generationToken =
          crypto.randomUUID();

      let generationSession = null;
      let shouldComplete = false;

      await db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(reference);

            if (!snapshot.exists) {
              throw new HttpsError(
                  "not-found",
                  "Play session not found",
              );
            }

            const session =
                snapshot.data() || {};

            const participants =
                Array.isArray(session.participants) ?
                session.participants :
                [];

            if (!participants.includes(uid)) {
              throw new HttpsError(
                  "permission-denied",
                  "You are not part of this session",
              );
            }

            if (session.status !== "playing") {
              throw new HttpsError(
                  "failed-precondition",
                  "Session is not currently playing",
              );
            }

            if (
              !session.hostResponse ||
              !session.guestResponse
            ) {
              throw new HttpsError(
                  "failed-precondition",
                  "Both players must answer or skip",
              );
            }

            const currentRound =
                Number(session.currentRound || 0);

            const maxRounds =
                Number(session.maxRounds || 10);

            if (currentRound >= maxRounds) {
              shouldComplete = true;

              transaction.update(reference, {
                status: "completed",
                completedAt: timestamp(),
                updatedAt: timestamp(),
              });

              return;
            }

            generationSession = session;

            transaction.update(reference, {
              status: "generating",
              generationToken,
              generationStartedAtMs:
                  Date.now(),
              updatedAt: timestamp(),
            });
          },
      );

      if (shouldComplete) {
        const completed =
            await reference.get();

        return publicSession(
            completed.id,
            completed.data() || {},
        );
      }

      const targetRound =
          Number(
              generationSession.currentRound || 0,
          ) + 1;

      const [prompt, reaction] =
          await Promise.all([
            buildPromptWithFallback({
              session: generationSession,
              uid,
              tier,
              targetRound,
            }),
            buildHostReaction({
              session: generationSession,
              uid,
              tier,
            }),
          ]);

      await db().runTransaction(
          async (transaction) => {
            const snapshot =
                await transaction.get(reference);

            if (!snapshot.exists) {
              return;
            }

            const current =
                snapshot.data() || {};

            if (
              current.status !== "generating" ||
              current.generationToken !==
                  generationToken
            ) {
              return;
            }

            transaction.update(reference, {
              status: "playing",
              currentRound: targetRound,
              currentPrompt: prompt,
              usedPromptIds: [
                ...(current.usedPromptIds || []),
                prompt.id,
              ],
              usedPromptTexts: [
                ...(current.usedPromptTexts || []),
                prompt.text,
              ].slice(-50),
              hostResponse: null,
              guestResponse: null,
              hostReaction: reaction,
              generationToken: null,
              generationStartedAtMs: null,
              promptVersion:
                  Number(
                      current.promptVersion || 0,
                  ) + 1,
              updatedAt: timestamp(),
            });
          },
      );

      const updated =
          await reference.get();

      return publicSession(
          updated.id,
          updated.data() || {},
      );
    },
);

exports.leavePlaySession = onCall(
    async (request) => {
      const uid = assertAuth(request);
      const sessionId = String(
          request.data && request.data.sessionId || "",
      ).trim();

      const reference = db()
          .collection("playSessions")
          .doc(sessionId);

      await db().runTransaction(async (transaction) => {
        const snapshot =
            await transaction.get(reference);

        if (!snapshot.exists) {
          return;
        }

        const session = snapshot.data() || {};
        const participants =
            Array.isArray(session.participants) ?
            session.participants :
            [];

        if (!participants.includes(uid)) {
          throw new HttpsError(
              "permission-denied",
              "You are not part of this session",
          );
        }

        transaction.update(reference, {
          status: "ended",
          endedBy: uid,
          endedAt: timestamp(),
          updatedAt: timestamp(),
        });
      });

      return {ok: true};
    },
);

module.exports.EXPERIENCES = EXPERIENCES;
