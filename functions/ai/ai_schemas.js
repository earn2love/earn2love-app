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

const MeeraChatAssistSchema = z.object({
  result: z.string().min(1).max(2000),
  alternatives: z.array(
      z.string().min(1).max(1000),
  ).max(4),
  detectedLanguage: z.string().min(1).max(80),
  responseLanguage: z.string().min(1).max(80),
  detectedTone: z.enum([
    "neutral",
    "friendly",
    "warm",
    "romantic",
    "funny",
    "professional",
    "serious",
    "unclear",
  ]),
  mode: z.enum([
    "rewrite",
    "improve",
    "grammar",
    "shorten",
    "expand",
    "friendly",
    "romantic",
    "funny",
    "professional",
    "translate",
    "conversation_starter",
    "reply_suggestions",
  ]),
  safetyFiltered: z.boolean(),
  safetyNote: z.string().max(500),
});

const MeeraProfileCoachSchema = z.object({
  score: z.number().int().min(0).max(100),
  summary: z.string().min(1).max(1200),
  strengths: z.array(
      z.string().min(1).max(250),
  ).max(8),
  improvements: z.array(
      z.object({
        area: z.enum([
          "name",
          "bio",
          "interests",
          "photos",
          "languages",
          "profile_completion",
          "conversation_style",
        ]),
        priority: z.enum([
          "low",
          "medium",
          "high",
        ]),
        reason: z.string().min(1).max(350),
        suggestion: z.string().min(1).max(500),
      }),
  ).max(12),
  bioSuggestions: z.array(
      z.object({
        style: z.enum([
          "friendly",
          "confident",
          "warm",
          "playful",
          "concise",
        ]),
        bio: z.string().min(1).max(140),
      }),
  ).max(5),
  suggestedInterests: z.array(
      z.string().min(1).max(60),
  ).max(12),
  conversationStyle: z.string().min(1).max(500),
  photoGuidance: z.array(
      z.string().min(1).max(300),
  ).max(8),
  responseLanguage: z.string().min(1).max(80),
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
  MeeraChatAssistSchema,
  MeeraProfileCoachSchema,
  AdminAssistantSchema,
};
