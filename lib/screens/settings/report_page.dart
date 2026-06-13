import 'package:flutter/material.dart';

class ReportPage extends StatelessWidget {
  final String targetUid;

  const ReportPage({
    super.key,
    required this.targetUid,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Report User')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Text('Report target user: $targetUid'),
      ),
    );
  }
}