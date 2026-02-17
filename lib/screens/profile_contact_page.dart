import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ProfileContactPage extends StatefulWidget {
  const ProfileContactPage({super.key});

  @override
  State<ProfileContactPage> createState() => _ProfileContactPageState();
}

class _ProfileContactPageState extends State<ProfileContactPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  final phoneCtrl = TextEditingController();
  final emailCtrl = TextEditingController();
  final emergencyNameCtrl = TextEditingController();
  final emergencyPhoneCtrl = TextEditingController();

  bool loading = true;
  bool saving = false;
  String? status;

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

      // Prefer auth values if Firestore empty
      final user = FirebaseAuth.instance.currentUser;

      phoneCtrl.text = (d['contactPhone'] ?? user?.phoneNumber ?? '').toString();
      emailCtrl.text = (d['contactEmail'] ?? user?.email ?? '').toString();

      emergencyNameCtrl.text = (d['emergencyName'] ?? '').toString();
      emergencyPhoneCtrl.text = (d['emergencyPhone'] ?? '').toString();
    } catch (e) {
      status = "Load failed: $e";
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> save() async {
    setState(() {
      saving = true;
      status = null;
    });

    try {
      await userRef.set({
        'contactPhone': phoneCtrl.text.trim(),
        'contactEmail': emailCtrl.text.trim(),
        'emergencyName': emergencyNameCtrl.text.trim(),
        'emergencyPhone': emergencyPhoneCtrl.text.trim(),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      status = "Saved ✅";
    } catch (e) {
      status = "Save failed: $e";
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  void dispose() {
    phoneCtrl.dispose();
    emailCtrl.dispose();
    emergencyNameCtrl.dispose();
    emergencyPhoneCtrl.dispose();
    super.dispose();
  }

  InputDecoration _dec(String label, {String? hint}) => InputDecoration(
        labelText: label,
        hintText: hint,
        border: const OutlineInputBorder(),
      );

  Widget _field(
    TextEditingController c,
    String label, {
    String? hint,
    TextInputType? type,
  }) {
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
    return Scaffold(
      appBar: AppBar(
        title: const Text("Contact Information"),
        actions: [
          TextButton(
            onPressed: saving ? null : save,
            child: Text(
              saving ? "Saving..." : "Save",
              style: const TextStyle(fontWeight: FontWeight.w900),
            ),
          )
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text("Keep contacts updated", style: TextStyle(fontWeight: FontWeight.w900)),
                        SizedBox(height: 6),
                        Text("Emergency contact helps safety & support features."),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                _field(phoneCtrl, "Phone", hint: "+91XXXXXXXXXX / +44XXXX", type: TextInputType.phone),
                _field(emailCtrl, "Email", hint: "example@gmail.com", type: TextInputType.emailAddress),

                const SizedBox(height: 8),
                const Text("Emergency Contact", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
                const SizedBox(height: 10),

                _field(emergencyNameCtrl, "Emergency Contact Name", hint: "Mom / Friend"),
                _field(emergencyPhoneCtrl, "Emergency Contact Phone", hint: "+91... / +44...", type: TextInputType.phone),

                if (status != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    status!,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: status!.toLowerCase().contains("fail") ? Colors.red : null,
                    ),
                  ),
                ],

                const SizedBox(height: 24),
              ],
            ),
    );
  }
}
