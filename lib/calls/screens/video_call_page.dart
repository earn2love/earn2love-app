import 'dart:async';

import 'package:agora_rtc_engine/agora_rtc_engine.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../models/call_session.dart';
import '../services/agora_service.dart';
import '../services/call_service.dart';

class VideoCallPage extends StatefulWidget {
  const VideoCallPage({
    super.key,
    required this.session,
    required this.otherName,
    required this.otherPhotoUrl,
    required this.callService,
    required this.agoraService,
  });

  final CallSession session;
  final String otherName;
  final String otherPhotoUrl;
  final CallService callService;
  final AgoraService agoraService;

  @override
  State<VideoCallPage> createState() => _VideoCallPageState();
}

class _VideoCallPageState extends State<VideoCallPage> {
  StreamSubscription<CallStatus>? _statusSub;
  StreamSubscription<int>? _remoteSub;
  StreamSubscription<String>? _errorSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _callStateSub;

  Timer? _timer;

  CallStatus _status = CallStatus.preparing;

  bool _muted = false;
  bool _speakerEnabled = true;
  bool _cameraEnabled = true;
  bool _remoteJoined = false;
  bool _everRemoteJoined = false;
  bool _ending = false;

  int _durationSeconds = 0;
  int? _remoteUid;

  String _serverStatus = 'ringing';
  String? _error;

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    _listenToServerCallState();

    _statusSub = widget.agoraService.statusStream.listen(
      (status) {
        if (!mounted) return;

        setState(() {
          _status = status;
        });
      },
    );

    _remoteSub = widget.agoraService.remoteUserStream.listen(
      (uid) {
        if (!mounted || _ending) return;

        final joined = uid > 0;
        final remoteLeftAfterConnection = !joined && _everRemoteJoined;

        setState(() {
          _remoteJoined = joined;
          _remoteUid = joined ? uid : null;

          if (joined) {
            _everRemoteJoined = true;
          }
        });

        if (joined) {
          _startConnectedTimer();
        } else if (remoteLeftAfterConnection) {
          unawaited(_endCall());
        }
      },
    );

    _errorSub = widget.agoraService.errorStream.listen(
      (message) {
        if (!mounted) return;

        setState(() {
          _error = message;
          _status = CallStatus.failed;
        });
      },
    );

