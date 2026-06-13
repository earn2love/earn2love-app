import 'dart:io';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class UploadPhotoPage extends StatefulWidget {
  const UploadPhotoPage({super.key});

  @override
  State<UploadPhotoPage> createState() => _UploadPhotoPageState();
}

class _UploadPhotoPageState extends State<UploadPhotoPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  bool busy = false;
  String info = '';
  File? file;

  Future<void> pick() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (x == null) return;
    setState(() {
      file = File(x.path);
      info = '';
    });
  }

  Future<void> upload() async {
    if (file == null) {
      setState(() => info = "Pick a photo first");
      return;
    }

    setState(() {
      busy = true;
      info = '';
    });

    try {
      final id = FirebaseFirestore.instance.collection('tmp').doc().id;
      final path = "users/$uid/media/photos/$id.jpg";
      final ref = FirebaseStorage.instance.ref().child(path);

      await ref.putFile(file!);
      final url = await ref.getDownloadURL();

      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('media')
          .doc(id)
          .set({
        'type': 'photo',
        'url': url,
        'flagged': false,
        'createdAt': FieldValue.serverTimestamp(),
        'ownerUid': uid,
      });

      if (!mounted) return;
      setState(() => info = "Uploaded ✅");
      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      setState(() => info = "Upload failed: $e");
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isFail = info.toLowerCase().contains("fail");

    return Scaffold(
      appBar: AppBar(title: const Text("Upload Photo")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            height: 220,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              color: Colors.grey.shade200,
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(18),
              child: file == null
                  ? Center(
                      child: Text(
                        "No photo selected",
                        style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.w800),
                      ),
                    )
                  : Image.file(file!, fit: BoxFit.cover),
            ),
          ),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            onPressed: busy ? null : pick,
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text("Pick Photo"),
          ),
          const SizedBox(height: 10),
          ElevatedButton.icon(
            onPressed: busy ? null : upload,
            icon: const Icon(Icons.cloud_upload_outlined),
            label: Text(busy ? "Uploading..." : "Upload"),
          ),
          if (info.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: isFail ? Colors.red.shade50 : Colors.green.shade50,
                border: Border.all(color: isFail ? Colors.red.shade200 : Colors.green.shade200),
              ),
              child: Text(
                info,
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w900, color: isFail ? Colors.red : Colors.green.shade800),
              ),
            ),
          ],
          const SizedBox(height: 18),
          Text(
            "Note: Later we will add nudity detection and auto-flagging.\nFlagged media will show warning before opening.",
            style: TextStyle(color: Colors.grey.shade700, fontSize: 12, height: 1.35),
          ),
        ],
      ),
    );
  }
}