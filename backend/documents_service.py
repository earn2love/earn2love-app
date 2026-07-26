"""Admin Documents: catalog of 89 documents + professional content generator + Firestore CRUD.
Stored in Firestore collection `adminDocuments`. Content is the BODY (HTML); the
branded header/footer/theme is applied by the frontend viewer & print layout.
"""
from datetime import datetime, timezone
from firebase_service import get_db

COLL = "adminDocuments"

# (number, title, category, kind)
# kind drives the generated template: policy | sop | checklist | technical | guide
CATALOG = [
    # 1. Legal & Compliance
    (1, "Privacy Policy", "Legal & Compliance", "policy"),
    (2, "Terms & Conditions", "Legal & Compliance", "policy"),
    (3, "Cookie Policy", "Legal & Compliance", "policy"),
    (4, "Acceptable Use Policy", "Legal & Compliance", "policy"),
    (5, "Community Guidelines", "Legal & Compliance", "policy"),
    (6, "Refund Policy", "Legal & Compliance", "policy"),
    (7, "Subscription Policy", "Legal & Compliance", "policy"),
    (8, "Rewards Policy", "Legal & Compliance", "policy"),
    (9, "Withdrawal Policy", "Legal & Compliance", "policy"),
    (10, "Virtual Currency Policy", "Legal & Compliance", "policy"),
    (11, "Payment Policy", "Legal & Compliance", "policy"),
    (12, "Chargeback Policy", "Legal & Compliance", "policy"),
    (13, "Account Deletion Policy", "Legal & Compliance", "policy"),
    (14, "Account Suspension Policy", "Legal & Compliance", "policy"),
    (15, "Age Verification Policy", "Legal & Compliance", "policy"),
    (16, "Child Safety Policy", "Legal & Compliance", "policy"),
    (17, "Content Moderation Policy", "Legal & Compliance", "policy"),
    (18, "Anti-Fraud Policy", "Legal & Compliance", "policy"),
    (19, "Anti-Spam Policy", "Legal & Compliance", "policy"),
    (20, "Data Protection Policy", "Legal & Compliance", "policy"),
    (21, "Data Retention Policy", "Legal & Compliance", "policy"),
    (22, "Security Policy", "Legal & Compliance", "policy"),
    (23, "Accessibility Statement", "Legal & Compliance", "policy"),
    (24, "Marketing Consent Policy", "Legal & Compliance", "policy"),
    (25, "Email Communication Policy", "Legal & Compliance", "policy"),
    (26, "Push Notification Policy", "Legal & Compliance", "policy"),
    (27, "Law Enforcement Request Policy", "Legal & Compliance", "policy"),
    (28, "Dispute Resolution Policy", "Legal & Compliance", "policy"),
    (29, "Intellectual Property Policy", "Legal & Compliance", "policy"),
    (30, "Copyright (DMCA) Policy", "Legal & Compliance", "policy"),
    (31, "Trademark Policy", "Legal & Compliance", "policy"),
    (32, "AI Usage Policy", "Legal & Compliance", "policy"),
    # 2. Operations & SOP
    (33, "Platform Operations Manual", "Operations & SOP", "sop"),
    (34, "Admin Operations Manual", "Operations & SOP", "sop"),
    (35, "Customer Support SOP", "Operations & SOP", "sop"),
    (36, "Moderator SOP", "Operations & SOP", "sop"),
    (37, "Finance SOP", "Operations & SOP", "sop"),
    (38, "Payment Operations SOP", "Operations & SOP", "sop"),
    (39, "Withdrawal SOP", "Operations & SOP", "sop"),
    (40, "Refund SOP", "Operations & SOP", "sop"),
    (41, "User Verification SOP", "Operations & SOP", "sop"),
    (42, "Content Review SOP", "Operations & SOP", "sop"),
    (43, "Appeals SOP", "Operations & SOP", "sop"),
    (44, "Fraud Prevention SOP", "Operations & SOP", "sop"),
    (45, "Risk Management Manual", "Operations & SOP", "sop"),
    (46, "Compliance Manual", "Operations & SOP", "sop"),
    (47, "Incident Response Plan", "Operations & SOP", "sop"),
    (48, "Security Incident Response Plan", "Operations & SOP", "sop"),
    (49, "Business Continuity Plan", "Operations & SOP", "sop"),
    (50, "Disaster Recovery Plan", "Operations & SOP", "sop"),
    (51, "Vendor Management Policy", "Operations & SOP", "policy"),
    (52, "Third-Party Risk Policy", "Operations & SOP", "policy"),
    (53, "Data Breach Procedure", "Operations & SOP", "sop"),
    (54, "Change Management Procedure", "Operations & SOP", "sop"),
    (55, "Release Management Procedure", "Operations & SOP", "sop"),
    (56, "Quality Assurance SOP", "Operations & SOP", "sop"),
    # 3. Deployment & Technical
    (57, "Production Deployment Checklist", "Deployment & Technical", "checklist"),
    (58, "Production Launch Checklist", "Deployment & Technical", "checklist"),
    (59, "Daily Operations Checklist", "Deployment & Technical", "checklist"),
    (60, "Weekly Operations Checklist", "Deployment & Technical", "checklist"),
    (61, "Monthly Operations Checklist", "Deployment & Technical", "checklist"),
    (62, "Audit Checklist", "Deployment & Technical", "checklist"),
    (63, "Compliance Checklist", "Deployment & Technical", "checklist"),
    (64, "Firestore Security Rules Documentation", "Deployment & Technical", "technical"),
    (65, "Firebase Authentication Documentation", "Deployment & Technical", "technical"),
    (66, "Cloud Functions Documentation", "Deployment & Technical", "technical"),
    (67, "API Documentation", "Deployment & Technical", "technical"),
    (68, "Database Schema Documentation", "Deployment & Technical", "technical"),
    (69, "Backup & Recovery Procedure", "Deployment & Technical", "sop"),
    (70, "Monitoring & Logging Guide", "Deployment & Technical", "technical"),
    # 4. Finance & Risk
    (71, "AML Policy", "Finance & Risk", "policy"),
    (72, "KYC Policy", "Finance & Risk", "policy"),
    (73, "Financial Crime Policy", "Finance & Risk", "policy"),
    (74, "Refund Approval Procedure", "Finance & Risk", "sop"),
    (75, "Withdrawal Risk Assessment", "Finance & Risk", "technical"),
    (76, "Virtual Currency Accounting Guide", "Finance & Risk", "guide"),
    # 5. Internal Administration
    (77, "Employee Code of Conduct", "Internal Administration", "policy"),
    (78, "Escalation Matrix", "Internal Administration", "technical"),
    (79, "Emergency Contacts", "Internal Administration", "technical"),
    (80, "Access Control Policy", "Internal Administration", "policy"),
    (81, "Password Policy", "Internal Administration", "policy"),
    (82, "Secure Development Policy", "Internal Administration", "policy"),
    (83, "Information Security Policy", "Internal Administration", "policy"),
    # 6. User Documentation
    (84, "Help Centre / FAQ", "User Documentation", "guide"),
    (85, "Wallet User Guide", "User Documentation", "guide"),
    (86, "Rewards Guide", "User Documentation", "guide"),
    (87, "Membership Guide", "User Documentation", "guide"),
    (88, "Safety Guide", "User Documentation", "guide"),
    (89, "Scam Awareness Guide", "User Documentation", "guide"),
]


