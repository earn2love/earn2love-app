import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class StreakService {
  static String get uid => FirebaseAuth.instance.currentUser!.uid;

  static DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  static DateTime _startOfDay(DateTime now) =>
      DateTime(now.year, now.month, now.day);

  static String _dateKey(DateTime d) =>
      "${d.year.toString().padLeft(4, '0')}-"
      "${d.month.toString().padLeft(2, '0')}-"
      "${d.day.toString().padLeft(2, '0')}";

  static int bonusPctForDays(int days) {
    if (days >= 30) return 10;
    if (days >= 14) return 7;
    if (days >= 7) return 5;
    return 0;
  }

  static Future<bool> checkTodayActivity() async {
    final now = DateTime.now();
    final start = _startOfDay(now);

    final chatsSnap = await FirebaseFirestore.instance
        .collection('chats')
        .where('participants', arrayContains: uid)
        .get();

    final chatIds = chatsSnap.docs.map((d) => d.id).toList();
    if (chatIds.isEmpty) return false;

    int goodChats = 0;

    for (final chatId in chatIds) {
      final msgSnap = await FirebaseFirestore.instance
          .collection('chats')
          .doc(chatId)
          .collection('messages')
          .where('senderId', isEqualTo: uid)
          .where('createdAt',
              isGreaterThanOrEqualTo: Timestamp.fromDate(start))
          .limit(300)
          .get();

      if (msgSnap.docs.length >= 10) {
        goodChats++;
        if (goodChats >= 3) return true;
      }
    }

    return false;
  }

  static Future<Map<String, dynamic>> updateStreakIfEligible() async {
    final snap = await userRef.get();
    final u = snap.data() ?? {};

    final now = DateTime.now();
    final todayKey = _dateKey(now);

    final lastDate = (u['streakLastDate'] ?? '').toString();
    final oldDays = (u['streakDays'] is int) ? u['streakDays'] as int : 0;

    if (lastDate == todayKey) {
      return {
        'ok': true,
        'msg': 'Already checked today ✅',
        'streakDays': oldDays,
        'bonusPct': bonusPctForDays(oldDays),
      };
    }

    final eligible = await checkTodayActivity();

    if (!eligible) {
      await userRef.set({
        'streakDays': 0,
        'streakBonusPct': 0,
        'streakLastDate': todayKey,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      return {
        'ok': false,
        'msg': 'Not eligible today. Need 3 active chats, 10 msgs each.',
        'streakDays': 0,
        'bonusPct': 0,
      };
    }

    int newDays = 1;

    if (lastDate.isNotEmpty) {
      final parts = lastDate.split('-');
      if (parts.length == 3) {
        final prev = DateTime(
          int.parse(parts[0]),
          int.parse(parts[1]),
          int.parse(parts[2]),
        );
        final diff =
            _startOfDay(now).difference(_startOfDay(prev)).inDays;

        if (diff == 1) {
          newDays = oldDays + 1;
        } else {
          newDays = 1;
        }
      }
    }

    if (newDays > 30) newDays = 1;

    final bonus = bonusPctForDays(newDays);

    await userRef.set({
      'streakDays': newDays,
      'streakBonusPct': bonus,
      'streakLastDate': todayKey,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    return {
      'ok': true,
      'msg': 'Streak updated ✅',
      'streakDays': newDays,
      'bonusPct': bonus,
    };
  }
}
