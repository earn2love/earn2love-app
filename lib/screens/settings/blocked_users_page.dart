import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class BlockedUsersPage extends StatelessWidget {
  const BlockedUsersPage({super.key});

  static const _bg = Color(0xFF0F1115);
  static const _card = Color(0xFF171A21);
  static const _border = Color(0xFF2A3140);
  static const _muted = Color(0xFF9AA3B2);

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get _blockedRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('blockedUsers');

  Future<void> _unblock(
    BuildContext context,
    String blockedUid,
    String roomId,
  ) async {
    final batch = FirebaseFirestore.instance.batch();

    final blockDoc = _blockedRef.doc(blockedUid);
    batch.delete(blockDoc);

    if (roomId.trim().isNotEmpty) {
      final roomRef =
          FirebaseFirestore.instance.collection('chatRooms').doc(roomId);

      batch.set(
        roomRef,
        {
          'blockedBy.$uid': FieldValue.delete(),
          'updatedAt': FieldValue.serverTimestamp(),
        },
        SetOptions(merge: true),
      );
    }

    await batch.commit();

    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('User unblocked')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        title: const Text('Blocked Users'),
      ),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: _blockedRef.orderBy('createdAt', descending: true).snapshots(),
        builder: (context, snap) {
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }

          final docs = snap.data!.docs;

          if (docs.isEmpty) {
            return const Center(
              child: Text(
                'No blocked users',
                style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w700),
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: docs.length,
            itemBuilder: (context, i) {
              final data = docs[i].data();
              final blockedUid = docs[i].id;
              final roomId = (data['roomId'] ?? '').toString();

              return FutureBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                future: FirebaseFirestore.instance
                    .collection('users')
                    .doc(blockedUid)
                    .get(),
                builder: (context, userSnap) {
                  final user = userSnap.data?.data() ?? {};
                  final name =
                      (user['displayName'] ?? user['name'] ?? 'User').toString();
                  final photo =
                      (user['photoUrl'] ?? user['profilePhoto'] ?? '').toString();

                  return Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: _card,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: _border),
                    ),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundImage:
                            photo.isEmpty ? null : NetworkImage(photo),
                        child: photo.isEmpty ? const Icon(Icons.person) : null,
                      ),
                      title: Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      subtitle: const Text(
                        'Blocked user',
                        style: TextStyle(color: _muted),
                      ),
                      trailing: TextButton(
                        onPressed: () => _unblock(context, blockedUid, roomId),
                        child: const Text('Unblock'),
                      ),
                    ),
                  );
                },
              );
            },
          );
        },
      ),
    );
  }
}