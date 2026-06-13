import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_stripe/flutter_stripe.dart';

import 'screens/auth_gate.dart';
import 'services/locale_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  Stripe.publishableKey = 'pk_live_51ThgKF2Ls9hAd0787X0dHKkqeqwKIjzMwnJaayiC5tQ8EjYSAAtRhGejZQEeq0N464qst4lQBkgShjGqBsbjavXD00kQ21iQcY';
  await Stripe.instance.applySettings();

  runApp(const Earn2LoveApp());
}

class Earn2LoveApp extends StatelessWidget {
  const Earn2LoveApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Locale>(
      valueListenable: LocaleService.locale,
      builder: (context, loc, _) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Earn2Love',
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
            useMaterial3: true,
          ),
          locale: loc,
          home: const AuthGate(),
        );
      },
    );
  }
}