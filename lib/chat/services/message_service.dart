import 'package:cloud_firestore/cloud_firestore.dart';

class MessageService {
  const MessageService({
    required this.firestore,
    required this.currentUid,
    required this.otherUid,
    required this.currentUserReference,
    required this.otherUserReference,
    required this.roomReference,
    required this.messagesReference,
  });

  final FirebaseFirestore firestore;
  final String currentUid;
  final String otherUid;

  final DocumentReference<Map<String, dynamic>> currentUserReference;
  final DocumentReference<Map<String, dynamic>> otherUserReference;
  final DocumentReference<Map<String, dynamic>> roomReference;
  final CollectionReference<Map<String, dynamic>> messagesReference;

  Future<void> sendMessage({
    required String type,
    required String text,
    String? imageUrl,
    String? audioUrl,
    int? audioDurationSec,
    Map<String, dynamic>? replyTo,
  }) async {
    final timestamp = FieldValue.serverTimestamp();

    var otherUserOnline = false;

    try {
      final otherSnapshot = await otherUserReference.get();
      otherUserOnline = (otherSnapshot.data()?['online'] ?? false) == true;
    } catch (_) {
      otherUserOnline = false;
    }

    final initialDeliveredTo =
        otherUserOnline ? <String>[otherUid] : <String>[];

    await messagesReference.add(<String, dynamic>{
      'senderId': currentUid,
      'text': text,
      'type': type,
      'imageUrl': imageUrl ?? '',
      'audioUrl': audioUrl ?? '',
      'audioDurationSec': audioDurationSec ?? 0,
      'replyTo': replyTo,
      'createdAt': timestamp,
      'deletedFor': <String>[],
      'deletedForEveryone': false,
      'deliveredTo': initialDeliveredTo,
      'seenBy': <String>[],
      'reactions': <String, dynamic>{},
    });

    final lastMessage = switch (type) {
      'image' => '📷 Photo',
      'voice' => '🎤 Voice message',
      'call_log' => text,
      _ => text,
    };

    await roomReference.set(
      <String, dynamic>{
        'lastMessage': lastMessage,
        'lastMessageAt': timestamp,
        'updatedAt': timestamp,
        'lastMessageSenderId': currentUid,
        'lastMessageType': type,
        'lastMessageDeliveredTo': initialDeliveredTo,
        'lastMessageSeenBy': <String>[],
        'unread.$otherUid': FieldValue.increment(1),
        'unread.$currentUid': 0,
      },
      SetOptions(merge: true),
    );

    await currentUserReference.set(
      <String, dynamic>{
        'counters.unreadChats': 0,
        'updatedAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );
  }

  Future<void> markSeenAndDelivered(
    List<QueryDocumentSnapshot<Map<String, dynamic>>> documents,
  ) async {
    final batch = firestore.batch();
    var changed = false;

    for (final document in documents) {
      final message = document.data();
      final senderId = (message['senderId'] ?? '').toString().trim();

      if (senderId == currentUid) continue;

      final deliveredTo = (message['deliveredTo'] as List?)
              ?.map((value) => value.toString())
              .toList() ??
          <String>[];

      final seenBy = (message['seenBy'] as List?)
              ?.map((value) => value.toString())
              .toList() ??
          <String>[];

      final updates = <String, dynamic>{};

      if (!deliveredTo.contains(currentUid)) {
        updates['deliveredTo'] = FieldValue.arrayUnion(<String>[currentUid]);
      }

      if (!seenBy.contains(currentUid)) {
        updates['seenBy'] = FieldValue.arrayUnion(<String>[currentUid]);
      }

      if (updates.isNotEmpty) {
        batch.set(
          document.reference,
          updates,
          SetOptions(merge: true),
        );
        changed = true;
      }
    }

    if (changed) {
      await batch.commit();
    }

    await roomReference.set(
      <String, dynamic>{
        'lastMessageDeliveredTo': FieldValue.arrayUnion(<String>[currentUid]),
        'lastMessageSeenBy': FieldValue.arrayUnion(<String>[currentUid]),
        'unread.$currentUid': 0,
        'updatedAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );

    await currentUserReference.set(
      <String, dynamic>{
        'counters.unreadChats': 0,
        'updatedAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );
  }

  Future<void> deleteForCurrentUser(String messageId) {
    return messagesReference.doc(messageId).set(
      <String, dynamic>{
        'deletedFor': FieldValue.arrayUnion(<String>[currentUid]),
      },
      SetOptions(merge: true),
    );
  }

  Future<void> deleteForEveryone(String messageId) {
    return messagesReference.doc(messageId).set(
      <String, dynamic>{
        'deletedForEveryone': true,
        'deletedAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );
  }

  Future<void> setReaction({
    required String messageId,
    required String emoji,
  }) {
    return messagesReference.doc(messageId).set(
      <String, dynamic>{
        'reactions.$currentUid': emoji,
      },
      SetOptions(merge: true),
    );
  }

  Future<void> removeReaction(String messageId) {
    return messagesReference.doc(messageId).set(
      <String, dynamic>{
        'reactions.$currentUid': FieldValue.delete(),
      },
      SetOptions(merge: true),
    );
  }
}
