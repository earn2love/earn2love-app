import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  final nameCtrl = TextEditingController();
  final bioCtrl = TextEditingController();

  bool loading = true;
  bool saving = false;
  bool uploading = false;

  String photoVisibility = "public"; // public / private (later)
  String? primaryPhotoUrl;

  String? msg;

  String asString(dynamic v, {String def = ""}) => v == null ? def : v.toString();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    nameCtrl.dispose();
    bioCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final snap = await userRef.get();
      final data = snap.data() ?? {};

      nameCtrl.text = asString(data["displayName"]);
      bioCtrl.text = asString(data["bio"]);

      photoVisibility = asString(data["photoVisibility"], def: "public");

      final urls = (data["photoUrls"] is List) ? (data["photoUrls"] as List) : [];
      primaryPhotoUrl = urls.isNotEmpty ? urls.first.toString() : null;

      setState(() => loading = false);
    } catch (e) {
      setState(() {
        loading = false;
        msg = "Load failed: $e";
      });
    }
  }

  Future<void> _save() async {
    setState(() {
      saving = true;
      msg = null;
    });

    try {
      await userRef.set({
        "displayName": nameCtrl.text.trim(),
        "bio": bioCtrl.text.trim(),
        "photoVisibility": photoVisibility,
        "updatedAt": FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (!mounted) return;
      setState(() => msg = "Saved ✅");
    } catch (e) {
      if (!mounted) return;
      setState(() => msg = "Save failed: $e");
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();

    setState(() {
      uploading = true;
      msg = null;
    });

    try {
      final x = await picker.pickImage(
        source: source,
        imageQuality: 75,
        maxWidth: 1080,
      );

      if (x == null) {
        setState(() => uploading = false);
        return;
      }

      final file = File(x.path);

      // upload
      final path = "users/$uid/profile_${DateTime.now().millisecondsSinceEpoch}.jpg";
      final ref = FirebaseStorage.instance.ref().child(path);

      await ref.putFile(file);
      final url = await ref.getDownloadURL();

      // save url as first photo
      await userRef.set({
        "photoUrls": [url], // Phase-1: only 1 primary photo
        "updatedAt": FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (!mounted) return;
      setState(() {
        primaryPhotoUrl = url;
        msg = "Photo updated ✅";
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => msg = "Upload failed: $e");
    } finally {
      if (mounted) setState(() => uploading = false);
    }
  }

  Future<void> _showPhotoPicker() async {
    await showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (_) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("Update Profile Photo",
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 10),
              ListTile(
                leading: const Icon(Icons.photo_library),
                title: const Text("From Gallery"),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage(ImageSource.gallery);
                },
              ),
              ListTile(
                leading: const Icon(Icons.camera_alt),
                title: const Text("From Camera"),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage(ImageSource.camera);
                },
              ),
              const SizedBox(height: 6),
            ],
          ),
        );
      },
    );
  }

  Widget _header() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 54,
              height: 54,
              decoration: BoxDecoration(
                color: Colors.pink.shade50,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.pink.shade200),
              ),
              child: Icon(Icons.favorite, color: Colors.pink.shade700),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                "My Profile\nPhoto • Name • Bio • Privacy",
                style: TextStyle(color: Colors.grey.shade800, fontWeight: FontWeight.w800),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _photoCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Stack(
              children: [
                CircleAvatar(
                  radius: 34,
                  backgroundColor: Colors.grey.shade200,
                  backgroundImage:
                      (primaryPhotoUrl == null) ? null : NetworkImage(primaryPhotoUrl!),
                  child: primaryPhotoUrl == null
                      ? const Icon(Icons.person, size: 34)
                      : null,
                ),
                if (uploading)
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.25),
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Profile Photo", style: TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text(
                    primaryPhotoUrl == null ? "No photo uploaded" : "Photo is set ✅",
                    style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: uploading ? null : _showPhotoPicker,
                    icon: const Icon(Icons.edit),
                    label: Text(uploading ? "Uploading..." : "Change Photo"),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _privacyCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("Privacy (Phase 1)", style: TextStyle(fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: photoVisibility,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: "Photo Visibility",
              ),
              items: const [
                DropdownMenuItem(value: "public", child: Text("Public")),
                DropdownMenuItem(value: "private", child: Text("Private")),
              ],
              onChanged: saving
                  ? null
                  : (v) => setState(() => photoVisibility = v ?? photoVisibility),
            ),
            const SizedBox(height: 8),
            Text(
              "Later we’ll add advanced privacy: who can see, blur, request access, etc.",
              style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.w600, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _formCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text("Display Name", style: TextStyle(fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: "Enter display name",
              ),
            ),
            const SizedBox(height: 14),
            const Text("Bio", style: TextStyle(fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            TextField(
              controller: bioCtrl,
              maxLines: 4,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: "Write something about you...",
              ),
            ),
            const SizedBox(height: 14),
            ElevatedButton.icon(
              onPressed: saving ? null : _save,
              icon: const Icon(Icons.save),
              label: Text(saving ? "Saving..." : "Save"),
            ),
          ],
        ),
      ),
    );
  }

  Widget _messageBox() {
    if (msg == null) return const SizedBox.shrink();

    final lower = msg!.toLowerCase();
    final isErr = lower.contains("fail") || lower.contains("error");

    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: isErr ? Colors.red.shade50 : Colors.green.shade50,
        border: Border.all(color: isErr ? Colors.red.shade200 : Colors.green.shade200),
      ),
      child: Text(
        msg!,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontWeight: FontWeight.w900,
          color: isErr ? Colors.red : Colors.green.shade800,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text("My Profile")),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          _header(),
          const SizedBox(height: 10),
          _photoCard(),
          const SizedBox(height: 10),
          _formCard(),
          const SizedBox(height: 10),
          _privacyCard(),
          _messageBox(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
