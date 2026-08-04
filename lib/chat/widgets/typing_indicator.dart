import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

class ChatTypingIndicator extends StatelessWidget {
  const ChatTypingIndicator({
    super.key,
    required this.roomStream,
    required this.otherUid,
    required this.online,
    required this.lastSeen,
    required this.formatLastSeen,
  });

  final Stream<DocumentSnapshot<Map<String, dynamic>>> roomStream;
  final String otherUid;
  final bool online;
  final Timestamp? lastSeen;
  final String Function(Timestamp? timestamp) formatLastSeen;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: roomStream,
      builder: (context, snapshot) {
        final typingValue = snapshot.data?.data()?['typing'];

        final typing = typingValue is Map
            ? typingValue.map(
                (key, value) => MapEntry(key.toString(), value),
              )
            : <String, dynamic>{};

        final otherTyping = typing[otherUid] == true;

        return Text(
          otherTyping
              ? 'typing...'
              : online
                  ? 'online'
                  : formatLastSeen(lastSeen),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 12,
            color: otherTyping ? Colors.green : Colors.black54,
            fontWeight: otherTyping ? FontWeight.w700 : FontWeight.w500,
          ),
        );
      },
    );
  }
}
