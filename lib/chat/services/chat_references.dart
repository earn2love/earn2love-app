import 'package:cloud_firestore/cloud_firestore.dart';

class ChatReferences {
  ChatReferences({
    required this.firestore,
    required this.currentUid,
    required this.otherUid,
    required this.roomId,
  });

  final FirebaseFirestore firestore;
  final String currentUid;
  final String otherUid;
  final String roomId;

  DocumentReference<Map<String, dynamic>> get currentUser =>
      firestore.collection('users').doc(currentUid);

  DocumentReference<Map<String, dynamic>> get otherUser =>
      firestore.collection('users').doc(otherUid);

  DocumentReference<Map<String, dynamic>> get room =>
      firestore.collection('chatRooms').doc(roomId);

  CollectionReference<Map<String, dynamic>> get messages =>
      room.collection('messages');

  CollectionReference<Map<String, dynamic>> get requests =>
      room.collection('requests');

  DocumentReference<Map<String, dynamic>> get chatPreferences =>
      currentUser.collection('chatPrefs').doc(roomId);

  DocumentReference<Map<String, dynamic>> get blockedUser =>
      currentUser.collection('blockedUsers').doc(otherUid);

  DocumentReference<Map<String, dynamic>> get friendRequest =>
      firestore.collection('friendRequests').doc(pairId(currentUid, otherUid));

  static String pairId(String firstUid, String secondUid) {
    final ids = <String>[firstUid, secondUid]..sort();
    return '${ids[0]}__${ids[1]}';
  }
}
