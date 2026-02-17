import 'package:flutter/material.dart';

class LocaleService {
  static final ValueNotifier<Locale> locale = ValueNotifier(const Locale('en'));

  static void setLocale(String code) {
    final c = (code.trim().isEmpty) ? 'en' : code.trim();
    locale.value = Locale(c);
  }
}
