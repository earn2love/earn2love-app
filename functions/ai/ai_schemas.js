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
  AdminAssistantSchema,
};
