"use strict";

const {HttpsError} = require(
    "firebase-functions/v2/https",
);

const {
  db,
  timestamp,
} = require("../call_util");

const MAX_CONVERSATION_TITLE = 100;
const MAX_MESSAGE_CHARACTERS = 3000;
const MAX_MEMORY_CHARACTERS = 500;

/**
 * Returns the user's Meera data root.
 *
 * @param {string} uid Firebase user ID.
 * @return {FirebaseFirestore.DocumentReference} User ref.
 */
function userReference(uid) {
  return db()
      .collection("users")
      .doc(uid);
}

/**
 * Returns the user's Meera conversation collection.
 *
 * @param {string} uid Firebase user ID.
 * @return {FirebaseFirestore.CollectionReference} Collection.
 */
function conversationsReference(uid) {
  return userReference(uid)
      .collection("meeraConversations");
}

/**
 * Returns one conversation reference.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @return {FirebaseFirestore.DocumentReference} Document.
 */
function conversationReference(
    uid,
    conversationId,
) {
  return conversationsReference(uid)
      .doc(conversationId);
}

/**
 * Returns the user's Meera memory collection.
 *
 * @param {string} uid Firebase user ID.
 * @return {FirebaseFirestore.CollectionReference} Collection.
 */
function memoriesReference(uid) {
  return userReference(uid)
      .collection("meeraMemories");
}

/**
 * Sanitises a short text value.
 *
 * @param {*} value Raw value.
 * @param {number} maximum Maximum characters.
 * @return {string} Sanitised text.
 */
function safeText(
    value,
    maximum,
) {
  return String(value || "")
      .trim()
      .replace(/\s+/g, " ")
      .slice(0, maximum);
}

/**
 * Generates a safe conversation title.
 *
 * @param {*} value Suggested title.
 * @param {*} fallbackMessage User message.
 * @return {string} Safe title.
 */
function safeConversationTitle(
    value,
    fallbackMessage,
) {
  const supplied = safeText(
      value,
      MAX_CONVERSATION_TITLE,
  );

  if (supplied) {
    return supplied;
  }

  const fallback = safeText(
      fallbackMessage,
      60,
  );

  return fallback || "New conversation";
}

/**
 * Ensures a conversation belongs to the user.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @return {Promise<FirebaseFirestore.DocumentSnapshot>} Snapshot.
 */
async function assertConversationExists(
    uid,
    conversationId,
) {
  const safeId = safeText(
      conversationId,
      160,
  );

  if (!safeId) {
    throw new HttpsError(
        "invalid-argument",
        "Conversation ID is required",
    );
  }

  const reference =
      conversationReference(uid, safeId);

  const snapshot = await reference.get();

  if (!snapshot.exists) {
    throw new HttpsError(
        "not-found",
        "Meera conversation was not found",
    );
  }

  return snapshot;
}

/**
 * Creates one Meera conversation.
 *
 * @param {string} uid Firebase user ID.
 * @param {object} input Conversation input.
 * @return {Promise<object>} Conversation summary.
 */
async function createConversation(
    uid,
    input = {},
) {
  const reference =
      conversationsReference(uid).doc();

  const title = safeConversationTitle(
      input.title,
      input.initialMessage,
  );

  const now = timestamp();

  await reference.set({
    uid,
    title,
    languageMode:
        safeText(
            input.languageMode,
            30,
        ) || "auto",
    requestedLanguage:
        safeText(
            input.requestedLanguage,
            60,
        ),
    messageCount: 0,
    lastMessage: "",
    createdAt: now,
    updatedAt: now,
  });

  return {
    id: reference.id,
    title,
  };
}

/**
 * Ensures a conversation exists or creates one.
 *
 * @param {string} uid Firebase user ID.
 * @param {*} conversationId Requested ID.
 * @param {object} input Creation context.
 * @return {Promise<object>} Conversation details.
 */
async function ensureConversation(
    uid,
    conversationId,
    input = {},
) {
  const safeId = safeText(
      conversationId,
      160,
  );

  if (safeId) {
    await assertConversationExists(
        uid,
        safeId,
    );

    return {
      id: safeId,
      created: false,
    };
  }

  const created =
      await createConversation(uid, input);

  return {
    id: created.id,
    title: created.title,
    created: true,
  };
}

/**
 * Saves one Meera conversation message.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @param {object} message Message data.
 * @return {Promise<string>} Message ID.
 */
