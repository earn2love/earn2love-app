import 'dart:async';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/coin_service.dart';
import '../services/streak_service.dart';
import 'wallet_history_page.dart';
import 'payment_page.dart';

class WalletPage extends StatefulWidget {
  const WalletPage({super.key});

  @override
  State<WalletPage> createState() => _WalletPageState();
}

class _WalletPageState extends State<WalletPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  bool busy = false;

  String fromCoin = 'Silver';
  String toCoin = 'Gold';
  final amountCtrl = TextEditingController();

  String info = '';

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

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  bool hasLove(String tier) => tier == 'love';
  bool hasFriendshipOrLove(String tier) => tier == 'friendship' || tier == 'love';

  List<String> get coinList => const ['Silver', 'Gold', 'Diamond'];

  List<String> get toOptions {
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

  Future<void> addDummySilver(int amount) async {
    setState(() {
      busy = true;
      info = '';
    });
    try {
      await CoinService.addSilver(amount, reason: 'ads');
      if (!mounted) return;
      setState(() => info = "+$amount 🥈 Silver added ✅");
    } catch (e) {
      if (!mounted) return;
      setState(() => info = "Failed: $e");
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget _pill(String text, {Color? bg, Color? border, Color? fg}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: bg ?? Colors.grey.shade100,
        border: Border.all(color: border ?? Colors.grey.shade300),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontWeight: FontWeight.w900,
          fontSize: 12,
          color: fg,
        ),
      ),
    );
  }

  Widget _infoBox() {
    if (info.isEmpty) return const SizedBox.shrink();
    final isFail = info.toLowerCase().contains('fail');
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: isFail ? Colors.red.shade50 : Colors.green.shade50,
        border: Border.all(color: isFail ? Colors.red.shade200 : Colors.green.shade200),
      ),
      child: Text(
        info,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontWeight: FontWeight.w900,
          color: isFail ? Colors.red : Colors.green.shade800,
        ),
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
            colors: [Colors.grey.shade100, Colors.grey.shade50],
          ),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 24)),
            const SizedBox(height: 10),
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            Text(hint, style: TextStyle(fontSize: 11, color: Colors.grey.shade700)),
          ],
        ),
      ),
    );
  }

  Widget walletCard(Map<String, dynamic> u) {
    final silver = asDouble(u['silverBalance']).toStringAsFixed(0);
    final gold = asDouble(u['goldBalance']).toStringAsFixed(0);
    final diamond = asDouble(u['diamondBalance']).toStringAsFixed(0);

    final tier = asString(u['tier'] ?? u['subTier'], def: 'casual');

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(Icons.account_balance_wallet),
                const SizedBox(width: 8),
                const Text("Your Wallet", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                const Spacer(),
                _pill(tier.toUpperCase()),
              ],
            ),
            const SizedBox(height: 12),
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
                  hint: "Tasks • Conversion",
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

  Widget _planSection({
    required String currentTier,
    required String sectionTier,
    required String title,
    required IconData icon,
    required String badgeText,
    required Color badgeBg,
    required Color badgeBorder,
    required List<String> bullets,
    required VoidCallback onTap,
    bool paid = false,
  }) {
    final active = currentTier == sectionTier;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        leading: CircleAvatar(
          backgroundColor: active ? Colors.green.shade50 : Colors.grey.shade100,
          child: Icon(icon, color: active ? Colors.green.shade700 : null),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
            if (active)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: _pill(
                  "ACTIVE",
                  bg: Colors.green.shade50,
                  border: Colors.green.shade200,
                  fg: Colors.green.shade800,
                ),
              ),
            _pill(
              badgeText,
              bg: badgeBg,
              border: badgeBorder,
            ),
          ],
        ),
        subtitle: Text(
          active ? "Currently enabled for your account ✅" : "Open to see what is included",
        ),
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              color: Colors.grey.shade50,
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "$title includes",
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                ...bullets.map(
                  (b) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text("• $b"),
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: active ? null : onTap,
                    icon: Icon(active ? Icons.check_circle : (paid ? Icons.lock_open : Icons.verified)),
                    label: Text(
                      active
                          ? "$title Active"
                          : paid
                              ? "Choose $title"
                              : "Switch to $title",
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget planOptions(Map<String, dynamic> u) {
    final tier = asString(u['tier'] ?? u['subTier'], def: 'casual');
    final country = asString(u['country'], def: 'IN');
    final currencySymbol = asString(u['currencySymbol'], def: country == 'IN' ? '₹' : '£');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text("Plans", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
        const SizedBox(height: 8),
        _planSection(
          currentTier: tier,
          sectionTier: 'casual',
          title: 'Casual',
          icon: Icons.person_outline,
          badgeText: 'FREE',
          badgeBg: Colors.green.shade50,
          badgeBorder: Colors.green.shade200,
          bullets: const [
            'Basic profile access',
            'Send casual-level requests',
            'Watch ads and earn Silver',
            'Use wallet basics',
            'No premium task unlock',
          ],
          onTap: () async {
            await userRef.set({
              'tier': 'casual',
              'subTier': 'casual',
              'updatedAt': FieldValue.serverTimestamp(),
            }, SetOptions(merge: true));
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text("Casual activated ✅")),
            );
          },
        ),
        _planSection(
          currentTier: tier,
          sectionTier: 'friendship',
          title: 'Friendship',
          icon: Icons.group_outlined,
          badgeText: '${currencySymbol}4.99',
          badgeBg: Colors.amber.shade50,
          badgeBorder: Colors.amber.shade200,
          bullets: const [
            'Everything in Casual',
            'Friendship tier access',
            'Offerwall / task unlock',
            'Better social access',
            'Premium feature expansion',
          ],
          paid: true,
          onTap: () async {
            final ok = await Navigator.push<bool>(
              context,
              MaterialPageRoute(
                builder: (_) => const PaymentPage(targetTier: 'friendship'),
              ),
            );
            if (!mounted) return;
            if (ok == true) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Friendship activated ✅")),
              );
            }
          },
        ),
        _planSection(
          currentTier: tier,
          sectionTier: 'love',
          title: 'Love',
          icon: Icons.favorite_border,
          badgeText: '${currencySymbol}9.99',
          badgeBg: Colors.pink.shade50,
          badgeBorder: Colors.pink.shade200,
          bullets: const [
            'Everything in Friendship',
            'Highest priority access',
            'Love plan features',
            'Diamond withdraw eligibility',
            'Premium wallet unlocks',
          ],
          paid: true,
          onTap: () async {
            final ok = await Navigator.push<bool>(
              context,
              MaterialPageRoute(
                builder: (_) => const PaymentPage(targetTier: 'love'),
              ),
            );
            if (!mounted) return;
            if (ok == true) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Love activated ✅")),
              );
            }
          },
        ),
        const SizedBox(height: 8),
        Card(
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.play_circle)),
            title: const Text("Ads", style: TextStyle(fontWeight: FontWeight.w900)),
            subtitle: const Text("Earn Silver by watching ads (dummy now)"),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => addDummySilver(10),
          ),
        ),
        Card(
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.task_alt)),
            title: const Text("Tasks", style: TextStyle(fontWeight: FontWeight.w900)),
            subtitle: Text(
              hasFriendshipOrLove(tier)
                  ? "Offerwall tasks → earn Gold"
                  : "Locked for Casual. Upgrade to Friendship or Love",
            ),
            trailing: hasFriendshipOrLove(tier)
                ? const Icon(Icons.chevron_right)
                : const Icon(Icons.lock),
            onTap: hasFriendshipOrLove(tier)
                ? () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text("Offerwall integration next ✅")),
                    );
                  }
                : null,
          ),
        ),
      ],
    );
  }

  Widget _sectionCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required Widget child,
    bool locked = false,
    String lockedText = "Locked",
  }) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        leading: Icon(icon),
        title: Row(
          children: [
            Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w900))),
            if (locked)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: Colors.red.shade50,
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(lockedText, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
              ),
          ],
        ),
        subtitle: Text(subtitle),
        children: [
          if (locked)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.red.shade50,
                border: Border.all(color: Colors.red.shade200),
              ),
              child: const Text(
                "This section is locked for your plan.\nUpgrade later (payments integration pending).",
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
            )
          else
            child,
        ],
      ),
    );
  }

  Widget ratesCard(String country, String currencySymbol) {
    final s2g = (country == 'UK') ? "3 Silver → 2.5 Gold" : "3 Silver → 2 Gold";
    final g2d = (country == 'UK') ? "3 Gold → 2.5 Diamond" : "3 Gold → 2 Diamond";

    String cash;
    if (country == 'UK') {
      cash = "1 Diamond = £0.01 (min £150)";
    } else if (country == 'IN') {
      cash = "1 Diamond = ₹0.01 (min ₹10,000)";
    } else if (country == 'US' || country == 'AU') {
      cash = "1 Diamond = ${currencySymbol}0.01 (min ${currencySymbol}150)";
    } else if (country == 'UAE') {
      cash = "1 Diamond = AED 0.01 (min AED 150)";
    } else {
      cash = "1 Diamond = ${currencySymbol}0.01 (min ${currencySymbol}150)";
    }

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
          Text("Rates ($country)", style: const TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          Text("• $s2g"),
          Text("• $g2d"),
          Text("• Withdraw: $cash"),
          const SizedBox(height: 6),
          const Text("Note: Direct Silver → Diamond not allowed.", style: TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  Widget conversionUI(Map<String, dynamic> u) {
    final country = asString(u['country'], def: 'IN');
    final currencySymbol = asString(u['currencySymbol'], def: country == 'IN' ? '₹' : '£');
    final streakDays = asInt(u['streakDays']);
    final bonusPct = asInt(u['streakBonusPct']);

    final opts = toOptions;
    if (!opts.contains(toCoin)) toCoin = opts.first;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: fromCoin,
                decoration: const InputDecoration(labelText: "From", border: OutlineInputBorder()),
                items: coinList.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
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
                decoration: const InputDecoration(labelText: "To", border: OutlineInputBorder()),
                items: toOptions.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                onChanged: busy ? null : (v) => setState(() => toCoin = v ?? toCoin),
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
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
          ),
        ),
        const SizedBox(height: 10),
        ElevatedButton.icon(
          onPressed: busy ? null : () => doConvert(bonusPct.toDouble()),
          icon: const Icon(Icons.swap_horiz),
          label: Text(busy ? "Please wait..." : "Convert"),
        ),
        const SizedBox(height: 10),
        ratesCard(country, currencySymbol),
      ],
    );
  }

  Widget streakUI(Map<String, dynamic> u) {
    final days = asInt(u['streakDays']);
    final bonus = asInt(u['streakBonusPct']);

    double progress = days / 30.0;
    if (progress < 0) progress = 0;
    if (progress > 1) progress = 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Current: $days days", style: const TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text("Bonus: $bonus% (Silver→Gold)", style: const TextStyle(fontWeight: FontWeight.w800)),
                ],
              ),
            ),
            const SizedBox(width: 10),
            SizedBox(width: 120, child: LinearProgressIndicator(value: progress, minHeight: 10)),
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
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Wallet")),
      body: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: userRef.snapshots(),
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          final u = snap.data?.data() ?? {};
          final tier = asString(u['tier'] ?? u['subTier'], def: 'casual');
          final love = hasLove(tier);
          final country = asString(u['country'], def: 'IN');
          final currencySymbol = asString(u['currencySymbol'], def: country == 'IN' ? '₹' : '£');

          String withdrawText;
          if (country == 'UK') {
            withdrawText = "Diamond → cash (Love only, KYC needed)";
          } else if (country == 'IN') {
            withdrawText = "Diamond → cash (Love only, KYC needed)";
          } else {
            withdrawText = "Diamond → cash (Love only, KYC needed)";
          }

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              walletCard(u),
              const SizedBox(height: 10),
              planOptions(u),
              const SizedBox(height: 10),
              _sectionCard(
                icon: Icons.swap_horiz,
                title: "Convert Coins",
                subtitle: "Silver ↔ Gold ↔ Diamond with streak bonus",
                child: conversionUI(u),
              ),
              _sectionCard(
                icon: Icons.history,
                title: "Wallet History",
                subtitle: "Ads, top-up, calls, conversions and rewards",
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text("Open full wallet history with details."),
                    const SizedBox(height: 10),
                    ElevatedButton.icon(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const WalletHistoryPage()),
                        );
                      },
                      icon: const Icon(Icons.open_in_new),
                      label: const Text("Open Wallet History"),
                    ),
                  ],
                ),
              ),
              _sectionCard(
                icon: Icons.local_fire_department,
                title: "Streak Rewards",
                subtitle: "Daily activity → conversion bonus",
                child: streakUI(u),
              ),
              _sectionCard(
                icon: Icons.account_balance,
                title: "Withdraw",
                subtitle: withdrawText,
                locked: !love,
                lockedText: "Love only",
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      country == 'UK'
                          ? "Rules summary:\n• UK min £150\n• 48hrs–7 business days"
                          : country == 'IN'
                              ? "Rules summary:\n• IN min ₹10,000\n• 48hrs–7 business days"
                              : "Rules summary:\n• Min ${currencySymbol}150\n• 48hrs–7 business days",
                    ),
                    const SizedBox(height: 10),
                    ElevatedButton(
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text("Withdraw flow (KYC + request status) next ✅")),
                        );
                      },
                      child: const Text("Start Withdraw (coming soon)"),
                    ),
                  ],
                ),
              ),
              _infoBox(),
              const SizedBox(height: 40),
            ],
          );
        },
      ),
    );
  }
}