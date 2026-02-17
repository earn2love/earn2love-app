import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/coin_service.dart';
import '../services/streak_service.dart';
import 'wallet_history_page.dart';

class EarnPage extends StatefulWidget {
  const EarnPage({super.key});

  @override
  State<EarnPage> createState() => _EarnPageState();
}

class _EarnPageState extends State<EarnPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  bool busy = false;

  // conversion UI
  String fromCoin = 'Silver';
  String toCoin = 'Gold';
  final amountCtrl = TextEditingController();

  String info = '';

  // ---------------- SAFE PARSERS (prevents crash) ----------------
  double asDouble(dynamic v, {double def = 0}) {
    if (v == null) return def;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v.trim()) ?? def;
    return def;
  }

  int asInt(dynamic v, {int def = 0}) {
    if (v == null) return def;
    if (v is int) return v;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v.trim()) ?? def;
    return def;
  }

  List<String> get coinList => const ['Silver', 'Gold', 'Diamond'];

  List<String> get toOptions {
    // disallow Silver -> Diamond direct
    if (fromCoin == 'Silver') return const ['Gold'];
    if (fromCoin == 'Gold') return const ['Silver', 'Diamond'];
    if (fromCoin == 'Diamond') return const ['Gold'];
    return const ['Gold'];
  }

  @override
  void dispose() {
    amountCtrl.dispose();
    super.dispose();
  }

  Future<void> doConvert(double bonusPct) async {
    final amt = double.tryParse(amountCtrl.text.trim());
    if (amt == null || amt <= 0) {
      setState(() => info = "Enter valid amount");
      return;
    }

    setState(() {
      busy = true;
      info = '';
    });

    try {
      await CoinService.convertCoins(
        from: fromCoin,
        to: toCoin,
        amount: amt,
        bonusPct: bonusPct,
      );

      if (!mounted) return;
      setState(() => info = "Converted ✅");
    } catch (e) {
      if (!mounted) return;
      setState(() => info = "Failed: $e");
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> checkStreak() async {
    setState(() {
      busy = true;
      info = '';
    });

    try {
      final res = await StreakService.updateStreakIfEligible();
      if (!mounted) return;
      setState(() => info = res['msg']?.toString() ?? "Done");
    } catch (e) {
      if (!mounted) return;
      setState(() => info = "Streak check failed: $e");
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  // ---------------- UI HELPERS ----------------
  Widget _sectionTitle(String text, {IconData? icon}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          if (icon != null) ...[
            Icon(icon, size: 18),
            const SizedBox(width: 6),
          ],
          Text(
            text,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
          ),
        ],
      ),
    );
  }

  Widget _walletTile({
    required String emoji,
    required String label,
    required String value,
    required String hint,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.grey.shade100,
              Colors.grey.shade50,
            ],
          ),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 24)),
            const SizedBox(height: 10),
            Text(
              value,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 2),
            Text(label,
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            Text(hint,
                style: TextStyle(fontSize: 11, color: Colors.grey.shade700)),
          ],
        ),
      ),
    );
  }

  Widget walletCard(Map<String, dynamic> u) {
    final silver = asDouble(u['silverBalance']).toStringAsFixed(0);
    final gold = asDouble(u['goldBalance']).toStringAsFixed(0);
    final diamond = asDouble(u['diamondBalance']).toStringAsFixed(0);

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _sectionTitle("Your Wallet", icon: Icons.account_balance_wallet),
            const SizedBox(height: 10),
            Row(
              children: [
                _walletTile(
                  emoji: "🥈",
                  label: "Silver",
                  value: silver,
                  hint: "Ads • Top-up • Calls",
                ),
                const SizedBox(width: 10),
                _walletTile(
                  emoji: "🪙",
                  label: "Gold",
                  value: gold,
                  hint: "Tasks / Offerwall",
                ),
                const SizedBox(width: 10),
                _walletTile(
                  emoji: "💎",
                  label: "Diamond",
                  value: diamond,
                  hint: "Withdraw later",
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget ratesCard(String country) {
    final s2g = (country == 'UK') ? "3 Silver → 2.5 Gold" : "3 Silver → 2 Gold";
    final g2d =
        (country == 'UK') ? "3 Gold → 2.5 Diamond" : "3 Gold → 2 Diamond";
    final cash = (country == 'UK')
        ? "1 Diamond = £0.01 (min £150)"
        : "1 Diamond = ₹0.01 (min ₹10,000)";

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Rates ($country)",
              style: const TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          Text("• $s2g"),
          Text("• $g2d"),
          Text("• Withdraw: $cash"),
          const SizedBox(height: 6),
          const Text("Note: Direct Silver → Diamond not allowed.",
              style: TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  Widget conversionCard(Map<String, dynamic> u) {
    final country = (u['country'] ?? 'IN').toString();
    final streakDays = asInt(u['streakDays']);
    final bonusPct = asInt(u['streakBonusPct']);

    // ensure toCoin valid when from changes
    final opts = toOptions;
    if (!opts.contains(toCoin)) toCoin = opts.first;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _sectionTitle("Conversion", icon: Icons.swap_horiz),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: fromCoin,
                    decoration: const InputDecoration(
                      labelText: "From",
                      border: OutlineInputBorder(),
                    ),
                    items: coinList
                        .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                        .toList(),
                    onChanged: busy
                        ? null
                        : (v) {
                            if (v == null) return;
                            setState(() {
                              fromCoin = v;
                              final opts2 = toOptions;
                              toCoin = opts2.first;
                            });
                          },
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: toCoin,
                    decoration: const InputDecoration(
                      labelText: "To",
                      border: OutlineInputBorder(),
                    ),
                    items: toOptions
                        .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                        .toList(),
                    onChanged: busy
                        ? null
                        : (v) => setState(() => toCoin = v ?? toCoin),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            TextField(
              controller: amountCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: "Amount",
                border: OutlineInputBorder(),
                hintText: "e.g. 30",
              ),
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.grey.shade50,
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Text(
                "Streak: $streakDays days • Bonus (Silver→Gold): $bonusPct%",
                style:
                    const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(height: 10),
            ElevatedButton.icon(
              onPressed: busy ? null : () => doConvert(bonusPct.toDouble()),
              icon: const Icon(Icons.swap_horiz),
              label: Text(busy ? "Please wait..." : "Convert"),
            ),
            const SizedBox(height: 10),
            ratesCard(country),
          ],
        ),
      ),
    );
  }

  Widget streakCard(Map<String, dynamic> u) {
    final days = asInt(u['streakDays']);
    final bonus = asInt(u['streakBonusPct']);

    double progress = days / 30.0;
    if (progress < 0) progress = 0;
    if (progress > 1) progress = 1;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _sectionTitle("Streak System", icon: Icons.local_fire_department),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Current: $days days",
                          style: const TextStyle(fontWeight: FontWeight.w900)),
                      const SizedBox(height: 4),
                      Text("Bonus: $bonus% (Silver→Gold)",
                          style: const TextStyle(fontWeight: FontWeight.w800)),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 120,
                  child:
                      LinearProgressIndicator(value: progress, minHeight: 10),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.grey.shade50,
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: const Text(
                "Rules:\n"
                "• Daily: 3 active chats\n"
                "• Each chat: minimum 10 messages\n\n"
                "Rewards:\n"
                "• 7 days: +5% on Silver→Gold\n"
                "• 14 days: +7%\n"
                "• 30 days: +10% (then resets)",
                style: TextStyle(fontSize: 12),
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: busy ? null : checkStreak,
              child: Text(busy ? "Checking..." : "Check Today & Update Streak"),
            ),
          ],
        ),
      ),
    );
  }

  Widget offersCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Offers / Promotions",
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
            SizedBox(height: 8),
            Text("Coming soon: promos, bonus silver, subscriptions discounts."),
          ],
        ),
      ),
    );
  }

  Widget historyShortcut() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: ListTile(
        leading: const Icon(Icons.history),
        title: const Text("Wallet History",
            style: TextStyle(fontWeight: FontWeight.w900)),
        subtitle: const Text("Filters: topup, ads, calls, conversion..."),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const WalletHistoryPage()),
          );
        },
      ),
    );
  }

  Widget adsCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _sectionTitle("Ads (Dummy)", icon: Icons.play_circle),
            const Text("Phase 1 testing: tap to add Silver."),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: busy
                  ? null
                  : () async {
                      setState(() {
                        busy = true;
                        info = '';
                      });
                      try {
                        await CoinService.addSilver(10, reason: 'ads');
                        if (!mounted) return;
                        setState(() => info = "+10 🥈 Silver added ✅");
                      } catch (e) {
                        if (!mounted) return;
                        setState(() => info = "Failed: $e");
                      } finally {
                        if (mounted) setState(() => busy = false);
                      }
                    },
              icon: const Icon(Icons.play_circle),
              label: Text(busy ? "Please wait..." : "Watch Ad → +10 🥈"),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Earn")),
      body: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: userRef.snapshots(),
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          final u = snap.data?.data() ?? {};

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              walletCard(u),
              const SizedBox(height: 10),
              adsCard(),
              const SizedBox(height: 10),
              conversionCard(u),
              const SizedBox(height: 10),
              historyShortcut(),
              const SizedBox(height: 10),
              streakCard(u),
              const SizedBox(height: 10),
              offersCard(),
              if (info.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: info.toLowerCase().contains("fail")
                        ? Colors.red.shade50
                        : Colors.green.shade50,
                    border: Border.all(
                      color: info.toLowerCase().contains("fail")
                          ? Colors.red.shade200
                          : Colors.green.shade200,
                    ),
                  ),
                  child: Text(
                    info,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      color: info.toLowerCase().contains("fail")
                          ? Colors.red
                          : Colors.green.shade800,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 40),
            ],
          );
        },
      ),
    );
  }
}
