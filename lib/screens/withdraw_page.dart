import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class WithdrawPage extends StatefulWidget {
  const WithdrawPage({super.key});

  @override
  State<WithdrawPage> createState() => _WithdrawPageState();
}

class _WithdrawPageState extends State<WithdrawPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  CollectionReference<Map<String, dynamic>> get historyRef =>
      FirebaseFirestore.instance.collection('users').doc(uid).collection('walletHistory');

  bool loading = true;
  bool saving = false;
  String? status;

  // Bank details (placeholder for Phase 1)
  final accountNameCtrl = TextEditingController();
  final bankNameCtrl = TextEditingController();
  final accountNumberCtrl = TextEditingController();
  final ifscOrSortCtrl = TextEditingController(); // IFSC (IN) / Sort Code (UK)
  final upiCtrl = TextEditingController(); // optional

  double diamondBalance = 0;
  String country = "IN";

  double _num(dynamic v) {
    if (v is int) return v.toDouble();
    if (v is double) return v;
    if (v is num) return v.toDouble();
    return 0;
  }

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      status = null;
    });

    try {
      final snap = await userRef.get();
      final d = snap.data() ?? {};

      country = (d['country'] ?? "IN").toString();
      diamondBalance = _num(d['diamondBalance']);

      final bank = (d['bankDetails'] is Map) ? (d['bankDetails'] as Map) : {};
      accountNameCtrl.text = (bank['accountName'] ?? '').toString();
      bankNameCtrl.text = (bank['bankName'] ?? '').toString();
      accountNumberCtrl.text = (bank['accountNumber'] ?? '').toString();
      ifscOrSortCtrl.text = (bank['ifscOrSort'] ?? '').toString();
      upiCtrl.text = (bank['upiId'] ?? '').toString();
    } catch (e) {
      status = "Load failed: $e";
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> saveBankDetails() async {
    setState(() {
      saving = true;
      status = null;
    });

    try {
      await userRef.set({
        'bankDetails': {
          'accountName': accountNameCtrl.text.trim(),
          'bankName': bankNameCtrl.text.trim(),
          'accountNumber': accountNumberCtrl.text.trim(),
          'ifscOrSort': ifscOrSortCtrl.text.trim(),
          'upiId': upiCtrl.text.trim(),
        },
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      status = "Bank details saved ✅";
    } catch (e) {
      status = "Save failed: $e";
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  // Phase 1: just create a withdraw request entry (no real withdrawal yet)
  Future<void> requestWithdraw() async {
    // Rules you decided (Phase 1 enforce basic)
    if (country == "IN") {
      // 1 diamond = 10000 INR, minimum withdraw not less (means need >=1 diamond)
      if (diamondBalance < 1) {
        setState(() => status = "Need at least 1 💎 Diamond to withdraw (India).");
        return;
      }
    } else if (country == "UK") {
      // 1 diamond = £0.01, minimum withdraw £150 => need 150/0.01 = 15000 diamonds
      if (diamondBalance < 15000) {
        setState(() => status = "Need at least 15000 💎 Diamonds to withdraw (UK).");
        return;
      }
    }

    setState(() {
      saving = true;
      status = null;
    });

    try {
      await historyRef.add({
        'type': 'withdraw',
        'title': 'Withdraw request',
        'fromCoin': 'Diamond',
        'fromAmount': 0, // we will implement deduction later (phase 2)
        'toCoin': 'Cash',
        'toAmount': 0,
        'country': country,
        'createdAt': FieldValue.serverTimestamp(),
        'status': 'requested',
      });

      status = "Withdraw request submitted ✅ (Phase 1 placeholder)";
    } catch (e) {
      status = "Request failed: $e";
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  void dispose() {
    accountNameCtrl.dispose();
    bankNameCtrl.dispose();
    accountNumberCtrl.dispose();
    ifscOrSortCtrl.dispose();
    upiCtrl.dispose();
    super.dispose();
  }

  InputDecoration _dec(String label, {String? hint}) => InputDecoration(
        labelText: label,
        hintText: hint,
        border: const OutlineInputBorder(),
      );

  Widget _field(TextEditingController c, String label, {String? hint, TextInputType? type}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: c,
        keyboardType: type,
        decoration: _dec(label, hint: hint),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final minText = (country == "UK")
        ? "Minimum: £150 (needs 15000 Diamonds)"
        : "Minimum: 1 Diamond (India rule)";

    return Scaffold(
      appBar: AppBar(title: const Text("Withdrawals")),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text("Your Balance", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                        const SizedBox(height: 8),
                        Text("💎 ${diamondBalance.toStringAsFixed(2)} Diamonds",
                            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 22)),
                        const SizedBox(height: 6),
                        Text("Country: $country • $minText"),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),
                const Text("Bank Details (Phase 1)", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
                const SizedBox(height: 10),

                _field(accountNameCtrl, "Account Holder Name", hint: "Your name"),
                _field(bankNameCtrl, "Bank Name", hint: "HDFC / Barclays"),
                _field(accountNumberCtrl, "Account Number", type: TextInputType.number),

                _field(
                  ifscOrSortCtrl,
                  country == "UK" ? "Sort Code" : "IFSC Code",
                  hint: country == "UK" ? "12-34-56" : "HDFC0001234",
                ),

                _field(upiCtrl, "UPI ID (optional)", hint: "name@upi", type: TextInputType.emailAddress),

                ElevatedButton.icon(
                  onPressed: saving ? null : saveBankDetails,
                  icon: const Icon(Icons.save),
                  label: Text(saving ? "Saving..." : "Save Bank Details"),
                ),

                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text("Withdraw Request", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                        const SizedBox(height: 8),
                        const Text(
                          "Phase 1: This will only submit a request.\n"
                          "Phase 2: We will add deduction, commission, review + payouts.",
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: saving ? null : requestWithdraw,
                          child: Text(saving ? "Please wait..." : "Request Withdraw"),
                        ),
                      ],
                    ),
                  ),
                ),

                if (status != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    status!,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: status!.toLowerCase().contains("fail") ? Colors.red : null,
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}
