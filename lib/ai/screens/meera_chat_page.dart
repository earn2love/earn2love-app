import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../screens/support_page.dart';
import '../models/meera_message.dart';
import '../services/meera_service.dart';

class MeeraChatPage extends StatefulWidget {
  const MeeraChatPage({
    super.key,
    this.initialMessage,
  });

  final String? initialMessage;

  @override
  State<MeeraChatPage> createState() => _MeeraChatPageState();
}

class _MeeraChatPageState extends State<MeeraChatPage> {
  static const _purple = Color(0xFF7B4EFF);
  static const _background = Color(0xFFF8F4FC);

  final TextEditingController _controller = TextEditingController();

  final ScrollController _scrollController = ScrollController();

  final FocusNode _focusNode = FocusNode();
  final MeeraService _service = MeeraService();

  final List<MeeraMessage> _messages = [];

  bool _sending = false;
  String _languageMode = 'auto';
  String _requestedLanguage = '';
  int? _remainingUsage;

  @override
  void initState() {
    super.initState();

    _messages.add(
      MeeraMessage(
        role: 'assistant',
        content: 'Hello, I’m Meera 😊\n\n'
            'You can speak to me in any language. '
            'I can help with your profile, chats, '
            'games, wallet, subscriptions and '
            'Earn2Love support.',
        createdAt: DateTime.now(),
      ),
    );

    final initialMessage = widget.initialMessage?.trim() ?? '';

    if (initialMessage.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback(
        (_) {
          _controller.text = initialMessage;
          _send();
        },
      );
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final message = _controller.text.trim();

    if (message.isEmpty || _sending) return;

    final history = List<MeeraMessage>.from(
      _messages,
    );

    setState(() {
      _messages.add(
        MeeraMessage(
          role: 'user',
          content: message,
          createdAt: DateTime.now(),
        ),
      );

      _controller.clear();
      _sending = true;
    });

    _scrollToBottom();

    try {
      final result = await _service.ask(
        message: message,
        history: history,
        languageMode: _languageMode,
        requestedLanguage: _requestedLanguage,
      );

      if (!mounted) return;

      setState(() {
        _remainingUsage = result.remaining;

        _messages.add(
          MeeraMessage(
            role: 'assistant',
            content: result.answer,
            createdAt: DateTime.now(),
            detectedLanguage: result.detectedLanguage,
            responseLanguage: result.responseLanguage,
            category: result.category,
            requiresHumanSupport: result.requiresHumanSupport,
            escalationReason: result.escalationReason,
            actions: result.actions,
          ),
        );
      });
    } on MeeraServiceException catch (error) {
      if (!mounted) return;

      setState(() {
        _messages.add(
          MeeraMessage(
            role: 'assistant',
            content: error.message,
            createdAt: DateTime.now(),
            isError: true,
          ),
        );
      });
    } finally {
      if (mounted) {
        setState(() => _sending = false);
        _scrollToBottom();
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback(
      (_) {
        if (!_scrollController.hasClients) {
          return;
        }

        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 260),
          curve: Curves.easeOut,
        );
      },
    );
  }

  Future<void> _openLanguageSettings() async {
    final result = await showModalBottomSheet<Map<String, String>>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        String selectedMode = _languageMode;
        String selectedLanguage = _requestedLanguage;

        return StatefulBuilder(
          builder: (
            context,
            setSheetState,
          ) {
            return SafeArea(
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                  18,
                  4,
                  18,
                  MediaQuery.viewInsetsOf(
                        context,
                      ).bottom +
                      24,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Meera language',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Auto mode replies in the '
                      'language you are currently using.',
                      style: TextStyle(
                        color: Colors.black54,
                      ),
                    ),
                    const SizedBox(height: 14),
                    SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(
                          value: 'auto',
                          label: Text('Auto'),
                        ),
                        ButtonSegment(
                          value: 'fixed',
                          label: Text('Fixed'),
                        ),
                      ],
                      selected: {selectedMode},
                      onSelectionChanged: (value) {
                        setSheetState(() {
                          selectedMode = value.first;
                        });
                      },
                    ),
                    if (selectedMode == 'fixed') ...[
                      const SizedBox(height: 14),
                      DropdownButtonFormField<String>(
                        initialValue:
                            selectedLanguage.isEmpty ? 'en' : selectedLanguage,
                        decoration: const InputDecoration(
                          labelText: 'Response language',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'en',
                            child: Text('English'),
                          ),
                          DropdownMenuItem(
                            value: 'en-GB',
                            child: Text(
                              'British English',
                            ),
                          ),
                          DropdownMenuItem(
                            value: 'te',
                            child: Text('Telugu'),
                          ),
                          DropdownMenuItem(
                            value: 'hi',
                            child: Text('Hindi'),
                          ),
                          DropdownMenuItem(
                            value: 'ta',
                            child: Text('Tamil'),
                          ),
                          DropdownMenuItem(
                            value: 'kn',
                            child: Text('Kannada'),
                          ),
                          DropdownMenuItem(
                            value: 'ml',
                            child: Text(
                              'Malayalam',
                            ),
                          ),
                          DropdownMenuItem(
                            value: 'bn',
                            child: Text('Bengali'),
                          ),
                          DropdownMenuItem(
                            value: 'ur',
                            child: Text('Urdu'),
                          ),
                          DropdownMenuItem(
                            value: 'es',
                            child: Text('Spanish'),
                          ),
                          DropdownMenuItem(
                            value: 'fr',
                            child: Text('French'),
                          ),
                          DropdownMenuItem(
                            value: 'de',
                            child: Text('German'),
                          ),
                          DropdownMenuItem(
                            value: 'pt',
                            child: Text(
                              'Portuguese',
                            ),
                          ),
                          DropdownMenuItem(
                            value: 'ar',
                            child: Text('Arabic'),
                          ),
                        ],
                        onChanged: (value) {
                          setSheetState(() {
                            selectedLanguage = value ?? 'en';
                          });
                        },
                      ),
                    ],
                    const SizedBox(height: 18),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: () {
                          Navigator.of(
                            sheetContext,
                          ).pop({
                            'mode': selectedMode,
                            'language': selectedMode == 'fixed'
                                ? (selectedLanguage.isEmpty
                                    ? 'en'
                                    : selectedLanguage)
                                : '',
                          });
                        },
                        child: const Text('Save'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    if (result == null || !mounted) return;

    setState(() {
      _languageMode = result['mode'] ?? 'auto';

      _requestedLanguage = result['language'] ?? '';
    });
  }

  Future<void> _handleAction(
    MeeraSuggestedAction action,
  ) async {
    Future<void> perform() async {
      switch (action.actionType) {
        case 'copy_text':
        case 'insert_text':
          await Clipboard.setData(
            ClipboardData(
              text: action.payload,
            ),
          );

          if (!mounted) return;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                action.actionType == 'insert_text'
                    ? 'Text copied. Open a chat '
                        'and paste it.'
                    : 'Copied',
              ),
            ),
          );

        case 'open_support':
          if (!mounted) return;

          await Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => const SupportPage(),
            ),
          );

        case 'navigate':
        case 'none':
          if (!mounted) return;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                action.payload.isEmpty ? action.label : action.payload,
              ),
            ),
          );
      }
    }

    if (!action.requiresConfirmation) {
      await perform();
      return;
    }

    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) {
            return AlertDialog(
              title: Text(action.label),
              content: const Text(
                'Do you want to continue?',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(
                    dialogContext,
                  ).pop(false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(
                    dialogContext,
                  ).pop(true),
                  child: const Text('Continue'),
                ),
              ],
            );
          },
        ) ??
        false;

    if (confirmed) {
      await perform();
    }
  }

  void _clearConversation() {
    setState(() {
      _messages
        ..clear()
        ..add(
          MeeraMessage(
            role: 'assistant',
            content: 'Conversation cleared. '
                'How can I help you now?',
            createdAt: DateTime.now(),
          ),
        );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _background,
      appBar: AppBar(
        backgroundColor: _background,
        scrolledUnderElevation: 0,
        titleSpacing: 4,
        title: const Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: Color(0xFFE9DFFF),
              child: Icon(
                Icons.auto_awesome_rounded,
                color: _purple,
                size: 20,
              ),
            ),
            SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Meera',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 17,
                  ),
                ),
                Text(
                  'Earn2Love AI assistant',
                  style: TextStyle(
                    fontSize: 10.5,
                    color: Colors.black54,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Language',
            onPressed: _openLanguageSettings,
            icon: const Icon(
              Icons.translate_rounded,
            ),
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'clear') {
                _clearConversation();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'clear',
                child: Text(
                  'Clear conversation',
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          if (_remainingUsage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 7,
              ),
              color: const Color(0xFFF0E9FA),
              child: Text(
                'AI requests remaining today: '
                '$_remainingUsage',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Color(0xFF645878),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.fromLTRB(
                14,
                16,
                14,
                18,
              ),
              itemCount: _messages.length + (_sending ? 1 : 0),
              itemBuilder: (context, index) {
                if (_sending && index == _messages.length) {
                  return const _MeeraThinking();
                }

                return _MessageBubble(
                  message: _messages[index],
                  onAction: _handleAction,
                );
              },
            ),
          ),
          _SuggestionRow(
            enabled: !_sending,
            onSelected: (value) {
              _controller.text = value;
              _focusNode.requestFocus();
            },
          ),
          SafeArea(
            top: false,
            child: Container(
              padding: const EdgeInsets.fromLTRB(
                12,
                8,
                12,
                10,
              ),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(
                  top: BorderSide(
                    color: Color(0xFFECE3F4),
                  ),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      focusNode: _focusNode,
                      minLines: 1,
                      maxLines: 6,
                      textInputAction: TextInputAction.newline,
                      decoration: const InputDecoration(
                        hintText: 'Message Meera…',
                        filled: true,
                        fillColor: Color(0xFFF7F3FA),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.all(
                            Radius.circular(22),
                          ),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    tooltip: 'Send',
                    onPressed: _sending ? null : _send,
                    style: IconButton.styleFrom(
                      backgroundColor: _purple,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: Colors.black12,
                    ),
                    icon: const Icon(
                      Icons.arrow_upward_rounded,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    required this.message,
    required this.onAction,
  });

  final MeeraMessage message;
  final Future<void> Function(
    MeeraSuggestedAction action,
  ) onAction;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.84,
        ),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(
          14,
          12,
          14,
          11,
        ),
        decoration: BoxDecoration(
          color: isUser
              ? const Color(0xFF7B4EFF)
              : message.isError
                  ? const Color(0xFFFFECEF)
                  : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(20),
            topRight: const Radius.circular(20),
            bottomLeft: Radius.circular(
              isUser ? 20 : 5,
            ),
            bottomRight: Radius.circular(
              isUser ? 5 : 20,
            ),
          ),
          border: isUser
              ? null
              : Border.all(
                  color: message.isError
                      ? const Color(0xFFFFB8C3)
                      : const Color(
                          0xFFE9E0F0,
                        ),
                ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.content,
              style: TextStyle(
                color: isUser
                    ? Colors.white
                    : const Color(
                        0xFF2E2838,
                      ),
                fontSize: 14.4,
                height: 1.42,
              ),
            ),
            if (!isUser && message.responseLanguage != null) ...[
              const SizedBox(height: 8),
              Text(
                message.responseLanguage!,
                style: const TextStyle(
                  color: Colors.black45,
                  fontSize: 10.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            if (message.actions.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 7,
                runSpacing: 7,
                children: message.actions
                    .map(
                      (action) => ActionChip(
                        label: Text(action.label),
                        onPressed: () => onAction(action),
                      ),
                    )
                    .toList(
                      growable: false,
                    ),
              ),
            ],
            if (message.requiresHumanSupport) ...[
              const SizedBox(height: 10),
              const Row(
                children: [
                  Icon(
                    Icons.support_agent_rounded,
                    size: 16,
                    color: Color(0xFFFF4D91),
                  ),
                  SizedBox(width: 5),
                  Expanded(
                    child: Text(
                      'Human support is '
                      'recommended.',
                      style: TextStyle(
                        color: Color(0xFFB12B63),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MeeraThinking extends StatelessWidget {
  const _MeeraThinking();

  @override
  Widget build(BuildContext context) {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.only(
          left: 4,
          bottom: 14,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
              ),
            ),
            SizedBox(width: 9),
            Text(
              'Meera is thinking…',
              style: TextStyle(
                color: Colors.black54,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SuggestionRow extends StatelessWidget {
  const _SuggestionRow({
    required this.enabled,
    required this.onSelected,
  });

  final bool enabled;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    const suggestions = [
      'Improve my profile',
      'Recommend a game',
      'Help me start a conversation',
      'Explain my wallet',
    ];

    return SizedBox(
      height: 46,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 5,
        ),
        scrollDirection: Axis.horizontal,
        itemCount: suggestions.length,
        separatorBuilder: (_, __) => const SizedBox(width: 7),
        itemBuilder: (context, index) {
          return ActionChip(
            label: Text(
              suggestions[index],
            ),
            onPressed: enabled
                ? () => onSelected(
                      suggestions[index],
                    )
                : null,
          );
        },
      ),
    );
  }
}
