import 'package:flutter/material.dart';

class RulesPage extends StatelessWidget {
  const RulesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Rules')),
      body: const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          'Community rules will appear here.',
        ),
      ),
    );
  }
}
