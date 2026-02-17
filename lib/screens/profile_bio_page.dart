import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ProfileBioPage extends StatefulWidget {
  const ProfileBioPage({super.key});

  @override
  State<ProfileBioPage> createState() => _ProfileBioPageState();
}

class _ProfileBioPageState extends State<ProfileBioPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  final bioCtrl = TextEditingController();
  final interestsCtrl = TextEditingController();

  bool loading = true;
  bool saving = false;
  String? status;

  List<String> interests = [];

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

      bioCtrl.text = (d['bio'] ?? '').toString();

      final list = d['interests'];
      if (list is List) {
        interests = list.map((e) => e.toString()).toList();
      }
    } catch (e) {
      status = "Load failed: $e";
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void addInterest() {
    final text = interestsCtrl.text.trim();
    if (text.isEmpty) return;

    final parts = text.split(",");
    for (final p in parts) {
      final item = p.trim();
      if (item.isNotEmpty && !interests.contains(item)) {
        interests.add(item);
      }
    }

    interestsCtrl.clear();
    setState(() {});
  }

  void removeInterest(String value) {
    interests.remove(value);
    setState(() {});
  }

  Future<void> save() async {
    setState(() {
      saving = true;
      status = null;
    });

    try {
      await userRef.set({
        'bio': bioCtrl.text.trim(),
        'interests': interests,
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
    bioCtrl.dispose();
    interestsCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Bio"),
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
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Your Bio",
                            style: TextStyle(fontWeight: FontWeight.w900)),
                        SizedBox(height: 6),
                        Text(
                            "Write something attractive. Keep it simple and honest."),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: bioCtrl,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: "Bio",
                    border: OutlineInputBorder(),
                    hintText: "Tell about yourself...",
                  ),
                ),
                const SizedBox(height: 16),
                const Text("Interests",
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: interestsCtrl,
                        decoration: const InputDecoration(
                          labelText: "Add interests",
                          hintText: "music, travel, gym",
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: addInterest,
                      child: const Text("Add"),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (interests.isEmpty)
                  const Text("No interests added yet.")
                else
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: interests.map((i) {
                      return Chip(
                        label: Text(i),
                        deleteIcon: const Icon(Icons.close),
                        onDeleted: () => removeInterest(i),
                      );
                    }).toList(),
                  ),
                if (status != null) ...[
                  const SizedBox(height: 14),
                  Text(
                    status!,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: status!.toLowerCase().contains("fail")
                          ? Colors.red
                          : null,
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}
