import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'profile_menu_page.dart';
import 'topup_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool created = false;

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  @override
  void initState() {
    super.initState();
    ensureUserDoc();
  }

  // --------- SAFE DEFAULT MERGE ----------
  Future<void> ensureUserDoc() async {
    final user = FirebaseAuth.instance.currentUser!;
    final ref = FirebaseFirestore.instance.collection('users').doc(user.uid);

    final snap = await ref.get();
    final existing = snap.data() ?? {};

    if (!snap.exists) {
      await ref.set({
        'uid': user.uid,
        'email': user.email,
        'phone': user.phoneNumber,
        'createdAt': FieldValue.serverTimestamp(),

        'displayName': '',
        'bio': '',
        'photoUrls': [],

        // wallets
        'silverBalance': 0,
        'goldBalance': 0,
        'diamondBalance': 0,

        // defaults
        'country': 'IN',
        'appLanguage': 'en',
        'matchLanguage': 'en',

        'streakDays': 0,
        'streakBonusPct': 0,
        'streakLastDate': '',

        'freezeUntil': null,
        'isPremium': false,

        // subscription tier
        'subTier': 'casual', // casual | friendship | love
      });
    } else {
      await ref.set({
        // numeric defaults (avoid null crash)
        'silverBalance': FieldValue.increment(0),
        'goldBalance': FieldValue.increment(0),
        'diamondBalance': FieldValue.increment(0),

        'country': (existing['country'] ?? 'IN').toString(),
        'appLanguage': (existing['appLanguage'] ?? 'en').toString(),
        'matchLanguage': (existing['matchLanguage'] ?? 'en').toString(),

        'streakDays': FieldValue.increment(0),
        'streakBonusPct': FieldValue.increment(0),
        'streakLastDate': (existing['streakLastDate'] ?? '').toString(),

        // subTier default
        'subTier': (existing['subTier'] ?? 'casual').toString(),

        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }

    if (mounted) setState(() => created = true);
  }

  Future<void> openTopup() async {
    final snap = await userRef.get();
    final c = (snap.data()?['country'] ?? 'IN').toString();
    if (!mounted) return;
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => TopUpPage(country: c)),
    );
  }

  void openProfile() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const ProfileMenuPage()),
    );
  }

  // ---------- SUB ACCESS ----------
  bool _hasFriendship(String tier) => tier == 'friendship' || tier == 'love';
  bool _hasLove(String tier) => tier == 'love';

  Future<void> _setTierForTesting(String tier) async {
    await userRef.set(
      {'subTier': tier, 'updatedAt': FieldValue.serverTimestamp()},
      SetOptions(merge: true),
    );
  }

  Future<void> _showUpgradeSheet({
    required String need,
    required String current,
  }) async {
    await showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (_) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 22),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.lock, size: 34),
              const SizedBox(height: 8),
              const Text(
                "Locked 🔒",
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
              ),
              const SizedBox(height: 6),
              Text(
                "This section needs: $need\nYour plan: $current",
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.grey.shade700,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 14),

              // dummy upgrade buttons (Phase-1 testing)
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () async {
                        await _setTierForTesting('friendship');
                        if (context.mounted) Navigator.pop(context);
                      },
                      child: const Text("Test: Friendship"),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () async {
                        await _setTierForTesting('love');
                        if (context.mounted) Navigator.pop(context);
                      },
                      child: const Text("Test: Love"),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 10),
              Text(
                "Payments later. Now these buttons only change Firestore tier for testing.",
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.grey.shade600,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ---------- SAFE READERS ----------
  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  int asInt(dynamic v, {int def = 0}) {
    if (v == null) return def;
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse(v.toString().trim()) ?? def;
  }

  List<String> asStringList(dynamic v) {
    if (v is List) {
      return v
          .map((e) => e.toString())
          .where((e) => e.trim().isNotEmpty)
          .toList();
    }
    return [];
  }

  // ---------- UI HELPERS ----------
  Widget _coinMini(
      {required String emoji, required String label, required String value}) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.white.withOpacity(0.12),
          border: Border.all(color: Colors.white.withOpacity(0.18)),
        ),
        child: Column(
          children: [
            Text(emoji, style: const TextStyle(fontSize: 18)),
            const SizedBox(height: 4),
            Text(value,
                style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                    fontSize: 16)),
            const SizedBox(height: 2),
            Text(label,
                style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontWeight: FontWeight.w700,
                    fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Widget _topupButton() {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: openTopup,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: Colors.white,
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.add_circle, size: 18),
            SizedBox(width: 6),
            Text("Top Up", style: TextStyle(fontWeight: FontWeight.w900)),
          ],
        ),
      ),
    );
  }

  String _tierLabel(String tier) {
    if (tier == 'love') return "Love 💖";
    if (tier == 'friendship') return "Friendship 🤝";
    return "Casual 🙂";
  }

  Widget _headerCard(Map<String, dynamic> u) {
    final tier = asString(u['subTier'], def: 'casual');
    final name = asString(u['displayName'], def: 'My Profile');
    final photos = asStringList(u['photoUrls']);
    final photo = photos.isNotEmpty ? photos.first : '';

    final silver = asInt(u['silverBalance']).toString();
    final gold = asInt(u['goldBalance']).toString();
    final diamond = asInt(u['diamondBalance']).toString();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.deepPurple.shade600, Colors.pink.shade500],
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              InkWell(
                borderRadius: BorderRadius.circular(999),
                onTap: openProfile,
                child: CircleAvatar(
                  radius: 28,
                  backgroundColor: Colors.white.withOpacity(0.20),
                  backgroundImage: photo.isEmpty ? null : NetworkImage(photo),
                  child: photo.isEmpty
                      ? const Icon(Icons.person, color: Colors.white, size: 28)
                      : null,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: InkWell(
                  onTap: openProfile,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        "EARN2LOVE",
                        style: TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 20,
                          color: Colors.white,
                          letterSpacing: 0.4,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "$name • ${_tierLabel(tier)}",
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.92),
                          fontWeight: FontWeight.w800,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ),
              _topupButton(),
            ],
          ),
          const SizedBox(height: 12),

          // coins row
          Row(
            children: [
              _coinMini(emoji: "🥈", label: "Silver", value: silver),
              const SizedBox(width: 10),
              _coinMini(emoji: "🪙", label: "Gold", value: gold),
              const SizedBox(width: 10),
              _coinMini(emoji: "💎", label: "Diamond", value: diamond),
            ],
          ),
        ],
      ),
    );
  }

  Widget _featureCard({
    required String title,
    required String subtitle,
    required String emojiArt,
    required Color a,
    required Color b,
    required IconData icon,
    required bool locked,
    required VoidCallback onTap,
  }) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [a.withOpacity(0.18), b.withOpacity(0.12)],
            ),
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: Row(
            children: [
              Container(
                width: 58,
                height: 58,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: LinearGradient(colors: [a, b]),
                ),
                child: Center(
                  child: Text(
                    emojiArt,
                    style: const TextStyle(fontSize: 26),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(icon, size: 16),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            title,
                            style: const TextStyle(
                                fontWeight: FontWeight.w900, fontSize: 16),
                          ),
                        ),
                        if (locked)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(999),
                              color: Colors.red.shade50,
                              border: Border.all(color: Colors.red.shade200),
                            ),
                            child: const Text(
                              "Locked",
                              style: TextStyle(
                                  fontWeight: FontWeight.w900, fontSize: 11),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      style: TextStyle(
                          color: Colors.grey.shade700,
                          fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: userRef.snapshots(),
      builder: (context, snap) {
        final u = snap.data?.data() ?? {};
        final tier = asString(u['subTier'], def: 'casual');

        return Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            title: const Text(""),
          ),
          body: created
              ? ListView(
                  padding: const EdgeInsets.fromLTRB(14, 10, 14, 20),
                  children: [
                    _headerCard(u),
                    const SizedBox(height: 12),

                    // 1) Casual
                    _featureCard(
                      title: "Casual",
                      subtitle:
                          "Free access • Chat with Casual users only • AI bot available",
                      emojiArt: "👩‍❤️‍👨",
                      a: Colors.indigo,
                      b: Colors.cyan,
                      icon: Icons.chat_bubble_outline,
                      locked: false,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const CasualPage()),
                        );
                      },
                    ),

                    // 2) Friendship
                    _featureCard(
                      title: "Friendship",
                      subtitle:
                          "£4.99 subscription • Chat with Casual + Friendship users",
                      emojiArt: "🤝",
                      a: Colors.teal,
                      b: Colors.green,
                      icon: Icons.group_outlined,
                      locked: !_hasFriendship(tier),
                      onTap: () {
                        if (!_hasFriendship(tier)) {
                          _showUpgradeSheet(
                              need: "Friendship (£4.99)", current: tier);
                          return;
                        }
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const FriendshipPage()),
                        );
                      },
                    ),

                    // 3) Love
                    _featureCard(
                      title: "Love",
                      subtitle:
                          "£9.99 subscription • Access Love + Friendship + Casual",
                      emojiArt: "🫂",
                      a: Colors.pink,
                      b: Colors.deepPurple,
                      icon: Icons.favorite_border,
                      locked: !_hasLove(tier),
                      onTap: () {
                        if (!_hasLove(tier)) {
                          _showUpgradeSheet(
                              need: "Love (£9.99)", current: tier);
                          return;
                        }
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const LovePage()),
                        );
                      },
                    ),

                    // 4) Ads
                    _featureCard(
                      title: "Ads",
                      subtitle:
                          "Earn Silver coins • 30s / 60s / 90s / 120s / 180s ads",
                      emojiArt: "🪙",
                      a: Colors.orange,
                      b: Colors.amber,
                      icon: Icons.play_circle_outline,
                      locked: false,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const AdsHubPage()),
                        );
                      },
                    ),

                    // 5) Tasks (Love only)
                    _featureCard(
                      title: "Tasks",
                      subtitle:
                          "Earn Gold coins • Offerwall tasks (Love plan only)",
                      emojiArt: "🏆",
                      a: Colors.blueGrey,
                      b: Colors.blue,
                      icon: Icons.task_alt,
                      locked: !_hasLove(tier),
                      onTap: () {
                        if (!_hasLove(tier)) {
                          _showUpgradeSheet(
                              need: "Love plan required", current: tier);
                          return;
                        }
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const TasksHubPage()),
                        );
                      },
                    ),

                    const SizedBox(height: 10),

                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        color: Colors.grey.shade50,
                        border: Border.all(color: Colors.grey.shade200),
                      ),
                      child: Text(
                        "Tip: Tap your profile picture (top) → Account Settings.\nLogout will be moved there.",
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: Colors.grey.shade800,
                            fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                )
              : const Center(child: CircularProgressIndicator()),
        );
      },
    );
  }
}

