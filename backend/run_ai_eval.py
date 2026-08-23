"""Offline AI engine runner (in-memory repo + real LLM). Usage:
  python run_ai_eval.py diverge   # quick 3-char divergence
  python run_ai_eval.py full      # full multi-turn battery for all 3 chars
"""
import sys, json, asyncio
from ai_engine.repository import InMemoryCharacterRepository
from ai_engine.registry import seed_reference
from ai_engine.engine import CharacterEngine
from ai_engine import evaluation as E


async def main(mode):
    repo = InMemoryCharacterRepository()
    ids = seed_reference(repo)
    engine = CharacterEngine(repo)
    if mode == "diverge":
        out = await E.run_divergence(engine, ids)
    else:
        out = await E.run_full(engine, ids)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "diverge"))
