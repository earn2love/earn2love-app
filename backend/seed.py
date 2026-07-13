import random
import uuid
from datetime import datetime, timezone, timedelta

from auth import hash_password, ROLES

random.seed(42)

UK_FIRST = ["Oliver", "Amelia", "Harry", "Isla", "Jack", "Emily", "George", "Ava", "Noah", "Sophia",
            "Charlie", "Grace", "Jacob", "Poppy", "Thomas", "Freya", "Oscar", "Lily", "William", "Ella"]
UK_LAST = ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson", "Davies", "Patel", "Robinson",
           "Wright", "Thompson", "Evans", "Walker", "White", "Roberts", "Green", "Hall", "Wood", "Clarke"]
IN_FIRST = ["Aarav", "Aditi", "Vivaan", "Ananya", "Arjun", "Diya", "Sai", "Ishika", "Reyansh", "Kiara",
            "Krishna", "Saanvi", "Ishaan", "Aadhya", "Rohan", "Myra", "Kabir", "Anika", "Vihaan", "Prisha"]
IN_LAST = ["Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Reddy", "Nair", "Rao", "Iyer",
           "Mehta", "Chopra", "Malhotra", "Bose", "Das", "Joshi", "Kapoor", "Menon", "Pillai", "Shah"]

GENDERS = ["Male", "Female", "Other", "Prefer not to say"]
TIERS = ["Casual", "Friendship", "Love"]
ACCOUNT_STATUS = ["Active", "Frozen", "Banned", "Under Review"]
VERIF_STATUS = ["Verified", "Unverified", "Pending", "Needs Review"]
COIN_TYPES = ["Silver", "Gold", "Diamond"]


def rand_dt(days_back=180):
    d = datetime.now(timezone.utc) - timedelta(days=random.randint(0, days_back),
                                               hours=random.randint(0, 23),
                                               minutes=random.randint(0, 59))
    return d.isoformat()


def uid():
    return "u_" + uuid.uuid4().hex[:10]


def make_user():
    country = random.choices(["United Kingdom", "India"], weights=[45, 55])[0]
    if country == "United Kingdom":
        name = f"{random.choice(UK_FIRST)} {random.choice(UK_LAST)}"
        currency, symbol, dial = "GBP", "£", "+44"
    else:
        name = f"{random.choice(IN_FIRST)} {random.choice(IN_LAST)}"
        currency, symbol, dial = "INR", "₹", "+91"
    tier = random.choices(TIERS, weights=[55, 30, 15])[0]
    status = random.choices(ACCOUNT_STATUS, weights=[78, 8, 6, 8])[0]
    gender = random.choice(GENDERS)
    online = random.random() < 0.28 and status == "Active"
    first = name.split()[0].lower()
    return {
        "id": uid(),
        "name": name,
        "age": random.randint(18, 55),
        "gender": gender,
        "email": f"{first}{random.randint(10,999)}@example.com",
        "phone": f"{dial} {random.randint(7000000000, 9999999999)}",
        "country": country,
        "currency": currency,
        "currency_symbol": symbol,
        "tier": tier,
        "account_status": status,
        "online": online,
        "photo": f"https://i.pravatar.cc/150?u={uuid.uuid4().hex[:8]}",
        "join_date": rand_dt(365),
        "last_seen": rand_dt(10),
        "reports_count": random.choices([0, 0, 0, 1, 2, 3, 5], weights=[50, 20, 10, 8, 6, 4, 2])[0],
        "verification_status": random.choices(VERIF_STATUS, weights=[45, 35, 12, 8])[0],
        "wallet_silver": random.randint(0, 5000),
        "wallet_gold": random.randint(0, 1200),
        "wallet_diamond": random.randint(0, 400),
        "wallet_frozen": status in ("Frozen", "Banned"),
        "risk_level": random.choices(["Low", "Medium", "High"], weights=[70, 22, 8])[0],
        "lifetime_revenue": round(random.uniform(0, 1200), 2),
        "lifetime_earnings": round(random.uniform(0, 800), 2),
        "is_demo": True,
    }