// ======================================================
// BELOW: DUMMY PAGES (so no missing files / errors)
// ======================================================

class CasualPage extends StatelessWidget {
  const CasualPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const _UsersListPage(
      title: "Casual",
      banner: "Free Subscription • Casual users only",
      badge: "CASUAL",
      badgeColor: Colors.indigo,
    );
  }
}

class FriendshipPage extends StatelessWidget {
  const FriendshipPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const _UsersListPage(
      title: "Friendship",
      banner: "£4.99 plan • Casual + Friendship users",
      badge: "FRIEND",
      badgeColor: Colors.teal,
    );
  }
}

class LovePage extends StatelessWidget {
  const LovePage({super.key});

  @override
  Widget build(BuildContext context) {
    return const _UsersListPage(
      title: "Love",
      banner: "£9.99 plan • Love + Friendship + Casual users",
      badge: "LOVE",
      badgeColor: Colors.pink,
    );
  }
}

class _UsersListPage extends StatelessWidget {
  final String title;
  final String banner;
  final String badge;
  final Color badgeColor;

  const _UsersListPage({
    required this.title,
    required this.banner,
    required this.badge,
    required this.badgeColor,
  });

  @override
  Widget build(BuildContext context) {
    final users = List.generate(12, (i) {
      return {
        "name": "User ${i + 1}",
        "subtitle": i % 3 == 0 ? "AI Bot available 🤖" : "Online recently",
      };
    });

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: LinearGradient(colors: [
                badgeColor.withOpacity(0.18),
                badgeColor.withOpacity(0.08)
              ]),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: badgeColor.withOpacity(0.15),
                    border: Border.all(color: badgeColor.withOpacity(0.35)),
                  ),
                  child: Text(badge,
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                ),
                const SizedBox(width: 10),
                Expanded(
                    child: Text(banner,
                        style: const TextStyle(fontWeight: FontWeight.w800))),
              ],
            ),
          ),
          const SizedBox(height: 12),
          ...users.map((u) {
            return Card(
              elevation: 0,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18)),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: Colors.grey.shade100,
                  child: const Icon(Icons.person),
                ),
                title: Text(u["name"]!,
                    style: const TextStyle(fontWeight: FontWeight.w900)),
                subtitle: Text(u["subtitle"]!),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                        content: Text(
                            "Chat feature next ✅ (permission & structure next step)")),
                  );
                },
              ),
            );
          }),
        ],
      ),
    );
  }
}

