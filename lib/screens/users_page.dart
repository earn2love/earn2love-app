import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'chat_room_page.dart';
import '../widgets/heart_avatar.dart';

class UsersPage extends StatelessWidget {
  const UsersPage({super.key});

  String _roomIdFor(String a, String b) {
    final ids = [a, b]..sort();
    return "${ids[0]}_${ids[1]}";
  }

  String _todayKey() {
    final now = DateTime.now();
    final y = now.year.toString().padLeft(4, '0');
    final m = now.month.toString().padLeft(2, '0');
    final d = now.day.toString().padLeft(2, '0');
    return "$y$m$d";
  }

  bool _allowedRequest(String fromTier, String toTier) {
    if (fromTier == "love") return true;
    if (fromTier == "friendship") {
      return toTier == "casual" || toTier == "friendship";
    }
    if (fromTier == "casual") return toTier == "casual";
    return false;
  }

  Future<bool> _checkAndIncDailyLimit({
    required String uid,
    required String tier,
  }) async {
    if (tier != "casual") return true;

    final day = _todayKey();
    final ref = FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('limits')
        .doc(day);

    return FirebaseFirestore.instance.runTransaction((tx) async {
      final snap = await tx.get(ref);
      final data = snap.data() ?? {};
      final count = (data['requestsSent'] is num)
          ? (data['requestsSent'] as num).toInt()
          : 0;

      if (count >= 100) return false;

      if (!snap.exists) {
        tx.set(ref, {
          'requestsSent': 1,
          'dateId': day,
          'createdAt': FieldValue.serverTimestamp(),
          'updatedAt': FieldValue.serverTimestamp(),
        });
      } else {
        tx.update(ref, {
          'requestsSent': count + 1,
          'updatedAt': FieldValue.serverTimestamp(),
        });
      }
      return true;
    });
  }

  Future<QueryDocumentSnapshot<Map<String, dynamic>>?> _latestRequestBetween(
    String me,
    String other,
  ) async {
    final col = FirebaseFirestore.instance.collection('requests');

    final outSnap = await col
        .where('fromUid', isEqualTo: me)
        .where('toUid', isEqualTo: other)
        .orderBy('createdAt', descending: true)
        .limit(1)
        .get();

    final inSnap = await col
        .where('fromUid', isEqualTo: other)
        .where('toUid', isEqualTo: me)
        .orderBy('createdAt', descending: true)
        .limit(1)
        .get();

    final outDoc = outSnap.docs.isNotEmpty ? outSnap.docs.first : null;
    final inDoc = inSnap.docs.isNotEmpty ? inSnap.docs.first : null;

    if (outDoc == null) return inDoc;
    if (inDoc == null) return outDoc;

    final outTs = outDoc.data()['createdAt'] as Timestamp?;
    final inTs = inDoc.data()['createdAt'] as Timestamp?;

    if (outTs == null && inTs == null) return outDoc;
    if (outTs == null) return inDoc;
    if (inTs == null) return outDoc;

    return (outTs.compareTo(inTs) >= 0) ? outDoc : inDoc;
  }

