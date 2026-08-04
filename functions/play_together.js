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

const TIER_RANK = Object.freeze({
  casual: 0,
  friendship: 1,
  love: 2,
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
    hostReady: session.hostReady === true,
    guestReady: session.guestReady === true,
    currentRound: Number(session.currentRound || 0),
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
        status: "waiting",
        hostReady: false,
        guestReady: false,
        currentRound: 0,
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
    async (request) => {
      const uid = assertAuth(request);
      const sessionId = String(
          request.data && request.data.sessionId || "",
      ).trim();

      const ready =
          request.data && request.data.ready === true;

      if (!sessionId) {
        throw new HttpsError(
            "invalid-argument",
            "sessionId required",
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

        if (session.guestUid &&
            hostReady &&
            guestReady) {
          update.status = "ready";
        } else {
          update.status = "waiting";
        }

        transaction.update(reference, update);
      });

      const updated = await reference.get();

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
