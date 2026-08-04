class MeeraSuggestedAction {
  const MeeraSuggestedAction({
    required this.id,
    required this.label,
    required this.actionType,
    required this.payload,
    required this.requiresConfirmation,
  });

  final String id;
  final String label;
  final String actionType;
  final String payload;
  final bool requiresConfirmation;

  factory MeeraSuggestedAction.fromMap(
    Map<String, dynamic> map,
  ) {
    return MeeraSuggestedAction(
      id: (map['id'] ?? '').toString().trim(),
      label: (map['label'] ?? '').toString().trim(),
      actionType: (map['actionType'] ?? 'none').toString().trim(),
      payload: (map['payload'] ?? '').toString(),
      requiresConfirmation: map['requiresConfirmation'] == true,
    );
  }
}

class MeeraMessage {
  const MeeraMessage({
    required this.role,
    required this.content,
    required this.createdAt,
    this.detectedLanguage,
    this.responseLanguage,
    this.category,
    this.requiresHumanSupport = false,
    this.escalationReason,
    this.actions = const [],
    this.isError = false,
  });

  final String role;
  final String content;
  final DateTime createdAt;

  final String? detectedLanguage;
  final String? responseLanguage;
  final String? category;

  final bool requiresHumanSupport;
  final String? escalationReason;

  final List<MeeraSuggestedAction> actions;
  final bool isError;

  bool get isUser => role == 'user';

  Map<String, dynamic> toHistoryMap() {
    return {
      'role': role,
      'content': content,
    };
  }
}

class MeeraAssistantResult {
  const MeeraAssistantResult({
    required this.answer,
    required this.detectedLanguage,
    required this.responseLanguage,
    required this.languageMode,
    required this.category,
    required this.requiresHumanSupport,
    required this.escalationReason,
    required this.actions,
    required this.used,
    required this.limit,
    required this.remaining,
  });

  final String answer;
  final String detectedLanguage;
  final String responseLanguage;
  final String languageMode;
  final String category;

  final bool requiresHumanSupport;
  final String escalationReason;

  final List<MeeraSuggestedAction> actions;

  final int used;
  final int limit;
  final int remaining;

  factory MeeraAssistantResult.fromMap(
    Map<String, dynamic> map,
  ) {
    final usage = map['usage'] is Map
        ? Map<String, dynamic>.from(
            map['usage'] as Map,
          )
        : <String, dynamic>{};

    final rawActions = map['suggestedActions'] is List
        ? map['suggestedActions'] as List
        : const [];

    return MeeraAssistantResult(
      answer: (map['answer'] ?? '').toString().trim(),
      detectedLanguage: (map['detectedLanguage'] ?? 'Unknown').toString(),
      responseLanguage: (map['responseLanguage'] ?? 'Unknown').toString(),
      languageMode: (map['languageMode'] ?? 'auto').toString(),
      category: (map['category'] ?? 'general').toString(),
      requiresHumanSupport: map['requiresHumanSupport'] == true,
      escalationReason: (map['escalationReason'] ?? '').toString(),
      actions: rawActions
          .whereType<Map>()
          .map(
            (item) => MeeraSuggestedAction.fromMap(
              Map<String, dynamic>.from(item),
            ),
          )
          .toList(growable: false),
      used: _toInt(usage['used']),
      limit: _toInt(usage['limit']),
      remaining: _toInt(usage['remaining']),
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();

    return int.tryParse(
          value?.toString() ?? '',
        ) ??
        0;
  }
}
