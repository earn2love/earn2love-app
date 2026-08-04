import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/play_session.dart';
import '../services/play_together_service.dart';
import 'play_session_page.dart';

class PlayLobbyPage extends StatefulWidget {
  const PlayLobbyPage({
    super.key,
    required this.initialSession,
    required this.service,
  });

  final PlaySession initialSession;
  final PlayTogetherService service;

  @override
  State<PlayLobbyPage> createState() => _PlayLobbyPageState();
}

class _PlayLobbyPageState extends State<PlayLobbyPage> {
  late PlaySession _session;

  Timer? _pollTimer;
  bool _busy = false;
  bool _leaving = false;
  bool _openedGame = false;
  String? _error;

  String get _uid => FirebaseAuth.instance.currentUser?.uid ?? '';

  bool get _isHost => _session.hostUid == _uid;

  bool get _myReady => _isHost ? _session.hostReady : _session.guestReady;

  String get _myComfort =>
      _isHost ? _session.hostComfort : _session.guestComfort;

  String get _partnerComfort =>
      _isHost ? _session.guestComfort : _session.hostComfort;

  bool get _partnerJoined =>
      _session.guestUid != null && _session.guestUid!.trim().isNotEmpty;

  @override
  void initState() {
    super.initState();
    _session = widget.initialSession;

    _pollTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _refresh(),
    );
  }

  Future<void> _refresh() async {
    if (_busy || _leaving || _openedGame) return;

    try {
      final updated = await widget.service.getSession(
        sessionId: _session.sessionId,
      );

      if (!mounted) return;

      setState(() {
        _session = updated;
        _error = null;
      });

      await _openGameWhenReady(updated);
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.toString();
      });
    }
  }

  Future<void> _openGameWhenReady(
    PlaySession session,
  ) async {
    if (_openedGame || session.status != 'playing') {
      return;
    }

    _openedGame = true;
    _pollTimer?.cancel();

    if (!mounted) return;

    await Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => PlaySessionPage(
          initialSession: session,
          service: widget.service,
        ),
      ),
    );
  }

  Future<void> _setComfort(
    String comfortLevel,
  ) async {
    if (_busy || comfortLevel == _myComfort) return;

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final updated = await widget.service.setComfort(
        sessionId: _session.sessionId,
        comfortLevel: comfortLevel,
      );

      if (!mounted) return;

      setState(() {
        _session = updated;
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _toggleReady() async {
    if (_busy || !_partnerJoined) return;

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final updated = await widget.service.setReady(
        sessionId: _session.sessionId,
        ready: !_myReady,
      );

      if (!mounted) return;

      setState(() {
        _session = updated;
      });

      await _openGameWhenReady(updated);
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted && !_openedGame) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _copyInviteCode() async {
    await Clipboard.setData(
      ClipboardData(text: _session.inviteCode),
    );

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Invite code copied'),
      ),
    );
  }

  Future<void> _leave() async {
    if (_leaving) return;

    _leaving = true;
    _pollTimer?.cancel();

    try {
      await widget.service.leaveSession(
        sessionId: _session.sessionId,
      );
    } catch (_) {
      // The user must still be able to close the lobby.
    } finally {
      if (mounted) {
        Navigator.of(context).pop();
      }
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _leave();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(_session.experienceTitle),
          leading: IconButton(
            tooltip: 'Leave session',
            onPressed: _leaving ? null : _leave,
            icon: const Icon(Icons.close),
          ),
        ),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const Text(
                'Invite your partner',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 23,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Share this private code. The experience begins '
                'only after both players join and confirm they are ready.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              InkWell(
                borderRadius: BorderRadius.circular(22),
                onTap: _copyInviteCode,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 24,
                  ),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF7B4EFF),
                        Color(0xFFFF4D91),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Column(
                    children: [
                      const Text(
                        'INVITE CODE',
                        style: TextStyle(
                          color: Colors.white70,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _session.inviteCode,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 34,
                          letterSpacing: 5,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Tap to copy',
                        style: TextStyle(
                          color: Colors.white70,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 25),
              const Text(
                'Your comfort level',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Each player chooses independently. The session '
                'uses the lower level accepted by both players.',
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('Friendly'),
                    selected: _myComfort == 'standard',
                    onSelected: _busy ? null : (_) => _setComfort('standard'),
                  ),
                  ChoiceChip(
                    label: const Text('Romantic'),
                    selected: _myComfort == 'romantic',
                    onSelected: _busy ? null : (_) => _setComfort('romantic'),
                  ),
                  if (_session.adultEligible)
                    ChoiceChip(
                      label: const Text('Mature 18+'),
                      selected: _myComfort == 'mature',
                      onSelected: _busy ? null : (_) => _setComfort('mature'),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Card(
                child: ListTile(
                  leading: const Icon(
                    Icons.handshake_outlined,
                  ),
                  title: const Text(
                    'Shared session level',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  subtitle: Text(
                    'You: ${_comfortLabel(_myComfort)}\n'
                    'Partner: ${_comfortLabel(_partnerComfort)}',
                  ),
                  trailing: Text(
                    _comfortLabel(
                      _session.effectiveComfort,
                    ),
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              _PlayerStatusTile(
                title: 'You',
                joined: true,
                ready: _myReady,
                comfort: _myComfort,
              ),
              const SizedBox(height: 10),
              _PlayerStatusTile(
                title: 'Partner',
                joined: _partnerJoined,
                ready: _isHost ? _session.guestReady : _session.hostReady,
                comfort: _partnerComfort,
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.red,
                  ),
                ),
              ],
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _busy || !_partnerJoined ? null : _toggleReady,
                icon: Icon(
                  _myReady
                      ? Icons.pause_circle_outline
                      : Icons.check_circle_outline,
                ),
                label: Text(
                  _myReady ? 'I am not ready' : 'I am ready',
                ),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: _leaving ? null : _leave,
                child: const Text('Leave session'),
              ),
              if (!_partnerJoined) ...[
                const SizedBox(height: 16),
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(width: 16),
                        Expanded(
                          child: Text(
                            'Waiting for your partner to join...',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

String _comfortLabel(String comfort) {
  switch (comfort) {
    case 'mature':
      return 'Mature 18+';
    case 'romantic':
      return 'Romantic';
    default:
      return 'Friendly';
  }
}

class _PlayerStatusTile extends StatelessWidget {
  const _PlayerStatusTile({
    required this.title,
    required this.joined,
    required this.ready,
    required this.comfort,
  });

  final String title;
  final bool joined;
  final bool ready;
  final String comfort;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      tileColor: Theme.of(context).colorScheme.surfaceContainerHighest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      leading: CircleAvatar(
        child: Icon(
          joined ? Icons.person : Icons.hourglass_empty,
        ),
      ),
      title: Text(
        title,
        style: const TextStyle(
          fontWeight: FontWeight.w900,
        ),
      ),
      subtitle: Text(
        joined ? 'Joined · ${_comfortLabel(comfort)}' : 'Waiting to join',
      ),
      trailing: Icon(
        ready ? Icons.check_circle : Icons.circle_outlined,
        color: ready ? Colors.green : Colors.grey,
      ),
    );
  }
}
