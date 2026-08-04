import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

class ChatTypingIndicator extends StatelessWidget {
  const ChatTypingIndicator({
    super.key,
    required this.isTyping,
    required this.online,
    required this.lastSeen,
    required this.formatLastSeen,
  });

  final bool isTyping;
  final bool online;
  final Timestamp? lastSeen;
  final String Function(Timestamp? timestamp) formatLastSeen;

  @override
  Widget build(BuildContext context) {
    return Text(
      isTyping
          ? 'typing...'
          : online
              ? 'online'
              : formatLastSeen(lastSeen),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(
        fontSize: 12,
        color: isTyping ? Colors.green : Colors.black54,
        fontWeight: isTyping ? FontWeight.w700 : FontWeight.w500,
      ),
    );
  }
}
