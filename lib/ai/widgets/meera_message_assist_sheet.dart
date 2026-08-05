import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/meera_chat_assist.dart';
import '../services/meera_service.dart';

class MeeraMessageAssistSheet extends StatefulWidget {
  const MeeraMessageAssistSheet({
    super.key,
    required this.mode,
    required this.sourceText,
    required this.recentMessages,
    required this.onUse,
    this.requestedLanguage = '',
  });

  final String mode;
  final String sourceText;
  final List<Map<String, String>> recentMessages;
  final ValueChanged<String> onUse;
  final String requestedLanguage;

  @override
  State<MeeraMessageAssistSheet> createState() =>
      _MeeraMessageAssistSheetState();
}

class _MeeraMessageAssistSheetState extends State<MeeraMessageAssistSheet> {
  static const _purple = Color(0xFF7B4EFF);

  final MeeraService _service = MeeraService();

  bool _loading = true;
  String? _error;
  MeeraChatAssistResult? _result;

  bool get _isTranslation => widget.mode == 'translate';

  String get _title => _isTranslation ? 'Translate message' : 'Smart replies';

  String get _loadingLabel =>
      _isTranslation ? 'Meera is translating…' : 'Meera is creating replies…';

  @override
  void initState() {
    super.initState();
    _generate();
  }

  Future<void> _generate() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await _service.generateChatAssist(
        mode: widget.mode,
        text: widget.sourceText,
        recentMessages: widget.recentMessages,
        languageMode: widget.requestedLanguage.isEmpty ? 'auto' : 'fixed',
        requestedLanguage: widget.requestedLanguage,
      );

      if (!mounted) return;

      setState(() {
        _result = result;
      });
    } on MeeraServiceException catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.message;
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  List<String> get _suggestions {
    final result = _result;

    if (result == null) return const [];

    final values = <String>[
      result.result,
      ...result.alternatives,
    ];

    final unique = <String>[];

    for (final value in values) {
      final trimmed = value.trim();

      if (trimmed.isEmpty) continue;

      final exists = unique.any(
        (item) => item.toLowerCase() == trimmed.toLowerCase(),
      );

      if (!exists) {
        unique.add(trimmed);
      }
    }

    return unique.take(4).toList(
          growable: false,
        );
  }

  Future<void> _copy(String value) async {
    await Clipboard.setData(
      ClipboardData(text: value),
    );

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied'),
      ),
    );
  }

  void _use(String value) {
    final text = value.trim();

    if (text.isEmpty) return;

    widget.onUse(text);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    final suggestions = _suggestions;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          16,
          4,
          16,
          20,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const CircleAvatar(
                    backgroundColor: Color(0xFFE9DFFF),
                    child: Icon(
                      Icons.auto_awesome_rounded,
                      color: _purple,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _title,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const Text(
                          'Review before sending',
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
              _MessagePreviewCard(
                title: 'Original message',
                text: widget.sourceText,
              ),
              const SizedBox(height: 12),
              if (_loading)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    vertical: 26,
                  ),
                  child: Center(
                    child: Column(
                      children: [
                        const CircularProgressIndicator(),
                        const SizedBox(height: 12),
                        Text(_loadingLabel),
                      ],
                    ),
                  ),
                )
              else if (_error != null)
                _ErrorCard(
                  message: _error!,
                  onRetry: _generate,
                )
              else if (suggestions.isEmpty)
                _ErrorCard(
                  message: 'Meera could not generate a result.',
                  onRetry: _generate,
                )
              else ...[
                if (_isTranslation)
                  _TranslationResultCard(
                    text: suggestions.first,
                    responseLanguage: result?.responseLanguage ?? '',
                    onCopy: () => _copy(suggestions.first),
                    onUse: () => _use(suggestions.first),
                  )
                else
                  ...suggestions.asMap().entries.map(
                    (entry) {
                      return Padding(
                        padding: const EdgeInsets.only(
                          bottom: 9,
                        ),
                        child: _ReplySuggestionCard(
                          number: entry.key + 1,
                          text: entry.value,
                          onCopy: () => _copy(entry.value),
                          onUse: () => _use(entry.value),
                        ),
                      );
                    },
                  ),
                Row(
                  children: [
                    if ((result?.responseLanguage ?? '').isNotEmpty)
                      Expanded(
                        child: Text(
                          result!.responseLanguage,
                          style: const TextStyle(
                            color: Colors.black45,
                            fontSize: 11,
                          ),
                        ),
                      )
                    else
                      const Spacer(),
                    TextButton.icon(
                      onPressed: _loading ? null : _generate,
                      icon: const Icon(
                        Icons.refresh_rounded,
                      ),
                      label: const Text('Regenerate'),
                    ),
                  ],
                ),
                if (result?.safetyFiltered == true &&
                    (result?.safetyNote ?? '').isNotEmpty)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(11),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF3E5),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(
                      result!.safetyNote,
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

class _MessagePreviewCard extends StatelessWidget {
  const _MessagePreviewCard({
    required this.title,
    required this.text,
  });

  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F1F8),
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

class _ReplySuggestionCard extends StatelessWidget {
  const _ReplySuggestionCard({
    required this.number,
    required this.text,
    required this.onCopy,
    required this.onUse,
  });

  final int number;
  final String text;
  final VoidCallback onCopy;
  final VoidCallback onUse;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(17),
        border: Border.all(
          color: const Color(0xFFDCCEF0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'REPLY $number',
            style: const TextStyle(
              color: Color(0xFF7B4EFF),
              fontSize: 10.5,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
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
                onPressed: onUse,
                child: const Text(
                  'Use as reply',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TranslationResultCard extends StatelessWidget {
  const _TranslationResultCard({
    required this.text,
    required this.responseLanguage,
    required this.onCopy,
    required this.onUse,
  });

  final String text;
  final String responseLanguage;
  final VoidCallback onCopy;
  final VoidCallback onUse;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFDCCEF0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.translate_rounded,
                color: Color(0xFF7B4EFF),
                size: 19,
              ),
              const SizedBox(width: 7),
              const Text(
                'Translation',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                ),
              ),
              if (responseLanguage.isNotEmpty) ...[
                const Spacer(),
                Text(
                  responseLanguage,
                  style: const TextStyle(
                    color: Colors.black45,
                    fontSize: 10.5,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          Text(
            text,
            style: const TextStyle(
              height: 1.45,
              fontSize: 14.5,
            ),
          ),
          const SizedBox(height: 11),
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
                onPressed: onUse,
                child: const Text(
                  'Reply using this',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFECEF),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Text(
            message,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 9),
          FilledButton.tonal(
            onPressed: onRetry,
            child: const Text('Try again'),
          ),
        ],
      ),
    );
  }
}
