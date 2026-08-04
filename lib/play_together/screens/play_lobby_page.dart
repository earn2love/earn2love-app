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
  String? _error;
  bool _openedGame = false;

  String get _uid => FirebaseAuth.instance.currentUser?.uid ?? '';

  bool get _isHost => _session.hostUid == _uid;

  bool get _myReady => _isHost ? _session.hostReady : _session.guestReady;

  @override
  void initState() {
    super.initState();
    _session = widget.initialSession;

    _pollTimer = Timer.periodic(
      const Duration(seconds: 3),
      (_) => _refresh(),
    );
  }

  Future<void> _refresh() async {
    if (_busy) return;

    try {
      final updated = await widget.service.getSession(
        sessionId: _session.sessionId,
      );

      if (!mounted) return;

      setState(() {
        _session = updated;
        _error = null;
      });

      if (updated.status == 'playing' && !_openedGame && mounted) {
        _openedGame = true;

        await Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => PlaySessionPage(
              initialSession: updated,
              service: widget.service,
            ),
          ),
        );
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    }
  }

  Future<void> _toggleReady() async {
    setState(() => _busy = true);

    try {
      final updated = await widget.service.setReady(
        sessionId: _session.sessionId,
        ready: !_myReady,
      );

      if (!mounted) return;
      setState(() => _session = updated);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _leave() async {
    try {
      await widget.service.leaveSession(
        sessionId: _session.sessionId,
      );
    } finally {
      if (mounted) Navigator.of(context).pop();
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final partnerJoined =
        _session.guestUid != null && _session.guestUid!.isNotEmpty;

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
            icon: const Icon(Icons.close),
            onPressed: _leave,
          ),
        ),
        body: ListView(
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
            const SizedBox(height: 10),
            const Text(
              'Share this private invitation code. '
              'The experience begins only after both players are ready.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28),
            InkWell(
              borderRadius: BorderRadius.circular(22),
              onTap: () async {
                await Clipboard.setData(
                  ClipboardData(text: _session.inviteCode),
                );

                if (!context.mounted) return;

                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Invite code copied'),
                  ),
                );
              },
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
                        fontWeight: FontWeight.bold,
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
                      style: TextStyle(color: Colors.white70),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 25),
            _PlayerStatusTile(
              title: 'You',
              joined: true,
              ready: _session.hostReady,
            ),
            const SizedBox(height: 10),
            _PlayerStatusTile(
              title: 'Partner',
              joined: partnerJoined,
              ready: _session.guestReady,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
            ],
            const SizedBox(height: 26),
            FilledButton.icon(
              onPressed: _busy || !partnerJoined ? null : _toggleReady,
              icon: Icon(
                _myReady
                    ? Icons.pause_circle_outline
                    : Icons.check_circle_outline,
              ),
              label: Text(
                _session.hostReady ? 'Not ready' : 'I am ready',
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _leave,
              child: const Text('Leave session'),
            ),
            if (_session.status == 'ready') ...[
              const SizedBox(height: 22),
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Column(
                    children: [
                      Icon(
                        Icons.auto_awesome,
                        size: 34,
                        color: Color(0xFFFF4D91),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Both players are ready',
                        style: TextStyle(
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      SizedBox(height: 5),
                      Text(
                        'Dynamic AI rounds will connect in the next engine step.',
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _PlayerStatusTile extends StatelessWidget {
  const _PlayerStatusTile({
    required this.title,
    required this.joined,
    required this.ready,
  });

  final String title;
  final bool joined;
  final bool ready;

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
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
      subtitle: Text(
        joined ? 'Joined' : 'Waiting to join',
      ),
      trailing: Icon(
        ready ? Icons.check_circle : Icons.circle_outlined,
        color: ready ? Colors.green : Colors.grey,
      ),
    );
  }
}
