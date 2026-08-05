import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/meera_chat_assist.dart';
import '../services/meera_service.dart';

class MeeraWritingAssistantSheet extends StatefulWidget {
  const MeeraWritingAssistantSheet({
    super.key,
    required this.initialText,
    required this.onReplace,
    this.recentMessages = const [],
  });

  final String initialText;

  final List<Map<String, String>> recentMessages;

  final ValueChanged<String> onReplace;

  @override
  State<MeeraWritingAssistantSheet> createState() =>
      _MeeraWritingAssistantSheetState();
}

class _MeeraWritingAssistantSheetState
    extends State<MeeraWritingAssistantSheet> {
  static const _purple = Color(0xFF7B4EFF);

  final MeeraService _service = MeeraService();

  bool _loading = false;
  String? _selectedMode;
  String _requestedLanguage = '';

  MeeraChatAssistResult? _result;

  bool get _hasSourceText => widget.initialText.trim().isNotEmpty;

  List<MeeraChatAssistMode> get _modes {
    if (!_hasSourceText) {
      return const [
        MeeraChatAssistMode(
          id: 'conversation_starter',
          label: 'Conversation starter',
          description: 'Start a natural new conversation',
        ),
        MeeraChatAssistMode(
          id: 'reply_suggestions',
          label: 'Suggested replies',
          description: 'Create replies from recent context',
        ),
      ];
    }

    return const [
      MeeraChatAssistMode(
        id: 'rewrite',
        label: 'Rewrite',
        description: 'Say it in a clearer way',
      ),
      MeeraChatAssistMode(
        id: 'improve',
        label: 'Improve',
        description: 'Improve flow and wording',
      ),
      MeeraChatAssistMode(
        id: 'grammar',
        label: 'Grammar',
        description: 'Fix grammar and spelling',
      ),
      MeeraChatAssistMode(
        id: 'shorten',
        label: 'Shorten',
        description: 'Make it concise',
      ),
      MeeraChatAssistMode(
        id: 'expand',
        label: 'Expand',
        description: 'Add natural detail',
      ),
      MeeraChatAssistMode(
        id: 'friendly',
        label: 'Friendly',
        description: 'Make it warmer',
      ),
      MeeraChatAssistMode(
        id: 'romantic',
        label: 'Romantic',
        description: 'Gentle and respectful',
      ),
      MeeraChatAssistMode(
        id: 'funny',
        label: 'Funny',
        description: 'Add light humour',
      ),
      MeeraChatAssistMode(
        id: 'professional',
        label: 'Professional',
        description: 'Polished and formal',
      ),
      MeeraChatAssistMode(
        id: 'translate',
        label: 'Translate',
        description: 'Translate naturally',
      ),
    ];
  }

  Future<void> _run(
    String mode,
  ) async {
    if (_loading) return;

    if (mode == 'translate') {
      final language = await _chooseTranslationLanguage();

      if (!mounted || language == null) {
        return;
      }

      _requestedLanguage = language;
    }

    setState(() {
      _loading = true;
      _selectedMode = mode;
      _result = null;
    });

    try {
      final result = await _service.generateChatAssist(
        mode: mode,
        text: widget.initialText,
        recentMessages: widget.recentMessages,
        languageMode: _requestedLanguage.isEmpty ? 'auto' : 'fixed',
        requestedLanguage: _requestedLanguage,
      );

      if (!mounted) return;

      setState(() {
        _result = result;
      });
    } on MeeraServiceException catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<String?> _chooseTranslationLanguage() {
    return showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        const languages = {
          'en': 'English',
          'en-GB': 'British English',
          'te': 'Telugu',
          'hi': 'Hindi',
          'ta': 'Tamil',
          'kn': 'Kannada',
          'ml': 'Malayalam',
          'bn': 'Bengali',
          'ur': 'Urdu',
          'es': 'Spanish',
          'fr': 'French',
          'de': 'German',
          'pt': 'Portuguese',
          'ar': 'Arabic',
        };

        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.only(bottom: 18),
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(
                  18,
                  4,
                  18,
                  10,
                ),
                child: Text(
                  'Translate to',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              ...languages.entries.map(
                (entry) => ListTile(
                  title: Text(entry.value),
                  onTap: () => Navigator.of(sheetContext).pop(entry.key),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _replace(String text) {
    final value = text.trim();

    if (value.isEmpty) return;

    widget.onReplace(value);
    Navigator.of(context).pop();
  }

  Future<void> _copy(String text) async {
    await Clipboard.setData(
      ClipboardData(text: text),
    );

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          16,
          4,
          16,
          MediaQuery.viewInsetsOf(context).bottom + 18,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  CircleAvatar(
                    backgroundColor: Color(0xFFE9DFFF),
                    child: Icon(
                      Icons.auto_awesome_rounded,
                      color: _purple,
                    ),
                  ),
                  SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Ask Meera',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        Text(
                          'Nothing is sent automatically',
                          style: TextStyle(
                            color: Colors.black54,
                            fontSize: 11.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 15),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _modes
                    .map(
                      (mode) => ActionChip(
                        avatar: _selectedMode == mode.id && _loading
                            ? const SizedBox(
                                width: 15,
                                height: 15,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : null,
                        label: Text(mode.label),
                        onPressed: _loading ? null : () => _run(mode.id),
                      ),
                    )
                    .toList(growable: false),
              ),
              if (_hasSourceText) ...[
                const SizedBox(height: 15),
                _PreviewCard(
                  title: 'Original',
                  text: widget.initialText,
                  muted: true,
                ),
              ],
              if (result != null) ...[
                const SizedBox(height: 10),
                _ResultCard(
                  title: 'Meera suggestion',
                  text: result.result,
                  onReplace: () => _replace(result.result),
                  onCopy: () => _copy(result.result),
                ),
                ...result.alternatives.map(
                  (alternative) => Padding(
                    padding: const EdgeInsets.only(
                      top: 8,
                    ),
                    child: _ResultCard(
                      title: 'Alternative',
                      text: alternative,
                      onReplace: () => _replace(alternative),
                      onCopy: () => _copy(alternative),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (result.responseLanguage.isNotEmpty)
                      Expanded(
                        child: Text(
                          result.responseLanguage,
                          style: const TextStyle(
                            color: Colors.black45,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    TextButton.icon(
                      onPressed: _loading || _selectedMode == null
                          ? null
                          : () => _run(
                                _selectedMode!,
                              ),
                      icon: const Icon(
                        Icons.refresh_rounded,
                      ),
                      label: const Text('Regenerate'),
                    ),
                  ],
                ),
                if (result.safetyFiltered && result.safetyNote.isNotEmpty)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(11),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF3E5),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(
                      result.safetyNote,
                      style: const TextStyle(
                        color: Color(0xFF8B5A20),
                        fontSize: 11.5,
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({
    required this.title,
    required this.text,
    required this.muted,
  });

  final String title;
  final String text;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: muted ? const Color(0xFFF5F1F8) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFE6DDED),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Colors.black45,
              fontSize: 10.5,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            text,
            style: const TextStyle(height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.title,
    required this.text,
    required this.onReplace,
    required this.onCopy,
  });

  final String title;
  final String text;
  final VoidCallback onReplace;
  final VoidCallback onCopy;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFDCCEF0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF7B4EFF),
              fontSize: 10.5,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            text,
            style: const TextStyle(height: 1.4),
          ),
          const SizedBox(height: 9),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton.icon(
                onPressed: onCopy,
                icon: const Icon(
                  Icons.copy_rounded,
                  size: 17,
                ),
                label: const Text('Copy'),
              ),
              const SizedBox(width: 5),
              FilledButton.tonal(
                onPressed: onReplace,
                child: const Text('Use this'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