def _code(cat, num):
    prefix = {
        "Legal & Compliance": "LEG", "Operations & SOP": "OPS", "Deployment & Technical": "TEC",
        "Finance & Risk": "FIN", "Internal Administration": "ADM", "User Documentation": "USR",
    }.get(cat, "DOC")
    return f"E2L-{prefix}-{num:03d}"


def _t(rows, headers):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _version_table():
    return _t([
        ["1.0", "[Approval Date]", "[Document Owner]", "Initial published version."],
    ], ["Version", "Date", "Author / Owner", "Summary of Changes"])


def _common_defs():
    return _t([
        ["Earn2Love / “the Platform”", "The Earn2Love 18+ social connection and rewards service (web and mobile apps)."],
        ["User / Member", "Any individual with a registered Earn2Love account."],
        ["Company", "[Earn2Love Legal Entity Name], the operator of the Platform."],
        ["Rewards / Coins", "Silver, Gold and Diamond virtual coins earned through eligible activities."],
    ], ["Term", "Definition"])


def generate_body(title, category, kind):
    """Return professional BODY HTML for a document (sections, tables, a figure)."""
    lead = (f"<p class='lead'>This document sets out the {title} for Earn2Love. It applies to all "
            f"users, staff and third parties interacting with the Platform, and forms part of the "
            f"Earn2Love {category} framework. Availability, limits and eligibility requirements apply; "
            f"rewards and withdrawals are not guaranteed.</p>")

    if kind == "policy":
        return (
            f"{lead}"
            "<h2>1. Purpose</h2>"
            f"<p>The purpose of this {title} is to define the principles, obligations and controls that govern "
            "how Earn2Love and its users act in relation to this subject, and to ensure the Platform operates "
            "lawfully, safely and transparently across all supported regions (currently the United Kingdom and India).</p>"
            "<h2>2. Scope</h2>"
            "<p>This policy applies to all Earn2Love accounts, all platform features, and all personnel and vendors "
            "acting on behalf of the Company. It is read together with the Terms &amp; Conditions and Privacy Policy.</p>"
            "<h2>3. Definitions</h2>" + _common_defs() +
            "<h2>4. Policy Statements</h2>"
            "<ul>"
            f"<li>Earn2Love will handle all matters relating to {title.lower()} in accordance with applicable law "
            "and industry good practice.</li>"
            "<li>Users must comply with this policy; breaches may lead to warnings, freezing, suspension or permanent "
            "ban, and reversal of invalid or fraudulent activity.</li>"
            "<li>The Platform maintains records and audit logs of relevant decisions and enforcement actions.</li>"
            "<li>The service remains strictly 18+ and enforces age and identity checks where required.</li>"
            "</ul>"
            "<h2>5. Roles &amp; Responsibilities</h2>" + _t([
                ["Super Admin", "Owns and approves this policy; final escalation authority."],
                ["Compliance / Safety Admin", "Monitors adherence, investigates breaches, maintains records."],
                ["Finance Admin", "Handles money, rewards and withdrawal aspects where applicable."],
                ["User", "Reads, understands and complies with this policy."],
            ], ["Role", "Responsibility"]) +
            "<h2>6. Enforcement &amp; Consequences</h2>"
            "<p>Non-compliance may result in restriction of features, freezing of wallet balances pending review, "
            "account suspension or termination, and referral to the relevant authorities where legally required.</p>"
            "<h2>7. Governing Law</h2>"
            "<p>This policy is governed by the laws of [Jurisdiction]. Disputes are handled under the Dispute "
            "Resolution Policy. Legal specifics marked in [brackets] must be reviewed by qualified counsel before publication.</p>"
            "<h2>8. Review &amp; Version History</h2>"
            "<p>This document is reviewed at least annually or upon material change.</p>" + _version_table()
        )

    if kind == "sop":
        return (
            f"{lead}"
            "<h2>1. Purpose</h2>"
            f"<p>This Standard Operating Procedure defines the step-by-step process staff must follow for "
            f"{title.replace(' SOP','').replace(' Manual','').replace(' Procedure','').replace(' Plan','')} "
            "to ensure consistent, auditable and compliant operations.</p>"
            "<h2>2. Scope &amp; Roles</h2>" + _t([
                ["Requestor / User", "Initiates the request or event."],
                ["Support / Moderator", "First-line handling and triage."],
                ["Admin / Finance", "Approval and execution of privileged actions."],
                ["Super Admin", "Escalation and exception approval."],
            ], ["Role", "Responsibility"]) +
            "<h2>3. Procedure</h2>" + _t([
                ["1", "Receive & log the request/event in the admin system.", "Support"],
                ["2", "Verify identity, eligibility and account status (active / frozen / banned).", "Support/Admin"],
                ["3", "Perform required checks (fraud, risk, compliance) and gather evidence.", "Admin"],
                ["4", "Approve, reject or escalate with a recorded reason.", "Admin/Super Admin"],
                ["5", "Execute the action via secure backend (never edit balances manually).", "Finance/Admin"],
                ["6", "Notify the user and write an entry to adminAuditLogs.", "System/Admin"],
            ], ["Step", "Action", "Owner"]) +
            "<h2>4. Service Levels</h2>" + _t([
                ["Standard", "Within 24–48 hours"],
                ["Priority / Safety", "Within 2–4 hours"],
                ["Financial dispute", "Within 5 business days"],
            ], ["Priority", "Target Response"]) +
            "<h2>5. Escalation</h2>"
            "<p>Unresolved or high-risk cases are escalated per the Escalation Matrix. All escalations are logged.</p>"
            "<h2>6. Records &amp; Review</h2>"
            "<p>All actions are recorded in the audit log. This SOP is reviewed at least annually.</p>" + _version_table()
        )

    if kind == "checklist":
        return (
            f"{lead}"
            "<h2>1. Purpose</h2>"
            f"<p>This checklist ensures every required step for {title.replace(' Checklist','')} is completed, "
            "verified and signed off before proceeding.</p>"
            "<h2>2. Checklist</h2>" + _t([
                ["1", "Confirm environment variables & secrets are set (no secrets in source).", "☐", "DevOps"],
                ["2", "Firestore & Storage security rules deployed and verified.", "☐", "DevOps"],
                ["3", "Required composite indexes built and active.", "☐", "DevOps"],
                ["4", "Cloud Functions deployed & health-checked.", "☐", "Backend"],
                ["5", "Payments (Stripe) webhook verified end-to-end in test mode.", "☐", "Finance/Eng"],
                ["6", "Backups configured and a restore test completed.", "☐", "DevOps"],
                ["7", "Monitoring, logging and alerts enabled.", "☐", "DevOps"],
                ["8", "Legal documents & consents published and versioned.", "☐", "Compliance"],
                ["9", "Age-gate (18+) and safety tooling verified.", "☐", "Safety"],
                ["10", "Sign-off recorded by owner.", "☐", "Super Admin"],
            ], ["#", "Item", "Done", "Owner"]) +
            "<h2>3. Sign-off</h2>" + _t([
                ["Prepared by", "[Name]", "[Date]"],
                ["Reviewed by", "[Name]", "[Date]"],
                ["Approved by", "[Name]", "[Date]"],
            ], ["Stage", "Name", "Date"]) +
            "<h2>4. Version History</h2>" + _version_table()
        )

    if kind == "technical":
        return (
            f"{lead}"
            "<h2>1. Overview</h2>"
            f"<p>This document provides the technical reference for {title}. It is intended for engineers, "
            "administrators and auditors working on the Earn2Love platform.</p>"
            "<figure class='figure'><img src='/earn2love-logo.png' alt='Earn2Love architecture' />"
            "<figcaption>Figure 1 — Earn2Love reference (replace with the relevant architecture diagram).</figcaption></figure>"
            "<h2>2. Components</h2>" + _t([
                ["Firebase Auth", "User authentication (phone/email/Google) + admin custom-claim roles."],
                ["Cloud Firestore", "Primary datastore: users, chatRooms, walletHistory, reports, etc."],
                ["Cloud Functions", "Server-authoritative logic: payments, wallet, calls, withdrawals, admin."],
                ["Firebase Storage", "Media & verification documents with scoped security rules."],
            ], ["Component", "Responsibility"]) +
            "<h2>3. Key Details</h2>"
            "<ul><li>All monetary/coin mutations occur only in secure backend transactions.</li>"
            "<li>Access is gated by authentication, ownership and admin role claims.</li>"
            "<li>Required composite indexes are documented and deployed.</li></ul>"
            "<h2>4. References &amp; Change Log</h2>" + _version_table()
        )

    # guide
    return (
        f"{lead}"
        "<h2>1. Introduction</h2>"
        f"<p>Welcome to the {title}. This guide explains, in clear and simple terms, how to use this part of "
        "Earn2Love safely and get the most from your experience.</p>"
        "<figure class='figure'><img src='/earn2love-logo.png' alt='Earn2Love' />"
        "<figcaption>Earn2Love — Communicate. Connect. Collect.</figcaption></figure>"
        "<h2>2. Getting Started</h2>"
        "<ul><li>Make sure your account is verified and you are 18 or older.</li>"
        "<li>Keep your profile complete and your login details private.</li>"
        "<li>Only earn rewards through eligible activities — fraudulent or invalid activity may be reversed.</li></ul>"
        "<h2>3. Frequently Asked Questions</h2>" + _t([
            ["How do I earn rewards?", "Through eligible activities such as chats, calls and tasks. Limits apply."],
            ["When can I withdraw?", "When you meet the membership, minimum balance and verification requirements."],
            ["Are rewards guaranteed?", "No. Availability, limits and eligibility requirements apply."],
            ["How do I stay safe?", "Never share contact details early, report suspicious users, and block anyone who makes you uncomfortable."],
        ], ["Question", "Answer"]) +
        "<h2>4. Need Help?</h2>"
        "<p>Contact support at [support@earn2love.com] or visit the Help Centre. For safety concerns, use the in-app Report tool.</p>"
        "<h2>5. Version History</h2>" + _version_table()
    )


