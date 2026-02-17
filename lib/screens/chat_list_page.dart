import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'chat_room_page.dart';
import 'users_page.dart';
import '../widgets/heart_avatar.dart';

class ChatListPage extends StatelessWidget {
  const ChatListPage({super.key});

  String _otherIdFromParticipants(List participants, String myId) {
    for (final p in participants) {
      final id = p.toString();
      if (id != myId) return id;
    }
    return '';
  }

  String _chatIdFor(String a, String b) {
    final ids = [a, b]..sort();
    return "${ids[0]}_${ids[1]}";
  }

  @override
  Widget build(BuildContext context) {
    final me = FirebaseAuth.instance.currentUser;
    if (me == null) return const Center(child: Text("Not logged in"));

    final chatsQuery = FirebaseFirestore.instance
        .collection('chats')
        .where('participants', arrayContains: me.uid)
        .orderBy('updatedAt', descending: true);

    return Scaffold(
      appBar: AppBar(
        title: const Text("Chats"),
        actions: [
          IconButton(
            tooltip: "New chat",
            icon: const Icon(Icons.add),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const UsersPage()),
              );
            },
          )
        ],
      ),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: chatsQuery.snapshots(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Error: ${snapshot.error}"));
          }

          final docs = snapshot.data?.docs ?? [];
          if (docs.isEmpty) {
            return const Center(child: Text("No chats yet. Tap + to start."));
          }

          return ListView.separated(
            itemCount: docs.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final doc = docs[index];
              final data = doc.data();

              final participants = (data['participants'] ?? []) as List;
              final otherId = _otherIdFromParticipants(participants, me.uid);

              final lastMessage = (data['lastMessage'] ?? '').toString();
              final updatedAt = data['updatedAt'];

              String timeText = '';
              if (updatedAt is Timestamp) {
                final dt = updatedAt.toDate();
                timeText =
                    "${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}";
              }

              return FutureBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                future: FirebaseFirestore.instance
                    .collection('users')
                    .doc(otherId)
                    .get(),
                builder: (context, userSnap) {
                  final userData = userSnap.data?.data();

                  final rawName =
                      (userData?['displayName'] ?? '').toString().trim();
                  final otherName = rawName.isEmpty ? 'User' : rawName;

                  final photoUrl = (() {
                    final urls = (userData?['photoUrls'] ?? []) as List;
                    if (urls.isNotEmpty) return urls.first.toString();
                    return null;
                  })();

                  return ListTile(
                    leading: HeartAvatar(
                      imageUrl: photoUrl,
                      size: 46,
                    ),
                    title: Text(otherName),
                    subtitle: lastMessage.isEmpty
                        ? const Text("...")
                        : Text(
                            lastMessage,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                    trailing: timeText.isEmpty ? null : Text(timeText),
                    onTap: () {
                      final chatId = doc.id.isNotEmpty
                          ? doc.id
                          : _chatIdFor(me.uid, otherId);

                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ChatRoomPage(
                            chatId: chatId,
                            otherUserId: otherId,
                            otherUserName: otherName,
                          ),
                        ),
                      );
                    },
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
