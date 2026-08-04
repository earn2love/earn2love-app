import 'package:flutter/material.dart';

class ChatReplyBanner extends StatelessWidget {
  const ChatReplyBanner({
    super.key,
    required this.replyingTo,
    required this.currentUid,
    required this.onClose,
  });

  final Map<String, dynamic>? replyingTo;
  final String currentUid;
  final VoidCallback onClose;

  String _asString(dynamic value, {String def = ''}) {
    if (value == null) return def;
    final result = value.toString().trim();
    return result.isEmpty ? def : result;
  }

  @override
  Widget build(BuildContext context) {
    final reply = replyingTo;
    if (reply == null) return const SizedBox.shrink();

    final senderId = _asString(reply['senderId']);
    final senderName = senderId == currentUid ? 'You' : 'Reply';
    final type = _asString(reply['type'], def: 'text');

    final text = switch (type) {
      'image' => '📷 Photo',
      'voice' => '🎤 Voice message',
      _ => _asString(reply['text']),
    };

    return Container(
      margin: const EdgeInsets.fromLTRB(10, 0, 10, 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.deepPurple.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.deepPurple.withValues(alpha: 0.18),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 38,
            decoration: BoxDecoration(
              color: Colors.deepPurple,
              borderRadius: BorderRadius.circular(10),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  senderName,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                    color: Colors.deepPurple,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  text,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Cancel reply',
            onPressed: onClose,
            icon: const Icon(Icons.close),
          ),
        ],
      ),
    );
  }
}
