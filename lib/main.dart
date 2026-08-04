import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';
import 'package:flutter/material.dart';

import 'screens/auth_gate.dart';
import 'services/locale_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

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
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.deepPurple,
            ),
            useMaterial3: true,
          ),
          locale: loc,
          home: const AuthGate(),
        );
      },
    );
  }
}
