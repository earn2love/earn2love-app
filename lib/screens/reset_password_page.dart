import 'dart:convert';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:country_picker/country_picker.dart';
import 'package:crypto/crypto.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ResetPasswordPage extends StatefulWidget {
  const ResetPasswordPage({super.key});

  @override
  State<ResetPasswordPage> createState() => _ResetPasswordPageState();
}

class _ResetPasswordPageState extends State<ResetPasswordPage> {
  final idCtrl = TextEditingController();
  final otpCtrl = TextEditingController();
  final passCtrl = TextEditingController();
  final pass2Ctrl = TextEditingController();

  Country? selectedCountry;

  bool otpSent = false;
  bool otpVerified = false;
  bool busy = false;

  String? verificationId;
  int? resendToken;

  // ---- same sizes (as requested) ----
  static const double _appBarIcon = 42;
  static const double _appBarTitle = 38;
  static const double _centerIcon = 240;
  static const double _pageTitle = 34;

  String get dialCode => '+${selectedCountry?.phoneCode ?? '44'}';

  bool get isEmail {
    final t = idCtrl.text.trim();
    return RegExp(r"^[^\s@]+@[^\s@]+\.[^\s@]+$").hasMatch(t);
  }

  bool get isPhone {
    final t = idCtrl.text.trim();
    final digits = t.replaceAll(RegExp(r'[^0-9]'), '');
    return digits.length >= 8 && RegExp(r"^[0-9+\s-]+$").hasMatch(t);
  }

  String get phoneDigitsOnly =>
      idCtrl.text.trim().replaceAll(RegExp(r'[^0-9]'), '');
  String get fullPhone => '$dialCode$phoneDigitsOnly';

  String _hash(String s) => sha256.convert(utf8.encode(s)).toString();

  DocumentReference<Map<String, dynamic>> userRef(String uid) =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  @override
  void dispose() {
    idCtrl.dispose();
    otpCtrl.dispose();
    passCtrl.dispose();
    pass2Ctrl.dispose();
    super.dispose();
  }

