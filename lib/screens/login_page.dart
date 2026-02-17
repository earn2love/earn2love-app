import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

enum _VerifyAnimState { none, verifying, success, fail }

class _LoginPageState extends State<LoginPage>
    with SingleTickerProviderStateMixin {
  // 0=Phone, 1=Email
  int tabIndex = 0;

  // Phone
  final phoneCtrl = TextEditingController();
  final otpCtrl = TextEditingController();
  bool sendingOtp = false;
  bool verifyingOtp = false;

  String dialCode = "+91";
  String country = "IN"; // derived
  String? verificationId;
  int? resendToken;

  // Email
  final emailCtrl = TextEditingController();
  final passCtrl = TextEditingController();
  bool emailLoading = false;
  bool emailIsLogin = true;

  String? status;

  // Verify overlay animation
  _VerifyAnimState _animState = _VerifyAnimState.none;
  late final AnimationController _heartCtrl;
  late final Animation<double> _heartScale;

  DocumentReference<Map<String, dynamic>> userRef(String uid) =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  // Dial code options (Phase-1: few popular)
  static const _dialOptions = <Map<String, String>>[
    {"flag": "🇮🇳", "code": "+91", "short": "IN", "name": "India"},
    {"flag": "🇬🇧", "code": "+44", "short": "UK", "name": "United Kingdom"},
    {"flag": "🇺🇸", "code": "+1", "short": "US", "name": "United States"},
    {"flag": "🇦🇺", "code": "+61", "short": "AU", "name": "Australia"},
    {"flag": "🇦🇪", "code": "+971", "short": "UAE", "name": "UAE"},
  ];

  @override
  void initState() {
    super.initState();
    _initLocal();

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
  }

  @override
  void dispose() {
    phoneCtrl.dispose();
    otpCtrl.dispose();
    emailCtrl.dispose();
    passCtrl.dispose();
    _heartCtrl.dispose();
    super.dispose();
  }

  Future<void> _initLocal() async {
    final sp = await SharedPreferences.getInstance();
    final savedDial = sp.getString("selectedDialCode");
    if (savedDial != null) dialCode = savedDial;
    _deriveCountryFromDial(dialCode);
    if (mounted) setState(() {});
  }

  Map<String, String> _optForCode(String code) {
    for (final o in _dialOptions) {
      if (o["code"] == code) return o;
    }
    return const {
      "flag": "🌍",
      "code": "+0",
      "short": "OTHER",
      "name": "Other"
    };
  }

  void _deriveCountryFromDial(String code) {
    final o = _optForCode(code);
    dialCode = code;
    country = o["short"] ?? "OTHER";

    SharedPreferences.getInstance().then((sp) {
      sp.setString("selectedDialCode", code);
      sp.setString("selectedCountry", country);
    });
  }

  String get fullPhone {
    final raw = phoneCtrl.text.trim().replaceAll(" ", "");
    final digitsOnly = raw.replaceAll(RegExp(r'[^0-9]'), '');
    return "$dialCode$digitsOnly";
  }

  // ---------------- FIRESTORE USER DOC ----------------
  Future<void> ensureUserDoc({required String country}) async {
    final user = FirebaseAuth.instance.currentUser!;
    final ref = userRef(user.uid);

    final snap = await ref.get();

    if (!snap.exists) {
      const defaultAppLang = "en";
      final defaultMatchLang = (country == "IN") ? "te" : "en";

      await ref.set({
        'uid': user.uid,
        'phone': user.phoneNumber,
        'email': user.email,
        'createdAt': FieldValue.serverTimestamp(),

        'displayName': '',
        'bio': '',
        'photoUrls': [],

        // wallets
        'silverBalance': 0,
        'goldBalance': 0,
        'diamondBalance': 0,

        // country + language
        'country': country,
        'appLanguage': defaultAppLang,
        'matchLanguage': defaultMatchLang,

        // streak
        'streakDays': 0,
        'streakBonusPct': 0,
        'streakLastDate': '',

        // moderation
        'freezeUntil': null,

        'isPremium': false,
      });
    } else {
      await ref.set({
        'country': country,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }

    // defaults for old users too (avoid null/type crash)
    await ref.set({
      'silverBalance': FieldValue.increment(0),
      'goldBalance': FieldValue.increment(0),
      'diamondBalance': FieldValue.increment(0),
      'streakDays': FieldValue.increment(0),
      'streakBonusPct': FieldValue.increment(0),
      'country': country,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  // ---------------- VERIFY OVERLAY HELPERS ----------------
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

  // ---------------- PHONE OTP ----------------
  Future<void> sendOtp() async {
    final raw = phoneCtrl.text.trim();
    if (raw.isEmpty) {
      setState(() => status = "Enter phone number");
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
          // Auto verified
          await FirebaseAuth.instance.signInWithCredential(credential);
          await ensureUserDoc(country: country);
          if (!mounted) return;
          setState(() => status = "Verified automatically ✅");
        },
        verificationFailed: (FirebaseAuthException e) {
          setState(() => status = "OTP failed: ${e.code} ${e.message}");
        },
        codeSent: (String verId, int? token) {
          verificationId = verId;
          resendToken = token;
          otpCtrl.clear();
          if (!mounted) return;
          setState(() => status = "OTP sent ✅");
        },
        codeAutoRetrievalTimeout: (String verId) {
          verificationId = verId;
        },
      );
    } catch (e) {
      setState(() => status = "$e");
    } finally {
      if (mounted) setState(() => sendingOtp = false);
    }
  }

  Future<void> verifyOtp() async {
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

      if (!mounted) return;

      setState(() => status = "Login success ✅");
      await _showSuccess();
      // AuthGate will route to AppShell automatically
    } on FirebaseAuthException catch (e) {
      if (!mounted) return;
      setState(() => status = "Verify failed: ${e.code} ${e.message}");
      await _showFail();
    } catch (e) {
      if (!mounted) return;
      setState(() => status = "Verify failed: $e");
      await _showFail();
    } finally {
      if (mounted) setState(() => verifyingOtp = false);
    }
  }

  // ---------------- EMAIL/PASSWORD ----------------
  Future<void> emailSubmit() async {
    final email = emailCtrl.text.trim();
    final pass = passCtrl.text.trim();

    if (email.isEmpty || pass.isEmpty) {
      setState(() => status = "Enter email & password");
      return;
    }

    setState(() {
      emailLoading = true;
      status = null;
    });

    try {
      if (emailIsLogin) {
        await FirebaseAuth.instance
            .signInWithEmailAndPassword(email: email, password: pass);
      } else {
        await FirebaseAuth.instance
            .createUserWithEmailAndPassword(email: email, password: pass);
      }

      await ensureUserDoc(country: country);

      if (!mounted) return;
      setState(() => status =
          emailIsLogin ? "Email login success ✅" : "Account created ✅");
    } on FirebaseAuthException catch (e) {
      if (!mounted) return;
      setState(() => status = "Email error: ${e.code} ${e.message}");
    } catch (e) {
      if (!mounted) return;
      setState(() => status = "Email error: $e");
    } finally {
      if (mounted) setState(() => emailLoading = false);
    }
  }

  // ---------------- UI (PHONE) ----------------
  Widget _phoneRowCombined() {
    final o = _optForCode(dialCode);
    final _flag = o["flag"] ?? "🌍";
    final _code = o["code"] ?? dialCode;

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.grey.shade300),
        color: Colors.white,
      ),
      child: Row(
        children: [
          // LEFT: small country code box
          SizedBox(
            width: 120, // ✅ small
            child: Padding(
              padding: const EdgeInsets.only(left: 10, right: 6),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: dialCode,
                  isExpanded: true,
                  icon: const Icon(Icons.keyboard_arrow_down),
                  items: _dialOptions.map((opt) {
                    final c = opt["code"]!;
                    final f = opt["flag"]!;
                    return DropdownMenuItem<String>(
                      value: c,
                      child: Text(
                        "$f $c",
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                    );
                  }).toList(),
                  onChanged: (v) {
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

          // divider
          Container(width: 1, height: 52, color: Colors.grey.shade300),

          // RIGHT: big phone number box
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(left: 12, right: 12),
              child: TextField(
                controller: phoneCtrl,
                keyboardType: TextInputType.phone,
                decoration: InputDecoration(
                  border: InputBorder.none,
                  hintText: "Phone number",
                  hintStyle: TextStyle(color: Colors.grey.shade500),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _phoneTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _phoneRowCombined(),
        const SizedBox(height: 12),
        ElevatedButton(
          onPressed: sendingOtp ? null : sendOtp,
          child: Text(sendingOtp ? "Sending..." : "Send OTP"),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: otpCtrl,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: "Enter OTP",
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 10),
        ElevatedButton(
          onPressed:
              (verifyingOtp || verificationId == null) ? null : verifyOtp,
          child: Text(verifyingOtp ? "Verifying..." : "Verify & Continue"),
        ),
        const SizedBox(height: 8),
        Text(
          "Selected: ${_optForCode(dialCode)['flag']} $dialCode",
          textAlign: TextAlign.center,
          style: TextStyle(
              color: Colors.grey.shade700,
              fontWeight: FontWeight.w700,
              fontSize: 12),
        ),
      ],
    );
  }

  // ---------------- UI (EMAIL) ----------------
  Widget _emailTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: emailLoading
                    ? null
                    : () => setState(() => emailIsLogin = true),
                child: Text(emailIsLogin ? "Login ✅" : "Login"),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: OutlinedButton(
                onPressed: emailLoading
                    ? null
                    : () => setState(() => emailIsLogin = false),
                child: Text(!emailIsLogin ? "Signup ✅" : "Signup"),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        TextField(
          controller: emailCtrl,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            labelText: "Email",
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: passCtrl,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: "Password",
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        ElevatedButton(
          onPressed: emailLoading ? null : emailSubmit,
          child: Text(emailLoading
              ? "Please wait..."
              : (emailIsLogin ? "Login" : "Create account")),
        ),
      ],
    );
  }

  Widget _verifyOverlay() {
    if (_animState == _VerifyAnimState.none) return const SizedBox.shrink();

    Widget content;
    if (_animState == _VerifyAnimState.verifying) {
      content = AnimatedBuilder(
        animation: _heartScale,
        builder: (_, __) {
          return Transform.scale(
            scale: _heartScale.value,
            child: const Text("❤️", style: TextStyle(fontSize: 92)),
          );
        },
      );
    } else if (_animState == _VerifyAnimState.success) {
      content = const Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text("🫶", style: TextStyle(fontSize: 92)),
          SizedBox(height: 10),
          Text("Verified!",
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
        ],
      );
    } else {
      content = const Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text("💔", style: TextStyle(fontSize: 92)),
          SizedBox(height: 10),
          Text("Retry",
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
        ],
      );
    }

    return Positioned.fill(
      child: Container(
        color: Colors.black.withOpacity(0.60),
        child: Center(child: content),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasError = (status ?? "").toLowerCase().contains("fail") ||
        (status ?? "").toLowerCase().contains("error");

    return Scaffold(
      appBar: AppBar(title: const Text("Earn2Love - Login")),
      body: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const SizedBox(height: 6),
              const Text(
                "Login / Signup",
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 4),
              Text(
                "Phone OTP or Email/Password",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade700),
              ),
              const SizedBox(height: 16),
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 0, label: Text("Phone")),
                  ButtonSegment(value: 1, label: Text("Email")),
                ],
                selected: {tabIndex},
                onSelectionChanged: (s) {
                  setState(() {
                    tabIndex = s.first;
                    status = null;
                  });
                },
              ),
              const SizedBox(height: 16),
              if (tabIndex == 0) _phoneTab() else _emailTab(),
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
                      fontWeight: FontWeight.w800,
                      color: hasError ? Colors.red : Colors.green.shade800,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 20),
            ],
          ),

          // overlay animation (verify)
          _verifyOverlay(),
        ],
      ),
    );
  }
}
