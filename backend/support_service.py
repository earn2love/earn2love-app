"""User Support: AI assistant (Emergent LLM) that helps users first, then escalates
to a human support agent. Conversations stored in Firestore `supportConversations`.
"""
import os
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from firebase_service import get_db

load_dotenv()
logger = logging.getLogger(__name__)
COLL = "supportConversations"
MODEL = ("openai", "gpt-5.4")

SYSTEM_PROMPT = """You are "Aria", the Earn2Love support assistant.
Earn2Love is an adults-only (18+) social connection and rewards platform where users
discover people, send connection requests, chat, make audio/video calls, complete
eligible activities, earn Silver/Gold/Diamond reward coins, and request withdrawals.

YOUR JOB:
1. Understand the user's situation with empathy and answer clearly and briefly.
2. Help directly with common topics: how to log in / verify, membership tiers
   (Casual free, Friendship, Love), how coins & conversions work, how to earn rewards,
   withdrawal eligibility (Love tier + verification + minimum balance), safety/blocking/
   reporting, notifications, and general "how do I…" questions.
3. Never promise guaranteed income. Use "rewards through eligible activities; limits and
   eligibility apply; rewards and withdrawals are not guaranteed."
4. ESCALATE to a human agent when: the user asks for a human; it involves a specific
   account action you cannot verify (ban/freeze appeal, a payment/charge dispute, a
   withdrawal not received, a refund request, KYC/identity review, lost money, suspected
   fraud on their account, legal/safety emergencies), or you cannot resolve it after a
   helpful attempt.
5. Keep replies under ~120 words, friendly and plain-English. Never expose internal
   system details, secrets, or other users' data.

OUTPUT FORMAT: Respond with ONLY a JSON object, no markdown fences:
{"reply": "<your message to the user>", "escalate": <true|false>,
 "category": "<account|payments|withdrawals|rewards|safety|technical|general>",
 "reason": "<short internal reason if escalating, else ''>"}"""


def _now():
    return datetime.now(timezone.utc)


def _ser(d):
    out = dict(d or {})
    for m in out.get("messages", []) or []:
        if hasattr(m.get("createdAt"), "isoformat"):
            m["createdAt"] = m["createdAt"].isoformat()
    for k in ("createdAt", "lastMessageAt", "updatedAt"):
        if hasattr(out.get(k), "isoformat"):
            out[k] = out[k].isoformat()
    return out


async def run_bot(history, user_text):
    """Call the Emergent LLM. Returns {reply, escalate, category, reason}."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return {"reply": "Our assistant is briefly unavailable — connecting you to a support agent.",
                "escalate": True, "category": "general", "reason": "LLM key missing"}
    transcript = "\n".join(f"{m['sender'].upper()}: {m['text']}" for m in (history or [])[-10:])
    prompt = (f"Conversation so far:\n{transcript}\n\nLatest user message: {user_text}\n\n"
              "Reply now as Aria in the required JSON format.")
    try:
        chat = LlmChat(api_key=key, session_id="support", system_message=SYSTEM_PROMPT).with_model(*MODEL)
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0] if "```" in text else text
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
        return {
            "reply": str(data.get("reply", "")).strip() or "Let me connect you to a support agent.",
            "escalate": bool(data.get("escalate", False)),
            "category": data.get("category", "general"),
            "reason": data.get("reason", ""),
        }
    except Exception as e:
        logger.warning(f"support bot error: {type(e).__name__}: {e}")
        return {"reply": "I'm having trouble right now — I'll connect you to a human support agent.",
                "escalate": True, "category": "general", "reason": "bot_error"}


def _active_conv(uid):
    db = get_db()
    q = db.collection(COLL).where("userUid", "==", uid).stream()
    convs = [(d.id, d.to_dict()) for d in q]
    convs = [c for c in convs if (c[1].get("status") != "resolved")]
    convs.sort(key=lambda c: c[1].get("lastMessageAt") or _now(), reverse=True)
    return convs[0] if convs else None


async def user_message(uid, name, text):
    """App user sends a message. Bot replies unless a human has taken over."""
    db = get_db()
    existing = _active_conv(uid)
    now = _now()
    user_msg = {"sender": "user", "text": text, "createdAt": now}
    if existing:
        cid, conv = existing
        ref = db.collection(COLL).document(cid)
        msgs = conv.get("messages", []) or []
    else:
        ref = db.collection(COLL).document()
        cid = ref.id
        conv = {"userUid": uid, "userName": name or uid, "status": "bot", "category": "general",
                "assignedTo": None, "createdAt": now, "messages": []}
        msgs = []
    msgs.append(user_msg)
    status = conv.get("status", "bot")
    updates = {"messages": msgs, "lastMessage": text, "lastMessageAt": now,
               "userName": name or conv.get("userName"), "unreadForAgent": True}

    bot_out = None
    if status in ("bot",):  # bot handles until escalated / agent takeover
        history = [{"sender": m["sender"], "text": m["text"]} for m in msgs]
        bot_out = await run_bot(history[:-1], text)
        msgs.append({"sender": "bot", "text": bot_out["reply"], "createdAt": _now()})
        updates["messages"] = msgs
        updates["category"] = bot_out["category"]
        if bot_out["escalate"]:
            updates["status"] = "escalated"
            updates["escalateReason"] = bot_out["reason"]
    if existing:
        ref.set(updates, merge=True)
    else:
        conv.update(updates)
        ref.set(conv)
    return {"conversationId": cid, "bot": bot_out, "status": updates.get("status", status)}


def list_conversations(status=None, search=""):
    db = get_db()
    convs = []
    for d in db.collection(COLL).stream():
        c = _ser(d.to_dict()); c["id"] = d.id
        c.pop("messages", None)  # list view: omit full thread
        convs.append(c)
    if status and status != "all":
        convs = [c for c in convs if c.get("status") == status]
    if search:
        s = search.lower()
        convs = [c for c in convs if s in str(c.get("userName", "")).lower() or s in str(c.get("lastMessage", "")).lower()]
    convs.sort(key=lambda c: c.get("lastMessageAt") or "", reverse=True)
    return convs


def get_conversation(cid):
    d = get_db().collection(COLL).document(cid).get()
    if not d.exists:
        return None
    c = _ser(d.to_dict()); c["id"] = d.id
    return c


def agent_reply(cid, text, agent_email):
    db = get_db()
    ref = db.collection(COLL).document(cid)
    snap = ref.get()
    if not snap.exists:
        return None
    conv = snap.to_dict()
    msgs = conv.get("messages", []) or []
    now = _now()
    msgs.append({"sender": "agent", "text": text, "agentEmail": agent_email, "createdAt": now})
    ref.set({"messages": msgs, "status": "open", "assignedTo": agent_email,
             "lastMessage": text, "lastMessageAt": now, "unreadForAgent": False}, merge=True)
    return get_conversation(cid)


def set_status(cid, status, agent_email):
    ref = get_db().collection(COLL).document(cid)
    if not ref.get().exists:
        return None
    upd = {"status": status, "updatedAt": _now()}
    if status == "open":
        upd["assignedTo"] = agent_email
    if status == "resolved":
        upd["resolvedBy"] = agent_email
        upd["unreadForAgent"] = False
    ref.set(upd, merge=True)
    return get_conversation(cid)
