import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class StreakService {
  static String get uid => FirebaseAuth.instance.currentUser!.uid;

  static DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  static CollectionReference<Map<String, dynamic>> chatsCol =>
      FirebaseFirestore.instance.collection('chats');

  static String _todayKey() {
    final now = DateTime.now();
    return "${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}";
  }

  static int _bonusForDays(int days) {
    if (days >= 30) return 10;
    if (days >= 14) return 7;
    if (days >= 7) return 5;
    return 0;
  }

  /// Checks today's eligibility and updates streak fields.
  /// Returns: { ok: bool, msg: String, streakDays: int, bonusPct: int }
  static Future<Map<String, dynamic>> updateStreakIfEligible() async {
    final today = _todayKey();

    final uSnap = await userRef.get();
    final u = uSnap.data() ?? {};

    final last = (u['streakLastDate'] ?? '').toString();
    int days = (u['streakDays'] is num) ? (u['streakDays'] as num).toInt() : 0;

    if (last == today) {
      final bonus = (u['streakBonusPct'] is num) ? (u['streakBonusPct'] as num).toInt() : _bonusForDays(days);
      return {
        'ok': true,
        'msg': "Already checked today ✅",
        'streakDays': days,
        'bonusPct': bonus,
      };
    }

    // 1) Find chats where user participates
    final chats = await chatsCol.where('participants', arrayContains: uid).get();

    int activeChats = 0;

    for (final c in chats.docs) {
      final chatId = c.id;

      // 2) Count messages in this chat for today
      // We'll just fetch last ~50 and count those having createdAt today.
      // (Phase-1 simple. Later: indexing/optimized)
      final msgSnap = await chatsCol
          .doc(chatId)
          .collection('messages')
          .orderBy('createdAt', descending: true)
          .limit(50)
          .get();

      int todayMsgs = 0;

      for (final m in msgSnap.docs) {
        final ts = m.data()['createdAt'];
        if (ts is! Timestamp) continue;
        final dt = ts.toDate();
        final key =
            "${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}";

        if (key != today) break; // because ordered desc, once past today stop
        todayMsgs++;
      }

      if (todayMsgs >= 10) activeChats++;
      if (activeChats >= 3) break;
    }

    if (activeChats < 3) {
      return {
        'ok': false,
        'msg': "Not eligible today ❌ Need 3 chats with 10 msgs each. Current: $activeChats",
        'streakDays': days,
        'bonusPct': _bonusForDays(days),
      };
    }

    // Eligible today ✅
    days = days + 1;

    // reset after 30 days (as per your rule)
    if (days > 30) days = 1;

    final bonusPct = _bonusForDays(days);

    await userRef.set({
      'streakDays': days,
      'streakBonusPct': bonusPct,
      'streakLastDate': today,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    return {
      'ok': true,
      'msg': "Streak updated ✅ Now: $days days (+$bonusPct% Silver→Gold)",
      'streakDays': days,
      'bonusPct': bonusPct,
    };
  }
}