async def seed_all(db):
    # Idempotent: only seed if users collection empty
    if await db.users.count_documents({}) > 0:
        return

    users = [make_user() for _ in range(250)]
    await db.users.insert_many([dict(u) for u in users])

    def ref():
        u = random.choice(users)
        return u

    # Countries
    countries = [
        {"id": "c_in", "name": "India", "code": "IN", "dial_code": "+91", "currency_code": "INR",
         "currency_symbol": "₹", "region": "APAC", "enabled": True,
         "price_casual": 0, "price_friendship": 99, "price_love": 499,
         "withdrawal_min": 10000, "audio_rate": 10, "video_rate": 25,
         "gateways": ["Razorpay", "Stripe"], "tax": 18, "is_demo": True},
        {"id": "c_uk", "name": "United Kingdom", "code": "GB", "dial_code": "+44", "currency_code": "GBP",
         "currency_symbol": "£", "region": "EU", "enabled": True,
         "price_casual": 0, "price_friendship": 4.99, "price_love": 9.99,
         "withdrawal_min": 150, "audio_rate": 10, "video_rate": 25,
         "gateways": ["Stripe", "TrueLayer"], "tax": 20, "is_demo": True},
    ]
    await db.countries.insert_many([dict(c) for c in countries])

    # Reports
    cats = ["Harassment", "Abuse", "Scam", "Fake profile", "Underage concern", "Explicit content",
            "Spam", "Impersonation", "Payment fraud", "Suspicious task activity", "Call abuse", "Other"]
    rstatus = ["Open", "Assigned", "Investigating", "Waiting for User", "Resolved", "Rejected", "Escalated"]
    prio = ["Critical", "High", "Medium", "Low"]
    reports = []
    for i in range(60):
        ru, rp = ref(), ref()
        reports.append({
            "id": f"RPT-{1000+i}", "reported_user": ru["name"], "reported_user_id": ru["id"],
            "reporter": rp["name"], "reporter_id": rp["id"], "category": random.choice(cats),
            "priority": random.choices(prio, weights=[10, 25, 40, 25])[0],
            "status": random.choice(rstatus), "created_date": rand_dt(90),
            "assigned_admin": random.choice(["Ram", "Priya", "Unassigned", "James", "Aisha"]),
            "country": ru["country"], "is_demo": True,
        })
    await db.reports.insert_many([dict(x) for x in reports])

    # Liveness verifications
    ls = ["Pending", "Approved", "Rejected", "Needs Review"]
    liveness = []
    for i in range(40):
        u = ref()
        liveness.append({
            "id": f"LV-{2000+i}", "user": u["name"], "user_id": u["id"],
            "trigger_reason": random.choice(["3 reports", "Manual request", "Withdrawal", "New device", "Task"]),
            "submitted_date": rand_dt(45), "country": u["country"],
            "confidence_score": round(random.uniform(0.4, 0.99), 2),
            "fraud_flags": random.choice([0, 0, 1, 2]), "status": random.choice(ls),
            "assigned_admin": random.choice(["Ram", "Aisha", "Unassigned"]),
            "device_ip": f"{random.randint(10,220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "is_demo": True,
        })
    await db.liveness_verifications.insert_many([dict(x) for x in liveness])

    # Identity verifications
    doctypes = ["Passport", "Driving Licence", "National ID", "Residence Permit"]
    istatus = ["Not Submitted", "Pending", "Approved", "Rejected", "Expired", "Needs Review"]
    identity = []
    for i in range(40):
        u = ref()
        identity.append({
            "id": f"IDV-{3000+i}", "user": u["name"], "user_id": u["id"],
            "verification_type": random.choice(doctypes), "country": u["country"],
            "submitted_date": rand_dt(60), "status": random.choice(istatus),
            "risk_score": random.randint(1, 99), "name_match": random.choice([True, False]),
            "dob_match": random.choice([True, True, False]), "is_demo": True,
        })
    await db.identity_verifications.insert_many([dict(x) for x in identity])

    # Subscriptions
    subs = []
    for i, u in enumerate([x for x in users if x["tier"] != "Casual"][:170]):
        price = {"Friendship": 99 if u["country"] == "India" else 4.99,
                 "Love": 499 if u["country"] == "India" else 9.99}[u["tier"]]
        subs.append({
            "id": f"SUB-{4000+i}", "user": u["name"], "user_id": u["id"], "plan": u["tier"],
            "country": u["country"], "currency": u["currency"], "amount": price,
            "status": random.choices(["Active", "Cancelled", "Past Due", "Trialing"], weights=[70, 15, 8, 7])[0],
            "started_date": rand_dt(200), "renews_date": rand_dt(30), "is_demo": True,
        })
    await db.subscriptions.insert_many([dict(x) for x in subs])

    # Payments
    gws = ["Stripe", "Razorpay", "TrueLayer"]
    ptypes = ["Subscription", "Coin top-up", "Platform fee", "Other"]
    pstatus = ["Pending", "Successful", "Failed", "Cancelled", "Refunded", "Partially Refunded", "Disputed"]
    payments = []
    for i in range(300):
        u = ref()
        payments.append({
            "id": f"PAY-{5000+i}", "user": u["name"], "user_id": u["id"],
            "gateway": random.choice(gws), "reference": "txn_" + uuid.uuid4().hex[:12],
            "country": u["country"], "currency": u["currency"],
            "amount": round(random.uniform(1, 500), 2), "payment_type": random.choice(ptypes),
            "status": random.choices(pstatus, weights=[8, 65, 10, 4, 5, 4, 4])[0],
            "created_date": rand_dt(120), "fraud_risk": random.choice(["Low", "Low", "Medium", "High"]),
            "is_demo": True,
        })
    await db.payments.insert_many([dict(x) for x in payments])

    # Wallet transactions
    wtx = []
    ttypes = ["Earned", "Purchased", "Spent", "Converted", "Withdrawn", "Manual Credit", "Manual Debit"]
    for i in range(400):
        u = ref()
        wtx.append({
            "id": f"WTX-{6000+i}", "user": u["name"], "user_id": u["id"],
            "coin_type": random.choice(COIN_TYPES), "type": random.choice(ttypes),
            "amount": random.randint(1, 500), "reason": random.choice(["Call", "Task", "Top-up", "Advert", "Adjustment", "Conversion"]),
            "status": random.choices(["Completed", "Pending", "Reversed"], weights=[85, 10, 5])[0],
            "date": rand_dt(90), "is_demo": True,
        })
    await db.wallet_transactions.insert_many([dict(x) for x in wtx])

    # Coin conversions
    conv = []
    for i in range(120):
        u = ref()
        src, dst = random.choice([("Silver", "Gold"), ("Gold", "Diamond")])
        conv.append({
            "id": f"CNV-{7000+i}", "user": u["name"], "user_id": u["id"],
            "source_coin": src, "destination_coin": dst,
            "source_amount": random.choice([3, 6, 9, 12]), "destination_amount": random.choice([2, 4, 6, 8]),
            "rate": "3:2" if u["country"] == "India" else "3:2.5", "country": u["country"],
            "status": random.choices(["Completed", "Pending", "Failed", "Reversed", "Under Review"], weights=[70, 12, 8, 5, 5])[0],
            "created_date": rand_dt(90), "risk_flags": random.choice([0, 0, 1, 2]), "is_demo": True,
        })
    await db.coin_conversions.insert_many([dict(x) for x in conv])

    # Withdrawals
    wstatus = ["Pending", "Under Review", "Approved", "Processing", "Paid", "Rejected", "Cancelled", "Failed"]
    wds = []
    for i in range(80):
        u = ref()
        dia = random.randint(1000, 50000)
        rate = 0.01
        wds.append({
            "id": f"WD-{8000+i}", "user": u["name"], "user_id": u["id"], "country": u["country"],
            "currency": u["currency"], "diamond_amount": dia, "cash_amount": round(dia * rate, 2),
            "payment_method": random.choice(["Bank Transfer", "UPI", "PayPal"]),
            "account_holder": u["name"], "status": random.choice(wstatus),
            "requested_date": rand_dt(60), "assigned_admin": random.choice(["Ram", "Priya", "Unassigned"]),
            "risk_score": random.randint(1, 99), "is_demo": True,
        })
    await db.withdrawals.insert_many([dict(x) for x in wds])

    # Calls
    cstatus = ["Requested", "Accepted", "Rejected", "Missed", "Connected", "Completed", "Failed", "Cancelled"]
    calls = []
    for i in range(300):
        caller, receiver = ref(), ref()
        ctype = random.choice(["Audio", "Video"])
        dur = random.randint(0, 45)
        rate = 10 if ctype == "Audio" else 25
        erate = 2 if ctype == "Audio" else 5
        calls.append({
            "id": f"CALL-{9000+i}", "caller": caller["name"], "caller_id": caller["id"],
            "receiver": receiver["name"], "receiver_id": receiver["id"], "call_type": ctype,
            "duration": dur, "silver_charged": dur * rate, "silver_earned": dur * erate,
            "status": random.choices(cstatus, weights=[5, 5, 8, 12, 5, 45, 10, 10])[0],
            "country": caller["country"], "reported": random.choice([False, False, False, True]),
            "start_time": rand_dt(60), "is_demo": True,
        })
    await db.calls.insert_many([dict(x) for x in calls])

    # Tasks
    tstatus = ["Draft", "Active", "Paused", "Expired", "Disabled"]
    tasks = []
    providers = ["OfferToro", "AdGate", "Ayet", "Tapjoy", "Internal"]
    for i in range(30):
        tasks.append({
            "id": f"TSK-{100+i}", "provider": random.choice(providers),
            "title": random.choice(["Complete survey", "Install app", "Sign up offer", "Watch & rate", "Play game to level 5"]),
            "country": random.choice(["India", "United Kingdom", "All"]),
            "required_tier": random.choice(["Friendship", "Love"]),
            "reward_type": "Silver", "reward_amount": random.choice([10, 25, 40, 50, 100]),
            "daily_cap": random.choice([5, 10, 20]), "status": random.choice(tstatus),
            "approval_type": random.choice(["Auto", "Provider", "Manual"]),
            "start_date": rand_dt(60), "is_demo": True,
        })
    await db.tasks.insert_many([dict(x) for x in tasks])

    # Advertisements
    ads = []
    for i in range(20):
        views = random.randint(100, 50000)
        ads.append({
            "id": f"AD-{200+i}", "title": random.choice(["Watch Advert", "Premium Advert", "Special Advert"]),
            "provider": random.choice(["AdMob", "Unity Ads", "AppLovin", "IronSource"]),
            "country": random.choice(["India", "United Kingdom", "All"]),
            "reward_amount": random.choice([10, 25, 50]), "user_tier": random.choice(["All", "Casual", "Friendship", "Love"]),
            "daily_limit": random.choice([3, 5, 10]), "status": random.choice(["Active", "Paused", "Draft"]),
            "views": views, "completed_views": int(views * 0.7), "rewarded_views": int(views * 0.6),
            "fraud_views": int(views * 0.02), "revenue": round(views * 0.004, 2), "is_demo": True,
        })
    await db.advertisements.insert_many([dict(x) for x in ads])

    # Friend requests
    frstatus = ["Pending", "Accepted", "Rejected", "Cancelled", "Expired", "Blocked"]
    frs = []
    for i in range(200):
        s, r = ref(), ref()
        frs.append({
            "id": f"FR-{300+i}", "sender": s["name"], "sender_id": s["id"],
            "receiver": r["name"], "receiver_id": r["id"],
            "initial_message": random.choice(["Hi there!", "Hello, how are you?", "Loved your profile", "Hey 👋", ""]),
            "sender_tier": s["tier"], "receiver_tier": r["tier"],
            "status": random.choice(frstatus), "created_date": rand_dt(60),
            "reported": random.choice([False, False, False, True]), "is_demo": True,
        })
    await db.friend_requests.insert_many([dict(x) for x in frs])

    # Chat rooms
    chats = []
    for i in range(120):
        a, b = ref(), ref()
        chats.append({
            "id": f"CHAT-{400+i}", "participants": f"{a['name']}, {b['name']}",
            "created_date": rand_dt(90), "last_message_date": rand_dt(10),
            "message_count": random.randint(1, 500), "report_count": random.choice([0, 0, 0, 1, 2]),
            "archived": random.choice([False, False, True]), "blocked": random.choice([False, False, False, True]),
            "is_demo": True,
        })
    await db.chat_rooms.insert_many([dict(x) for x in chats])

    # Moderation items
    queues = ["Profile photo", "Uploaded photo", "Uploaded video", "Reported message", "Suspicious text",
              "Phone number", "Social link", "Explicit content", "Scam content"]
    mods = []
    for i in range(80):
        u = ref()
        mods.append({
            "id": f"MOD-{500+i}", "user": u["name"], "user_id": u["id"], "queue": random.choice(queues),
            "status": random.choices(["Pending", "Approved", "Rejected", "Removed"], weights=[50, 25, 15, 10])[0],
            "created_date": rand_dt(30), "priority": random.choice(["High", "Medium", "Low"]),
            "country": u["country"], "is_demo": True,
        })
    await db.moderation_items.insert_many([dict(x) for x in mods])

    # Notifications
    ntypes = ["Account warning", "Account frozen", "Verification request", "Verification approved",
              "Withdrawal update", "Subscription update", "Payment update", "Promotion", "System announcement"]
    notifs = []
    for i in range(40):
        sent = random.randint(100, 50000)
        notifs.append({
            "id": f"NTF-{600+i}", "title": random.choice(["Weekend Bonus!", "Verify your account", "New Love plan", "Security alert", "Maintenance notice"]),
            "type": random.choice(ntypes), "channel": random.choice(["In-app", "Email", "Push", "SMS"]),
            "audience": random.choice(["All users", "UK users", "India users", "Love tier", "Unverified"]),
            "status": random.choices(["Sent", "Scheduled", "Draft", "Failed"], weights=[60, 20, 15, 5])[0],
            "sent_count": sent, "open_rate": round(random.uniform(10, 65), 1),
            "created_date": rand_dt(40), "is_demo": True,
        })
    await db.notifications.insert_many([dict(x) for x in notifs])

    # Support tickets
    tcats = ["Account", "Payment", "Subscription", "Withdrawal", "Calls", "Tasks", "Safety", "Verification", "Technical", "Other"]
    tk_status = ["Open", "Assigned", "Waiting for User", "Resolved", "Closed"]
    tickets = []
    for i in range(60):
        u = ref()
        tickets.append({
            "id": f"TKT-{700+i}", "user": u["name"], "user_id": u["id"],
            "subject": random.choice(["Cannot withdraw", "Payment failed", "Account frozen unfairly",
                                      "Coins missing", "Verification stuck", "App crashing", "Refund request"]),
            "category": random.choice(tcats), "priority": random.choice(["Critical", "High", "Medium", "Low"]),
            "status": random.choice(tk_status), "assigned_admin": random.choice(["Ram", "Priya", "James", "Unassigned"]),
            "created_date": rand_dt(45), "last_updated": rand_dt(10), "is_demo": True,
        })
    await db.support_tickets.insert_many([dict(x) for x in tickets])

    # Audit logs (seed history)
    modules = ["users", "reports", "payments", "withdrawals", "wallets", "settings", "liveness", "identity"]
    actions = ["Froze account", "Banned account", "Approved withdrawal", "Rejected report", "Manual credit",
               "Updated settings", "Approved verification", "Force logout", "Refunded payment"]
    logs = []
    for i in range(120):
        u = ref()
        logs.append({
            "id": f"LOG-{800+i}", "admin": random.choice(["Ram", "Priya", "James", "Aisha", "David"]),
            "role": random.choice(ROLES), "action": random.choice(actions),
            "module": random.choice(modules), "target": u["name"], "target_id": u["id"],
            "reason": random.choice(["Policy violation", "User request", "Fraud check", "Routine", "Escalation"]),
            "ip": f"{random.randint(10,220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "device": random.choice(["Chrome/Mac", "Firefox/Win", "Safari/iOS", "Edge/Win"]),
            "result": random.choice(["Success", "Success", "Success", "Failed"]),
            "timestamp": rand_dt(60), "is_demo": True,
        })
    await db.audit_logs.insert_many([dict(x) for x in logs])


