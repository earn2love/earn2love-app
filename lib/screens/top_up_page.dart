import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/coin_service.dart';

class TopUpPage extends StatelessWidget {
  final String country; // "UK" / "IN"
  const TopUpPage({super.key, required this.country});

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get meRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  double asDouble(dynamic v, {double def = 0}) {
    if (v == null) return def;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v.trim()) ?? def;
    return def;
  }

  List<Map<String, dynamic>> _packsForCountry(String c) {
    if (c == 'IN') {
      return const [
        {'price': '₹99', 'coins': 100, 'bonus': 0, 'badge': 'STARTER'},
        {'price': '₹299', 'coins': 260, 'bonus': 20, 'badge': 'POPULAR'},
        {'price': '₹499', 'coins': 550, 'bonus': 70, 'badge': 'BEST VALUE'},
        {'price': '₹999', 'coins': 1200, 'bonus': 200, 'badge': 'MEGA'},
        {'price': '₹2499', 'coins': 3200, 'bonus': 800, 'badge': 'ULTRA'},
      ];
    }
    if (c == 'US') {
      return const [
        {'price': '\$1.99', 'coins': 100, 'bonus': 0, 'badge': 'STARTER'},
        {'price': '\$4.99', 'coins': 260, 'bonus': 20, 'badge': 'POPULAR'},
        {'price': '\$9.99', 'coins': 550, 'bonus': 70, 'badge': 'BEST VALUE'},
        {'price': '\$19.99', 'coins': 1200, 'bonus': 200, 'badge': 'MEGA'},
        {'price': '\$49.99', 'coins': 3200, 'bonus': 800, 'badge': 'ULTRA'},
      ];
    }
    if (c == 'AU') {
      return const [
        {'price': '\$1.99', 'coins': 100, 'bonus': 0, 'badge': 'STARTER'},
        {'price': '\$4.99', 'coins': 260, 'bonus': 20, 'badge': 'POPULAR'},
        {'price': '\$9.99', 'coins': 550, 'bonus': 70, 'badge': 'BEST VALUE'},
        {'price': '\$19.99', 'coins': 1200, 'bonus': 200, 'badge': 'MEGA'},
        {'price': '\$49.99', 'coins': 3200, 'bonus': 800, 'badge': 'ULTRA'},
      ];
    }
    if (c == 'UAE') {
      return const [
        {'price': 'AED 9', 'coins': 100, 'bonus': 0, 'badge': 'STARTER'},
        {'price': 'AED 19', 'coins': 260, 'bonus': 20, 'badge': 'POPULAR'},
        {'price': 'AED 39', 'coins': 550, 'bonus': 70, 'badge': 'BEST VALUE'},
        {'price': 'AED 79', 'coins': 1200, 'bonus': 200, 'badge': 'MEGA'},
        {'price': 'AED 199', 'coins': 3200, 'bonus': 800, 'badge': 'ULTRA'},
      ];
    }

    return const [
      {'price': '£1.99', 'coins': 100, 'bonus': 0, 'badge': 'STARTER'},
      {'price': '£4.99', 'coins': 260, 'bonus': 20, 'badge': 'POPULAR'},
      {'price': '£9.99', 'coins': 550, 'bonus': 70, 'badge': 'BEST VALUE'},
      {'price': '£19.99', 'coins': 1200, 'bonus': 200, 'badge': 'MEGA'},
      {'price': '£49.99', 'coins': 3200, 'bonus': 800, 'badge': 'ULTRA'},
    ];
  }

  @override
  Widget build(BuildContext context) {
    final packs = _packsForCountry(country);
    final featured = packs[2];
    final others = [packs[0], packs[1], packs[3], packs[4]];

    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(title: const Text("Top Up")),
      body: SafeArea(
        child: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
          stream: meRef.snapshots(),
          builder: (context, snap) {
            final me = snap.data?.data() ?? {};
            final silver = asDouble(me['silverBalance']).toStringAsFixed(0);

            return CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
                    child: _HeroBalanceCard(country: country, silver: silver),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 6, 14, 10),
                    child: Row(
                      children: [
                        const Expanded(
                          child: Text(
                            "Choose your pack",
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(999),
                            color: Colors.white,
                            border: Border.all(color: Colors.grey.shade200),
                          ),
                          child: Text(
                            "Offers",
                            style: TextStyle(
                              fontWeight: FontWeight.w900,
                              fontSize: 12,
                              color: Colors.green.shade800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
                    child: _FeaturedPackCard(
                      price: featured['price'] as String,
                      coins: featured['coins'] as int,
                      bonus: featured['bonus'] as int,
                      badge: featured['badge'] as String,
                      onTap: () => _openCheckout(
                        context,
                        label: featured['price'] as String,
                        totalSilver: (featured['coins'] as int) + (featured['bonus'] as int),
                        bonusSilver: featured['bonus'] as int,
                      ),
                    ),
                  ),
                ),
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                  sliver: SliverGrid(
                    delegate: SliverChildBuilderDelegate(
                      (context, i) {
                        final p = others[i];
                        return _PackCardGrid(
                          price: p['price'] as String,
                          coins: p['coins'] as int,
                          bonus: p['bonus'] as int,
                          badge: p['badge'] as String,
                          onTap: () => _openCheckout(
                            context,
                            label: p['price'] as String,
                            totalSilver: (p['coins'] as int) + (p['bonus'] as int),
                            bonusSilver: p['bonus'] as int,
                          ),
                        );
                      },
                      childCount: others.length,
                    ),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      mainAxisExtent: 164,
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 0, 14, 18),
                    child: Card(
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              height: 42,
                              width: 42,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                color: Colors.indigo.shade50,
                                border: Border.all(color: Colors.indigo.shade100),
                              ),
                              child: Icon(Icons.lock_outline, color: Colors.indigo.shade400),
                            ),
                            const SizedBox(width: 12),
                            const Expanded(
                              child: Text(
                                "Demo checkout: Pay Now → coins add avtayi.\nPayment gateway next ✅",
                                style: TextStyle(fontWeight: FontWeight.w800, height: 1.35),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _openCheckout(
    BuildContext context, {
    required String label,
    required int totalSilver,
    required int bonusSilver,
  }) async {
    await showModalBottomSheet(
      context: context,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) {
        return SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Container(
                      height: 44,
                      width: 44,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        color: Colors.amber.shade50,
                        border: Border.all(color: Colors.amber.shade200),
                      ),
                      child: const Center(child: Text("🥈", style: TextStyle(fontSize: 20))),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "Checkout",
                            style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            "Pack $label",
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Colors.pink.shade400, Colors.purple.shade500, Colors.indigo.shade600],
                    ),
                  ),
                  child: Row(
                    children: [
                      const Expanded(
                        child: Text(
                          "You will receive",
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                        ),
                      ),
                      Text(
                        "$totalSilver 🥈",
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22),
                      ),
                    ],
                  ),
                ),
                if (bonusSilver > 0) ...[
                  const SizedBox(height: 10),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      color: Colors.green.shade50,
                      border: Border.all(color: Colors.green.shade200),
                    ),
                    child: Text(
                      "Bonus included: +$bonusSilver Silver 🎁",
                      style: TextStyle(fontWeight: FontWeight.w900, color: Colors.green.shade800),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  onPressed: () async {
                    try {
                      await CoinService.addSilver(totalSilver, reason: 'topup');
                      if (context.mounted) {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text("Success ✅ Added +$totalSilver 🥈 Silver")),
                        );
                      }
                    } catch (e) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed: $e")));
                      }
                    }
                  },
                  icon: const Icon(Icons.payment),
                  label: Text("Pay Now ($label)", style: const TextStyle(fontWeight: FontWeight.w900)),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _HeroBalanceCard extends StatelessWidget {
  final String country;
  final String silver;
  const _HeroBalanceCard({required this.country, required this.silver});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.pink.shade400, Colors.purple.shade500, Colors.indigo.shade600],
        ),
        boxShadow: [
          BoxShadow(
            blurRadius: 18,
            offset: const Offset(0, 10),
            color: Colors.black.withOpacity(0.12),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                height: 40,
                width: 40,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: Colors.white.withOpacity(0.18),
                  border: Border.all(color: Colors.white.withOpacity(0.22)),
                ),
                child: const Icon(Icons.account_balance_wallet, color: Colors.white, size: 20),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  "Top up Silver",
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  color: Colors.white.withOpacity(0.18),
                  border: Border.all(color: Colors.white.withOpacity(0.22)),
                ),
                child: Text(
                  country.toUpperCase(),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              color: Colors.white.withOpacity(0.14),
              border: Border.all(color: Colors.white.withOpacity(0.18)),
            ),
            child: Row(
              children: [
                const Text("🥈", style: TextStyle(fontSize: 22)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        "Balance",
                        style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800, fontSize: 12),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        silver,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: Colors.black.withOpacity(0.14),
                    border: Border.all(color: Colors.white.withOpacity(0.18)),
                  ),
                  child: const Text(
                    "Instant",
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FeaturedPackCard extends StatelessWidget {
  final String price;
  final int coins;
  final int bonus;
  final String badge;
  final VoidCallback onTap;

  const _FeaturedPackCard({
    required this.price,
    required this.coins,
    required this.bonus,
    required this.badge,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final total = coins + bonus;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Colors.purple.shade50, Colors.indigo.shade50],
            ),
            border: Border.all(color: Colors.purple.shade200),
          ),
          child: Row(
            children: [
              Container(
                height: 58,
                width: 58,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Colors.pink.shade400, Colors.purple.shade500, Colors.indigo.shade600],
                  ),
                ),
                child: const Center(child: Text("🥈", style: TextStyle(fontSize: 24))),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _Chip(text: badge, mode: _ChipMode.purple),
                        if (bonus > 0) _Chip(text: "+$bonus bonus", mode: _ChipMode.green),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      "$total Silver",
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: Colors.black87,
                ),
                child: Text(
                  "Buy $price",
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}

class _PackCardGrid extends StatelessWidget {
  final String price;
  final int coins;
  final int bonus;
  final String badge;
  final VoidCallback onTap;

  const _PackCardGrid({
    required this.price,
    required this.coins,
    required this.bonus,
    required this.badge,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final total = coins + bonus;
    final hasBonus = bonus > 0;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            color: Colors.white,
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _Chip(text: badge, mode: _ChipMode.neutral),
                  if (hasBonus) _Chip(text: "+$bonus", mode: _ChipMode.green),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  const Text("🥈", style: TextStyle(fontSize: 18)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      "$total",
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 22),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              Text(
                "Silver",
                style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.w800, fontSize: 12),
              ),
              const Spacer(),
              Container(
                height: 36,
                width: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Colors.pink.shade400, Colors.purple.shade500, Colors.indigo.shade600],
                  ),
                ),
                child: Center(
                  child: Text(
                    "Buy $price",
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

enum _ChipMode { neutral, green, purple }

class _Chip extends StatelessWidget {
  final String text;
  final _ChipMode mode;
  const _Chip({required this.text, required this.mode});

  @override
  Widget build(BuildContext context) {
    Color bg, border, fg;

    if (mode == _ChipMode.green) {
      bg = Colors.green.shade50;
      border = Colors.green.shade200;
      fg = Colors.green.shade800;
    } else if (mode == _ChipMode.purple) {
      bg = Colors.purple.shade50;
      border = Colors.purple.shade200;
      fg = Colors.purple.shade800;
    } else {
      bg = Colors.grey.shade100;
      border = Colors.grey.shade200;
      fg = Colors.grey.shade900;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: bg,
        border: Border.all(color: border),
      ),
      child: Text(
        text,
        style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11, color: fg, letterSpacing: 0.2),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}