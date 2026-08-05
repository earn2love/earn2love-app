class MeeraChatAssistResult {
  const MeeraChatAssistResult({
    required this.result,
    required this.alternatives,
    required this.detectedLanguage,
    required this.responseLanguage,
    required this.detectedTone,
    required this.mode,
    required this.safetyFiltered,
    required this.safetyNote,
    required this.used,
    required this.limit,
    required this.remaining,
  });

  final String result;
  final List<String> alternatives;

  final String detectedLanguage;
  final String responseLanguage;
  final String detectedTone;
  final String mode;

  final bool safetyFiltered;
  final String safetyNote;

  final int used;
  final int limit;
  final int remaining;

  factory MeeraChatAssistResult.fromMap(
    Map<String, dynamic> map,
  ) {
    final usage = map['usage'] is Map
        ? Map<String, dynamic>.from(
            map['usage'] as Map,
          )
        : <String, dynamic>{};

    final alternatives = map['alternatives'] is List
        ? (map['alternatives'] as List)
            .map(
              (item) => item.toString().trim(),
            )
            .where(
              (item) => item.isNotEmpty,
            )
            .toList(growable: false)
        : const <String>[];

    return MeeraChatAssistResult(
      result: (map['result'] ?? '').toString().trim(),
      alternatives: alternatives,
      detectedLanguage: (map['detectedLanguage'] ?? '').toString().trim(),
      responseLanguage: (map['responseLanguage'] ?? '').toString().trim(),
      detectedTone: (map['detectedTone'] ?? 'unclear').toString().trim(),
      mode: (map['mode'] ?? 'improve').toString().trim(),
      safetyFiltered: map['safetyFiltered'] == true,
      safetyNote: (map['safetyNote'] ?? '').toString().trim(),
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

class MeeraChatAssistMode {
  const MeeraChatAssistMode({
    required this.id,
    required this.label,
    required this.description,
  });

  final String id;
  final String label;
  final String description;
}
