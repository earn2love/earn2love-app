import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:country_picker/country_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'auth_gate.dart';
import 'reset_password_page.dart';

enum AuthMode { signup, login }

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  static const _kPendingPhoneDigits = "pendingPhoneDigits";
  static const _kPendingDial = "pendingDialCode";
  static const _kPendingOtpVerified = "pendingOtpVerified";
  static const _kPendingEmail = "pendingEmail";
  static const _kPendingEmailLinkSent = "pendingEmailLinkSent";

  AuthMode mode = AuthMode.signup;

  final idCtrl = TextEditingController();
  final otpCtrl = TextEditingController();
  final passCtrl = TextEditingController();
  final pass2Ctrl = TextEditingController();

  Country? selectedCountry;

  bool otpSent = false;
  bool otpVerified = false;
  bool busy = false;

  String? _verificationId;
  int? _resendToken;

  @override
  void dispose() {
    idCtrl.dispose();
    otpCtrl.dispose();
    passCtrl.dispose();
    pass2Ctrl.dispose();
    super.dispose();
  }

  bool get isEmail {
    final t = idCtrl.text.trim();
    return t.contains('@') && t.contains('.');
  }

  String get phoneE164 {
    final cc = selectedCountry?.phoneCode ?? '44';
    final raw = idCtrl.text.trim().replaceAll(' ', '');
    if (raw.startsWith('+')) return raw;
    return '+$cc$raw';
  }

  void _toast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg)),
    );
  }

  Future<void> _clearPendingPrefs() async {
    final sp = await SharedPreferences.getInstance();
    await sp.remove(_kPendingPhoneDigits);
    await sp.remove(_kPendingDial);
    await sp.remove(_kPendingOtpVerified);
    await sp.remove(_kPendingEmail);
    await sp.remove(_kPendingEmailLinkSent);
  }

  Future<void> _ensureUserDoc({
    required User user,
    required String loginType,
  }) async {
    final ref = FirebaseFirestore.instance.collection('users').doc(user.uid);

    await ref.set(
      {
        'uid': user.uid,
        'email': user.email,
        'phoneNumber': user.phoneNumber,
        'loginType': loginType,
        'createdAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
        'silverCoins': 0,
        'goldCoins': 0,
        'diamondCoins': 0,
        'tier': null,
        'subTier': null,
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
      },
      SetOptions(merge: true),
    );
  }

  Future<void> sendOtp() async {
    final id = idCtrl.text.trim();
    if (id.isEmpty) {
      _toast('Enter phone number or email');
      return;
    }

    setState(() => busy = true);

    try {
      if (isEmail) {
        setState(() {
          otpSent = true;
        });
        _toast('Email OTP: Coming soon. Use phone OTP for now.');
      } else {
        await FirebaseAuth.instance.verifyPhoneNumber(
          phoneNumber: phoneE164,
          timeout: const Duration(seconds: 60),
          forceResendingToken: _resendToken,
          verificationCompleted: (PhoneAuthCredential credential) async {
            try {
              await FirebaseAuth.instance.signInWithCredential(credential);
              setState(() {
                otpSent = true;
                otpVerified = true;
              });
              _toast('OTP verified');
            } catch (_) {}
          },
          verificationFailed: (FirebaseAuthException e) {
            _toast(e.message ?? 'OTP failed');
          },
          codeSent: (String verificationId, int? resendToken) {
            setState(() {
              _verificationId = verificationId;
              _resendToken = resendToken;
              otpSent = true;
            });
            _toast('OTP sent');
          },
          codeAutoRetrievalTimeout: (String verificationId) {
            _verificationId = verificationId;
          },
        );
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> verifyOtp() async {
    if (!otpSent) return;

    if (isEmail) {
      if (otpCtrl.text.trim().isEmpty) {
        _toast('Enter OTP');
        return;
      }
      setState(() {
        otpVerified = true;
      });
      _toast('Verified (stub)');
      return;
    }

    final code = otpCtrl.text.trim();
    if (code.isEmpty) {
      _toast('Enter OTP');
      return;
    }
    if (_verificationId == null) {
      _toast('Please send OTP again');
      return;
    }

    setState(() => busy = true);
    try {
      final cred = PhoneAuthProvider.credential(
        verificationId: _verificationId!,
        smsCode: code,
      );
      await FirebaseAuth.instance.signInWithCredential(cred);

      setState(() {
        otpVerified = true;
      });
      _toast('OTP verified');
    } on FirebaseAuthException catch (e) {
      _toast(e.message ?? 'Invalid OTP');
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> signup() async {
    if (!otpVerified) {
      _toast('Verify OTP first');
      return;
    }

    final p1 = passCtrl.text.trim();
    final p2 = pass2Ctrl.text.trim();

    if (p1.length < 6) {
      _toast('Password must be at least 6 characters');
      return;
    }
    if (p1 != p2) {
      _toast('Passwords do not match');
      return;
    }

    setState(() => busy = true);

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        _toast('User not found. Please verify OTP again.');
        return;
      }

      await _ensureUserDoc(
        user: user,
        loginType: isEmail ? 'email' : 'phone',
      );

      await _clearPendingPrefs();

      if (!mounted) return;
      _toast('Sign up success');

      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const AuthGate()),
        (route) => false,
      );
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> login() async {
    final id = idCtrl.text.trim();
    final pw = passCtrl.text;

    if (id.isEmpty) {
      _toast('Enter phone number or email');
      return;
    }
    if (pw.isEmpty) {
      _toast('Enter password');
      return;
    }

    setState(() => busy = true);
    try {
      if (isEmail) {
        final cred = await FirebaseAuth.instance.signInWithEmailAndPassword(
          email: id,
          password: pw,
        );

        final user = cred.user;
        if (user != null) {
          await _ensureUserDoc(user: user, loginType: 'email');
        }

        await _clearPendingPrefs();

        if (!mounted) return;
        _toast('Login success');

        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const AuthGate()),
          (route) => false,
        );
      } else {
        _toast(
            'Phone+Password login not supported. Use OTP login or email login.');
      }
    } on FirebaseAuthException catch (e) {
      _toast(e.message ?? 'Login failed');
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isSignup = mode == AuthMode.signup;

    const bg = Color(0xFFF8F2FF);
    const purple = Color(0xFF6C4AA3);
    const green = Color(0xFF7FAE7D);

    const titleStyle = TextStyle(
      fontSize: 34,
      fontWeight: FontWeight.w800,
    );

    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        backgroundColor: bg,
        elevation: 0,
        titleSpacing: 16,
        title: Row(
          children: [
            Image.asset(
              'assets/images/earn2love_icon.png',
              width: 26,
              height: 26,
            ),
            const SizedBox(width: 10),
            ShaderMask(
              shaderCallback: (rect) {
                return const LinearGradient(
                  colors: [Color(0xFF7B4EFF), Color(0xFFFF4FB6)],
                ).createShader(rect);
              },
              child: const Text(
                'Earn2Love',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: busy
                ? null
                : () {
                    setState(() {
                      mode = isSignup ? AuthMode.login : AuthMode.signup;
                      otpSent = false;
                      otpVerified = false;
                      otpCtrl.clear();
                      passCtrl.clear();
                      pass2Ctrl.clear();
                    });
                  },
            child: Text(
              isSignup ? 'Login' : 'Sign Up',
              style: const TextStyle(
                color: purple,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 20),
          child: Column(
            children: [
              const SizedBox(height: 10),
              Text(
                isSignup ? 'Sign Up' : 'Login',
                style: titleStyle.copyWith(color: purple),
              ),
              const SizedBox(height: 18),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 18),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.55),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: Colors.black12),
                ),
                child: Center(
                  child: Image.asset(
                    'assets/images/earn2love_icon.png',
                    width: 120,
                    height: 120,
                    fit: BoxFit.contain,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    flex: 1,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: busy
                          ? null
                          : () {
                              showCountryPicker(
                                context: context,
                                showPhoneCode: true,
                                onSelect: (c) =>
                                    setState(() => selectedCountry = c),
                              );
                            },
                      child: Container(
                        height: 54,
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: Colors.black12),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(selectedCountry?.flagEmoji ?? '🇬🇧'),
                            const SizedBox(width: 6),
                            Text(
                              '+${selectedCountry?.phoneCode ?? '44'}',
                              style:
                                  const TextStyle(fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(width: 6),
                            const Icon(Icons.keyboard_arrow_down_rounded),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    flex: 4,
                    child: Container(
                      height: 54,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: Colors.black12),
                      ),
                      child: Center(
                        child: TextField(
                          controller: idCtrl,
                          enabled: !busy,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            border: InputBorder.none,
                            hintText: 'Phone number / Email',
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (isSignup) ...[
                Container(
                  height: 54,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.black12),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 14),
                          child: TextField(
                            controller: otpCtrl,
                            enabled: !busy,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              border: InputBorder.none,
                              hintText: 'Enter OTP',
                            ),
                          ),
                        ),
                      ),
                      Container(
                        height: 54,
                        width: 130,
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.only(
                            topRight: Radius.circular(14),
                            bottomRight: Radius.circular(14),
                          ),
                          border: Border(
                            left: BorderSide(color: Colors.black12),
                          ),
                        ),
                        child: TextButton(
                          onPressed: busy
                              ? null
                              : () async {
                                  if (!otpSent) {
                                    await sendOtp();
                                  } else if (!otpVerified) {
                                    await verifyOtp();
                                  }
                                },
                          child: Text(
                            !otpSent
                                ? 'Send OTP'
                                : (!otpVerified ? 'Verify OTP' : 'Verified'),
                            style: const TextStyle(
                              color: purple,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    style: TextButton.styleFrom(
                        padding: const EdgeInsets.only(left: 4)),
                    onPressed: busy ? null : () async => sendOtp(),
                    child: const Text('Resend'),
                  ),
                ),
                const SizedBox(height: 4),
                if (otpVerified) ...[
                  _roundedField(
                    controller: passCtrl,
                    hint: 'Enter new password',
                    obscure: true,
                    enabled: !busy,
                  ),
                  const SizedBox(height: 10),
                  _roundedField(
                    controller: pass2Ctrl,
                    hint: 'Re-enter new password',
                    obscure: true,
                    enabled: !busy,
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: green,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      onPressed: busy ? null : signup,
                      child: const Text(
                        'Sign Up',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w800),
                      ),
                    ),
                  ),
                ] else ...[
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: green.withValues(alpha: 0.35),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      onPressed: null,
                      child: const Text(
                        'Sign Up',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w800),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 10),
                Text(
                  'Country: ${selectedCountry?.name ?? 'United Kingdom'}',
                  style: TextStyle(color: Colors.black.withValues(alpha: 0.55)),
                ),
              ] else ...[
                _roundedField(
                  controller: passCtrl,
                  hint: 'Enter your password',
                  obscure: true,
                  enabled: !busy,
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: purple,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    onPressed: busy ? null : login,
                    child: const Text(
                      'Login',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: busy
                        ? null
                        : () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => const ResetPasswordPage(),
                              ),
                            );
                          },
                    child: const Text('Forgot password?'),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _roundedField({
    required TextEditingController controller,
    required String hint,
    required bool enabled,
    bool obscure = false,
  }) {
    return Container(
      height: 54,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.black12),
      ),
      child: Center(
        child: TextField(
          controller: controller,
          enabled: enabled,
          obscureText: obscure,
          decoration: InputDecoration(
            border: InputBorder.none,
            hintText: hint,
          ),
        ),
      ),
    );
  }
}
