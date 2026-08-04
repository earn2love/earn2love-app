"use strict";

const {z} = require("zod");

const PlayPromptSchema = z.object({
  type: z.enum([
    "truth",
    "dare",
    "choice",
    "discussion",
    "challenge",
    "story",
    "puzzle",
    "reflection",
  ]),
  text: z.string().min(5).max(700),
  hostIntroduction: z.string().min(1).max(300),
  followUpHint: z.string().max(300),
  visualTheme: z.string().min(1).max(100),
  consentReminder: z.string().max(200),
});

const HostReactionSchema = z.object({
  reaction: z.string().min(1).max(500),
  sharedInsight: z.string().max(400),
  nextRoundTone: z.enum([
    "lighter",
    "same",
    "deeper",
  ]),
});

const SupportAnswerSchema = z.object({
  answer: z.string().min(1).max(1500),
  category: z.enum([
    "account",
    "profile",
    "subscription",
    "wallet",
    "payment",
    "chat",
    "call",
    "play_together",
    "safety",
    "report",
    "technical",
    "general",
  ]),
  requiresHumanAgent: z.boolean(),
  escalationReason: z.string().max(400),
  suggestedActions: z.array(
      z.string().min(1).max(200),
  ).max(5),
});

const MeeraAssistantSchema = z.object({
  answer: z.string().min(1).max(3000),
  detectedLanguage: z.string().min(1).max(80),
  responseLanguage: z.string().min(1).max(80),
  languageMode: z.enum([
    "auto",
    "app_language",
    "fixed",
    "bilingual",
  ]),
  category: z.enum([
    "general",
    "navigation",
    "profile",
    "matching",
    "chat",
    "translation",
    "games",
    "calls",
    "wallet",
    "subscription",
    "support",
    "safety",
    "technical",
  ]),
  requiresHumanSupport: z.boolean(),
  escalationReason: z.string().max(500),
  suggestedActions: z.array(
      z.object({
        id: z.string().min(1).max(80),
        label: z.string().min(1).max(120),
        actionType: z.enum([
          "navigate",
          "insert_text",
          "copy_text",
          "open_support",
          "none",
        ]),
        payload: z.string().max(1500),
        requiresConfirmation: z.boolean(),
      }),
  ).max(5),
});

const AdminAssistantSchema = z.object({
  summary: z.string().min(1).max(1500),
  findings: z.array(
      z.string().min(1).max(400),
  ).max(10),
  suggestedActions: z.array(
      z.string().min(1).max(400),
  ).max(10),
  requiresConfirmation: z.boolean(),
  riskLevel: z.enum([
    "low",
    "medium",
    "high",
    "critical",
  ]),
});

module.exports = {
  PlayPromptSchema,
  HostReactionSchema,
  SupportAnswerSchema,
  MeeraAssistantSchema,
  AdminAssistantSchema,
};