// ------------------ Ads Hub ------------------
class AdsHubPage extends StatefulWidget {
  const AdsHubPage({super.key});

  @override
  State<AdsHubPage> createState() => _AdsHubPageState();
}

class _AdsHubPageState extends State<AdsHubPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get historyRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('walletHistory');

  DateTimeRange range = DateTimeRange(
    start: DateTime.now().subtract(const Duration(days: 7)),
    end: DateTime.now(),
  );

  String _two(int n) => n.toString().padLeft(2, '0');
  String _fmtDate(DateTime d) => "${_two(d.day)}/${_two(d.month)}/${d.year}";

  Future<void> pickRange() async {
    final r = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
      initialDateRange: range,
    );
    if (r != null) setState(() => range = r);
  }

  @override
  Widget build(BuildContext context) {
    const ads = [30, 60, 90, 120, 180];

    return Scaffold(
      appBar: AppBar(title: const Text("Ads • Earn Silver")),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: historyRef
            .where('type', isEqualTo: 'ads')
            .orderBy('createdAt', descending: true)
            .limit(500)
            .snapshots(),
        builder: (context, snap) {
          final docs = snap.data?.docs ?? [];

          double totalSilver = 0;
          int count = 0;

          final start =
              DateTime(range.start.year, range.start.month, range.start.day);
          final end = DateTime(
              range.end.year, range.end.month, range.end.day, 23, 59, 59);

          for (final d in docs) {
            final data = d.data();
            final ts = data['createdAt'];
            if (ts is! Timestamp) continue;
            final dt = ts.toDate();

            if (dt.isBefore(start) || dt.isAfter(end)) continue;

            final v = data['toAmount'];
            if (v is num) totalSilver += v.toDouble();
            count += 1;
          }

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  color: Colors.orange.shade50,
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text("Your Earnings",
                        style: TextStyle(
                            fontWeight: FontWeight.w900, fontSize: 16)),
                    const SizedBox(height: 6),
                    Text(
                        "Range: ${_fmtDate(range.start)} → ${_fmtDate(range.end)}",
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    Text("Ads watched: $count",
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text("Silver earned: 🥈 ${totalSilver.toStringAsFixed(0)}",
                        style: const TextStyle(fontWeight: FontWeight.w900)),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: pickRange,
                      icon: const Icon(Icons.date_range),
                      label: const Text("Change Date Range"),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const Text("Available Ads",
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 8),
              ...ads.map((sec) {
                return Card(
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(18)),
                  child: ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.play_arrow)),
                    title: Text("$sec sec Ad",
                        style: const TextStyle(fontWeight: FontWeight.w900)),
                    subtitle: const Text("Coins allocation later (Phase-1)."),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                            content: Text(
                                "Ad $sec sec clicked ✅ (integration later)")),
                      );
                    },
                  ),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}