    try {
      final credentials = await widget.callService.generateAgoraToken(
        channelName: widget.session.channelName,
        agoraUid: 0,
      );

      await widget.agoraService.initialize(
        appId: credentials.appId,
        enableVideo: true,
      );

      if (!mounted) return;

      setState(() {
        _status = CallStatus.connecting;
      });

      await widget.agoraService.join(
        credentials: credentials,
        callType: CallType.video,
      );
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _status = CallStatus.failed;
        _error = error.toString();
      });
    }
  }

  void _startConnectedTimer() {
    if (_timer != null || !_everRemoteJoined) return;

    _timer = Timer.periodic(
      const Duration(seconds: 1),
      (_) {
        if (!mounted || _ending) return;

        setState(() {
          _durationSeconds++;
        });
      },
    );
  }

  void _listenToServerCallState() {
    _callStateSub?.cancel();

    _callStateSub = FirebaseFirestore.instance
        .collection('calls')
        .doc(widget.session.callId)
        .snapshots()
        .listen(
      (snapshot) {
        if (!mounted || _ending || !snapshot.exists) return;

        final data = snapshot.data() ?? <String, dynamic>{};
        final status = data['status']?.toString().trim() ?? '';

        if (status.isEmpty) return;

        _serverStatus = status;

        if (status == 'rejected') {
          unawaited(
            _finishWithoutBilling('Video call rejected'),
          );
        } else if (status == 'cancelled') {
          unawaited(
            _finishWithoutBilling('Video call cancelled'),
          );
        } else if (status == 'ended') {
          unawaited(
            _finishWithoutBilling('Video call ended'),
          );
        }
      },
      onError: (Object error) {
        debugPrint('Video call state error: $error');
      },
    );
  }

  Future<void> _finishWithoutBilling(
    String message,
  ) async {
    if (_ending) return;

    _ending = true;
    _timer?.cancel();

    if (mounted) {
      setState(() {
        _status = CallStatus.ended;
        _error = message;
      });
    }

    try {
      await widget.agoraService.leave();
    } catch (_) {}

    if (!mounted) return;

    Navigator.of(context).pop(_durationSeconds);
  }

  Future<void> _toggleMute() async {
    final muted = await widget.agoraService.toggleMute();

    if (!mounted) return;

    setState(() {
      _muted = muted;
    });
  }

  Future<void> _toggleSpeaker() async {
    final enabled = await widget.agoraService.toggleSpeaker();

    if (!mounted) return;

    setState(() {
      _speakerEnabled = enabled;
    });
  }

  Future<void> _toggleCamera() async {
    final enabled = await widget.agoraService.toggleCamera();

    if (!mounted) return;

    setState(() {
      _cameraEnabled = enabled;
    });
  }

  Future<void> _switchCamera() async {
    await widget.agoraService.switchCamera();
  }

  Future<void> _endCall() async {
    if (_ending) return;

    setState(() {
      _ending = true;
    });

    _timer?.cancel();

    try {
      await widget.agoraService.leave();

      final unansweredRingingCall = widget.session.isCaller &&
          !_everRemoteJoined &&
          _serverStatus == 'ringing';

      if (unansweredRingingCall) {
        await widget.callService.cancelCall(
          callId: widget.session.callId,
        );
      } else {
        await widget.callService.endCall(
          callId: widget.session.callId,
          durationSeconds: _everRemoteJoined ? _durationSeconds : 0,
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Video call ended with a warning: $error',
            ),
          ),
        );
      }
    } finally {
      if (mounted) {
        Navigator.of(context).pop(_durationSeconds);
      }
    }
  }

  String get _durationLabel {
    final minutes = _durationSeconds ~/ 60;
    final seconds = _durationSeconds % 60;

    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  String get _statusLabel {
    if (_ending) return 'Ending video call...';

    switch (_status) {
      case CallStatus.preparing:
        return 'Preparing camera...';
      case CallStatus.ringing:
        return 'Ringing...';
      case CallStatus.connecting:
        return 'Connecting...';
      case CallStatus.connected:
        return _remoteJoined ? 'Connected' : 'Waiting for user...';
      case CallStatus.ended:
        return 'Video call ended';
      case CallStatus.failed:
        return _error ?? 'Video call failed';
    }
  }

  Widget _buildRemoteVideo() {
    final engine = widget.agoraService.engine;
    final uid = _remoteUid;

    if (engine == null || uid == null || uid <= 0) {
      return _WaitingVideo(
        name: widget.otherName,
        photoUrl: widget.otherPhotoUrl,
        status: _statusLabel,
      );
    }

    return AgoraVideoView(
      controller: VideoViewController.remote(
        rtcEngine: engine,
        canvas: VideoCanvas(uid: uid),
        connection: RtcConnection(
          channelId: widget.session.channelName,
        ),
      ),
    );
  }

  Widget _buildLocalVideo() {
    final engine = widget.agoraService.engine;

    if (engine == null || !_cameraEnabled) {
      return Container(
        alignment: Alignment.center,
        color: Colors.black87,
        child: const Icon(
          Icons.videocam_off,
          color: Colors.white70,
          size: 32,
        ),
      );
    }

    return AgoraVideoView(
      controller: VideoViewController(
        rtcEngine: engine,
        canvas: const VideoCanvas(uid: 0),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _statusSub?.cancel();
    _remoteSub?.cancel();
    _errorSub?.cancel();
    _callStateSub?.cancel();
    unawaited(widget.agoraService.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _ending,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _endCall();
        }
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          children: [
            Positioned.fill(
              child: _buildRemoteVideo(),
            ),
            Positioned(
              top: MediaQuery.paddingOf(context).top + 16,
              right: 16,
              width: 112,
              height: 160,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(18),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Colors.black,
                    border: Border.all(
                      color: Colors.white24,
                    ),
                  ),
                  child: _buildLocalVideo(),
                ),
              ),
            ),
            Positioned(
              top: MediaQuery.paddingOf(context).top + 18,
              left: 18,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.otherName.trim().isEmpty
                            ? 'User'
                            : widget.otherName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '$_durationLabel • $_statusLabel',
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              left: 14,
              right: 14,
              bottom: MediaQuery.paddingOf(context).bottom + 18,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 14,
                ),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.72),
                  borderRadius: BorderRadius.circular(26),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _VideoControl(
                      icon: _muted ? Icons.mic_off : Icons.mic,
                      label: _muted ? 'Unmute' : 'Mute',
                      active: _muted,
                      onTap: _ending ? null : _toggleMute,
                    ),
                    _VideoControl(
                      icon:
                          _cameraEnabled ? Icons.videocam : Icons.videocam_off,
                      label: 'Camera',
                      active: !_cameraEnabled,
                      onTap: _ending ? null : _toggleCamera,
                    ),
                    _VideoControl(
                      icon: Icons.cameraswitch,
                      label: 'Switch',
                      onTap: _ending || !_cameraEnabled ? null : _switchCamera,
                    ),
                    _VideoControl(
                      icon: _speakerEnabled ? Icons.volume_up : Icons.hearing,
                      label: 'Speaker',
                      active: _speakerEnabled,
                      onTap: _ending ? null : _toggleSpeaker,
                    ),
                    _VideoControl(
                      icon: Icons.call_end,
                      label: 'End',
                      destructive: true,
                      onTap: _ending ? null : _endCall,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WaitingVideo extends StatelessWidget {
  const _WaitingVideo({
    required this.name,
    required this.photoUrl,
    required this.status,
  });

  final String name;
  final String photoUrl;
  final String status;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF17111F),
      alignment: Alignment.center,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 62,
            backgroundColor: Colors.white12,
            backgroundImage:
                photoUrl.trim().isEmpty ? null : NetworkImage(photoUrl),
            child: photoUrl.trim().isEmpty
                ? const Icon(
                    Icons.person,
                    size: 70,
                    color: Colors.white70,
                  )
                : null,
          ),
          const SizedBox(height: 20),
          Text(
            name.trim().isEmpty ? 'User' : name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            status,
            style: const TextStyle(
              color: Colors.white70,
            ),
          ),
        ],
      ),
    );
  }
}

class _VideoControl extends StatelessWidget {
  const _VideoControl({
    required this.icon,
    required this.label,
    required this.onTap,
    this.active = false,
    this.destructive = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final bool active;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final background = destructive
        ? Colors.red
        : active
            ? Colors.white
            : Colors.white12;

    final foreground = active && !destructive ? Colors.black : Colors.white;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Material(
          color: background,
          shape: const CircleBorder(),
          child: InkWell(
            onTap: onTap,
            customBorder: const CircleBorder(),
            child: SizedBox(
              width: 50,
              height: 50,
              child: Icon(
                icon,
                color: foreground,
                size: 23,
              ),
            ),
          ),
        ),
        const SizedBox(height: 5),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 9.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
