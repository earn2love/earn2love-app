import 'package:flutter/material.dart';

class ArchivedChatsPage extends StatelessWidget {
  final List<Widget> archivedTiles;

  const ArchivedChatsPage({
    super.key,
    required this.archivedTiles,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2EBF8),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 1,
        iconTheme: const IconThemeData(color: Color(0xFF2F2747)),
        title: const Text(
          'Archived Chats',
          style: TextStyle(
            color: Color(0xFF2F2747),
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      body: archivedTiles.isEmpty
          ? const Center(
              child: Text(
                'No archived chats',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
            )
          : ListView(
              padding: const EdgeInsets.only(bottom: 12),
              children: [
                Container(
                  color: Colors.white,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: archivedTiles,
                  ),
                ),
              ],
            ),
    );
  }
}
