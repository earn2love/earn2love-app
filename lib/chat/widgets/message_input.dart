import 'package:flutter/material.dart';

class ChatMessageInput extends StatelessWidget {
  const ChatMessageInput({
    super.key,
    required this.fieldKey,
    required this.controller,
    required this.focusNode,
    required this.isBlocked,
    required this.blockedByCurrentUser,
    required this.isRecording,
    required this.hasTypedText,
    required this.sendingText,
    required this.sendingImage,
    required this.onTypingChanged,
    required this.onSend,
    required this.onPickImage,
    required this.onStartRecording,
    required this.onStopAndSendRecording,
    required this.onCancelRecording,
    required this.onColorPressed,
    required this.onAiPressed,
    required this.aiBusy,
  });

  final Key fieldKey;
  final TextEditingController controller;
  final FocusNode focusNode;

  final bool isBlocked;
  final bool blockedByCurrentUser;
  final bool isRecording;
  final bool hasTypedText;
  final bool sendingText;
  final bool sendingImage;

  final ValueChanged<String> onTypingChanged;

  final Future<void> Function() onSend;
  final Future<void> Function() onPickImage;
  final Future<void> Function() onStartRecording;
  final Future<void> Function() onStopAndSendRecording;
  final Future<void> Function() onCancelRecording;

  final VoidCallback onColorPressed;
  final VoidCallback onAiPressed;
  final bool aiBusy;

  String get _hintText {
    if (!isBlocked) return 'Message';
    return blockedByCurrentUser ? 'You blocked this user' : 'You are blocked';
  }

  bool get _mainActionDisabled => isBlocked || sendingText;

  Future<void> _handleMainAction() async {
    if (_mainActionDisabled) return;

    if (hasTypedText) {
      await onSend();
      return;
    }

    if (isRecording) {
      await onStopAndSendRecording();
      focusNode.requestFocus();
      return;
    }

    await onStartRecording();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 6, 8, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 6,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.98),
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(
                    color: const Color(0xFFE5D8FA),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.04),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    IconButton(
                      tooltip: 'Colors',
                      visualDensity: VisualDensity.compact,
                      onPressed: isBlocked ? null : onColorPressed,
                      icon: Icon(
                        Icons.palette_outlined,
                        color: Colors.grey.shade600,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Ask Meera',
                      visualDensity: VisualDensity.compact,
                      onPressed: isBlocked || aiBusy ? null : onAiPressed,
                      icon: aiBusy
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Icon(
                              Icons.auto_awesome_rounded,
                              color: Color(0xFF7B4EFF),
                            ),
                    ),
                    Expanded(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(
                          minHeight: 40,
                          maxHeight: 120,
                        ),
                        child: TextField(
                          key: fieldKey,
                          controller: controller,
                          focusNode: focusNode,
                          enabled: !isBlocked && !isRecording,
                          minLines: 1,
                          maxLines: 5,
                          textCapitalization: TextCapitalization.sentences,
                          keyboardType: TextInputType.multiline,
                          textInputAction: TextInputAction.newline,
                          onChanged: onTypingChanged,
                          decoration: InputDecoration(
                            hintText: _hintText,
                            border: InputBorder.none,
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 2,
                              vertical: 10,
                            ),
                          ),
                        ),
                      ),
                    ),
                    if (!hasTypedText)
                      IconButton(
                        tooltip: sendingImage ? 'Sending...' : 'Camera',
                        visualDensity: VisualDensity.compact,
                        onPressed:
                            isBlocked || sendingImage ? null : onPickImage,
                        icon: Icon(
                          Icons.camera_alt_outlined,
                          color: isBlocked
                              ? Colors.grey.shade400
                              : Colors.grey.shade700,
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 48,
              height: 48,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: (hasTypedText || sendingText || !isRecording)
                      ? const LinearGradient(
                          colors: [
                            Color(0xFF8D67FF),
                            Color(0xFFFF5DA2),
                          ],
                        )
                      : null,
                  color: isRecording ? Colors.red : null,
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: _mainActionDisabled ? null : _handleMainAction,
                    child: Center(
                      child: sendingText
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : Icon(
                              hasTypedText
                                  ? Icons.send_rounded
                                  : isRecording
                                      ? Icons.stop
                                      : Icons.mic,
                              color: Colors.white,
                              size: 22,
                            ),
                    ),
                  ),
                ),
              ),
            ),
            if (isRecording) ...[
              const SizedBox(width: 6),
              IconButton(
                tooltip: 'Cancel recording',
                onPressed: onCancelRecording,
                icon: const Icon(Icons.close),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
