import 'package:flutter/material.dart';

import '../services/payment_service.dart';

class PaymentTestPage extends StatefulWidget {
  const PaymentTestPage({super.key});

  @override
  State<PaymentTestPage> createState() => _PaymentTestPageState();
}

class _PaymentTestPageState extends State<PaymentTestPage> {
  bool _loading = false;

  Future<void> _buy(String packId) async {
    setState(() => _loading = true);
    try {
      await PaymentService.buyPack(packId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Payment completed')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Payment failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Widget _packButton(String title, String packId) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _loading ? null : () => _buy(packId),
        child: Text(title),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment Test'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            if (_loading) const LinearProgressIndicator(),
            const SizedBox(height: 16),
            _packButton('Buy £1.99 - 100 Silver', 'uk_199'),
            _packButton('Buy £4.99 - 280 Silver', 'uk_499'),
            _packButton('Buy £9.99 - 620 Silver', 'uk_999'),
            const SizedBox(height: 20),
            _packButton('Buy ₹99 - 100 Silver', 'in_99'),
            _packButton('Buy ₹299 - 280 Silver', 'in_299'),
            _packButton('Buy ₹499 - 620 Silver', 'in_499'),
          ],
        ),
      ),
    );
  }
}