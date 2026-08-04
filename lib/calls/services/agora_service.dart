import 'dart:async';

import 'package:agora_rtc_engine/agora_rtc_engine.dart';

import '../models/call_session.dart';

class AgoraServiceException implements Exception {
  const AgoraServiceException(
    this.message, {
    this.originalError,
  });

  final String message;
  final Object? originalError;

  @override
  String toString() => message;
}

class AgoraService {
  RtcEngine? _engine;
  RtcEngineEventHandler? _eventHandler;

  final StreamController<int> _remoteUserController =
      StreamController<int>.broadcast();

  final StreamController<CallStatus> _statusController =
      StreamController<CallStatus>.broadcast();

  final StreamController<String> _errorController =
      StreamController<String>.broadcast();

  int? _remoteUid;
  bool _joined = false;
  bool _muted = false;
  bool _speakerEnabled = true;
  bool _videoEnabled = false;

  Stream<int> get remoteUserStream => _remoteUserController.stream;
  Stream<CallStatus> get statusStream => _statusController.stream;
  Stream<String> get errorStream => _errorController.stream;

  RtcEngine? get engine => _engine;
  int? get remoteUid => _remoteUid;
  bool get joined => _joined;
  bool get muted => _muted;
  bool get speakerEnabled => _speakerEnabled;
  bool get videoEnabled => _videoEnabled;

  Future<void> initialize({
    required String appId,
    required bool enableVideo,
  }) async {
    if (appId.trim().isEmpty) {
      throw const AgoraServiceException(
        'Agora App ID is missing.',
      );
    }

    await disposeEngine();

    try {
      final engine = createAgoraRtcEngine();

      await engine.initialize(
        RtcEngineContext(
          appId: appId.trim(),
          channelProfile: ChannelProfileType.channelProfileCommunication,
        ),
      );

      _videoEnabled = enableVideo;

      _eventHandler = RtcEngineEventHandler(
        onJoinChannelSuccess: (
          RtcConnection connection,
          int elapsed,
        ) {
          _joined = true;
          _statusController.add(CallStatus.connected);
        },
        onUserJoined: (
          RtcConnection connection,
          int remoteUid,
          int elapsed,
        ) {
          _remoteUid = remoteUid;
          _remoteUserController.add(remoteUid);
        },
        onUserOffline: (
          RtcConnection connection,
          int remoteUid,
          UserOfflineReasonType reason,
        ) {
          if (_remoteUid == remoteUid) {
            _remoteUid = null;
          }

          _remoteUserController.add(0);
        },
        onConnectionStateChanged: (
          RtcConnection connection,
          ConnectionStateType state,
          ConnectionChangedReasonType reason,
        ) {
          if (state == ConnectionStateType.connectionStateConnecting) {
            _statusController.add(CallStatus.connecting);
          }

          if (state == ConnectionStateType.connectionStateFailed) {
            _statusController.add(CallStatus.failed);
          }
        },
        onError: (
          ErrorCodeType errorCode,
          String message,
        ) {
          _errorController.add(
            'Agora error ${errorCode.name}: $message',
          );
        },
        onTokenPrivilegeWillExpire: (
          RtcConnection connection,
          String token,
        ) {
          _errorController.add(
            'Agora token will expire soon.',
          );
        },
      );

      engine.registerEventHandler(_eventHandler!);

      await engine.enableAudio();
      await engine.setEnableSpeakerphone(true);

      if (enableVideo) {
        await engine.enableVideo();
        await engine.startPreview();
      } else {
        await engine.disableVideo();
      }

      _engine = engine;
      _muted = false;
      _speakerEnabled = true;
      _remoteUid = null;
    } catch (error) {
      await disposeEngine();

      throw AgoraServiceException(
        'Agora could not be initialized: $error',
        originalError: error,
      );
    }
  }

  Future<void> join({
    required AgoraCredentials credentials,
    required CallType callType,
  }) async {
    final engine = _engine;

    if (engine == null) {
      throw const AgoraServiceException(
        'Agora has not been initialized.',
      );
    }

    _statusController.add(CallStatus.connecting);

    try {
      await engine.joinChannel(
        token: credentials.token,
        channelId: credentials.channelName,
        uid: credentials.uid,
        options: ChannelMediaOptions(
          autoSubscribeAudio: true,
          autoSubscribeVideo: callType == CallType.video,
          publishMicrophoneTrack: true,
          publishCameraTrack: callType == CallType.video,
          clientRoleType: ClientRoleType.clientRoleBroadcaster,
          channelProfile: ChannelProfileType.channelProfileCommunication,
        ),
      );
    } catch (error) {
      _statusController.add(CallStatus.failed);

      throw AgoraServiceException(
        'Agora channel join failed: $error',
        originalError: error,
      );
    }
  }

  Future<void> renewToken(String token) async {
    final engine = _engine;

    if (engine == null || token.trim().isEmpty) return;

    await engine.renewToken(token.trim());
  }

  Future<bool> toggleMute() async {
    final engine = _engine;

    if (engine == null) return _muted;

    _muted = !_muted;
    await engine.muteLocalAudioStream(_muted);

    return _muted;
  }

  Future<bool> toggleSpeaker() async {
    final engine = _engine;

    if (engine == null) return _speakerEnabled;

    _speakerEnabled = !_speakerEnabled;
    await engine.setEnableSpeakerphone(_speakerEnabled);

    return _speakerEnabled;
  }

  Future<void> switchCamera() async {
    final engine = _engine;

    if (engine == null || !_videoEnabled) return;

    await engine.switchCamera();
  }

  Future<void> leave() async {
    final engine = _engine;

    if (engine == null) return;

    try {
      await engine.leaveChannel();
    } finally {
      _joined = false;
      _remoteUid = null;
      _statusController.add(CallStatus.ended);
    }
  }

  Future<void> disposeEngine() async {
    final engine = _engine;
    final handler = _eventHandler;

    _engine = null;
    _eventHandler = null;
    _joined = false;
    _remoteUid = null;

    if (engine == null) return;

    try {
      if (handler != null) {
        engine.unregisterEventHandler(handler);
      }

      await engine.leaveChannel();

      if (_videoEnabled) {
        await engine.stopPreview();
      }
    } catch (_) {
      // Cleanup should continue even if the channel is already closed.
    }

    await engine.release();
  }

  Future<void> dispose() async {
    await disposeEngine();

    if (!_remoteUserController.isClosed) {
      await _remoteUserController.close();
    }

    if (!_statusController.isClosed) {
      await _statusController.close();
    }

    if (!_errorController.isClosed) {
      await _errorController.close();
    }
  }
}
