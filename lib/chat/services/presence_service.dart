import 'package:cloud_firestore/cloud_firestore.dart';

class PresenceService {
  const PresenceService({
    required this.userReference,
  });

  final DocumentReference<Map<String, dynamic>> userReference;

  Future<void> setOnline(bool isOnline) {
    return userReference.set(
      <String, dynamic>{
        'online': isOnline,
        'lastSeenAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );
  }
}
