import 'package:cloud_firestore/cloud_firestore.dart';

class TypingService {
  const TypingService({
    required this.roomReference,
    required this.currentUid,
  });

  final DocumentReference<Map<String, dynamic>> roomReference;
  final String currentUid;

  Future<void> setTyping(bool isTyping) {
    return roomReference.set(
      <String, dynamic>{
        'typing.$currentUid': isTyping,
      },
      SetOptions(merge: true),
    );
  }

  Future<void> clearTyping() => setTyping(false);
}
