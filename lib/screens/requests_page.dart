import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'chat_room_page.dart';
import 'user_profile_page.dart';

class RequestsPage extends StatelessWidget {
  const RequestsPage({super.key});

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  /// Stable doc id for friend requests (same either direction)
  String requestDocId(String a, String b) {
    final ids = [a, b]..sort();
    return "${ids[0]}__${ids[1]}";
  }

  Future<void> _acceptRequest({
    required BuildContext context,
    required String fromUid,
  }) async {
    if (fromUid.isEmpty || fromUid == uid) return;

    final docId = requestDocId(uid, fromUid);

    // mark accepted
    await FirebaseFirestore.instance
        .collection('friendRequests')
        .doc(docId)
        .set({
      'fromUid': fromUid,
      'toUid': uid,
      'status': 'accepted',
      'acceptedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    // ensure chat room exists
    final rooms = FirebaseFirestore.instance.collection('chatRooms');

    // find existing 1-1 room
    final q =
        await rooms.where('participants', arrayContains: uid).limit(50).get();
    String? roomId;
    for (final d in q.docs) {
      final p = (d.data()['participants'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          [];
      if (p.contains(fromUid) && p.length == 2) {
        roomId = d.id;
        break;
      }
    }

    roomId ??= rooms.doc().id;
    await rooms.doc(roomId).set({
      'participants': [uid, fromUid],
      'updatedAt': FieldValue.serverTimestamp(),
      'lastMessage': '',
      'lastMessageAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!context.mounted) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatRoomPage(roomId: roomId!, otherUid: fromUid),
      ),
    );
  }

  Future<void> _rejectRequest({
    required String fromUid,
  }) async {
    if (fromUid.isEmpty || fromUid == uid) return;

    final docId = requestDocId(uid, fromUid);

    await FirebaseFirestore.instance
        .collection('friendRequests')
        .doc(docId)
        .set({
      'fromUid': fromUid,
      'toUid': uid,
      'status': 'rejected',
      'rejectedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _incomingRequests() {
    return FirebaseFirestore.instance
        .collection('friendRequests')
        .where('toUid', isEqualTo: uid)
        .where('status', isEqualTo: 'pending')
        .orderBy('createdAt', descending: true)
        .limit(200)
        .snapshots();
  }

  @override
  Widget build(BuildContext context) {
    final me = FirebaseAuth.instance.currentUser;
    if (me == null)
      return const Scaffold(body: Center(child: Text("Not logged in")));

    return Scaffold(
      appBar: AppBar(title: const Text("Requests")),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: _incomingRequests(),
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) return Center(child: Text("Error: ${snap.error}"));

          final docs = snap.data?.docs ?? [];
          if (docs.isEmpty) {
            return const Center(child: Text("No requests yet."));
          }

          return ListView.separated(
            itemCount: docs.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final reqDoc = docs[i];
              final data = reqDoc.data();
              final fromUid = (data['fromUid'] ?? '').toString();

              return FutureBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                future: FirebaseFirestore.instance
                    .collection('users')
                    .doc(fromUid)
                    .get(),
                builder: (context, userSnap) {
                  final u = userSnap.data?.data() ?? {};
                  final name = (u['displayName'] ?? 'User').toString();
                  final photo =
                      (u['photoUrl'] ?? u['profilePhoto'] ?? '').toString();
                  final tier =
                      (u['tier'] ?? u['subTier'] ?? 'casual').toString();

                  return ListTile(
                    leading: CircleAvatar(
                      backgroundImage:
                          photo.isEmpty ? null : NetworkImage(photo),
                      child: photo.isEmpty ? const Icon(Icons.person) : null,
                    ),
                    title: Text(name,
                        style: const TextStyle(fontWeight: FontWeight.w900)),
                    subtitle: Text("Plan: ${tier.toUpperCase()}"),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => UserProfilePage(userId: fromUid)),
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          tooltip: "Reject",
                          icon: const Icon(Icons.close, color: Colors.red),
                          onPressed: () => _rejectRequest(fromUid: fromUid),
                        ),
                        IconButton(
                          tooltip: "Accept",
                          icon: const Icon(Icons.check, color: Colors.green),
                          onPressed: () => _acceptRequest(
                              context: context, fromUid: fromUid),
                        ),
                      ],
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
