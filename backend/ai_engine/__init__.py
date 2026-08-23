"""Earn2Love — Advanced AI Character Engine.

A modular, provider-agnostic orchestration pipeline that powers many distinct AI
character profiles (AI chat + future Play Together AI participation). Built as a
separate reusable intelligence layer; does NOT touch the existing support bot,
chat, wallet, games, or other production systems.

Pipeline:
  user message
   -> conversation understanding
   -> character identity / world model
   -> working + long-term memory retrieval
   -> relationship / familiarity state
   -> language / cultural style resolution
   -> conversation planner
   -> provider layer (LLM, provider-agnostic)
   -> character style enforcement
   -> consistency guard -> repetition guard -> safety guard
   -> final response -> persistence / metrics

Persistence is behind a repository interface (Firestore in prod, in-memory for
tests/sandbox/evaluation). Business logic is identical regardless of backend.
"""
