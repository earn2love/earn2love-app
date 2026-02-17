import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class CoinService {
  static String get uid => FirebaseAuth.instance.currentUser!.uid;

  static DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  static CollectionReference<Map<String, dynamic>> get historyRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('walletHistory');

  static double _toDouble(dynamic v, {double def = 0}) {
    if (v == null) return def;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v.trim()) ?? def;
    return def;
  }

  static int _toInt(dynamic v, {int def = 0}) {
    if (v == null) return def;
    if (v is int) return v;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v.trim()) ?? def;
    return def;
  }

  /// Always returns safe defaults (prevents: Null is not a subtype of int)
  static Future<Map<String, dynamic>> getUser() async {
    final snap = await userRef.get();
    final data = (snap.data() ?? <String, dynamic>{});

    // wallets (always keep numeric)
    data['silverBalance'] = _toDouble(data['silverBalance']);
    data['goldBalance'] = _toDouble(data['goldBalance']);
    data['diamondBalance'] = _toDouble(data['diamondBalance']);

    // streak
    data['streakDays'] = _toInt(data['streakDays']);
    data['streakBonusPct'] = _toInt(data['streakBonusPct']);

    // country fallback
    data['country'] = (data['country'] ?? 'IN').toString();

    return data;
  }

  // ------------------- HISTORY HELPERS -------------------
  static Future<void> _log({
    required String type,
    required String title,
    String fromCoin = '',
    double fromAmount = 0,
    String toCoin = '',
    double toAmount = 0,
    double bonusPct = 0,
  }) async {
    await historyRef.add({
      'type': type,
      'title': title,
      'fromCoin': fromCoin,
      'fromAmount': fromAmount,
      'toCoin': toCoin,
      'toAmount': toAmount,
      'bonusPct': bonusPct,
      'createdAt': FieldValue.serverTimestamp(),
    });
  }

  // ------------------- EARN / SPEND -------------------
  static Future<void> addSilver(int amount, {String reason = 'ads'}) async {
    await userRef.set({
      'silverBalance': FieldValue.increment(amount),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await _log(
      type: reason, // ads/topup/promo/tasks
      title: reason.toUpperCase(),
      toCoin: 'Silver',
      toAmount: amount.toDouble(),
    );
  }

  static Future<void> spendSilver(int amount, {required String reason}) async {
    await userRef.set({
      'silverBalance': FieldValue.increment(-amount),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await _log(
      type: reason, // audio_call/video_call
      title: reason.toUpperCase(),
      fromCoin: 'Silver',
      fromAmount: amount.toDouble(),
    );
  }

  // ------------------- RATES (Country Based) -------------------
  // India: 3 Silver = 2 Gold; 3 Gold = 2 Diamond
  // UK:    3 Silver = 2.5 Gold; 3 Gold = 2.5 Diamond
  static double _rateSilverToGold(String country) =>
      (country == 'UK') ? (2.5 / 3.0) : (2.0 / 3.0);

  static double _rateGoldToDiamond(String country) =>
      (country == 'UK') ? (2.5 / 3.0) : (2.0 / 3.0);

  static double _clampPct(double v) {
    if (v.isNaN) return 0;
    if (v < 0) return 0;
    if (v > 100) return 100;
    return v;
  }

  // ------------------- CONVERSION -------------------
  static Future<void> convertCoins({
    required String from,
    required String to,
    required double amount,
    required double bonusPct, // streak bonus for Silver->Gold only
  }) async {
    final a = _toDouble(amount);
    if (a <= 0) throw Exception("Enter valid amount");
    if (from == to) throw Exception("From and To cannot be same");

    // rule: no direct silver->diamond
    if (from == 'Silver' && to == 'Diamond') {
      throw Exception("Direct Silver → Diamond not allowed");
    }

    final u = await getUser();
    final country = (u['country'] ?? 'IN').toString();

    final s = _toDouble(u['silverBalance']);
    final g = _toDouble(u['goldBalance']);
    final d = _toDouble(u['diamondBalance']);

    double out = 0;

    if (from == 'Silver' && to == 'Gold') {
      out = a * _rateSilverToGold(country);

      final pct = _clampPct(_toDouble(bonusPct));
      final bonus = out * (pct / 100.0);
      out = out + bonus;
    } else if (from == 'Gold' && to == 'Diamond') {
      out = a * _rateGoldToDiamond(country);
    } else if (from == 'Gold' && to == 'Silver') {
      out = a / _rateSilverToGold(country);
    } else if (from == 'Diamond' && to == 'Gold') {
      out = a / _rateGoldToDiamond(country);
    } else {
      throw Exception("Conversion not enabled in Phase 1");
    }

    // validate
    if (from == 'Silver' && s < a) throw Exception("Not enough Silver");
    if (from == 'Gold' && g < a) throw Exception("Not enough Gold");
    if (from == 'Diamond' && d < a) throw Exception("Not enough Diamond");

    final updates = <String, dynamic>{
      'updatedAt': FieldValue.serverTimestamp(),
    };

    void inc(String field, double val) {
      updates[field] = FieldValue.increment(val);
    }

    if (from == 'Silver') inc('silverBalance', -a);
    if (from == 'Gold') inc('goldBalance', -a);
    if (from == 'Diamond') inc('diamondBalance', -a);

    if (to == 'Silver') inc('silverBalance', out);
    if (to == 'Gold') inc('goldBalance', out);
    if (to == 'Diamond') inc('diamondBalance', out);

    await userRef.set(updates, SetOptions(merge: true));

    await _log(
      type: 'conversion',
      title: 'CONVERSION',
      fromCoin: from,
      fromAmount: a,
      toCoin: to,
      toAmount: out,
      bonusPct: (from == 'Silver' && to == 'Gold') ? _clampPct(_toDouble(bonusPct)) : 0,
    );
  }
}
