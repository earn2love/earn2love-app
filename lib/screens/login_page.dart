import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:crypto/crypto.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'auth_gate.dart';
import 'reset_password_page.dart';
import 'vibe_selection_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    this.forceSignupMode = false,
    this.showEmailVerifyBlock = false,
    this.showSetPasswordBlock = false,
  });

  final bool forceSignupMode;
  final bool showEmailVerifyBlock;
  final bool showSetPasswordBlock;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

enum _VerifyAnimState { none, verifying, success, fail }

class _LoginPageState extends State<LoginPage>
    with SingleTickerProviderStateMixin {
  bool isLoginMode = false;

  final idCtrl = TextEditingController();
  final otpCtrl = TextEditingController();
  final passCtrl = TextEditingController();
  final pass2Ctrl = TextEditingController();

  bool sendingOtp = false;
  bool verifyingOtp = false;
  bool emailLoading = false;

  String dialCode = "+91";
  String country = "IN";
  String? verificationId;
  int? resendToken;

  bool otpSent = false;
  bool otpVerified = false;

  bool lockId = false;
  bool lockDial = false;

  String? status;

  _VerifyAnimState _animState = _VerifyAnimState.none;
  late final AnimationController _heartCtrl;
  late final Animation<double> _heartScale;

  static const _kDeviceSessionId = "deviceSessionId";
  String? _deviceSessionId;

  static const _kPendingPhoneDigits = "pendingPhoneDigits";
  static const _kPendingDial = "pendingDialCode";
  static const _kPendingOtpVerified = "pendingOtpVerified";

  static const _kPendingEmail = "pendingEmail";
  static const _kPendingEmailLinkSent = "pendingEmailLinkSent";

  static const String _logoPath = "assets/images/earn2love_icon.png";

  DocumentReference<Map<String, dynamic>> userRef(String uid) =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  static const _dialOptions = <Map<String, String>>[
    {"flag": "🇮🇳", "code": "+91", "short": "IN", "name": "India"},
    {"flag": "🇬🇧", "code": "+44", "short": "UK", "name": "United Kingdom"},
    {"flag": "🇺🇸", "code": "+1", "short": "US", "name": "United States"},
    {"flag": "🇦🇺", "code": "+61", "short": "AU", "name": "Australia"},
    {"flag": "🇦🇪", "code": "+971", "short": "UAE", "name": "UAE"},
  ];

  static const double kAppBarTitle = 32;
  static const double kTopBarIcon = 34;
  static const double kCenterIcon = 240;
  static const double kPageTitle = 34;

  final _bg = const Color(0xFFF8F2FF);
  final _purple = const Color(0xFF6C4AA3);
  final _green = const Color(0xFF7FAE7D);

  @override
  void initState() {
    super.initState();

    isLoginMode = widget.forceSignupMode ? false : false;

    _heartCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 550),
    );
    _heartScale = Tween<double>(begin: 0.88, end: 1.10).animate(
      CurvedAnimation(parent: _heartCtrl, curve: Curves.easeInOut),
    );

    _heartCtrl.addStatusListener((s) {
      if (_animState != _VerifyAnimState.verifying) return;
      if (s == AnimationStatus.completed) _heartCtrl.reverse();
      if (s == AnimationStatus.dismissed) _heartCtrl.forward();
    });

    _initLocal();
  }

  @override
  void dispose() {
    idCtrl.dispose();
    otpCtrl.dispose();
    passCtrl.dispose();
    pass2Ctrl.dispose();
    _heartCtrl.dispose();
    super.dispose();
  }

  Future<void> _initLocal() async {
    await _ensureDeviceSessionId();

    final sp = await SharedPreferences.getInstance();
    final savedDial = sp.getString("selectedDialCode");
    if (savedDial != null && savedDial.isNotEmpty) {
      dialCode = savedDial;
    }
    _deriveCountryFromDial(dialCode);

    if (widget.showEmailVerifyBlock) {
      final pendingEmail = sp.getString(_kPendingEmail);
      final pendingEmailLinkSent = sp.getBool(_kPendingEmailLinkSent) ?? false;

      if (pendingEmail != null && pendingEmail.isNotEmpty) {
        idCtrl.text = pendingEmail;
      }
      if (pendingEmailLinkSent) {
        otpSent = true;
        otpVerified = false;
        lockId = true;
        lockDial = true;
        status =
            "Verification link sent ✅ Check email and click link, then tap Verify Link.";
      }
    }

    if (widget.showSetPasswordBlock) {
      final pendingDigits = sp.getString(_kPendingPhoneDigits);
      final pendingDial = sp.getString(_kPendingDial);
      final pendingVerified = sp.getBool(_kPendingOtpVerified) ?? false;

      if (pendingDial != null && pendingDial.isNotEmpty) {
        dialCode = pendingDial;
        _deriveCountryFromDial(dialCode);
      }
      if (pendingDigits != null && pendingDigits.isNotEmpty) {
        idCtrl.text = pendingDigits;
      }
      if (pendingVerified) {
        otpSent = true;
        otpVerified = true;
        lockId = true;
        lockDial = true;
        status =
            "OTP verified ✅ Now set password (2 boxes) and tap Sign Up to continue.";
      }
    }

    if (mounted) setState(() {});
  }

  Future<void> _ensureDeviceSessionId() async {
    final sp = await SharedPreferences.getInstance();
    final existing = sp.getString(_kDeviceSessionId);
    if (existing != null && existing.isNotEmpty) {
      _deviceSessionId = existing;
      return;
    }
    final r = Random.secure();
    final newId =
        "${DateTime.now().millisecondsSinceEpoch}_${r.nextInt(1 << 32)}";
    await sp.setString(_kDeviceSessionId, newId);
    _deviceSessionId = newId;
  }

  Map<String, String> _pricingMetaForCountry(String shortCountry) {
    switch (shortCountry) {
      case 'IN':
        return const {
          'currencyCode': 'INR',
          'currencySymbol': '₹',
          'pricingRegion': 'IN',
        };
      case 'UK':
        return const {
          'currencyCode': 'GBP',
          'currencySymbol': '£',
          'pricingRegion': 'UK',
        };
      case 'US':
        return const {
          'currencyCode': 'USD',
          'currencySymbol': r'$',
          'pricingRegion': 'US',
        };
      case 'AU':
        return const {
          'currencyCode': 'AUD',
          'currencySymbol': r'$',
          'pricingRegion': 'AU',
        };
      case 'UAE':
        return const {
          'currencyCode': 'AED',
          'currencySymbol': 'AED',
          'pricingRegion': 'UAE',
        };
      default:
        return const {
          'currencyCode': 'GBP',
          'currencySymbol': '£',
          'pricingRegion': 'UK',
        };
    }
  }

  Future<void> _setCountryPricingOnUserDoc(String uid) async {
    final meta = _pricingMetaForCountry(country);
    await userRef(uid).set({
      'country': country,
      'dialCode': dialCode,
      'currencyCode': meta['currencyCode'],
      'currencySymbol': meta['currencySymbol'],
      'pricingRegion': meta['pricingRegion'],
      'economy': {
        'country': country,
        'dialCode': dialCode,
        'currencyCode': meta['currencyCode'],
        'currencySymbol': meta['currencySymbol'],
        'pricingRegion': meta['pricingRegion'],
      },
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> _setActiveSessionOnUserDoc(String uid) async {
    if (_deviceSessionId == null) await _ensureDeviceSessionId();
    await userRef(uid).set({
      'activeSessionId': _deviceSessionId,
      'activeSessionAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> _savePendingEmailState(String email) async {
    final sp = await SharedPreferences.getInstance();
    await sp.setString(_kPendingEmail, email.trim());
    await sp.setBool(_kPendingEmailLinkSent, true);
  }

  Future<void> _clearPendingEmailState() async {
    final sp = await SharedPreferences.getInstance();
    await sp.remove(_kPendingEmail);
    await sp.remove(_kPendingEmailLinkSent);
  }

  Future<void> _savePendingPhoneState() async {
    final sp = await SharedPreferences.getInstance();
    await sp.setString(_kPendingPhoneDigits, phoneDigitsOnly);
    await sp.setString(_kPendingDial, dialCode);
    await sp.setBool(_kPendingOtpVerified, true);
  }

  Future<void> _clearPendingPhoneState() async {
    final sp = await SharedPreferences.getInstance();
    await sp.remove(_kPendingPhoneDigits);
    await sp.remove(_kPendingDial);
    await sp.remove(_kPendingOtpVerified);
  }

  Future<void> _clearAllPendingState() async {
    await _clearPendingEmailState();
    await _clearPendingPhoneState();
  }

  Map<String, String> _optForCode(String code) {
    for (final o in _dialOptions) {
      if (o["code"] == code) return o;
    }
    return const {
      "flag": "🌍",
      "code": "+0",
      "short": "OTHER",
      "name": "Other",
    };
  }

  void _deriveCountryFromDial(String code) {
    final o = _optForCode(code);
    dialCode = code;
    country = o["short"] ?? "OTHER";

    final pricing = _pricingMetaForCountry(country);

    SharedPreferences.getInstance().then((sp) {
      sp.setString("selectedDialCode", code);
      sp.setString("selectedCountry", country);
      sp.setString("selectedCurrencyCode", pricing['currencyCode'] ?? 'GBP');
      sp.setString("selectedCurrencySymbol", pricing['currencySymbol'] ?? '£');
      sp.setString("selectedPricingRegion", pricing['pricingRegion'] ?? 'UK');
    });
  }

  bool get isEmail {
    final t = idCtrl.text.trim();
    return RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(t);
  }

  bool get isPhone {
    final t = idCtrl.text.trim();
    final digits = t.replaceAll(RegExp(r'[^0-9]'), '');
    return digits.length >= 10 && RegExp(r'^[0-9+\s-]+$').hasMatch(t);
  }

  String get phoneDigitsOnly =>
      idCtrl.text.trim().replaceAll(RegExp(r'[^0-9]'), '');

  String get fullPhone => "$dialCode$phoneDigitsOnly";

  String get fullPhoneDigitsOnly => fullPhone.replaceAll(RegExp(r'[^0-9]'), '');

  String _hash(String s) => sha256.convert(utf8.encode(s)).toString();

  bool _passwordsValid() {
    final p1 = passCtrl.text.trim();
    final p2 = pass2Ctrl.text.trim();
    return p1.length >= 6 && p1 == p2;
  }

  void _goHome() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthGate()),
      (r) => false,
    );
  }

  void _goToVibeSelection() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const VibeSelectionPage()),
      (r) => false,
    );
  }

  Future<void> _hardLogout() async {
    try {
      await FirebaseAuth.instance.signOut();
      await _clearAllPendingState();

      if (!mounted) return;
      setState(() {
        otpSent = false;
        otpVerified = false;
        lockId = false;
        lockDial = false;
        verificationId = null;
        resendToken = null;
        sendingOtp = false;
        verifyingOtp = false;
        emailLoading = false;
        status = "Signed out ✅";
      });

      idCtrl.clear();
      otpCtrl.clear();
      passCtrl.clear();
      pass2Ctrl.clear();

      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const AuthGate()),
        (r) => false,
      );
    } catch (e) {
      if (mounted) setState(() => status = "Sign out failed: $e");
    }
  }

  Future<void> ensureUserDoc({required String country}) async {
    final user = FirebaseAuth.instance.currentUser!;
    final ref = userRef(user.uid);
    final snap = await ref.get();
    final existing = snap.data() ?? {};

    final userPhone = user.phoneNumber;
    final phoneDigits = userPhone?.replaceAll(RegExp(r'[^0-9]'), '');

    final pricing = _pricingMetaForCountry(country);

    if (!snap.exists) {
      await ref.set({
        'uid': user.uid,
        'phone': user.phoneNumber,
        'email': user.email,
        'createdAt': FieldValue.serverTimestamp(),
        'displayName': '',
        'bio': '',
        'photoUrls': [],
        'silverBalance': 0,
        'goldBalance': 0,
        'diamondBalance': 0,
        'country': country,
        'dialCode': dialCode,
        'currencyCode': pricing['currencyCode'],
        'currencySymbol': pricing['currencySymbol'],
        'pricingRegion': pricing['pricingRegion'],
        'economy': {
          'country': country,
          'dialCode': dialCode,
          'currencyCode': pricing['currencyCode'],
          'currencySymbol': pricing['currencySymbol'],
          'pricingRegion': pricing['pricingRegion'],
        },
        'appLanguage': 'en',
        'matchLanguage': country == "IN" ? 'te' : 'en',
        'streakDays': 0,
        'streakBonusPct': 0,
        'streakLastDate': '',
        'freezeUntil': null,
        'reportsCount': 0,
        'tier': 'casual',
        'subTier': 'casual',
        'selectedVibe': null,
        'subscriptionPlan': null,
        'subscriptionStatus': null,
        'vibeSelectionCompleted': false,
        'onboardingBonusGranted': false,
        'permissions': {
          'limitedChats': false,
          'unlimitedChats': false,
          'callsAllowed': false,
          'earningsAllowed': false,
        },
        'livenessVerifiedAt': null,
        'nextLivenessDueAt': null,
        'isPremium': false,
        'hasPassword': false,
        'passwordHash': '',
        'phoneDigits': phoneDigits,
      });
    } else {
      await ref.set({
        'phone': user.phoneNumber ?? existing['phone'],
        'email': user.email ?? existing['email'],
        'phoneDigits': phoneDigits ?? existing['phoneDigits'],
        'country': country,
        'dialCode': dialCode,
        'currencyCode': pricing['currencyCode'],
        'currencySymbol': pricing['currencySymbol'],
        'pricingRegion': pricing['pricingRegion'],
        'economy': {
          'country': country,
          'dialCode': dialCode,
          'currencyCode': pricing['currencyCode'],
          'currencySymbol': pricing['currencySymbol'],
          'pricingRegion': pricing['pricingRegion'],
        },
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }
  }

  void _showVerifying() {
    setState(() => _animState = _VerifyAnimState.verifying);
    _heartCtrl.forward(from: 0);
  }

  Future<void> _showSuccess() async {
    _heartCtrl.stop();
    setState(() => _animState = _VerifyAnimState.success);
    await Future.delayed(const Duration(milliseconds: 900));
    if (!mounted) return;
    setState(() => _animState = _VerifyAnimState.none);
  }

  Future<void> _showFail() async {
    _heartCtrl.stop();
    setState(() => _animState = _VerifyAnimState.fail);
    await Future.delayed(const Duration(milliseconds: 1200));
    if (!mounted) return;
    setState(() => _animState = _VerifyAnimState.none);
  }

  String _randomTempPassword() {
    const chars =
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#\$%^&*";
    final r = Random.secure();
    return List.generate(16, (_) => chars[r.nextInt(chars.length)]).join();
  }

  String _phoneAliasEmail(String fullDigits) => "p$fullDigits@earn2love.app";
  String _phoneAliasEmailLegacy(String localDigits) =>
      "p$localDigits@earn2love.app";

  Future<bool> _phoneAccountAlreadyExists() async {
    try {
      final users = FirebaseFirestore.instance.collection('users');

      final exactPhone =
          await users.where('phone', isEqualTo: fullPhone).limit(1).get();
      if (exactPhone.docs.isNotEmpty) {
        final data = exactPhone.docs.first.data();
        final hasPassword = data['hasPassword'] == true;
        final loginEmail = (data['loginEmail'] ?? '').toString().trim();
        if (hasPassword || loginEmail.isNotEmpty) return true;
      }

      final exactDigits = await users
          .where('phoneDigits', isEqualTo: fullPhoneDigitsOnly)
          .limit(1)
          .get();
      if (exactDigits.docs.isNotEmpty) {
        final data = exactDigits.docs.first.data();
        final hasPassword = data['hasPassword'] == true;
        final loginEmail = (data['loginEmail'] ?? '').toString().trim();
        if (hasPassword || loginEmail.isNotEmpty) return true;
      }

      final legacyDigits = await users
          .where('localPhoneDigits', isEqualTo: phoneDigitsOnly)
          .limit(3)
          .get();
      for (final d in legacyDigits.docs) {
        final data = d.data();
        final hasPassword = data['hasPassword'] == true;
        final loginEmail = (data['loginEmail'] ?? '').toString().trim();
        if (hasPassword || loginEmail.isNotEmpty) return true;
      }
    } catch (_) {}

    return false;
  }

  Future<bool> _emailAccountAlreadyExists(String email) async {
    try {
      final q = await FirebaseFirestore.instance
          .collection('users')
          .where('email', isEqualTo: email.trim().toLowerCase())
          .limit(1)
          .get();

      if (q.docs.isNotEmpty) {
        final data = q.docs.first.data();
        final hasPassword = data['hasPassword'] == true;
        if (hasPassword) return true;
      }
    } catch (_) {}

    return false;
  }

  Future<void> _emailSendLinkNoPasswordFirst() async {
    final email = idCtrl.text.trim().toLowerCase();
    if (!isEmail) {
      setState(() => status = "Enter valid email");
      return;
    }

    final alreadyExists = await _emailAccountAlreadyExists(email);
    if (alreadyExists) {
      setState(() => status = "Account already exists. Please Login.");
      return;
    }

    setState(() {
      sendingOtp = true;
      status = null;
    });

    try {
      debugPrint("EMAIL STEP 1: Signup email process started.");
      final auth = FirebaseAuth.instance;
      final current = auth.currentUser;

      if (current != null) {
        final currentEmail = (current.email ?? '').trim().toLowerCase();
        if (currentEmail.isNotEmpty && currentEmail != email) {
          await auth.signOut();
        }
      }

      User? user = auth.currentUser;
      debugPrint(
        "EMAIL STEP 2: Current user before creation: ${user?.uid ?? 'none'}",
      );

      if (user == null) {
        final tempPass = _randomTempPassword();
        final cred = await auth.createUserWithEmailAndPassword(
          email: email,
          password: tempPass,
        );
        user = cred.user;
      } else if ((user.email ?? '').toLowerCase() != email) {
        final tempPass = _randomTempPassword();
        final cred = await auth.createUserWithEmailAndPassword(
          email: email,
          password: tempPass,
        );
        user = cred.user;
      }

      if (user == null) {
        setState(() => status = "Could not create email account");
        return;
      }

      if (mounted) {
        setState(() {
          status = "Account created. Sending verification email...";
        });
      }

      debugPrint("EMAIL STEP 3: Sending verification email...");

      try {
        await user.sendEmailVerification().timeout(
              const Duration(seconds: 20),
            );
        debugPrint("EMAIL STEP 4: Verification email request completed.");
      } on TimeoutException {
        debugPrint("EMAIL TIMEOUT: Verification request exceeded 20 seconds.");
        if (mounted) {
          setState(() {
            status =
                "Email request timed out. Check internet and try Send Link again.";
          });
        }
        return;
      } on FirebaseAuthException catch (e) {
        debugPrint("EMAIL FIREBASE ERROR: ${e.code} ${e.message}");
        if (mounted) {
          setState(() {
            status = "Email error: ${e.code} ${e.message ?? ''}".trim();
          });
        }
        return;
      }

      if (mounted) {
        setState(() {
          status = "Email sent. Saving account information...";
        });
      }

      await _savePendingEmailState(email).timeout(
        const Duration(seconds: 10),
      );

      await ensureUserDoc(country: country).timeout(
        const Duration(seconds: 10),
      );

      await _setCountryPricingOnUserDoc(user.uid).timeout(
        const Duration(seconds: 10),
      );

      if (!mounted) return;
      setState(() {
        otpSent = true;
        otpVerified = false;
        lockId = true;
        lockDial = true;
        status =
            "Verification link sent ✅ Check email inbox/spam and click the link, then tap Verify Link.";
      });

      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(
          builder: (_) => const LoginPage(
            forceSignupMode: true,
            showEmailVerifyBlock: true,
          ),
        ),
        (r) => false,
      );
    } on FirebaseAuthException catch (e) {
      if (e.code == 'email-already-in-use') {
        setState(() => status = "Account already exists. Please Login.");
      } else if (e.code == 'operation-not-allowed') {
        setState(() => status =
            "Email/Password sign-in disabled in Firebase Console. Enable it first.");
      } else {
        setState(() => status = "Email error: ${e.code} ${e.message}");
      }
    } catch (e) {
      setState(() => status = "Email error: $e");
    } finally {
      if (mounted) setState(() => sendingOtp = false);
    }
  }

  Future<void> _emailVerifyLink() async {
    setState(() {
      verifyingOtp = true;
      status = null;
    });
    _showVerifying();

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        setState(() => status = "Please Send Link first");
        await _showFail();
        return;
      }

      await user.reload();
      final refreshed = FirebaseAuth.instance.currentUser;

      if (refreshed != null && refreshed.emailVerified) {
        await ensureUserDoc(country: country);
        await _setCountryPricingOnUserDoc(refreshed.uid);
        setState(() {
          otpVerified = true;
          lockId = true;
          lockDial = true;
          status = "Email verified ✅ Now enter password and tap Sign Up.";
        });
        await _showSuccess();
      } else {
        setState(() => status =
            "Not verified yet. Open email link from inbox/spam, then try again.");
        await _showFail();
      }
    } catch (e) {
      setState(() => status = "Verify error: $e");
      await _showFail();
    } finally {
      if (mounted) setState(() => verifyingOtp = false);
    }
  }

  Future<void> _sendPhoneOtp() async {
    if (!isPhone) {
      setState(() => status = "Enter valid phone number");
      return;
    }

    final alreadyExists = await _phoneAccountAlreadyExists();
    if (alreadyExists) {
      setState(() => status = "Account already exists. Please Login.");
      return;
    }

    setState(() {
      sendingOtp = true;
      status = null;
    });

    try {
      await FirebaseAuth.instance.verifyPhoneNumber(
        phoneNumber: fullPhone,
        timeout: const Duration(seconds: 60),
        forceResendingToken: resendToken,
        verificationCompleted: (PhoneAuthCredential credential) async {
          try {
            await FirebaseAuth.instance.signInWithCredential(credential);
            await ensureUserDoc(country: country);

            final u = FirebaseAuth.instance.currentUser;
            if (u != null) {
              await userRef(u.uid).set({
                'phone': fullPhone,
                'phoneDigits': fullPhoneDigitsOnly,
                'localPhoneDigits': phoneDigitsOnly,
                'dialCode': dialCode,
                'country': country,
                'hasPassword': false,
                'updatedAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
              await _setCountryPricingOnUserDoc(u.uid);
            }

            await _savePendingPhoneState();

            if (!mounted) return;
            setState(() {
              otpSent = true;
              otpVerified = true;
              lockId = true;
              lockDial = true;
              status = "OTP verified ✅ Now enter password and tap Sign Up.";
            });

            if (!mounted) return;
            Navigator.of(context).pushAndRemoveUntil(
              MaterialPageRoute(
                builder: (_) => const LoginPage(
                  forceSignupMode: true,
                  showSetPasswordBlock: true,
                ),
              ),
              (r) => false,
            );
          } catch (e) {
            if (mounted) {
              setState(() => status = "Auto verify failed: $e");
            }
          }
        },
        verificationFailed: (FirebaseAuthException e) {
          if (!mounted) return;

          setState(() {
            sendingOtp = false;
            status = "OTP failed: ${e.code} ${e.message ?? ''}";
          });
        },
        codeSent: (String verId, int? token) {
          if (!mounted) return;

          verificationId = verId;
          resendToken = token;

          setState(() {
            sendingOtp = false;
            otpSent = true;
            otpVerified = false;
            lockId = true;
            lockDial = true;
            status = "OTP sent ✅ Enter the code sent to $fullPhone.";
          });
        },
        codeAutoRetrievalTimeout: (String verId) {
          verificationId = verId;

          if (!mounted) return;

          setState(() {
            sendingOtp = false;
          });
        },
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        sendingOtp = false;
        status = "OTP error: $e";
      });
    }
  }

  Future<void> _verifyPhoneOtp() async {
    final otp = otpCtrl.text.trim();
    if (verificationId == null) {
      setState(() => status = "First send OTP");
      return;
    }
    if (otp.length < 4) {
      setState(() => status = "Enter valid OTP");
      return;
    }

    setState(() {
      verifyingOtp = true;
      status = null;
    });

    _showVerifying();

    try {
      final cred = PhoneAuthProvider.credential(
        verificationId: verificationId!,
        smsCode: otp,
      );

      await FirebaseAuth.instance.signInWithCredential(cred);
      await ensureUserDoc(country: country);

      final u = FirebaseAuth.instance.currentUser;
      if (u != null) {
        await userRef(u.uid).set({
          'phone': fullPhone,
          'phoneDigits': fullPhoneDigitsOnly,
          'localPhoneDigits': phoneDigitsOnly,
          'dialCode': dialCode,
          'country': country,
          'hasPassword': false,
          'updatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
        await _setCountryPricingOnUserDoc(u.uid);
      }

      await _savePendingPhoneState();

      setState(() {
        otpVerified = true;
        lockId = true;
        lockDial = true;
        status = "OTP verified ✅ Now enter password and tap Sign Up.";
      });

      await _showSuccess();

      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(
          builder: (_) => const LoginPage(
            forceSignupMode: true,
            showSetPasswordBlock: true,
          ),
        ),
        (r) => false,
      );
    } on FirebaseAuthException catch (e) {
      setState(() => status = "Verify failed: ${e.code} ${e.message}");
      await _showFail();
    } catch (e) {
      setState(() => status = "Verify failed: $e");
      await _showFail();
    } finally {
      if (mounted) setState(() => verifyingOtp = false);
    }
  }

  Future<void> _linkPhoneAliasCredential({
    required User user,
    required String password,
  }) async {
    final loginEmailNew = _phoneAliasEmail(fullPhoneDigitsOnly);
    final loginEmailOld = _phoneAliasEmailLegacy(phoneDigitsOnly);

    FirebaseAuthException? lastAuthError;

    for (final alias in [loginEmailNew, loginEmailOld]) {
      try {
        final cred =
            EmailAuthProvider.credential(email: alias, password: password);
        await user.linkWithCredential(cred);

        await userRef(user.uid).set({
          'loginEmail': alias,
          'phone': fullPhone,
          'phoneDigits': fullPhoneDigitsOnly,
          'localPhoneDigits': phoneDigitsOnly,
          'dialCode': dialCode,
          'country': country,
          'hasPassword': true,
          'passwordHash': _hash(password),
          'updatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));

        await _setCountryPricingOnUserDoc(user.uid);
        return;
      } on FirebaseAuthException catch (e) {
        lastAuthError = e;

        if (e.code == 'provider-already-linked') {
          await userRef(user.uid).set({
            'loginEmail': loginEmailNew,
            'phone': fullPhone,
            'phoneDigits': fullPhoneDigitsOnly,
            'localPhoneDigits': phoneDigitsOnly,
            'dialCode': dialCode,
            'country': country,
            'hasPassword': true,
            'passwordHash': _hash(password),
            'updatedAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _setCountryPricingOnUserDoc(user.uid);
          return;
        }

        if (e.code == 'email-already-in-use' ||
            e.code == 'credential-already-in-use') {
          continue;
        }

        rethrow;
      }
    }

    if (lastAuthError != null) throw lastAuthError;
  }

  Future<void> _finalSignup() async {
    if (!otpVerified) {
      setState(
          () => status = isEmail ? "Verify Link first" : "Verify OTP first");
      return;
    }

    if (!_passwordsValid()) {
      setState(() => status = "Passwords must match (min 6 chars)");
      return;
    }

    final p1 = passCtrl.text.trim();

    if (isEmail || widget.showEmailVerifyBlock) {
      final u = FirebaseAuth.instance.currentUser;
      if (u == null) {
        setState(() => status = "Please Send Link again");
        return;
      }

      try {
        await u.updatePassword(p1);
      } on FirebaseAuthException catch (e) {
        setState(() => status = "Set password failed: ${e.message ?? e.code}");
        return;
      }

      await ensureUserDoc(country: country);
      await _setCountryPricingOnUserDoc(u.uid);

      await userRef(u.uid).set({
        'hasPassword': true,
        'passwordHash': _hash(p1),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      await _clearPendingEmailState();
      await _setActiveSessionOnUserDoc(u.uid);

      setState(() => status = "Sign up success ✅");
      _goToVibeSelection();
      return;
    }

    final u = FirebaseAuth.instance.currentUser;
    if (u == null) {
      setState(() => status = "Please verify OTP again");
      return;
    }

    await ensureUserDoc(country: country);
    await _setCountryPricingOnUserDoc(u.uid);

    await userRef(u.uid).set({
      'phone': fullPhone,
      'phoneDigits': fullPhoneDigitsOnly,
      'localPhoneDigits': phoneDigitsOnly,
      'dialCode': dialCode,
      'country': country,
      'hasPassword': true,
      'passwordHash': _hash(p1),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    try {
      await _linkPhoneAliasCredential(user: u, password: p1);
    } on FirebaseAuthException catch (e) {
      if (mounted) {
        setState(() {
          status = "Sign up ok ✅ but password-login link failed (${e.code}).";
        });
      }
    }

    await _clearPendingPhoneState();
    await _setActiveSessionOnUserDoc(u.uid);

    setState(() => status = "Sign up success ✅");
    _goToVibeSelection();
  }

  Future<String?> _findStoredPhoneLoginEmail() async {
    try {
      final users = FirebaseFirestore.instance.collection('users');

      final exactPhoneSnap =
          await users.where('phone', isEqualTo: fullPhone).limit(1).get();
      if (exactPhoneSnap.docs.isNotEmpty) {
        final v = (exactPhoneSnap.docs.first.data()['loginEmail'] ?? '')
            .toString()
            .trim();
        if (v.isNotEmpty) return v;
      }

      final exactDigitsSnap = await users
          .where('phoneDigits', isEqualTo: fullPhoneDigitsOnly)
          .limit(1)
          .get();
      if (exactDigitsSnap.docs.isNotEmpty) {
        final v = (exactDigitsSnap.docs.first.data()['loginEmail'] ?? '')
            .toString()
            .trim();
        if (v.isNotEmpty) return v;
      }

      final legacySnap = await users
          .where('localPhoneDigits', isEqualTo: phoneDigitsOnly)
          .limit(3)
          .get();
      for (final d in legacySnap.docs) {
        final data = d.data();
        final v = (data['loginEmail'] ?? '').toString().trim();
        if (v.isNotEmpty) return v;
      }
    } catch (_) {}

    return null;
  }

  Future<UserCredential> _signInWithAnyPhoneAlias({
    required String password,
  }) async {
    final found = await _findStoredPhoneLoginEmail();

    final aliases = <String>{
      if (found != null && found.isNotEmpty) found,
      _phoneAliasEmail(fullPhoneDigitsOnly),
      _phoneAliasEmailLegacy(phoneDigitsOnly),
    }.toList();

    FirebaseAuthException? lastAuthError;

    for (final alias in aliases) {
      try {
        return await FirebaseAuth.instance.signInWithEmailAndPassword(
          email: alias,
          password: password,
        );
      } on FirebaseAuthException catch (e) {
        lastAuthError = e;
      }
    }

    throw lastAuthError ??
        FirebaseAuthException(
          code: 'user-not-found',
          message: 'Phone password login not found.',
        );
  }

  Future<void> _loginNow() async {
    final pass = passCtrl.text.trim();
    if (pass.isEmpty) {
      setState(() => status = "Enter password");
      return;
    }

    setState(() {
      emailLoading = true;
      status = null;
    });

    String friendly(FirebaseAuthException e, {String? context}) {
      switch (e.code) {
        case 'invalid-email':
          return "Invalid email format.";
        case 'user-disabled':
          return "This account is disabled.";
        case 'user-not-found':
          return context == 'phone'
              ? "Phone password login not found for this number.\nFirst do Sign Up → OTP verify → set password."
              : "No account found for this email.";
        case 'wrong-password':
          return "Wrong password. Try again.";
        case 'invalid-credential':
          return "Invalid credentials. Check email/phone and password.";
        case 'too-many-requests':
          return "Too many attempts. Try again later.";
        case 'network-request-failed':
          return "Network error. Check internet and try again.";
        case 'operation-not-allowed':
          return "Email/Password sign-in is disabled in Firebase Console.";
        default:
          return "Login error: ${e.code} ${e.message ?? ''}".trim();
      }
    }

    try {
      if (isEmail) {
        final email = idCtrl.text.trim().toLowerCase();

        await FirebaseAuth.instance.signInWithEmailAndPassword(
          email: email,
          password: pass,
        );

        final u = FirebaseAuth.instance.currentUser;
        if (u != null) {
          await u.reload();
          final refreshed = FirebaseAuth.instance.currentUser;

          if (refreshed == null) {
            setState(() => status = "Login session lost. Please try again.");
            return;
          }

          if (!refreshed.emailVerified) {
            await FirebaseAuth.instance.signOut();
            setState(() => status = "Please verify email first");
            return;
          }

          await ensureUserDoc(country: country);
          await _setCountryPricingOnUserDoc(refreshed.uid);
          await userRef(refreshed.uid).set({
            'hasPassword': true,
            'passwordHash': _hash(pass),
            'updatedAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _clearPendingEmailState();
          await _setActiveSessionOnUserDoc(refreshed.uid);
        }

        setState(() => status = "Login success ✅");
        _goHome();
        return;
      }

      if (isPhone) {
        await _signInWithAnyPhoneAlias(password: pass);
        await ensureUserDoc(country: country);

        final uid = FirebaseAuth.instance.currentUser?.uid;
        if (uid != null) {
          await userRef(uid).set({
            'phone': fullPhone,
            'phoneDigits': fullPhoneDigitsOnly,
            'localPhoneDigits': phoneDigitsOnly,
            'dialCode': dialCode,
            'country': country,
            'updatedAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _setCountryPricingOnUserDoc(uid);
          await _setActiveSessionOnUserDoc(uid);
        }

        setState(() => status = "Login success ✅");
        _goHome();
        return;
      }

      setState(() => status = "Enter valid phone number or email");
    } on FirebaseAuthException catch (e) {
      if (isPhone) {
        setState(() => status = friendly(e, context: 'phone'));
      } else {
        setState(() => status = friendly(e, context: 'email'));
      }
    } catch (e) {
      setState(() => status = "Login error: $e");
    } finally {
      if (mounted) setState(() => emailLoading = false);
    }
  }

  Widget _verifyOverlay() {
    if (_animState == _VerifyAnimState.none) {
      return const SizedBox.shrink();
    }

    Widget content;
    if (_animState == _VerifyAnimState.verifying) {
      content = AnimatedBuilder(
        animation: _heartScale,
        builder: (_, __) => Transform.scale(
          scale: _heartScale.value,
          child: const Text("❤️", style: TextStyle(fontSize: 92)),
        ),
      );
    } else if (_animState == _VerifyAnimState.success) {
      content = const Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            "🫶",
            style: TextStyle(fontSize: 92),
          ),
          SizedBox(height: 10),
          Text(
            "Verified!",
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
          ),
        ],
      );
    } else {
      content = const Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            "💔",
            style: TextStyle(fontSize: 92),
          ),
          SizedBox(height: 10),
          Text(
            "Retry",
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
          ),
        ],
      );
    }

    return Positioned.fill(
      child: Container(
        color: Colors.black.withValues(alpha: 0.60),
        child: Center(child: content),
      ),
    );
  }

  PreferredSizeWidget _topBar() {
    return AppBar(
      toolbarHeight: 78,
      backgroundColor: _bg,
      elevation: 0,
      automaticallyImplyLeading: false,
      titleSpacing: 12,
      title: Row(
        children: [
          Image.asset(
            _logoPath,
            width: kTopBarIcon,
            height: kTopBarIcon,
            fit: BoxFit.contain,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              "Earn2Love",
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: kAppBarTitle,
                fontWeight: FontWeight.w900,
                color: _purple,
              ),
            ),
          ),
        ],
      ),
      actions: [
        if (widget.showEmailVerifyBlock || widget.showSetPasswordBlock)
          TextButton(
            onPressed: () async => _hardLogout(),
            child: Text(
              "Sign Out",
              style: TextStyle(
                fontWeight: FontWeight.w900,
                fontSize: 18,
                color: _purple,
              ),
            ),
          )
        else
          TextButton(
            onPressed: () {
              setState(() {
                isLoginMode = !isLoginMode;
                otpSent = false;
                otpVerified = false;
                lockId = false;
                lockDial = false;
                verificationId = null;
                resendToken = null;
                otpCtrl.clear();
                passCtrl.clear();
                pass2Ctrl.clear();
                status = null;
              });
            },
            child: Text(
              isLoginMode ? "Sign Up" : "Login",
              style: TextStyle(
                fontWeight: FontWeight.w900,
                fontSize: 18,
                color: _purple,
              ),
            ),
          ),
        const SizedBox(width: 10),
      ],
    );
  }

  Widget _centerIcon() {
    return Center(
      child: Image.asset(
        _logoPath,
        width: kCenterIcon,
        height: kCenterIcon,
        fit: BoxFit.contain,
      ),
    );
  }

  Widget _idRow() {
    return Row(
      children: [
        SizedBox(
          width: 128,
          height: 56,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.85),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.black12),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: dialCode,
                isExpanded: true,
                alignment: Alignment.center,
                icon: const Icon(Icons.keyboard_arrow_down_rounded),
                items: _dialOptions.map((opt) {
                  final c = opt["code"]!;
                  final f = opt["flag"]!;
                  return DropdownMenuItem<String>(
                    value: c,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(f, style: const TextStyle(fontSize: 18)),
                        const SizedBox(width: 8),
                        Text(
                          c,
                          style: const TextStyle(fontWeight: FontWeight.w900),
                        ),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: lockDial
                    ? null
                    : (v) {
                        if (v == null) return;
                        setState(() {
                          dialCode = v;
                          _deriveCountryFromDial(v);
                        });
                      },
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: SizedBox(
            height: 56,
            child: TextField(
              controller: idCtrl,
              enabled: !lockId,
              decoration: InputDecoration(
                hintText: "Phone number / Email",
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.85),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 16,
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(color: Colors.black12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(color: _purple, width: 1.2),
                ),
              ),
              onChanged: (_) {
                if (lockId) return;
                setState(() {
                  otpSent = false;
                  otpVerified = false;
                  verificationId = null;
                  status = null;
                });
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _otpRow() {
    final rightText = isEmail
        ? (!otpSent
            ? (sendingOtp ? "Sending..." : "Send Link")
            : (!otpVerified
                ? (verifyingOtp ? "Checking..." : "Verify Link")
                : "Verified"))
        : (!otpSent
            ? (sendingOtp ? "Sending..." : "Send OTP")
            : (!otpVerified
                ? (verifyingOtp ? "Verifying..." : "Verify OTP")
                : "Verified"));

    return SizedBox(
      height: 56,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: otpCtrl,
              enabled: !isEmail && otpSent && !otpVerified,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                hintText: isEmail ? "Check email link" : "Enter OTP",
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.85),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 16,
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: const BorderSide(color: Colors.black12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(color: _purple, width: 1.2),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 140,
            height: 56,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: _purple,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                  side: const BorderSide(color: Colors.black12),
                ),
                textStyle: const TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 16,
                ),
              ),
              onPressed: (sendingOtp || verifyingOtp || otpVerified)
                  ? null
                  : () async {
                      if (!isEmail && !isPhone) {
                        setState(
                          () => status = "Enter valid phone number or email",
                        );
                        return;
                      }

                      if (isEmail) {
                        if (!otpSent) {
                          await _emailSendLinkNoPasswordFirst();
                        } else {
                          await _emailVerifyLink();
                        }
                      } else {
                        if (!otpSent) {
                          await _sendPhoneOtp();
                        } else {
                          await _verifyPhoneOtp();
                        }
                      }
                    },
              child: Text(rightText),
            ),
          ),
        ],
      ),
    );
  }

  Widget _roundedField({
    required TextEditingController controller,
    required String hint,
    bool obscure = false,
  }) {
    return SizedBox(
      height: 56,
      child: TextField(
        controller: controller,
        obscureText: obscure,
        decoration: InputDecoration(
          hintText: hint,
          filled: true,
          fillColor: Colors.white.withValues(alpha: 0.85),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 14,
            vertical: 16,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Colors.black12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide(color: _purple, width: 1.2),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasError = (status ?? "").toLowerCase().contains("fail") ||
        (status ?? "").toLowerCase().contains("error");

    return Scaffold(
      backgroundColor: _bg,
      appBar: _topBar(),
      body: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.fromLTRB(18, 6, 18, 20),
            children: [
              Text(
                isLoginMode ? "Login" : "Sign Up",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: kPageTitle,
                  fontWeight: FontWeight.w900,
                  color: _purple,
                  height: 1.0,
                ),
              ),
              const SizedBox(height: 2),
              _centerIcon(),
              const SizedBox(height: 6),
              _idRow(),
              const SizedBox(height: 12),
              if (!isLoginMode) ...[
                _otpRow(),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.only(left: 2, top: 0),
                      minimumSize: const Size(0, 24),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    onPressed: (sendingOtp || verifyingOtp || otpVerified)
                        ? null
                        : () async {
                            if (!otpSent) return;
                            if (isEmail) {
                              await _emailSendLinkNoPasswordFirst();
                            } else {
                              await _sendPhoneOtp();
                            }
                          },
                    child: Text(
                      isEmail ? "Resend Link" : "Resend",
                      style: const TextStyle(fontWeight: FontWeight.w900),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                _roundedField(
                  controller: passCtrl,
                  hint: "Enter new password",
                  obscure: true,
                ),
                const SizedBox(height: 12),
                _roundedField(
                  controller: pass2Ctrl,
                  hint: "Re-enter new password",
                  obscure: true,
                ),
                const SizedBox(height: 16),
                SizedBox(
                  height: 60,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _green,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(18),
                      ),
                      textStyle: const TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 20,
                      ),
                    ),
                    onPressed: emailLoading ? null : _finalSignup,
                    child: Text(emailLoading ? "Please wait..." : "Sign Up"),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  "Country: ${_optForCode(dialCode)['name']}",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.grey.shade700,
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                  ),
                ),
              ] else ...[
                _roundedField(
                  controller: passCtrl,
                  hint: "Enter your password",
                  obscure: true,
                ),
                const SizedBox(height: 14),
                SizedBox(
                  height: 60,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _purple,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(18),
                      ),
                      textStyle: const TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 20,
                      ),
                    ),
                    onPressed: emailLoading ? null : _loginNow,
                    child: Text(emailLoading ? "Please wait..." : "Login"),
                  ),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const ResetPasswordPage(),
                        ),
                      );
                    },
                    child: const Text(
                      "Forgot password?",
                      style: TextStyle(fontWeight: FontWeight.w900),
                    ),
                  ),
                ),
              ],
              if (status != null) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: hasError ? Colors.red.shade50 : Colors.green.shade50,
                    border: Border.all(
                      color: hasError
                          ? Colors.red.shade200
                          : Colors.green.shade200,
                    ),
                  ),
                  child: Text(
                    status!,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      color: hasError ? Colors.red : Colors.green.shade800,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 20),
            ],
          ),
          _verifyOverlay(),
        ],
      ),
    );
  }
}
