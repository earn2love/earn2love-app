class MeeraProfileImprovement {
  const MeeraProfileImprovement({
    required this.area,
    required this.priority,
    required this.reason,
    required this.suggestion,
  });

  final String area;
  final String priority;
  final String reason;
  final String suggestion;

  factory MeeraProfileImprovement.fromMap(
    Map<String, dynamic> map,
  ) {
    return MeeraProfileImprovement(
      area: (map['area'] ?? 'profile_completion').toString().trim(),
      priority: (map['priority'] ?? 'medium').toString().trim(),
      reason: (map['reason'] ?? '').toString().trim(),
      suggestion: (map['suggestion'] ?? '').toString().trim(),
    );
  }
}

class MeeraBioSuggestion {
  const MeeraBioSuggestion({
    required this.style,
    required this.bio,
  });

  final String style;
  final String bio;

  factory MeeraBioSuggestion.fromMap(
    Map<String, dynamic> map,
  ) {
    return MeeraBioSuggestion(
      style: (map['style'] ?? 'friendly').toString(),
      bio: (map['bio'] ?? '').toString().trim(),
    );
  }
}

class MeeraProfileCoachResult {
  const MeeraProfileCoachResult({
    required this.score,
    required this.summary,
    required this.strengths,
    required this.improvements,
    required this.bioSuggestions,
    required this.suggestedInterests,
    required this.conversationStyle,
    required this.photoGuidance,
    required this.responseLanguage,
    required this.used,
    required this.limit,
    required this.remaining,
  });

  final int score;
  final String summary;
  final List<String> strengths;

  final List<MeeraProfileImprovement> improvements;
  final List<MeeraBioSuggestion> bioSuggestions;
  final List<String> suggestedInterests;

  final String conversationStyle;
  final List<String> photoGuidance;
  final String responseLanguage;

  final int used;
  final int limit;
  final int remaining;

  factory MeeraProfileCoachResult.fromMap(
    Map<String, dynamic> map,
  ) {
    final usage = map['usage'] is Map
        ? Map<String, dynamic>.from(
            map['usage'] as Map,
          )
        : <String, dynamic>{};

    return MeeraProfileCoachResult(
      score: _toInt(map['score']),
      summary: (map['summary'] ?? '').toString().trim(),
      strengths: _stringList(map['strengths']),
      improvements: _mapList(
        map['improvements'],
      )
          .map(
            MeeraProfileImprovement.fromMap,
          )
          .toList(growable: false),
      bioSuggestions: _mapList(
        map['bioSuggestions'],
      )
          .map(MeeraBioSuggestion.fromMap)
          .where((item) => item.bio.isNotEmpty)
          .toList(growable: false),
      suggestedInterests: _stringList(map['suggestedInterests']),
      conversationStyle: (map['conversationStyle'] ?? '').toString().trim(),
      photoGuidance: _stringList(map['photoGuidance']),
      responseLanguage: (map['responseLanguage'] ?? '').toString().trim(),
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

  static List<String> _stringList(dynamic value) {
    if (value is! List) return const [];

    return value
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }

  static List<Map<String, dynamic>> _mapList(
    dynamic value,
  ) {
    if (value is! List) return const [];

    return value
        .whereType<Map>()
        .map(
          (item) => Map<String, dynamic>.from(
            item,
          ),
        )
        .toList(growable: false);
  }
}
