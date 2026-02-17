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

  static double _num(dynamic v) {
    if (v is int) return v.toDouble();
    if (v is double) return v;
    if (v is num) return v.toDouble();
    return 0;
  }

  static Future<Map<String, dynamic>> getUser() async {
    final snap = await userRef.get();
    return snap.data() ?? {};
  }

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

  // ------------------- ADD / SPEND -------------------
  static Future<void> addSilver(int amount, {String reason = 'ads'}) async {
    await userRef.set({
      'silverBalance': FieldValue.increment(amount),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await _log(
      type: reason,
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
      type: reason,
      title: reason.toUpperCase(),
      fromCoin: 'Silver',
      fromAmount: amount.toDouble(),
    );
  }

  // ------------------- COUNTRY RATES -------------------
  // India: 3S=2G, 3G=2D
  // UK:    3S=2.5G, 3G=2.5D
  static double _rateSilverToGold(String country) =>
      (country == 'UK') ? (2.5 / 3.0) : (2.0 / 3.0);

  static double _rateGoldToDiamond(String country) =>
      (country == 'UK') ? (2.5 / 3.0) : (2.0 / 3.0);

  static Future<void> convertCoins({
    required String from,
    required String to,
    required double amount,
    required double bonusPct,
  }) async {
    if (amount <= 0) throw Exception("Enter valid amount");
    if (from == to) throw Exception("From and To cannot be same");
    if (from == 'Silver' && to == 'Diamond') {
      throw Exception("Direct Silver → Diamond not allowed");
    }

    final u = await getUser();
    final country = (u['country'] ?? 'IN').toString();

    final s = _num(u['silverBalance']);
    final g = _num(u['goldBalance']);
    final d = _num(u['diamondBalance']);

    double out = 0;

    if (from == 'Silver' && to == 'Gold') {
      out = amount * _rateSilverToGold(country);
      final bonus = out * (bonusPct / 100.0);
      out = out + bonus;
    } else if (from == 'Gold' && to == 'Diamond') {
      out = amount * _rateGoldToDiamond(country);
    } else if (from == 'Gold' && to == 'Silver') {
      out = amount / _rateSilverToGold(country);
    } else if (from == 'Diamond' && to == 'Gold') {
      out = amount / _rateGoldToDiamond(country);
    } else {
      throw Exception("Conversion not enabled in Phase 1");
    }

    if (from == 'Silver' && s < amount) throw Exception("Not enough Silver");
    if (from == 'Gold' && g < amount) throw Exception("Not enough Gold");
    if (from == 'Diamond' && d < amount) throw Exception("Not enough Diamond");

    final updates = <String, dynamic>{
      'updatedAt': FieldValue.serverTimestamp(),
    };

    void inc(String field, double val) {
      updates[field] = FieldValue.increment(val);
    }

    if (from == 'Silver') inc('silverBalance', -amount);
    if (from == 'Gold') inc('goldBalance', -amount);
    if (from == 'Diamond') inc('diamondBalance', -amount);

    if (to == 'Silver') inc('silverBalance', out);
    if (to == 'Gold') inc('goldBalance', out);
    if (to == 'Diamond') inc('diamondBalance', out);

    await userRef.set(updates, SetOptions(merge: true));

    await _log(
      type: 'conversion',
      title: 'CONVERSION',
      fromCoin: from,
      fromAmount: amount,
      toCoin: to,
      toAmount: out,
      bonusPct: (from == 'Silver' && to == 'Gold') ? bonusPct : 0,
    );
  }
}
