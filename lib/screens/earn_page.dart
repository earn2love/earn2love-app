import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/coin_service.dart';

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
  String info = '';

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  bool hasFriendshipOrLove(String tier) => tier == 'friendship' || tier == 'love';

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
          final tier = asString(u['tier'] ?? u['subTier'], def: 'casual');
          final lockedTasks = !hasFriendshipOrLove(tier);

          Widget tile({
            required IconData icon,
            required String title,
            required String subtitle,
            required VoidCallback onTap,
            bool locked = false,
          }) {
            return Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: ListTile(
                leading: CircleAvatar(child: Icon(icon)),
                title: Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
                subtitle: Text(subtitle),
                trailing: locked ? const Icon(Icons.lock) : const Icon(Icons.chevron_right),
                onTap: locked ? null : onTap,
              ),
            );
          }

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              tile(
                icon: Icons.play_circle,
                title: "Ads",
                subtitle: "Earn Silver by watching ads (dummy now)",
                onTap: () => addDummySilver(10),
              ),
              tile(
                icon: Icons.task_alt,
                title: "Tasks",
                subtitle: lockedTasks
                    ? "Offerwall tasks → earn Gold (Friendship/Love only)"
                    : "Offerwall tasks → earn Gold (ready to integrate)",
                locked: lockedTasks,
                onTap: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Offerwall integration next ✅")),
                  );
                },
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