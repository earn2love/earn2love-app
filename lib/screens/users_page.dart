import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'chat_room_page.dart';
import '../widgets/heart_avatar.dart';

class UsersPage extends StatelessWidget {
  const UsersPage({super.key});

  String _chatIdFor(String a, String b) {
    final ids = [a, b]..sort();
    return "${ids[0]}_${ids[1]}";
  }

  @override
  Widget build(BuildContext context) {
    final me = FirebaseAuth.instance.currentUser;
    if (me == null) {
      return const Center(child: Text("Not logged in"));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("Users"),
      ),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: FirebaseFirestore.instance.collection('users').snapshots(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Error: ${snapshot.error}"));
          }

          final docs = snapshot.data?.docs ?? [];
          final otherUsers = docs.where((d) => d.id != me.uid).toList();

          if (otherUsers.isEmpty) {
            return const Center(child: Text("No other users yet."));
          }

          return ListView.separated(
            itemCount: otherUsers.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final doc = otherUsers[index];
              final data = doc.data();

              final uid = doc.id;

              final rawName = (data['displayName'] ?? '').toString().trim();
              final showName = rawName.isEmpty ? 'User' : rawName;

              final bio = (data['bio'] ?? '').toString();

              final photoUrl = (() {
                final urls = (data['photoUrls'] ?? []) as List;
                if (urls.isNotEmpty) return urls.first.toString();
                return null;
              })();

              return ListTile(
                leading: HeartAvatar(
                  imageUrl: photoUrl,
                  size: 46,
                ),
                title: Text(showName),
                subtitle: bio.isEmpty
                    ? null
                    : Text(
                        bio,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  final chatId = _chatIdFor(me.uid, uid);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ChatRoomPage(
                        chatId: chatId,
                        otherUserId: uid,
                        otherUserName: showName,
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