async function saveConversationMessage(
    uid,
    conversationId,
    message,
) {
  const role =
      message.role === "assistant" ?
        "assistant" :
        "user";

  const content = safeText(
      message.content,
      MAX_MESSAGE_CHARACTERS,
  );

  if (!content) {
    throw new HttpsError(
        "invalid-argument",
        "Message content is required",
    );
  }

  const conversation =
      conversationReference(
          uid,
          conversationId,
      );

  const messageReference =
      conversation
          .collection("messages")
          .doc();

  const now = timestamp();

  const batch = db().batch();

  batch.set(messageReference, {
    uid,
    role,
    content,
    detectedLanguage:
        safeText(
            message.detectedLanguage,
            80,
        ),
    responseLanguage:
        safeText(
            message.responseLanguage,
            80,
        ),
    category:
        safeText(
            message.category,
            80,
        ),
    requiresHumanSupport:
        message.requiresHumanSupport === true,
    createdAt: now,
  });

  batch.set(
      conversation,
      {
        lastMessage: content.slice(0, 180),
        lastRole: role,
        updatedAt: now,
        messageCount:
            require("firebase-admin")
                .firestore
                .FieldValue
                .increment(1),
      },
      {merge: true},
  );

  await batch.commit();

  return messageReference.id;
}

/**
 * Lists conversations for one user.
 *
 * @param {string} uid Firebase user ID.
 * @param {number} limit Requested limit.
 * @return {Promise<object[]>} Conversation summaries.
 */
async function listConversations(
    uid,
    limit = 30,
) {
  const safeLimit = Math.min(
      Math.max(Number(limit) || 30, 1),
      50,
  );

  const snapshot =
      await conversationsReference(uid)
          .orderBy("updatedAt", "desc")
          .limit(safeLimit)
          .get();

  return snapshot.docs.map((document) => {
    const data = document.data();

    return {
      id: document.id,
      title:
          safeConversationTitle(
              data.title,
              "",
          ),
      lastMessage:
          safeText(
              data.lastMessage,
              180,
          ),
      lastRole:
          safeText(
              data.lastRole,
              20,
          ),
      messageCount:
          Number(data.messageCount || 0),
      languageMode:
          safeText(
              data.languageMode,
              30,
          ) || "auto",
      requestedLanguage:
          safeText(
              data.requestedLanguage,
              60,
          ),
      createdAt:
          data.createdAt || null,
      updatedAt:
          data.updatedAt || null,
    };
  });
}

/**
 * Loads one conversation and recent messages.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @param {number} limit Message limit.
 * @return {Promise<object>} Conversation result.
 */
async function getConversation(
    uid,
    conversationId,
    limit = 60,
) {
  const snapshot =
      await assertConversationExists(
          uid,
          conversationId,
      );

  const safeLimit = Math.min(
      Math.max(Number(limit) || 60, 1),
      100,
  );

  const messages =
      await snapshot.ref
          .collection("messages")
          .orderBy("createdAt", "desc")
          .limit(safeLimit)
          .get();

  return {
    id: snapshot.id,
    ...snapshot.data(),
    messages: messages.docs
        .map((document) => ({
          id: document.id,
          ...document.data(),
        }))
        .reverse(),
  };
}

/**
 * Loads recent history for AI context.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @param {number} limit Message limit.
 * @return {Promise<object[]>} AI-safe history.
 */
async function loadRecentHistory(
    uid,
    conversationId,
    limit = 12,
) {
  const safeId = safeText(
      conversationId,
      160,
  );

  if (!safeId) {
    return [];
  }

  await assertConversationExists(
      uid,
      safeId,
  );

  const snapshot =
      await conversationReference(
          uid,
          safeId,
      )
          .collection("messages")
          .orderBy("createdAt", "desc")
          .limit(
              Math.min(
                  Math.max(
                      Number(limit) || 12,
                      1,
                  ),
                  20,
              ),
          )
          .get();

  return snapshot.docs
      .map((document) => {
        const data = document.data();

        return {
          role:
              data.role === "assistant" ?
                "assistant" :
                "user",
          content:
              safeText(
                  data.content,
                  1500,
              ),
        };
      })
      .reverse()
      .filter(
          (entry) => entry.content,
      );
}

/**
 * Renames one conversation.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @param {*} title New title.
 * @return {Promise<object>} Updated summary.
 */
async function renameConversation(
    uid,
    conversationId,
    title,
) {
  const snapshot =
      await assertConversationExists(
          uid,
          conversationId,
      );

  const safeTitle =
      safeConversationTitle(title, "");

  await snapshot.ref.set(
      {
        title: safeTitle,
        updatedAt: timestamp(),
      },
      {merge: true},
  );

  return {
    id: snapshot.id,
    title: safeTitle,
  };
}

