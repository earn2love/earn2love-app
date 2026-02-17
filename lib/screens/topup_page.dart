import 'package:flutter/material.dart';
import '../services/coin_service.dart';

class TopUpPage extends StatelessWidget {
  final String country;
  const TopUpPage({super.key, required this.country});

  @override
  Widget build(BuildContext context) {
    final isUk = country == 'UK';

    final packs = isUk
        ? const [
            {'label': '£1', 'silver': 50},
            {'label': '£5', 'silver': 250},
            {'label': '£10', 'silver': 500},
            {'label': '£20', 'silver': 1000},
          ]
        : const [
            {'label': '₹100', 'silver': 100},
            {'label': '₹500', 'silver': 500},
            {'label': '₹1000', 'silver': 1000},
            {'label': '₹2000', 'silver': 2000},
          ];

    final rateText = isUk ? "£1 = 50 🥈 Silver" : "₹100 = 100 🥈 Silver";

    return Scaffold(
      appBar: AppBar(title: const Text("Top Up")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Topup Packs",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    "Phase-1: Payments later. Now it adds Silver for testing.",
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Rate: $rateText",
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          ...packs.map((p) {
            final label = p['label'].toString();
            final silver = (p['silver'] as int);

            return Card(
              child: ListTile(
                leading: const Text("🥈", style: TextStyle(fontSize: 22)),
                title: Text("Pack $label",
                    style: const TextStyle(fontWeight: FontWeight.w900)),
                subtitle: Text("+$silver Silver"),
                trailing: const Icon(Icons.chevron_right),
                onTap: () async {
                  try {
                    await CoinService.addSilver(silver, reason: 'topup');
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text("Added +$silver 🥈 Silver ✅")),
                      );
                    }
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text("Failed: $e")),
                      );
                    }
                  }
                },
              ),
            );
          }),
        ],
      ),
    );
  }
}