async def seed_admins(db):
    admins = [
        {"name": "Ram", "email": "ram@earn2love.com", "role": "Owner", "password": "Owner@2026"},
        {"name": "Priya Nair", "email": "priya@earn2love.com", "role": "Super Admin", "password": "Admin@2026"},
        {"name": "James Wright", "email": "james@earn2love.com", "role": "Finance Admin", "password": "Finance@2026"},
        {"name": "Aisha Khan", "email": "aisha@earn2love.com", "role": "Safety Admin", "password": "Safety@2026"},
        {"name": "David Brown", "email": "david@earn2love.com", "role": "Read-only Analyst", "password": "Analyst@2026"},
    ]
    for a in admins:
        existing = await db.admins.find_one({"email": a["email"]})
        doc = {
            "id": "adm_" + a["email"].split("@")[0],
            "name": a["name"], "email": a["email"], "role": a["role"],
            "password_hash": hash_password(a["password"]),
            "initials": "".join([p[0] for p in a["name"].split()[:2]]).upper(),
            "status": "Active", "avatar": None,
            "last_login": None, "last_ip": None, "created_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": True,
        }
        if existing is None:
            await db.admins.insert_one(doc)
        else:
            await db.admins.update_one({"email": a["email"]}, {"$set": {
                "password_hash": doc["password_hash"], "role": a["role"], "name": a["name"],
                "initials": doc["initials"]}})