/**
 * Deletes all messages from a conversation.
 *
 * @param {FirebaseFirestore.DocumentReference} conversation Conversation ref.
 * @return {Promise<void>} Completion.
 */
async function deleteConversationMessages(
    conversation,
) {
  let hasMessages = true;

  while (hasMessages) {
    const snapshot =
        await conversation
            .collection("messages")
            .limit(300)
            .get();

    hasMessages = !snapshot.empty;

    if (!hasMessages) {
      continue;
    }

    const batch = db().batch();

    for (const document of snapshot.docs) {
      batch.delete(document.ref);
    }

    await batch.commit();
  }
}

/**
 * Deletes one conversation.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} conversationId Conversation ID.
 * @return {Promise<object>} Deletion result.
 */
async function deleteConversation(
    uid,
    conversationId,
) {
  const snapshot =
      await assertConversationExists(
          uid,
          conversationId,
      );

  await deleteConversationMessages(
      snapshot.ref,
  );

  await snapshot.ref.delete();

  return {
    deleted: true,
    id: conversationId,
  };
}

/**
 * Saves a user-controlled Meera memory.
 *
 * @param {string} uid Firebase user ID.
 * @param {object} input Memory input.
 * @return {Promise<object>} Saved memory.
 */
async function saveMemory(
    uid,
    input = {},
) {
  const content = safeText(
      input.content,
      MAX_MEMORY_CHARACTERS,
  );

  if (!content) {
    throw new HttpsError(
        "invalid-argument",
        "Memory content is required",
    );
  }

  const category =
      safeText(
          input.category,
          60,
      ) || "preference";

  const reference =
      memoriesReference(uid).doc();

  const now = timestamp();

  await reference.set({
    uid,
    content,
    category,
    source:
        safeText(
            input.source,
            60,
        ) || "user_confirmed",
    active: true,
    createdAt: now,
    updatedAt: now,
  });

  return {
    id: reference.id,
    content,
    category,
  };
}

/**
 * Lists active Meera memories.
 *
 * @param {string} uid Firebase user ID.
 * @param {number} limit Memory limit.
 * @return {Promise<object[]>} Memories.
 */
async function listMemories(
    uid,
    limit = 30,
) {
  const safeLimit = Math.min(
      Math.max(Number(limit) || 30, 1),
      50,
  );

  const snapshot =
      await memoriesReference(uid)
          .where("active", "==", true)
          .limit(safeLimit)
          .get();

  return snapshot.docs.map((document) => ({
    id: document.id,
    ...document.data(),
  }));
}

/**
 * Loads a safe memory subset for Meera.
 *
 * @param {string} uid Firebase user ID.
 * @return {Promise<object[]>} Safe memories.
 */
async function loadMemoriesForContext(uid) {
  const memories =
      await listMemories(uid, 20);

  return memories.map((memory) => ({
    category:
        safeText(memory.category, 60),
    content:
        safeText(
            memory.content,
            MAX_MEMORY_CHARACTERS,
        ),
  }));
}

/**
 * Deletes one memory.
 *
 * @param {string} uid Firebase user ID.
 * @param {string} memoryId Memory ID.
 * @return {Promise<object>} Result.
 */
async function deleteMemory(
    uid,
    memoryId,
) {
  const safeId = safeText(
      memoryId,
      160,
  );

  if (!safeId) {
    throw new HttpsError(
        "invalid-argument",
        "Memory ID is required",
    );
  }

  const reference =
      memoriesReference(uid).doc(safeId);

  const snapshot = await reference.get();

  if (!snapshot.exists) {
    throw new HttpsError(
        "not-found",
        "Meera memory was not found",
    );
  }

  await reference.delete();

  return {
    deleted: true,
    id: safeId,
  };
}

/**
 * Deletes all user memories.
 *
 * @param {string} uid Firebase user ID.
 * @return {Promise<object>} Result.
 */
async function clearMemories(uid) {
  let deleted = 0;
  let hasMemories = true;

  while (hasMemories) {
    const snapshot =
        await memoriesReference(uid)
            .limit(300)
            .get();

    hasMemories = !snapshot.empty;

    if (!hasMemories) {
      continue;
    }

    const batch = db().batch();

    for (const document of snapshot.docs) {
      batch.delete(document.ref);
      deleted += 1;
    }

    await batch.commit();
  }

  return {
    deleted: true,
    deletedCount: deleted,
  };
}

module.exports = {
  safeText,
  safeConversationTitle,
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
};
