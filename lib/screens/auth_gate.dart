import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../app_shell.dart';
import 'login_page.dart';
import 'vibe_selection_page.dart';

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  static const _kPendingPhoneDigits = "pendingPhoneDigits";
  static const _kPendingDial = "pendingDialCode";
  static const _kPendingOtpVerified = "pendingOtpVerified";

  static const _kPendingEmail = "pendingEmail";
  static const _kPendingEmailLinkSent = "pendingEmailLinkSent";

  Future<_GateDecision> _decide() async {
    await Future.delayed(const Duration(milliseconds: 300));

    final sp = await SharedPreferences.getInstance();
    final user = FirebaseAuth.instance.currentUser;

    // ✅ IMPORTANT: If user already logged in → go home logic first
    if (user != null) {
      final userSnap = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();

      final data = userSnap.data() ?? <String, dynamic>{};
      final bool vibeDone = data['vibeSelectionCompleted'] == true;

      if (!vibeDone) {
        return _GateDecision.vibeSelection;
      }

      return _GateDecision.home;
    }

    // ---------- pending states (signup flow) ----------
    final pendingPhoneDigits = sp.getString(_kPendingPhoneDigits);
    final pendingDial = sp.getString(_kPendingDial);
    final pendingOtpVerified = sp.getBool(_kPendingOtpVerified) ?? false;

    final pendingEmail = sp.getString(_kPendingEmail);
    final pendingEmailLinkSent = sp.getBool(_kPendingEmailLinkSent) ?? false;

    if (pendingEmailLinkSent &&
        pendingEmail != null &&
        pendingEmail.isNotEmpty) {
      return _GateDecision.emailVerify;
    }

    if (pendingOtpVerified &&
        pendingPhoneDigits != null &&
        pendingPhoneDigits.isNotEmpty &&
        pendingDial != null &&
        pendingDial.isNotEmpty) {
      return _GateDecision.phonePasswordSetup;
    }

    return _GateDecision.loggedOut;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_GateDecision>(
      future: _decide(),
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(
            backgroundColor: Color(0xFFF8F2FF),
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final decision = snap.data ?? _GateDecision.loggedOut;

        switch (decision) {
          case _GateDecision.emailVerify:
            return const LoginPage(
              forceSignupMode: true,
              showEmailVerifyBlock: true,
            );

          case _GateDecision.phonePasswordSetup:
            return const LoginPage(
              forceSignupMode: true,
              showSetPasswordBlock: true,
            );

          case _GateDecision.vibeSelection:
            return const VibeSelectionPage();

          case _GateDecision.home:
            return const AppShell();

          case _GateDecision.loggedOut:
            return const LoginPage();
        }
      },
    );
  }
}

enum _GateDecision {
  loggedOut,
  emailVerify,
  phonePasswordSetup,
  vibeSelection,
  home,
}