DEFAULT_SETTINGS = {
    "id": "system",
    "general": {"platform_name": "Earn2Love", "tagline": "Communicate. Connect. Collect.",
                "support_email": "support@earn2love.com", "maintenance_mode": False},
    "age_restriction": {"minimum_age": 18},
    "report_thresholds": {"auto_freeze_reports": 3, "freeze_hours": 24, "require_liveness_after_freeze": True,
                          "permanent_ban_repeat": True, "enabled": True},
    "calls": {"audio_rate_silver": 10, "video_rate_silver": 25, "audio_receiver_silver": 2, "video_receiver_silver": 5},
    "tasks": {"max_per_day": 10, "cooldown_minutes": 15, "require_advert": True, "min_silver_spend": 40,
              "require_liveness": True, "eligible_tiers": ["Friendship", "Love"]},
    "advertisements": {"watch_reward": 10, "premium_reward": 25, "special_reward": 50},
    "coin_conversion": {"india_silver_gold": "3:2", "india_gold_diamond": "3:2", "india_diamond_value": 0.01,
                        "uk_silver_gold": "3:2.5", "uk_gold_diamond": "3:2.5", "uk_diamond_value": 0.01},
    "withdrawal_rules": {"india_min": 10000, "uk_min": 150, "large_amount_threshold": 50000, "require_approval": True},
    "feature_flags": {"calls_enabled": True, "tasks_enabled": True, "ads_enabled": True, "withdrawals_enabled": True},
    "data_retention": {"chat_days": 365, "call_metadata_days": 730, "deleted_account_days": 30},
    "is_demo": True,
}


async def seed_settings(db):
    existing = await db.system_settings.find_one({"id": "system"})
    if existing is None:
        await db.system_settings.insert_one(dict(DEFAULT_SETTINGS))
