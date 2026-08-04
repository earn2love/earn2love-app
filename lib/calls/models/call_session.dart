enum CallType {
  audio,
  video;

  String get apiValue => name;

  static CallType fromValue(dynamic value) {
    return value?.toString().trim().toLowerCase() == 'video'
        ? CallType.video
        : CallType.audio;
  }
}

enum CallStatus {
  preparing,
  ringing,
  connecting,
  connected,
  ended,
  failed,
}

class CallSession {
  const CallSession({
    required this.callId,
    required this.channelName,
    required this.type,
    required this.callerUid,
    required this.calleeUid,
    required this.ratePerMinute,
    required this.isCaller,
  });

  final String callId;
  final String channelName;
  final CallType type;
  final String callerUid;
  final String calleeUid;
  final int ratePerMinute;
  final bool isCaller;

  bool get isVideo => type == CallType.video;

  CallSession copyWith({
    String? callId,
    String? channelName,
    CallType? type,
    String? callerUid,
    String? calleeUid,
    int? ratePerMinute,
    bool? isCaller,
  }) {
    return CallSession(
      callId: callId ?? this.callId,
      channelName: channelName ?? this.channelName,
      type: type ?? this.type,
      callerUid: callerUid ?? this.callerUid,
      calleeUid: calleeUid ?? this.calleeUid,
      ratePerMinute: ratePerMinute ?? this.ratePerMinute,
      isCaller: isCaller ?? this.isCaller,
    );
  }

  Map<String, dynamic> toMap() {
    return <String, dynamic>{
      'callId': callId,
      'channelName': channelName,
      'type': type.apiValue,
      'callerUid': callerUid,
      'calleeUid': calleeUid,
      'ratePerMinute': ratePerMinute,
      'isCaller': isCaller,
    };
  }
}

class AgoraCredentials {
  const AgoraCredentials({
    required this.appId,
    required this.token,
    required this.channelName,
    required this.uid,
    required this.expiresAt,
  });

  final String appId;
  final String token;
  final String channelName;
  final int uid;
  final int expiresAt;

  factory AgoraCredentials.fromMap(Map<String, dynamic> map) {
    return AgoraCredentials(
      appId: _requiredString(map['appId'], 'appId'),
      token: _requiredString(map['token'], 'token'),
      channelName: _requiredString(
        map['channelName'],
        'channelName',
      ),
      uid: _asInt(map['uid']),
      expiresAt: _asInt(map['expiresAt']),
    );
  }
}

class EndCallResult {
  const EndCallResult({
    required this.ok,
    required this.alreadyCharged,
    required this.charge,
    required this.reward,
    required this.billedMinutes,
  });

  final bool ok;
  final bool alreadyCharged;
  final int charge;
  final int reward;
  final int billedMinutes;

  factory EndCallResult.fromMap(Map<String, dynamic> map) {
    return EndCallResult(
      ok: map['ok'] == true,
      alreadyCharged: map['alreadyCharged'] == true,
      charge: _asInt(map['charge']),
      reward: _asInt(map['reward']),
      billedMinutes: _asInt(map['billedMinutes']),
    );
  }
}

String _requiredString(dynamic value, String field) {
  final result = value?.toString().trim() ?? '';

  if (result.isEmpty) {
    throw StateError('Missing required call field: $field');
  }

  return result;
}

int _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

class CallPricingConfig {
  const CallPricingConfig({
    required this.enabled,
    required this.audioCallerPerMinute,
    required this.videoCallerPerMinute,
    required this.audioRewardPercent,
    required this.videoRewardPercent,
    required this.billingIncrementSeconds,
    required this.minimumBillableSeconds,
  });

  final bool enabled;
  final int audioCallerPerMinute;
  final int videoCallerPerMinute;
  final int audioRewardPercent;
  final int videoRewardPercent;
  final int billingIncrementSeconds;
  final int minimumBillableSeconds;

  factory CallPricingConfig.fromMap(
    Map<String, dynamic> map,
  ) {
    final audio = map['audio'] is Map
        ? Map<String, dynamic>.from(
            map['audio'] as Map,
          )
        : <String, dynamic>{};

    final video = map['video'] is Map
        ? Map<String, dynamic>.from(
            map['video'] as Map,
          )
        : <String, dynamic>{};

    return CallPricingConfig(
      enabled: map['enabled'] != false,
      audioCallerPerMinute: _asInt(audio['callerPerMinute']),
      videoCallerPerMinute: _asInt(video['callerPerMinute']),
      audioRewardPercent: _asInt(audio['receiverRewardPercent']),
      videoRewardPercent: _asInt(video['receiverRewardPercent']),
      billingIncrementSeconds: _asInt(map['billingIncrementSeconds']),
      minimumBillableSeconds: _asInt(map['minimumBillableSeconds']),
    );
  }
}
