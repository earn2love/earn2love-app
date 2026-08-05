import 'package:cached_network_image/cached_network_image.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

class ChatMessageBubble extends StatefulWidget {
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
    required this.onSmartReply,
    required this.onTranslate,
  });

  final String messageId;
  final Map<String, dynamic> message;
  final String currentUid;
  final String otherUid;
  final Timestamp? clearedAt;

  final Widget Function(Map<String, dynamic>?) replySnippetBuilder;
  final Widget Function(Map<String, dynamic>) voiceBubbleBuilder;
  final Widget Function(Map<String, dynamic>) messageStatusBuilder;
  final Widget Function(Map<String, dynamic>) reactionBarBuilder;
  final String Function(Timestamp?) formatTimestamp;

  final ValueChanged<String> onOpenImage;
  final VoidCallback onReply;
  final Future<void> Function() onDeleteForMe;
  final Future<void> Function() onDeleteForEveryone;
  final Future<void> Function() onReact;
  final Future<void> Function() onShowInfo;
  final Future<void> Function() onSmartReply;
  final Future<void> Function() onTranslate;

  @override
  State<ChatMessageBubble> createState() => _ChatMessageBubbleState();
}

class _ChatMessageBubbleState extends State<ChatMessageBubble>
    with SingleTickerProviderStateMixin {
  double _dragOffset = 0;
  bool _replyTriggered = false;

  String _string(dynamic value) {
    if (value == null) return '';
    return value.toString().trim();
  }

  bool _isAfterClear(Timestamp? createdAt) {
    final clearedAt = widget.clearedAt;
    if (clearedAt == null || createdAt == null) return true;

    return createdAt.toDate().isAfter(
          clearedAt.toDate(),
        );
  }

  void _handleHorizontalDragUpdate(
    DragUpdateDetails details,
  ) {
    final senderId = _string(widget.message['senderId']);
    final isMe = senderId == widget.currentUid;

    final delta = details.primaryDelta ?? 0;
    final allowedDelta =
        isMe ? delta.clamp(-8.0, 60.0) : delta.clamp(0.0, 60.0);

    setState(() {
      _dragOffset = (_dragOffset + allowedDelta).clamp(0.0, 60.0);
    });

    if (_dragOffset >= 48 && !_replyTriggered) {
      _replyTriggered = true;
      widget.onReply();
    }
  }

  void _handleHorizontalDragEnd(
    DragEndDetails details,
  ) {
    setState(() {
      _dragOffset = 0;
      _replyTriggered = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final message = widget.message;

    final senderId = _string(message['senderId']);
    final type =
        _string(message['type']).isEmpty ? 'text' : _string(message['type']);
    final text = _string(message['text']);
    final imageUrl = _string(message['imageUrl']);
    final timestamp = message['createdAt'] as Timestamp?;
    final deletedForEveryone = message['deletedForEveryone'] == true;

    final hiddenFor = (message['deletedFor'] as List?)
            ?.map((item) => item.toString())
            .toSet() ??
        <String>{};

    if (hiddenFor.contains(widget.currentUid) || !_isAfterClear(timestamp)) {
      return const SizedBox.shrink();
    }

    final isMe = senderId == widget.currentUid;

    final seenBy =
        (message['seenBy'] as List?)?.map((item) => item.toString()).toList() ??
            const <String>[];

    final replyTo = message['replyTo'] is Map
        ? Map<String, dynamic>.from(
            message['replyTo'] as Map,
          )
        : null;

    final bubbleColor = isMe ? const Color(0xFFDDF7E8) : Colors.white;

    final borderColor =
        isMe ? const Color(0xFFC2EBD3) : const Color(0xFFE7DEEF);

    final bubbleRadius = BorderRadius.only(
      topLeft: const Radius.circular(20),
      topRight: const Radius.circular(20),
      bottomLeft: Radius.circular(isMe ? 20 : 5),
      bottomRight: Radius.circular(isMe ? 5 : 20),
    );

    final bubble = Container(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.sizeOf(context).width * 0.78,
      ),
      padding: EdgeInsets.fromLTRB(
        type == 'image' ? 5 : 12,
        type == 'image' ? 5 : 9,
        type == 'image' ? 5 : 9,
        6,
      ),
      decoration: BoxDecoration(
        color: bubbleColor,
        borderRadius: bubbleRadius,
        border: Border.all(
          color: borderColor,
          width: 0.75,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(
              alpha: isMe ? 0.045 : 0.055,
            ),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (replyTo != null)
            Padding(
              padding: EdgeInsets.only(
                left: type == 'image' ? 6 : 0,
                right: type == 'image' ? 6 : 0,
                top: type == 'image' ? 4 : 0,
                bottom: 6,
              ),
              child: widget.replySnippetBuilder(replyTo),
            ),
          if (deletedForEveryone)
            const Padding(
              padding: EdgeInsets.symmetric(
                horizontal: 4,
                vertical: 3,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.block_flipped,
                    size: 14,
                    color: Colors.grey,
                  ),
                  SizedBox(width: 5),
                  Flexible(
                    child: Text(
                      'This message was deleted',
                      style: TextStyle(
                        fontStyle: FontStyle.italic,
                        color: Colors.grey,
                        fontSize: 12.5,
                      ),
                    ),
                  ),
                ],
              ),
            )
          else if (type == 'image' && imageUrl.isNotEmpty)
            GestureDetector(
              onTap: () => widget.onOpenImage(imageUrl),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(15),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: 260,
                    maxHeight: 320,
                    minWidth: 150,
                    minHeight: 110,
                  ),
                  child: CachedNetworkImage(
                    imageUrl: imageUrl,
                    fit: BoxFit.cover,
                    fadeInDuration: const Duration(milliseconds: 180),
                    placeholder: (_, __) => const SizedBox(
                      width: 200,
                      height: 145,
                      child: Center(
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                        ),
                      ),
                    ),
                    errorWidget: (_, __, ___) => Container(
                      width: 200,
                      height: 145,
                      color: Colors.black12,
                      alignment: Alignment.center,
                      child: const Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.broken_image_outlined,
                          ),
                          SizedBox(height: 6),
                          Text('Image unavailable'),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            )
          else if (type == 'voice')
            widget.voiceBubbleBuilder(message)
          else if (type == 'call_log')
            _CallLogContent(
              title: text,
              durationLabel: _string(message['durationLabel']),
              costLabel: _string(message['costLabel']),
            )
          else
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1),
              child: Text(
                text,
                style: const TextStyle(
                  color: Color(0xFF241E2F),
                  fontSize: 14.2,
                  height: 1.28,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          const SizedBox(height: 3),
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: type == 'image' ? 5 : 0,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(
                  widget.formatTimestamp(timestamp),
                  style: const TextStyle(
                    color: Color(0xFF77717E),
                    fontSize: 10.2,
                    height: 1,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (isMe) ...[
                  const SizedBox(width: 4),
                  widget.messageStatusBuilder(message),
                ],
              ],
            ),
          ),
          widget.reactionBarBuilder(message),
        ],
      ),
    );

    return Padding(
      padding: EdgeInsets.only(
        left: isMe ? 48 : 8,
        right: isMe ? 8 : 48,
        top: 2,
        bottom: 2,
      ),
      child: Align(
        alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
        child: Stack(
          alignment: Alignment.centerLeft,
          children: [
            AnimatedOpacity(
              opacity: _dragOffset > 12 ? 1 : 0,
              duration: const Duration(milliseconds: 100),
              child: Transform.scale(
                scale: (_dragOffset / 48).clamp(0.6, 1.0),
                child: Container(
                  width: 34,
                  height: 34,
                  decoration: const BoxDecoration(
                    color: Color(0xFFE9DFFF),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.reply_rounded,
                    size: 18,
                    color: Color(0xFF7B4EFF),
                  ),
                ),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 120),
              curve: Curves.easeOut,
              transform: Matrix4.translationValues(
                _dragOffset,
                0,
                0,
              ),
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onLongPress: () => _openActions(
                  context: context,
                  isMe: isMe,
                  deletedForEveryone: deletedForEveryone,
                  seenByOtherUser: seenBy.contains(
                    widget.otherUid,
                  ),
                  canUseAi: !isMe &&
                      type == 'text' &&
                      text.isNotEmpty &&
                      !deletedForEveryone,
                ),
                onHorizontalDragUpdate: _handleHorizontalDragUpdate,
                onHorizontalDragEnd: _handleHorizontalDragEnd,
                child: bubble,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openActions({
    required BuildContext context,
    required bool isMe,
    required bool deletedForEveryone,
    required bool seenByOtherUser,
    required bool canUseAi,
  }) async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) {
        return SafeArea(
          child: Container(
            margin: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 42,
                  height: 4,
                  margin: const EdgeInsets.only(top: 10),
                  decoration: BoxDecoration(
                    color: Colors.black12,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
                _ActionTile(
                  icon: Icons.reply_rounded,
                  title: 'Reply',
                  onTap: () => Navigator.pop(
                    context,
                    'reply',
                  ),
                ),
                if (canUseAi)
                  _ActionTile(
                    icon: Icons.auto_awesome_rounded,
                    title: 'Smart reply',
                    onTap: () => Navigator.pop(
                      context,
                      'smartReply',
                    ),
                  ),
                if (canUseAi)
                  _ActionTile(
                    icon: Icons.translate_rounded,
                    title: 'Translate',
                    onTap: () => Navigator.pop(
                      context,
                      'translate',
                    ),
                  ),
                _ActionTile(
                  icon: Icons.emoji_emotions_outlined,
                  title: 'React',
                  onTap: () => Navigator.pop(
                    context,
                    'react',
                  ),
                ),
                _ActionTile(
                  icon: Icons.info_outline_rounded,
                  title: 'Message info',
                  onTap: () => Navigator.pop(
                    context,
                    'info',
                  ),
                ),
                _ActionTile(
                  icon: Icons.delete_outline_rounded,
                  title: 'Delete for me',
                  onTap: () => Navigator.pop(
                    context,
                    'deleteForMe',
                  ),
                ),
                if (isMe && !deletedForEveryone && !seenByOtherUser)
                  _ActionTile(
                    icon: Icons.delete_forever_outlined,
                    title: 'Delete for everyone',
                    destructive: true,
                    onTap: () => Navigator.pop(
                      context,
                      'deleteForEveryone',
                    ),
                  ),
                const SizedBox(height: 6),
              ],
            ),
          ),
        );
      },
    );

    switch (choice) {
      case 'deleteForMe':
        await widget.onDeleteForMe();
      case 'deleteForEveryone':
        await widget.onDeleteForEveryone();
      case 'reply':
        widget.onReply();
      case 'smartReply':
        await widget.onSmartReply();
      case 'translate':
        await widget.onTranslate();
      case 'react':
        await widget.onReact();
      case 'info':
        await widget.onShowInfo();
      case null:
        return;
    }
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.onTap,
    this.destructive = false,
  });

  final IconData icon;
  final String title;
  final VoidCallback onTap;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final color = destructive ? Colors.red : const Color(0xFF3D354B);

    return ListTile(
      dense: true,
      leading: Icon(icon, color: color),
      title: Text(
        title,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
      onTap: onTap,
    );
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
    return Container(
      constraints: const BoxConstraints(
        minWidth: 145,
      ),
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.42),
        borderRadius: BorderRadius.circular(13),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.w800,
              fontSize: 13,
            ),
          ),
          if (durationLabel.isNotEmpty) ...[
            const SizedBox(height: 3),
            Text(
              durationLabel,
              style: const TextStyle(
                fontSize: 11.5,
                color: Colors.black54,
              ),
            ),
          ],
          if (costLabel.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              costLabel,
              style: const TextStyle(
                fontSize: 11.5,
                color: Colors.black54,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
