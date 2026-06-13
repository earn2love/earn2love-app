import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class PaymentPage extends StatefulWidget {
  final String targetTier; // friend or love

  const PaymentPage({
    super.key,
    required this.targetTier,
  });

  @override
  State<PaymentPage> createState() => _PaymentPageState();
}

class _PaymentPageState extends State<PaymentPage> {
  bool paying = false;
  bool loadingEconomy = true;

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  bool get isLove => widget.targetTier.toLowerCase() == 'love';
  bool get isFriend => widget.targetTier.toLowerCase() == 'friend';

  String country = 'UK';
  String currencySymbol = '£';
  String currencyCode = 'GBP';
  String pricingRegion = 'UK';

  @override
  void initState() {
    super.initState();
    _loadEconomy();
  }

  Future<void> _loadEconomy() async {
    try {
      final snap =
          await FirebaseFirestore.instance.collection('users').doc(uid).get();
      final data = snap.data() ?? <String, dynamic>{};

      if (!mounted) return;
      setState(() {
        country = (data['country'] ?? 'UK').toString();
        currencySymbol = (data['currencySymbol'] ?? '£').toString();
        currencyCode = (data['currencyCode'] ?? 'GBP').toString();
        pricingRegion = (data['pricingRegion'] ?? country).toString();
        loadingEconomy = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        loadingEconomy = false;
      });
    }
  }

  int get bonusCoins {
    if (isLove) return 100;
    if (isFriend) return 50;
    return 0;
  }

  String get priceText {
    if (country == 'IN') {
      if (isLove) return '₹499/month';
      if (isFriend) return '₹299/month';
      return 'Free';
    }
    if (country == 'UK') {
      if (isLove) return '£9.99/month';
      if (isFriend) return '£4.99/month';
      return 'Free';
    }
    if (country == 'US') {
      if (isLove) return '\$9.99/month';
      if (isFriend) return '\$4.99/month';
      return 'Free';
    }
    if (country == 'AU') {
      if (isLove) return '\$9.99/month';
      if (isFriend) return '\$4.99/month';
      return 'Free';
    }
    if (country == 'UAE') {
      if (isLove) return 'AED 39/month';
      if (isFriend) return 'AED 19/month';
      return 'Free';
    }

    if (isLove) return '${currencySymbol}9.99/month';
    if (isFriend) return '${currencySymbol}4.99/month';
    return 'Free';
  }

  Color get accentColor {
    if (isLove) return const Color(0xFFFF5FA8);
    return const Color(0xFF56B7FF);
  }

  Future<void> _payNow() async {
    setState(() => paying = true);

    try {
      await Future.delayed(const Duration(seconds: 1));

      final ref = FirebaseFirestore.instance.collection('users').doc(uid);

      await FirebaseFirestore.instance.runTransaction((tx) async {
        final snap = await tx.get(ref);
        final data = snap.data() ?? <String, dynamic>{};

        final bool vibeDone = data['vibeSelectionCompleted'] == true;
        final bool bonusGiven = data['onboardingBonusGranted'] == true;

        int coinsToAdd = 0;
        if (!vibeDone && !bonusGiven) {
          coinsToAdd = bonusCoins;
        }

        tx.set(
          ref,
          {
            'tier': widget.targetTier,
            'subTier': widget.targetTier,
            'selectedVibe': widget.targetTier,
            'subscriptionPlan': widget.targetTier,
            'subscriptionStatus': 'paid',
            'tierSelectedAt': FieldValue.serverTimestamp(),
            'updatedAt': FieldValue.serverTimestamp(),
            'vibeSelectionCompleted': true,
            'vibeSelectionCompletedAt': FieldValue.serverTimestamp(),
            'onboardingBonusGranted': true,
            'silverCoins': FieldValue.increment(coinsToAdd),
            'country': country,
            'currencyCode': currencyCode,
            'currencySymbol': currencySymbol,
            'pricingRegion': pricingRegion,
            'permissions': {
              'limitedChats': false,
              'unlimitedChats': true,
              'callsAllowed': true,
              'earningsAllowed': isLove,
            },
            'planMeta': {
              'planId': widget.targetTier,
              'priceText': priceText,
              'paymentStatus': 'paid',
              'bonusSilver': coinsToAdd,
              'currencyCode': currencyCode,
              'currencySymbol': currencySymbol,
              'pricingRegion': pricingRegion,
              'selectedAt': FieldValue.serverTimestamp(),
            },
          },
          SetOptions(merge: true),
        );
      });

      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Payment failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => paying = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.targetTier.toUpperCase();

    return Scaffold(
      backgroundColor: const Color(0xFFF8F2FF),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF8F2FF),
        elevation: 0,
        title: Text(
          "Payment • $t",
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            color: Color(0xFF4F2B84),
          ),
        ),
      ),
      body: loadingEconomy
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Card(
                elevation: 8,
                shadowColor: accentColor.withOpacity(0.18),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: isLove
                          ? const [
                              Color(0xFFFFD0E4),
                              Color(0xFFFFA7CB),
                              Color(0xFFFFC7D9),
                            ]
                          : const [
                              Color(0xFFD8F0FF),
                              Color(0xFFBEE4FF),
                              Color(0xFFD8D1FF),
                            ],
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          "$t Plan",
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF4F2B84),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          priceText,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            color: accentColor,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          isLove
                              ? "Includes unlimited chats, calls, real earnings access, and 100 silver bonus."
                              : "Includes unlimited chats, calls allowed, and 50 silver bonus.",
                          style: const TextStyle(
                            fontSize: 14.5,
                            height: 1.45,
                            color: Color(0xFF5C467D),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Text(
                          country == 'IN'
                              ? "Payment methods (add real gateway later):\n• Card\n• UPI\n• Netbanking\n• Google Pay / Apple Pay\n• In-App Subscription"
                              : "Payment methods (add real gateway later):\n• Card\n• Google Pay / Apple Pay\n• In-App Subscription",
                          style: const TextStyle(
                            fontSize: 14,
                            height: 1.5,
                            color: Color(0xFF5C467D),
                          ),
                        ),
                        const SizedBox(height: 18),
                        SizedBox(
                          height: 52,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: accentColor,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                            ),
                            onPressed: paying ? null : _payNow,
                            child: Text(
                              paying ? "Processing..." : "Pay & Continue",
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 50,
                          child: OutlinedButton(
                            style: OutlinedButton.styleFrom(
                              foregroundColor: const Color(0xFF5C467D),
                              side: const BorderSide(color: Color(0x335C467D)),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                            ),
                            onPressed: paying ? null : () => Navigator.pop(context, false),
                            child: const Text(
                              "Cancel",
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          "Note: Real payment gateway later integrate cheyyali. Ippudu Firestore tier activate avutundi.",
                          style: TextStyle(
                            fontSize: 12.5,
                            color: Color(0xFF7A699E),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}