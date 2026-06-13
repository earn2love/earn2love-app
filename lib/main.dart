import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_stripe/flutter_stripe.dart';

import 'screens/payment_test_page.dart';
import 'services/locale_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  Stripe.publishableKey =
      'pk_test_51ThgKF2Ls9hAd078zoddyW6NxKentLR3xxurjha6TATt2rxDhehHLoVuUR3DKGEugIzaGgfv7UWNOoRw7bbAR5U1008iyloMsR';
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
          home: const PaymentTestPage(),
        );
      },
    );
  }
}