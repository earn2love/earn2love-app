import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

class ChatMessageBubble extends StatelessWidget {
  const ChatMessageBubble({
    super.key,
    required this.messageId,
    required this.message,
    required this.currentUid,
    required this.otherUid,
    required this.clearedAt,
    required this.replySnippetBuilder,
    required this.voiceBubbleBuilder,
    required this.messageStatusBuilder,
    required this.reactionBarBuilder,
    required this.formatTimestamp,
    required this.onOpenImage,
    required this.onReply,
    required this.onDeleteForMe,
    required this.onDeleteForEveryone,
    required this.onReact,
    required this.onShowInfo,
  });

  final String messageId;
  final Map<String, dynamic> message;
  final String currentUid;
  final String otherUid;
  final Timestamp? clearedAt;

  final Widget Function(Map<String, dynamic>? replyTo) replySnippetBuilder;
  final Widget Function(Map<String, dynamic> message) voiceBubbleBuilder;
  final Widget Function(Map<String, dynamic> message) messageStatusBuilder;
  final Widget Function(Map<String, dynamic> message) reactionBarBuilder;

  final String Function(Timestamp? timestamp) formatTimestamp;

  final void Function(String url) onOpenImage;
  final VoidCallback onReply;

  final Future<void> Function() onDeleteForMe;
  final Future<void> Function() onDeleteForEveryone;
  final Future<void> Function() onReact;
  final Future<void> Function() onShowInfo;

  String _string(dynamic value, {String def = ''}) {
    if (value == null) return def;
    final result = value.toString().trim();
    return result.isEmpty ? def : result;
  }

  @override
  Widget build(BuildContext context) {
    final sender = _string(message['senderId']);
    final text = _string(message['text']);
    final type = _string(message['type'], def: 'text');
    final imageUrl = _string(message['imageUrl']);
    final timestamp = message['createdAt'] as Timestamp?;

    final deletedForEveryone = message['deletedForEveryone'] == true;
    final isMe = sender == currentUid;

    final seenBy = (message['seenBy'] as List?)
            ?.map((value) => value.toString())
            .toList() ??
        <String>[];

    final replyTo = message['replyTo'] is Map
        ? (message['replyTo'] as Map).map(
            (key, value) => MapEntry(key.toString(), value),
          )
        : null;

    if (clearedAt != null &&
        timestamp != null &&
        timestamp.toDate().isBefore(clearedAt!.toDate())) {
      return const SizedBox.shrink();
    }

    final bubble = ConstrainedBox(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.sizeOf(context).width * 0.72,
      ),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 2),
        padding: type == 'image'
            ? const EdgeInsets.all(5)
            : const EdgeInsets.symmetric(
                horizontal: 11,
                vertical: 7,
              ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: isMe ? const Color(0xFFEAFBF2) : const Color(0xFFF2EEFF),
          border: Border.all(
            color: isMe ? const Color(0xFFC7EED7) : const Color(0xFFE0D6FF),
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFD8CBEF).withValues(alpha: 0.08),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            replySnippetBuilder(replyTo),
            if (deletedForEveryone)
              const Text(
                'This message was deleted',
                style: TextStyle(
                  fontStyle: FontStyle.italic,
                  color: Colors.grey,
                  fontSize: 12,
                ),
              )
            else if (type == 'image' && imageUrl.isNotEmpty)
              GestureDetector(
                onTap: () => onOpenImage(imageUrl),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      maxWidth: 220,
                      maxHeight: 260,
                    ),
                    child: CachedNetworkImage(
                      imageUrl: imageUrl,
                      fit: BoxFit.cover,
                      fadeInDuration: const Duration(milliseconds: 160),
                      placeholder: (_, __) => const SizedBox(
                        width: 180,
                        height: 120,
                        child: Center(
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                          ),
                        ),
                      ),
                      errorWidget: (_, __, ___) => Container(
                        width: 180,
                        height: 120,
                        alignment: Alignment.center,
                        color: Colors.black12,
                        child: const Text('Image failed'),
                      ),
                    ),
                  ),
                ),
              )
            else if (type == 'voice')
              voiceBubbleBuilder(message)
            else if (type == 'call_log')
              _CallLogContent(
                title: text,
                durationLabel: _string(message['durationLabel']),
                costLabel: _string(message['costLabel']),
              )
            else
              Text(
                text,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  height: 1.15,
                ),
              ),
            const SizedBox(height: 3),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  formatTimestamp(timestamp),
                  style: const TextStyle(fontSize: 9.5),
                ),
                if (isMe) ...[
                  const SizedBox(width: 5),
                  messageStatusBuilder(message),
                ],
              ],
            ),
            reactionBarBuilder(message),
          ],
        ),
      ),
    );

    return Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onTap: () => _openActions(
          context: context,
          isMe: isMe,
          deletedForEveryone: deletedForEveryone,
          seenByOtherUser: seenBy.contains(otherUid),
        ),
        onHorizontalDragEnd: (_) => onReply(),
        child: bubble,
      ),
    );
  }

  Future<void> _openActions({
    required BuildContext context,
    required bool isMe,
    required bool deletedForEveryone,
    required bool seenByOtherUser,
  }) async {
    final items = <Widget>[
      ListTile(
        leading: const Icon(Icons.info_outline),
        title: const Text('Info'),
        onTap: () => Navigator.pop(context, 'info'),
      ),
      ListTile(
        leading: const Icon(Icons.reply),
        title: const Text('Reply'),
        onTap: () => Navigator.pop(context, 'reply'),
      ),
      ListTile(
        leading: const Icon(Icons.emoji_emotions_outlined),
        title: const Text('React'),
        onTap: () => Navigator.pop(context, 'react'),
      ),
      ListTile(
        leading: const Icon(Icons.delete_outline),
        title: const Text('Remove for me'),
        onTap: () => Navigator.pop(context, 'deleteForMe'),
      ),
    ];

    if (isMe && !deletedForEveryone && !seenByOtherUser) {
      items.add(
        ListTile(
          leading: const Icon(Icons.delete_forever_outlined),
          title: const Text('Delete for everyone'),
          onTap: () => Navigator.pop(
            context,
            'deleteForEveryone',
          ),
        ),
      );
    }

    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: items,
        ),
      ),
    );

    switch (choice) {
      case 'deleteForMe':
        await onDeleteForMe();
      case 'deleteForEveryone':
        await onDeleteForEveryone();
      case 'reply':
        onReply();
      case 'react':
        await onReact();
      case 'info':
        await onShowInfo();
      case null:
        return;
    }
  }
}

class _CallLogContent extends StatelessWidget {
  const _CallLogContent({
    required this.title,
    required this.durationLabel,
    required this.costLabel,
  });

  final String title;
  final String durationLabel;
  final String costLabel;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 13,
          ),
        ),
        if (durationLabel.isNotEmpty)
          Text(
            durationLabel,
            style: const TextStyle(fontSize: 11.5),
          ),
        if (costLabel.isNotEmpty)
          Text(
            costLabel,
            style: const TextStyle(fontSize: 11.5),
          ),
      ],
    );
  }
}
