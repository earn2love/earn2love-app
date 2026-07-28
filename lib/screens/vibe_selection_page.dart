import 'dart:ui';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../app_shell.dart';
import 'payment_page.dart';

class VibeSelectionPage extends StatefulWidget {
  const VibeSelectionPage({super.key});

  @override
  State<VibeSelectionPage> createState() => _VibeSelectionPageState();
}

class _VibeSelectionPageState extends State<VibeSelectionPage> {
  String selected = 'love';
  bool busy = false;

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  String country = 'UK';
  String currencySymbol = '£';
  bool pricesReady = false;

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
        pricesReady = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        country = 'UK';
        currencySymbol = '£';
        pricesReady = true;
      });
    }
  }

  String get friendPriceText {
    if (country == 'IN') return '₹299/month';
    if (country == 'UK') return '£4.99/month';
    if (country == 'US') return '\$4.99/month';
    if (country == 'AU') return '\$4.99/month';
    if (country == 'UAE') return 'AED 19/month';
    return '${currencySymbol}4.99/month';
  }

  String get lovePriceText {
    if (country == 'IN') return '₹499/month';
    if (country == 'UK') return '£9.99/month';
    if (country == 'US') return '\$9.99/month';
    if (country == 'AU') return '\$9.99/month';
    if (country == 'UAE') return 'AED 39/month';
    return '${currencySymbol}9.99/month';
  }

  Future<void> _handleContinue() async {
    if (busy) return;
    setState(() => busy = true);

    try {
      if (selected == 'casual') {
        await FirebaseFirestore.instance.collection('users').doc(uid).set(
          {
            'tier': 'casual',
            'subTier': 'casual',
            'selectedVibe': 'casual',
            'subscriptionPlan': 'casual',
            'subscriptionStatus': 'active',
            'tierSelectedAt': FieldValue.serverTimestamp(),
            'updatedAt': FieldValue.serverTimestamp(),
            'vibeSelectionCompleted': true,
            'vibeSelectionCompletedAt': FieldValue.serverTimestamp(),
            'onboardingBonusGranted': true,
            'permissions': {
              'limitedChats': true,
              'unlimitedChats': false,
              'callsAllowed': false,
              'earningsAllowed': false,
            },
            'planMeta': {
              'planId': 'casual',
              'priceText': 'Free',
              'paymentStatus': 'free',
              'bonusSilver': 0,
              'selectedAt': FieldValue.serverTimestamp(),
            },
          },
          SetOptions(merge: true),
        );

        if (!mounted) return;
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => const AppShell()),
          (route) => false,
        );
        return;
      }

      final ok = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => PaymentPage(targetTier: selected),
        ),
      );

      if (!mounted) return;

      if (ok == true) {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => const AppShell()),
          (route) => false,
        );
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  String get buttonText {
    switch (selected) {
      case 'casual':
        return 'Continue as Casual';
      case 'friend':
        return 'Continue as Friend';
      case 'love':
        return 'Continue as Love';
      default:
        return 'Continue';
    }
  }

  List<Color> get buttonGradient {
    switch (selected) {
      case 'casual':
        return const [Color(0xFF7A36FF), Color(0xFF4D7DFF)];
      case 'friend':
        return const [Color(0xFF15B8FF), Color(0xFF6D63FF)];
      case 'love':
        return const [Color(0xFFFF4FA8), Color(0xFFB93FFF)];
      default:
        return const [Color(0xFFFF4FA8), Color(0xFFB93FFF)];
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8EEFF),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFF9EFFF),
              Color(0xFFF1E1FF),
              Color(0xFFFEFAFF),
            ],
          ),
        ),
        child: Stack(
          children: [
            const _DreamyBg(),
            SafeArea(
              child: Column(
                children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                      child: Column(
                        children: [
                          _topBadge(),
                          const SizedBox(height: 10),
                          const Text(
                            'Choose your vibe',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontFamily: 'Poppins',
                              fontSize: 27,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF4E2488),
                              letterSpacing: -0.4,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Pick what you’re looking for and we’ll\npersonalize your experience.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontFamily: 'Poppins',
                              fontSize: 13.4,
                              fontWeight: FontWeight.w500,
                              height: 1.35,
                              color: Color(0xFF765D9D),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Expanded(
                            child: Column(
                              children: [
                                Expanded(child: _planCasual()),
                                const SizedBox(height: 10),
                                Expanded(child: _planFriend()),
                                const SizedBox(height: 10),
                                Expanded(child: _planLove()),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                    child: Column(
                      children: [
                        GestureDetector(
                          onTap: busy ? null : _handleContinue,
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 220),
                            height: 54,
                            width: double.infinity,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(999),
                              gradient: LinearGradient(colors: buttonGradient),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.86),
                                width: 1.3,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: buttonGradient.first.withOpacity(0.42),
                                  blurRadius: 24,
                                  offset: const Offset(0, 10),
                                ),
                              ],
                            ),
                            child: Center(
                              child: busy
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.2,
                                        color: Colors.white,
                                      ),
                                    )
                                  : Text(
                                      buttonText,
                                      style: const TextStyle(
                                        fontFamily: 'Poppins',
                                        fontSize: 16,
                                        fontWeight: FontWeight.w800,
                                        color: Colors.white,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'You can change this later in settings.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontFamily: 'Poppins',
                            fontSize: 12.2,
                            fontWeight: FontWeight.w500,
                            color: Color(0xFF7A699E),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _topBadge() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.30),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: Colors.white.withOpacity(0.68),
            ),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircleAvatar(
                radius: 12,
                backgroundColor: Color(0xFF4F67FF),
                child: Icon(Icons.check_rounded, color: Colors.white, size: 16),
              ),
              SizedBox(width: 8),
              Text(
                'Account created successfully',
                style: TextStyle(
                  fontFamily: 'Poppins',
                  fontSize: 12.8,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF5F4B88),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _planCasual() {
    final isSelected = selected == 'casual';

    return _glassCard(
      selected: isSelected,
      colors: const [
        Color(0xFFCE9CFF),
        Color(0xFFAC70FF),
        Color(0xFF739FFF),
      ],
      onTap: () => setState(() => selected = 'casual'),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Expanded(
            child: Padding(
              padding: EdgeInsets.only(top: 2, right: 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Casual',
                    style: TextStyle(
                      fontFamily: 'Poppins',
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 6),
                  Expanded(
                    child: Text(
                      'Enjoy light, easygoing chats without any pressure.',
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: 'Poppins',
                        fontSize: 11.6,
                        height: 1.22,
                        fontWeight: FontWeight.w500,
                        color: Color(0xFF47356F),
                      ),
                    ),
                  ),
                  SizedBox(height: 6),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _ChipPill(
                          text: 'Free',
                          colors: [Color(0xFFF7EEFF), Color(0xFFE8D8FF)],
                          textColor: Color(0xFF6A4EAA),
                        ),
                        SizedBox(width: 5),
                        _ChipPill(
                          text: 'Limited chats',
                          colors: [Color(0xFF9F64FF), Color(0xFF7E56FF)],
                        ),
                        SizedBox(width: 5),
                        _ChipPill(
                          text: 'No calls',
                          colors: [Color(0xFF9F64FF), Color(0xFF7E56FF)],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 6),
          _artCircle(
            imagePath: 'assets/ui/casual_hifi.png',
            topRightColors: const [Color(0xFF5F84FF), Color(0xFF4568FF)],
            onTap: () => setState(() => selected = 'casual'),
            selected: isSelected,
          ),
        ],
      ),
    );
  }

  Widget _planFriend() {
    final isSelected = selected == 'friend';

    return _glassCard(
      selected: isSelected,
      colors: const [
        Color(0xFF8EDBFF),
        Color(0xFF52C3FF),
        Color(0xFF8D80FF),
      ],
      onTap: () => setState(() => selected = 'friend'),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Expanded(
            child: Padding(
              padding: EdgeInsets.only(top: 2, right: 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Friend',
                    style: TextStyle(
                      fontFamily: 'Poppins',
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Meet warm people, build genuine bonds, and enjoy friendly conversations that feel real.',
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: 'Poppins',
                      fontSize: 11.3,
                      height: 1.20,
                      fontWeight: FontWeight.w500,
                      color: Color(0xFF47356F),
                    ),
                  ),
                  SizedBox(height: 6),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _ChipPill(
                          text: 'Unlimited friends',
                          colors: [Color(0xFF506DFF), Color(0xFF687FFF)],
                        ),
                        SizedBox(width: 5),
                        _ChipPill(
                          text: 'Unlimited chats',
                          colors: [Color(0xFF506DFF), Color(0xFF687FFF)],
                        ),
                        SizedBox(width: 5),
                        _ChipPill(
                          text: 'Calls allowed',
                          colors: [Color(0xFF506DFF), Color(0xFF687FFF)],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 6),
          _artCircle(
            imagePath: 'assets/ui/friend_hug.png',
            topLeftPrice: friendPriceText,
            priceColors: const [Color(0xFF13CADB), Color(0xFF1E9ED3)],
            topRightColors: const [Color(0xFF5F84FF), Color(0xFF4568FF)],
            onTap: () => setState(() => selected = 'friend'),
            selected: isSelected,
          ),
        ],
      ),
    );
  }

  Widget _planLove() {
    final isSelected = selected == 'love';

    return _glassCard(
      selected: isSelected,
      colors: const [
        Color(0xFFFF97C0),
        Color(0xFFFF5C9F),
        Color(0xFFFF6C7A),
      ],
      onTap: () => setState(() => selected = 'love'),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Expanded(
            child: Padding(
              padding: EdgeInsets.only(top: 2, right: 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Love',
                    style: TextStyle(
                      fontFamily: 'Poppins',
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Unlock deeper romantic connections, premium access, and a more rewarding experience.',
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: 'Poppins',
                      fontSize: 11.3,
                      height: 1.20,
                      fontWeight: FontWeight.w500,
                      color: Color(0xFF4A2F68),
                    ),
                  ),
                  SizedBox(height: 6),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _ChipPill(
                          text: 'Unlimited chats',
                          colors: [Color(0xFFFF3F95), Color(0xFFE54773)],
                        ),
                        SizedBox(width: 5),
                        _ChipPill(
                          text: 'Calls & rewards',
                          colors: [Color(0xFFFF3F95), Color(0xFFE54773)],
                        ),
                        SizedBox(width: 5),
                        _ChipPill(
                          text: 'Real earnings',
                          colors: [Color(0xFFFF3F95), Color(0xFFE54773)],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 6),
          _artCircle(
            imagePath: 'assets/ui/love_earnings.png',
            topLeftPrice: lovePriceText,
            priceColors: const [Color(0xFFFF498E), Color(0xFFFF644F)],
            topRightColors: const [Color(0xFFFF9763), Color(0xFFFF6F62)],
            onTap: () => setState(() => selected = 'love'),
            selected: isSelected,
          ),
        ],
      ),
    );
  }

  Widget _glassCard({
    required Widget child,
    required VoidCallback onTap,
    required List<Color> colors,
    required bool selected,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedScale(
        duration: const Duration(milliseconds: 220),
        scale: selected ? 1.008 : 1,
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: colors,
            ),
            border: Border.all(
              color: selected
                  ? Colors.white.withOpacity(0.98)
                  : Colors.white.withOpacity(0.82),
              width: selected ? 1.5 : 1.1,
            ),
            boxShadow: [
              BoxShadow(
                color: colors.first.withOpacity(0.28),
                blurRadius: 18,
                offset: const Offset(0, 9),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _artCircle({
    required String imagePath,
    required List<Color> topRightColors,
    required VoidCallback onTap,
    required bool selected,
    String? topLeftPrice,
    List<Color>? priceColors,
  }) {
    return SizedBox(
      width: 96,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          GestureDetector(
            onTap: onTap,
            child: Container(
              height: 96,
              width: 96,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withOpacity(0.92),
                  width: 2.4,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.white.withOpacity(0.18),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: ClipOval(
                child: Image.asset(
                  imagePath,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) {
                    return Container(
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          colors: [Color(0x3377AFFF), Color(0x33FF93C1)],
                        ),
                      ),
                      child: const Center(
                        child: Icon(
                          Icons.image_not_supported_rounded,
                          color: Colors.white,
                          size: 26,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
          Positioned(
            right: -2,
            top: 3,
            child: Container(
              height: 34,
              width: 34,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: topRightColors),
                border: Border.all(
                  color: Colors.white.withOpacity(0.84),
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: topRightColors.first.withOpacity(0.30),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: const Icon(
                Icons.check_rounded,
                color: Colors.white,
                size: 19,
              ),
            ),
          ),
          if (topLeftPrice != null && priceColors != null)
            Positioned(
              top: -2,
              left: -10,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8.5, vertical: 5.5),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  gradient: LinearGradient(colors: priceColors),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.78),
                    width: 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: priceColors.first.withOpacity(0.24),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Text(
                  topLeftPrice,
                  style: const TextStyle(
                    fontFamily: 'Poppins',
                    fontSize: 9.2,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ChipPill extends StatelessWidget {
  final String text;
  final List<Color> colors;
  final Color textColor;

  const _ChipPill({
    required this.text,
    required this.colors,
    this.textColor = Colors.white,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8.5, vertical: 5.2),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        gradient: LinearGradient(colors: colors),
        border: Border.all(
          color: Colors.white.withOpacity(0.68),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: colors.first.withOpacity(0.18),
            blurRadius: 7,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Text(
        text,
        style: TextStyle(
          fontFamily: 'Poppins',
          fontSize: 9.9,
          fontWeight: FontWeight.w700,
          color: textColor,
        ),
      ),
    );
  }
}

class _DreamyBg extends StatelessWidget {
  const _DreamyBg();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Stack(
        children: [
          Positioned(
            top: -40,
            left: -30,
            child: _blob(180, 180, const Color(0x66FFFFFF)),
          ),
          Positioned(
            top: -10,
            right: -20,
            child: _blob(210, 190, const Color(0x55FFD7F0)),
          ),
          Positioned(
            top: 250,
            right: -40,
            child: _blob(220, 180, const Color(0x44FFFFFF)),
          ),
          Positioned(
            bottom: -20,
            left: -20,
            child: _blob(240, 170, const Color(0x55D9D2FF)),
          ),
          Positioned(
            bottom: -40,
            right: -30,
            child: _blob(240, 170, const Color(0x44FFFFFF)),
          ),
          ..._hearts(),
          ..._stars(),
        ],
      ),
    );
  }

  Widget _blob(double w, double h, Color color) {
    return Container(
      width: w,
      height: h,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(999),
      ),
    );
  }

  List<Widget> _hearts() {
    const items = [
      [28.0, 80.0, 20.0],
      [320.0, 72.0, 15.0],
      [75.0, 230.0, 12.0],
      [280.0, 304.0, 12.0],
      [335.0, 452.0, 14.0],
      [88.0, 610.0, 10.0],
    ];

    return items.map((e) {
      return Positioned(
        left: e[0],
        top: e[1],
        child: Icon(
          Icons.favorite_rounded,
          size: e[2],
          color: Colors.white.withOpacity(0.30),
        ),
      );
    }).toList();
  }

  List<Widget> _stars() {
    const items = [
      [26.0, 58.0, 7.0],
      [116.0, 46.0, 5.0],
      [300.0, 110.0, 7.0],
      [340.0, 210.0, 6.0],
      [60.0, 420.0, 5.0],
      [280.0, 580.0, 6.0],
    ];

    return items.map((e) {
      return Positioned(
        left: e[0],
        top: e[1],
        child: Icon(
          Icons.auto_awesome_rounded,
          size: e[2],
          color: Colors.white.withOpacity(0.56),
        ),
      );
    }).toList();
  }
}
