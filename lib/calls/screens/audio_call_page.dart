import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../models/call_session.dart';
import '../services/agora_service.dart';
import '../services/call_service.dart';

class AudioCallPage extends StatefulWidget {
  const AudioCallPage({
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
  State<AudioCallPage> createState() => _AudioCallPageState();
}

class _AudioCallPageState extends State<AudioCallPage> {
  StreamSubscription<CallStatus>? _statusSub;
  StreamSubscription<int>? _remoteSub;
  StreamSubscription<String>? _errorSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _callStateSub;
  Timer? _timer;

  CallStatus _status = CallStatus.preparing;
  bool _muted = false;
  bool _speakerEnabled = true;
  bool _remoteJoined = false;
  bool _everRemoteJoined = false;
  bool _ending = false;
  int _durationSeconds = 0;
  String _serverStatus = 'ringing';
  String? _error;

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    _listenToServerCallState();

    _statusSub = widget.agoraService.statusStream.listen((status) {
      if (!mounted) return;

      setState(() {
        _status = status;
      });
    });

    _remoteSub = widget.agoraService.remoteUserStream.listen((uid) {
      if (!mounted || _ending) return;

      final joined = uid > 0;
      final remoteLeftAfterConnection = !joined && _everRemoteJoined;

      setState(() {
        _remoteJoined = joined;

        if (joined) {
          _everRemoteJoined = true;
        }
      });

      if (joined) {
        _startConnectedTimer();
      } else if (remoteLeftAfterConnection) {
        unawaited(_endCall());
      }
    });

    _errorSub = widget.agoraService.errorStream.listen((message) {
      if (!mounted) return;

      setState(() {
        _error = message;
        _status = CallStatus.failed;
      });
    });

    try {
      setState(() => _status = CallStatus.preparing);

      final credentials = await widget.callService.generateAgoraToken(
        channelName: widget.session.channelName,
        agoraUid: 0,
      );

      await widget.agoraService.initialize(
        appId: credentials.appId,
        enableVideo: false,
      );

      if (!mounted) return;

      setState(() => _status = CallStatus.connecting);

      await widget.agoraService.join(
        credentials: credentials,
        callType: CallType.audio,
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
            _finishWithoutBilling('Call rejected'),
          );
        } else if (status == 'cancelled') {
          unawaited(
            _finishWithoutBilling('Call cancelled'),
          );
        } else if (status == 'ended') {
          unawaited(
            _finishWithoutBilling('Call ended'),
          );
        }
      },
      onError: (Object error) {
        debugPrint('Call state listener error: $error');
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
    } catch (_) {
      // Continue closing even if Agora already disconnected.
    }

    if (!mounted) return;

    Navigator.of(context).pop(_durationSeconds);
  }

  String get _statusLabel {
    if (_ending) return 'Ending call...';

    switch (_status) {
      case CallStatus.preparing:
        return 'Preparing call...';
      case CallStatus.ringing:
        return 'Ringing...';
      case CallStatus.connecting:
        return 'Connecting...';
      case CallStatus.connected:
        return _remoteJoined ? 'Connected' : 'Waiting for user...';
      case CallStatus.ended:
        return 'Call ended';
      case CallStatus.failed:
        return _error ?? 'Call failed';
    }
  }

  String get _durationLabel {
    final minutes = _durationSeconds ~/ 60;
    final seconds = _durationSeconds % 60;

    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  Future<void> _toggleMute() async {
    final muted = await widget.agoraService.toggleMute();

    if (!mounted) return;
    setState(() => _muted = muted);
  }

  Future<void> _toggleSpeaker() async {
    final enabled = await widget.agoraService.toggleSpeaker();

    if (!mounted) return;
    setState(() => _speakerEnabled = enabled);
  }

  Future<void> _endCall() async {
    if (_ending) return;

    setState(() => _ending = true);
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
            content: Text('Call ended with a warning: $error'),
          ),
        );
      }
    } finally {
      if (mounted) {
        Navigator.of(context).pop(_durationSeconds);
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _statusSub?.cancel();
    _remoteSub?.cancel();
    _errorSub?.cancel();
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
        backgroundColor: const Color(0xFF17111F),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 40, 24, 30),
            child: Column(
              children: [
                const Spacer(),
                CircleAvatar(
                  radius: 62,
                  backgroundColor: Colors.white12,
                  backgroundImage: widget.otherPhotoUrl.trim().isEmpty
                      ? null
                      : NetworkImage(widget.otherPhotoUrl),
                  child: widget.otherPhotoUrl.trim().isEmpty
                      ? const Icon(
                          Icons.person,
                          size: 70,
                          color: Colors.white70,
                        )
                      : null,
                ),
                const SizedBox(height: 24),
                Text(
                  widget.otherName.trim().isEmpty ? 'User' : widget.otherName,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  _statusLabel,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  _durationLabel,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Spacer(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _CallControl(
                      icon: _muted ? Icons.mic_off : Icons.mic,
                      label: _muted ? 'Unmute' : 'Mute',
                      active: _muted,
                      onTap: _ending ? null : _toggleMute,
                    ),
                    _CallControl(
                      icon: _speakerEnabled ? Icons.volume_up : Icons.hearing,
                      label: 'Speaker',
                      active: _speakerEnabled,
                      onTap: _ending ? null : _toggleSpeaker,
                    ),
                    _CallControl(
                      icon: Icons.call_end,
                      label: 'End',
                      destructive: true,
                      onTap: _ending ? null : _endCall,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CallControl extends StatelessWidget {
  const _CallControl({
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

    final foreground =
        active && !destructive ? const Color(0xFF17111F) : Colors.white;

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
              width: 64,
              height: 64,
              child: Icon(
                icon,
                color: foreground,
                size: 28,
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