// ------------------ Tasks Hub ------------------
class TasksHubPage extends StatefulWidget {
  const TasksHubPage({super.key});

  @override
  State<TasksHubPage> createState() => _TasksHubPageState();
}

class _TasksHubPageState extends State<TasksHubPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get historyRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('walletHistory');

  DateTimeRange range = DateTimeRange(
    start: DateTime.now().subtract(const Duration(days: 7)),
    end: DateTime.now(),
  );

  String _two(int n) => n.toString().padLeft(2, '0');
  String _fmtDate(DateTime d) => "${_two(d.day)}/${_two(d.month)}/${d.year}";

  Future<void> pickRange() async {
    final r = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
      initialDateRange: range,
    );
    if (r != null) setState(() => range = r);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Tasks • Earn Gold")),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: historyRef
            .where('type', isEqualTo: 'tasks')
            .orderBy('createdAt', descending: true)
            .limit(500)
            .snapshots(),
        builder: (context, snap) {
          final docs = snap.data?.docs ?? [];

          double totalGold = 0;
          int count = 0;

          final start =
              DateTime(range.start.year, range.start.month, range.start.day);
          final end = DateTime(
              range.end.year, range.end.month, range.end.day, 23, 59, 59);

          for (final d in docs) {
            final data = d.data();
            final ts = data['createdAt'];
            if (ts is! Timestamp) continue;
            final dt = ts.toDate();

            if (dt.isBefore(start) || dt.isAfter(end)) continue;

            final v = data['toAmount'];
            if (v is num) totalGold += v.toDouble();
            count += 1;
          }

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  color: Colors.blue.shade50,
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text("Your Task Earnings",
                        style: TextStyle(
                            fontWeight: FontWeight.w900, fontSize: 16)),
                    const SizedBox(height: 6),
                    Text(
                        "Range: ${_fmtDate(range.start)} → ${_fmtDate(range.end)}",
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    Text("Tasks done: $count",
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                    Text("Gold earned: 🪙 ${totalGold.toStringAsFixed(0)}",
                        style: const TextStyle(fontWeight: FontWeight.w900)),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: pickRange,
                      icon: const Icon(Icons.date_range),
                      label: const Text("Change Date Range"),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const Text("Offerwall (Coming Soon)",
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 8),
              Card(
                elevation: 0,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18)),
                child: ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.rocket_launch)),
                  title: const Text("Connect Offerwall",
                      style: TextStyle(fontWeight: FontWeight.w900)),
                  subtitle: const Text(
                      "Here we will add tasks from offerwall provider."),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                          content: Text("Offerwall integration next ✅")),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
