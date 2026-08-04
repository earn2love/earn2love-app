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
    required this.hostReady,
    required this.guestReady,
    required this.currentRound,
    this.guestUid,
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
  final bool hostReady;
  final bool guestReady;
  final int currentRound;

  factory PlaySession.fromMap(
    Map<String, dynamic> map,
  ) {
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
      hostReady: map['hostReady'] == true,
      guestReady: map['guestReady'] == true,
      currentRound: (map['currentRound'] as num?)?.toInt() ?? 0,
    );
  }
}
