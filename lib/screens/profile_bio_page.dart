import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ProfileBioPage extends StatefulWidget {
  const ProfileBioPage({super.key});

  @override
  State<ProfileBioPage> createState() => _ProfileBioPageState();
}

class _ProfileBioPageState extends State<ProfileBioPage> {
  User? get currentUser => FirebaseAuth.instance.currentUser;

  DocumentReference<Map<String, dynamic>>? get userRef {
    final u = currentUser;
    if (u == null) return null;
    return FirebaseFirestore.instance.collection('users').doc(u.uid);
  }

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
    if (!mounted) return;

    setState(() {
      loading = true;
      status = null;
      interests = [];
    });

    try {
      final ref = userRef;
      if (ref == null) {
        if (!mounted) return;
        setState(() {
          loading = false;
          status = "User not logged in";
        });
        return;
      }

      final snap = await ref.get();
      final d = snap.data() ?? {};

      final bio = (d['bio'] ?? '').toString();

      final rawInterests = d['interests'];
      List<String> loadedInterests = [];

      if (rawInterests is List) {
        loadedInterests = rawInterests
            .map((e) => e.toString().trim())
            .where((e) => e.isNotEmpty)
            .toList();
      } else if (rawInterests is String) {
        loadedInterests = rawInterests
            .split(',')
            .map((e) => e.trim())
            .where((e) => e.isNotEmpty)
            .toList();
      }

      if (!mounted) return;
      setState(() {
        bioCtrl.text = bio;
        interests = loadedInterests;
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        loading = false;
        status = "Load failed: $e";
      });
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
    if (userRef == null) {
      setState(() {
        status = "User not logged in";
      });
      return;
    }

    setState(() {
      saving = true;
      status = null;
    });

    try {
      await userRef!.set({
        'bio': bioCtrl.text.trim(),
        'interests': interests,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (!mounted) return;
      setState(() {
        saving = false;
        status = "Saved ✅";
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        saving = false;
        status = "Save failed: $e";
      });
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
    final isLoggedIn = currentUser != null;

    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        title: const Text("Bio"),
        actions: [
          TextButton(
            onPressed: (!isLoggedIn || saving) ? null : save,
            child: Text(
              saving ? "Saving..." : "Save",
              style: const TextStyle(fontWeight: FontWeight.w900),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: loading
            ? const Center(child: CircularProgressIndicator())
            : !isLoggedIn
                ? const Center(
                    child: Text(
                      "User not logged in",
                      style: TextStyle(fontWeight: FontWeight.w800),
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      Card(
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: const Padding(
                          padding: EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "Your Bio",
                                style: TextStyle(fontWeight: FontWeight.w900),
                              ),
                              SizedBox(height: 6),
                              Text(
                                "Write something attractive. Keep it simple and honest.",
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: bioCtrl,
                        maxLines: 5,
                        decoration: InputDecoration(
                          labelText: "Bio",
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          hintText: "Tell about yourself...",
                          filled: true,
                          fillColor: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        "Interests",
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: interestsCtrl,
                              onSubmitted: (_) => addInterest(),
                              decoration: InputDecoration(
                                labelText: "Add interests",
                                hintText: "music, travel, gym",
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                filled: true,
                                fillColor: Colors.white,
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
                        Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: Colors.grey.shade200),
                          ),
                          child: const Text(
                            "No interests added yet.",
                            style: TextStyle(fontWeight: FontWeight.w700),
                          ),
                        )
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
                            color: status!.toLowerCase().contains("fail") ||
                                    status!.toLowerCase().contains("not logged")
                                ? Colors.red
                                : Colors.green,
                          ),
                        ),
                      ],
                    ],
                  ),
      ),
    );
  }
}