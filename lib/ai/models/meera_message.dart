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
    required this.conversationId,
    required this.conversationCreated,
    required this.conversationTitle,
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

  final String conversationId;
  final bool conversationCreated;
  final String conversationTitle;

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
      conversationId: (map['conversationId'] ?? '').toString(),
      conversationCreated: map['conversationCreated'] == true,
      conversationTitle: (map['conversationTitle'] ?? '').toString(),
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

class MeeraConversationSummary {
  const MeeraConversationSummary({
    required this.id,
    required this.title,
    required this.lastMessage,
    required this.lastRole,
    required this.messageCount,
    required this.languageMode,
    required this.requestedLanguage,
    this.updatedAt,
  });

  final String id;
  final String title;
  final String lastMessage;
  final String lastRole;
  final int messageCount;
  final String languageMode;
  final String requestedLanguage;
  final DateTime? updatedAt;

  factory MeeraConversationSummary.fromMap(
    Map<String, dynamic> map,
  ) {
    return MeeraConversationSummary(
      id: (map['id'] ?? '').toString(),
      title: (map['title'] ?? 'New conversation').toString().trim(),
      lastMessage: (map['lastMessage'] ?? '').toString().trim(),
      lastRole: (map['lastRole'] ?? '').toString().trim(),
      messageCount: MeeraAssistantResult._toInt(
        map['messageCount'],
      ),
      languageMode: (map['languageMode'] ?? 'auto').toString(),
      requestedLanguage: (map['requestedLanguage'] ?? '').toString(),
      updatedAt: _dateFromValue(map['updatedAt']),
    );
  }

  static DateTime? _dateFromValue(dynamic value) {
    if (value == null) return null;

    try {
      final dynamic date = value.toDate();
      return date as DateTime;
    } catch (_) {
      return DateTime.tryParse(value.toString());
    }
  }
}

class MeeraMemory {
  const MeeraMemory({
    required this.id,
    required this.content,
    required this.category,
    required this.source,
  });

  final String id;
  final String content;
  final String category;
  final String source;

  factory MeeraMemory.fromMap(
    Map<String, dynamic> map,
  ) {
    return MeeraMemory(
      id: (map['id'] ?? '').toString(),
      content: (map['content'] ?? '').toString().trim(),
      category: (map['category'] ?? 'preference').toString().trim(),
      source: (map['source'] ?? 'user_confirmed').toString().trim(),
    );
  }
}