  Future<void> _sendRequestDialog({
    required BuildContext context,
    required String myUid,
    required String otherUid,
    required String myTier,
    required String otherTier,
    required String otherName,
  }) async {
    final allowed = await _checkAndIncDailyLimit(uid: myUid, tier: myTier);
    if (!allowed) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content:
                  Text("Casual users can send only 100 requests per day.")),
        );
      }
      return;
    }

    if (!context.mounted) return;

    final msgCtrl = TextEditingController();

    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("Send request to $otherName"),
        content: TextField(
          controller: msgCtrl,
          maxLines: 3,
          maxLength: 300,
          decoration: const InputDecoration(
            hintText: "Write one message (max 300 chars)",
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text("Send"),
          ),
        ],
      ),
    );

    if (ok != true) return;

    final text = msgCtrl.text.trim();
    if (text.isEmpty) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Message cannot be empty.")),
        );
      }
      return;
    }

    await FirebaseFirestore.instance.collection('requests').add({
      'fromUid': myUid,
      'toUid': otherUid,
      'fromTier': myTier,
      'toTier': otherTier,
      'status': 'pending',
      'firstMessage': text,
      'createdAt': FieldValue.serverTimestamp(),
    });

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Request sent ✅")),
      );
    }
  }

  Future<void> _acceptRejectDialog({
    required BuildContext context,
    required QueryDocumentSnapshot<Map<String, dynamic>> reqDoc,
    required String myUid,
    required String otherUid,
    required String otherName,
  }) async {
    final data = reqDoc.data();
    final firstMessage = (data['firstMessage'] ?? '').toString();

    final action = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text("Request from $otherName"),
        content: Text(firstMessage.isEmpty ? "No message" : firstMessage),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, "reject"),
            child: const Text("Reject"),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, "accept"),
            child: const Text("Accept"),
          ),
        ],
      ),
    );

    if (action != "accept" && action != "reject") return;

    await FirebaseFirestore.instance
        .collection('requests')
        .doc(reqDoc.id)
        .update({
      'status': action == "accept" ? 'accepted' : 'rejected',
      'respondedAt': FieldValue.serverTimestamp(),
    });

    if (action == "accept") {
      final roomId = _roomIdFor(myUid, otherUid);
      final roomRef =
          FirebaseFirestore.instance.collection('chatRooms').doc(roomId);

      final snap = await roomRef.get();
      if (!snap.exists) {
        await roomRef.set({
          'participants': [myUid, otherUid]..sort(),
          'requestId': reqDoc.id,
          'lastMessage': '',
          'lastMessageAt': null,
          'updatedAt': FieldValue.serverTimestamp(),
          'createdAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      }

      if (context.mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ChatRoomPage(
              roomId: roomId,
              otherUid: otherUid,
            ),
          ),
        );
      }
    } else {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Request rejected.")),
        );
      }
    }
  }

  Future<void> _openChat({
    required BuildContext context,
    required String myUid,
    required String otherUid,
  }) async {
    final roomId = _roomIdFor(myUid, otherUid);
    final roomRef =
        FirebaseFirestore.instance.collection('chatRooms').doc(roomId);

    final snap = await roomRef.get();
    if (!snap.exists) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content:
                  Text("Chat not available yet. Send/accept request first.")),
        );
      }
      return;
    }

    if (context.mounted) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ChatRoomPage(roomId: roomId, otherUid: otherUid),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = FirebaseAuth.instance.currentUser;
    if (me == null) {
      return const Scaffold(body: Center(child: Text("Not logged in")));
    }

    final usersCol = FirebaseFirestore.instance.collection('users');

    return Scaffold(
      appBar: AppBar(title: const Text("Users")),
      body: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: usersCol.doc(me.uid).snapshots(),
        builder: (context, mySnap) {
          if (!mySnap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }

          final myData = mySnap.data!.data() ?? {};
          final myTier =
              (myData['tier'] ?? myData['subTier'] ?? 'casual').toString();

          return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: usersCol.snapshots(),
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError) {
                return Center(child: Text("Error: ${snap.error}"));
              }

              final docs = snap.data?.docs ?? [];
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

                  final otherUid = doc.id;
                  final rawName = (data['displayName'] ?? '').toString().trim();
                  final otherName = rawName.isEmpty ? 'User' : rawName;
                  final bio = (data['bio'] ?? '').toString();
                  final otherTier =
                      (data['tier'] ?? data['subTier'] ?? 'casual').toString();

                  final photoUrl =
                      (data['photoUrl'] ?? data['profilePhoto'] ?? '')
                          .toString();

                  final canRequest = _allowedRequest(myTier, otherTier);

                  return FutureBuilder<
                      QueryDocumentSnapshot<Map<String, dynamic>>?>(
                    future: _latestRequestBetween(me.uid, otherUid),
                    builder: (context, reqSnap) {
                      final req = reqSnap.data;
                      final reqData = req?.data();

                      final status = reqData?['status']?.toString();
                      final fromUid = reqData?['fromUid']?.toString();
                      final toUid = reqData?['toUid']?.toString();

                      final isIncomingPending = status == 'pending' &&
                          toUid == me.uid &&
                          fromUid == otherUid;
                      final isOutgoingPending = status == 'pending' &&
                          fromUid == me.uid &&
                          toUid == otherUid;

                      Widget trailing;
                      if (!canRequest &&
                          !(isIncomingPending || status == 'accepted')) {
                        trailing = const Text("Not allowed");
                      } else if (isIncomingPending) {
                        trailing = const Chip(label: Text("Accept?"));
                      } else if (isOutgoingPending) {
                        trailing = const Chip(label: Text("Pending"));
                      } else if (status == 'accepted') {
                        trailing = const Icon(Icons.chat_bubble_outline);
                      } else {
                        trailing = const Icon(Icons.chevron_right);
                      }

                      return ListTile(
                        leading: HeartAvatar(
                            imageUrl: photoUrl.isEmpty ? null : photoUrl,
                            size: 46),
                        title: Text(otherName),
                        subtitle: bio.isEmpty
                            ? Text("Tier: $otherTier")
                            : Text(
                                "$bio  •  Tier: $otherTier",
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                        trailing: trailing,
                        onTap: () async {
                          if (isIncomingPending && req != null) {
                            await _acceptRejectDialog(
                              context: context,
                              reqDoc: req,
                              myUid: me.uid,
                              otherUid: otherUid,
                              otherName: otherName,
                            );
                            return;
                          }

                          if (status == 'accepted') {
                            await _openChat(
                              context: context,
                              myUid: me.uid,
                              otherUid: otherUid,
                            );
                            return;
                          }

                          if (isOutgoingPending) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                  content: Text("Request already pending.")),
                            );
                            return;
                          }

                          if (!canRequest) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                    "Your tier ($myTier) cannot request $otherTier users."),
                              ),
                            );
                            return;
                          }

                          await _sendRequestDialog(
                            context: context,
                            myUid: me.uid,
                            otherUid: otherUid,
                            myTier: myTier,
                            otherTier: otherTier,
                            otherName: otherName,
                          );
                        },
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
