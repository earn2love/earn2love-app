class PlayPrompt {
  const PlayPrompt({
    required this.id,
    required this.type,
    required this.text,
    required this.comfort,
    required this.language,
    required this.source,
    required this.hostIntroduction,
    required this.followUpHint,
    required this.visualTheme,
    required this.consentReminder,
  });

  final String id;
  final String type;
  final String text;
  final String comfort;
  final String language;
  final String source;

  final String hostIntroduction;
  final String followUpHint;
  final String visualTheme;
  final String consentReminder;

  bool get isAiGenerated => source == 'openai';

  factory PlayPrompt.fromMap(Map<String, dynamic> map) {
    return PlayPrompt(
      id: (map['id'] ?? '').toString(),
      type: (map['type'] ?? 'discussion').toString(),
      text: (map['text'] ?? '').toString(),
      comfort: (map['comfort'] ?? 'standard').toString(),
      language: (map['language'] ?? 'en').toString(),
      source: (map['source'] ?? 'curated_fallback').toString(),
      hostIntroduction: (map['hostIntroduction'] ?? '').toString().trim(),
      followUpHint: (map['followUpHint'] ?? '').toString().trim(),
      visualTheme: (map['visualTheme'] ?? '').toString().trim(),
      consentReminder: (map['consentReminder'] ?? '').toString().trim(),
    );
  }
}

class PlayResponse {
  const PlayResponse({
    required this.text,
    required this.skipped,
  });

  final String text;
  final bool skipped;

  factory PlayResponse.fromMap(Map<String, dynamic> map) {
    return PlayResponse(
      text: (map['text'] ?? '').toString(),
      skipped: map['skipped'] == true,
    );
  }
}

class PlayHostReaction {
  const PlayHostReaction({
    required this.reaction,
    required this.sharedInsight,
    required this.nextRoundTone,
  });

  final String reaction;
  final String sharedInsight;
  final String nextRoundTone;

  factory PlayHostReaction.fromMap(Map<String, dynamic> map) {
    return PlayHostReaction(
      reaction: (map['reaction'] ?? '').toString().trim(),
      sharedInsight: (map['sharedInsight'] ?? '').toString().trim(),
      nextRoundTone: (map['nextRoundTone'] ?? 'same').toString().trim(),
    );
  }
}

class PlaySession {
  const PlaySession({
    required this.sessionId,
    required this.experienceId,
    required this.experienceTitle,
    required this.status,
    required this.hostUid,
    required this.inviteCode,
    required this.language,
    required this.comfortLevel,
    required this.hostComfort,
    required this.guestComfort,
    required this.effectiveComfort,
    required this.adultEligible,
    required this.hostReady,
    required this.guestReady,
    required this.currentRound,
    required this.maxRounds,
    required this.replacementCount,
    required this.generationState,
    this.guestUid,
    this.currentPrompt,
    this.hostResponse,
    this.guestResponse,
    this.hostReaction,
  });

  final String sessionId;
  final String experienceId;
  final String experienceTitle;
  final String status;
  final String hostUid;
  final String? guestUid;
  final String inviteCode;
  final String language;

  final String comfortLevel;
  final String hostComfort;
  final String guestComfort;
  final String effectiveComfort;
  final bool adultEligible;

  final bool hostReady;
  final bool guestReady;

  final int currentRound;
  final int maxRounds;
  final int replacementCount;

  final String generationState;

  final PlayPrompt? currentPrompt;
  final PlayResponse? hostResponse;
  final PlayResponse? guestResponse;
  final PlayHostReaction? hostReaction;

  bool get isGenerating =>
      status == 'generating' || generationState == 'generating';

  factory PlaySession.fromMap(Map<String, dynamic> map) {
    final rawPrompt = map['currentPrompt'];
    final rawHostResponse = map['hostResponse'];
    final rawGuestResponse = map['guestResponse'];
    final rawHostReaction = map['hostReaction'];

    return PlaySession(
      sessionId: (map['sessionId'] ?? '').toString(),
      experienceId: (map['experienceId'] ?? '').toString(),
      experienceTitle: (map['experienceTitle'] ?? 'Play Together').toString(),
      status: (map['status'] ?? 'waiting').toString(),
      hostUid: (map['hostUid'] ?? '').toString(),
      guestUid: map['guestUid']?.toString(),
      inviteCode: (map['inviteCode'] ?? '').toString(),
      language: (map['language'] ?? 'en').toString(),
      comfortLevel: (map['comfortLevel'] ?? 'standard').toString(),
      hostComfort: (map['hostComfort'] ?? 'standard').toString(),
      guestComfort: (map['guestComfort'] ?? 'standard').toString(),
      effectiveComfort: (map['effectiveComfort'] ?? 'standard').toString(),
      adultEligible: map['adultEligible'] == true,
      hostReady: map['hostReady'] == true,
      guestReady: map['guestReady'] == true,
      currentRound: (map['currentRound'] as num?)?.toInt() ?? 0,
      maxRounds: (map['maxRounds'] as num?)?.toInt() ?? 10,
      replacementCount: (map['replacementCount'] as num?)?.toInt() ?? 0,
      generationState: (map['generationState'] ?? 'idle').toString(),
      currentPrompt: rawPrompt is Map
          ? PlayPrompt.fromMap(
              Map<String, dynamic>.from(rawPrompt),
            )
          : null,
      hostResponse: rawHostResponse is Map
          ? PlayResponse.fromMap(
              Map<String, dynamic>.from(rawHostResponse),
            )
          : null,
      guestResponse: rawGuestResponse is Map
          ? PlayResponse.fromMap(
              Map<String, dynamic>.from(rawGuestResponse),
            )
          : null,
      hostReaction: rawHostReaction is Map
          ? PlayHostReaction.fromMap(
              Map<String, dynamic>.from(rawHostReaction),
            )
          : null,
    );
  }
}