def _now():
    return datetime.now(timezone.utc)


def _doc_out(d):
    out = dict(d.to_dict() or {})
    out["id"] = d.id
    for k in ("createdAt", "updatedAt"):
        v = out.get(k)
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out


def list_documents(category=None, search=""):
    db = get_db()
    docs = [_doc_out(d) for d in db.collection(COLL).stream()]
    if category and category != "All":
        docs = [d for d in docs if d.get("category") == category]
    if search:
        s = search.lower()
        docs = [d for d in docs if s in str(d.get("title", "")).lower()
                or s in str(d.get("code", "")).lower() or s in str(d.get("description", "")).lower()]
    docs.sort(key=lambda d: d.get("number", 9999))
    return docs


def get_document(doc_id):
    d = get_db().collection(COLL).document(doc_id).get()
    return _doc_out(d) if d.exists else None


def create_document(data, author=""):
    db = get_db()
    now = _now()
    nums = [d.get("number", 0) for d in list_documents()]
    doc = {
        "number": data.get("number") or (max(nums) + 1 if nums else 1),
        "title": data.get("title", "Untitled Document"),
        "category": data.get("category", "Other"),
        "code": data.get("code") or _code(data.get("category", "Other"), (max(nums) + 1 if nums else 1)),
        "description": data.get("description", ""),
        "status": data.get("status", "Draft"),
        "version": data.get("version", "1.0"),
        "contentHtml": data.get("contentHtml", "<p>New document.</p>"),
        "createdAt": now, "updatedAt": now, "updatedBy": author,
    }
    ref = db.collection(COLL).add(doc)[1]
    return get_document(ref.id)


