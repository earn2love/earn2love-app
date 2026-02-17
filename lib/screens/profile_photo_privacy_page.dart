import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ProfilePhotoPrivacyPage extends StatefulWidget {
  const ProfilePhotoPrivacyPage({super.key});

  @override
  State<ProfilePhotoPrivacyPage> createState() => _ProfilePhotoPrivacyPageState();
}

class _ProfilePhotoPrivacyPageState extends State<ProfilePhotoPrivacyPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  bool loading = true;
  bool saving = false;
  bool isPublic = true;
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
      final v = d['profilePhotoPublic'];
      if (v is bool) isPublic = v;
    } catch (e) {
      status = "Load failed: $e";
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> save(bool value) async {
    setState(() {
      saving = true;
      status = null;
    });

    try {
      await userRef.set({
        'profilePhotoPublic': value,
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
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Profile Photo Privacy")),
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
                        Text("Privacy Control", style: TextStyle(fontWeight: FontWeight.w900)),
                        SizedBox(height: 6),
                        Text(
                          "Public: anyone can see your profile photo.\n"
                          "Private: only after request accepted (we will enforce later).",
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                Card(
                  child: SwitchListTile(
                    title: const Text("Make profile photo public", style: TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text(isPublic ? "Public ✅" : "Private 🔒"),
                    value: isPublic,
                    onChanged: saving
                        ? null
                        : (v) async {
                            setState(() => isPublic = v);
                            await save(v);
                          },
                  ),
                ),

                const SizedBox(height: 12),

                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("Current setting", style: TextStyle(fontWeight: FontWeight.w900)),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(isPublic ? Icons.public : Icons.lock, color: isPublic ? Colors.green : Colors.red),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                isPublic
                                    ? "Your photo is visible to everyone."
                                    : "Your photo is private (will be visible only after acceptance).",
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),

                if (status != null) ...[
                  const SizedBox(height: 14),
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