  void _toast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  InputDecoration _decor(String hint) {
    return InputDecoration(
      hintText: hint,
      filled: true,
      fillColor: Colors.white.withOpacity(0.85),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: Colors.black12),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: Color(0xFF6C4AA3), width: 1.3),
      ),
    );
  }

  Future<void> sendOtpOrLink() async {
    final id = idCtrl.text.trim();
    if (id.isEmpty) {
      _toast('Enter phone number or email');
      return;
    }

    setState(() => busy = true);
    try {
      if (isEmail) {
        await FirebaseAuth.instance.sendPasswordResetEmail(email: id);
        _toast('Reset link sent ✅ Check email');
        // direct go login
        if (mounted) Navigator.of(context).pop();
        return;
      }

      if (!isPhone) {
        _toast('Enter valid phone number');
        return;
      }

      await FirebaseAuth.instance.verifyPhoneNumber(
        phoneNumber: fullPhone,
        timeout: const Duration(seconds: 60),
        forceResendingToken: resendToken,
        verificationCompleted: (PhoneAuthCredential credential) async {
          await FirebaseAuth.instance.signInWithCredential(credential);
          if (!mounted) return;
          setState(() {
            otpSent = true;
            otpVerified = true;
          });
          _toast('Verified automatically ✅');
        },
        verificationFailed: (FirebaseAuthException e) {
          _toast('OTP failed: ${e.message ?? e.code}');
        },
        codeSent: (String verId, int? token) {
          verificationId = verId;
          resendToken = token;
          otpCtrl.clear();
          setState(() {
            otpSent = true;
            otpVerified = false;
          });
          _toast('OTP sent ✅');
        },
        codeAutoRetrievalTimeout: (String verId) {
          verificationId = verId;
        },
      );
    } catch (e) {
      _toast('Error: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> verifyOtp() async {
    if (verificationId == null) {
      _toast('First send OTP');
      return;
    }
    final code = otpCtrl.text.trim();
    if (code.length < 4) {
      _toast('Enter valid OTP');
      return;
    }

    setState(() => busy = true);
    try {
      final cred = PhoneAuthProvider.credential(
        verificationId: verificationId!,
        smsCode: code,
      );
      await FirebaseAuth.instance.signInWithCredential(cred);
      setState(() => otpVerified = true);
      _toast('OTP verified ✅');
    } on FirebaseAuthException catch (e) {
      _toast('Verify failed: ${e.message ?? e.code}');
    } catch (e) {
      _toast('Error: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> resetPassword() async {
    // Email reset happens via link; for phone we set hash
    if (isEmail) {
      _toast('Check your email reset link');
      Navigator.of(context).pop();
      return;
    }

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

    final u = FirebaseAuth.instance.currentUser;
    if (u == null) {
      _toast('Please verify OTP again');
      return;
    }

    setState(() => busy = true);
    try {
      await userRef(u.uid).set({
        'hasPassword': true,
        'passwordHash': _hash(p1),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      _toast('Password reset successful ✅');
      await FirebaseAuth.instance.signOut();
      if (mounted) Navigator.of(context).pop(); // back to login
    } catch (e) {
      _toast('Error: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    const bg = Color(0xFFF8F2FF);
    const purple = Color(0xFF6C4AA3);
    const green = Color(0xFF7FAE7D);

    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        backgroundColor: bg,
        elevation: 0,
        titleSpacing: 16,
        title: Row(
          children: [
            Image.asset('assets/images/earn2love_icon.png',
                width: _appBarIcon, height: _appBarIcon),
            const SizedBox(width: 10),
            const Text(
              'Earn2Love',
              style: TextStyle(
                  fontSize: _appBarTitle,
                  fontWeight: FontWeight.w900,
                  color: purple),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: busy ? null : () => Navigator.of(context).pop(),
            child: const Text('Login',
                style: TextStyle(
                    color: purple, fontWeight: FontWeight.w900, fontSize: 16)),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 22),
          children: [
            const Text(
              'Reset Password',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: _pageTitle,
                  fontWeight: FontWeight.w900,
                  color: purple),
            ),
            const SizedBox(height: 14),

            Center(
              child: Image.asset(
                'assets/images/earn2love_icon.png',
                width: _centerIcon,
                height: _centerIcon,
                fit: BoxFit.contain,
              ),
            ),

            const SizedBox(height: 18),

            Row(
              children: [
                SizedBox(
                  width: 120,
                  height: 56,
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
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.85),
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
                            style: const TextStyle(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(width: 4),
                          const Icon(Icons.keyboard_arrow_down_rounded),
                        ],
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
                      enabled: !busy,
                      decoration: _decor('Phone number / Email'),
                      onChanged: (_) {
                        setState(() {
                          otpSent = false;
                          otpVerified = false;
                          verificationId = null;
                        });
                      },
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 14),

            // OTP row only for phone
            if (!isEmail) ...[
              SizedBox(
                height: 56,
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: otpCtrl,
                        enabled: !busy && otpSent,
                        keyboardType: TextInputType.number,
                        decoration: _decor('Enter OTP'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 140,
                      height: 56,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: purple,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                            side: const BorderSide(color: Colors.black12),
                          ),
                          textStyle: const TextStyle(
                              fontWeight: FontWeight.w900, fontSize: 16),
                        ),
                        onPressed: busy
                            ? null
                            : () async {
                                if (!otpSent) {
                                  await sendOtpOrLink();
                                } else if (!otpVerified) {
                                  await verifyOtp();
                                }
                              },
                        child: Text(!otpSent
                            ? 'Send OTP'
                            : (!otpVerified ? 'Verify OTP' : 'Verified')),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                  height: 56,
                  child: TextField(
                      controller: passCtrl,
                      enabled: !busy,
                      obscureText: true,
                      decoration: _decor('Enter new password'))),
              const SizedBox(height: 12),
              SizedBox(
                  height: 56,
                  child: TextField(
                      controller: pass2Ctrl,
                      enabled: !busy,
                      obscureText: true,
                      decoration: _decor('Re-enter new password'))),
              const SizedBox(height: 16),
              SizedBox(
                height: 60,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: green,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(18)),
                    textStyle: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 18),
                  ),
                  onPressed: busy ? null : resetPassword,
                  child: const Text('Reset Password'),
                ),
              ),
            ] else ...[
              SizedBox(
                height: 60,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: green,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(18)),
                    textStyle: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 18),
                  ),
                  onPressed: busy ? null : sendOtpOrLink,
                  child: Text(busy ? 'Please wait...' : 'Send Reset Link'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