def update_document(doc_id, data, author=""):
    db = get_db()
    ref = db.collection(COLL).document(doc_id)
    if not ref.get().exists:
        return None
    allowed = {k: data[k] for k in ("title", "category", "code", "description", "status", "version", "contentHtml", "number") if k in data}
    allowed["updatedAt"] = _now()
    allowed["updatedBy"] = author
    ref.set(allowed, merge=True)
    return get_document(doc_id)


def delete_document(doc_id):
    ref = get_db().collection(COLL).document(doc_id)
    if not ref.get().exists:
        return False
    ref.delete()
    return True


def seed_documents(force=False):
    db = get_db()
    existing = list(db.collection(COLL).limit(1).stream())
    if existing and not force:
        return {"seeded": 0, "skipped": True, "message": "Documents already exist"}
    now = _now()
    batch = db.batch()
    count = 0
    for (num, title, cat, kind) in CATALOG:
        ref = db.collection(COLL).document(f"e2l-{num:03d}")
        batch.set(ref, {
            "number": num, "title": title, "category": cat, "kind": kind,
            "code": _code(cat, num),
            "description": f"{title} — official Earn2Love {cat} document.",
            "status": "Published", "version": "1.0",
            "contentHtml": generate_body(title, cat, kind),
            "createdAt": now, "updatedAt": now, "updatedBy": "system",
        })
        count += 1
        if count % 400 == 0:
            batch.commit(); batch = db.batch()
    batch.commit()
    return {"seeded": count, "skipped": False}
