import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../models/play_session.dart';
import '../services/play_together_service.dart';

class PlaySessionPage extends StatefulWidget {
  const PlaySessionPage({
    super.key,
    required this.initialSession,
    required this.service,
  });

  final PlaySession initialSession;
  final PlayTogetherService service;

  @override
  State<PlaySessionPage> createState() => _PlaySessionPageState();
}

class _PlaySessionPageState extends State<PlaySessionPage> {
  late PlaySession _session;

  final TextEditingController _answerController = TextEditingController();

  Timer? _pollTimer;
  bool _busy = false;
  bool _leaving = false;
  String? _error;

  String get _uid => FirebaseAuth.instance.currentUser?.uid ?? '';

  bool get _isHost => _session.hostUid == _uid;

  PlayResponse? get _myResponse =>
      _isHost ? _session.hostResponse : _session.guestResponse;

  PlayResponse? get _partnerResponse =>
      _isHost ? _session.guestResponse : _session.hostResponse;

  bool get _bothResponded =>
      _session.hostResponse != null && _session.guestResponse != null;

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
    if (_busy || _leaving) return;

    try {
      final updated = await widget.service.getSession(
        sessionId: _session.sessionId,
      );

      if (!mounted) return;

      setState(() {
        _session = updated;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.toString();
      });
    }
  }

  Future<void> _submit() async {
    final answer = _answerController.text.trim();

    if (answer.isEmpty || _busy) return;

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final updated = await widget.service.submitResponse(
        sessionId: _session.sessionId,
        response: answer,
      );

      _answerController.clear();

      if (!mounted) return;
      setState(() => _session = updated);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _skip() async {
    if (_busy) return;

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final updated = await widget.service.skipPrompt(
        sessionId: _session.sessionId,
      );

      if (!mounted) return;
      setState(() => _session = updated);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _replace() async {
    if (_busy) return;

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final updated = await widget.service.replacePrompt(
        sessionId: _session.sessionId,
      );

      _answerController.clear();

      if (!mounted) return;
      setState(() => _session = updated);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _next() async {
    if (_busy) return;

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final updated = await widget.service.nextPrompt(
        sessionId: _session.sessionId,
      );

      _answerController.clear();

      if (!mounted) return;
      setState(() => _session = updated);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
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
      // Leaving the screen must still remain possible.
    } finally {
      if (mounted) {
        Navigator.of(context).pop();
      }
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _answerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_session.status == 'completed') {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Session complete'),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.favorite,
                  size: 72,
                  color: Color(0xFFFF4D91),
                ),
                const SizedBox(height: 18),
                Text(
                  _session.experienceTitle,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 25,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'You completed '
                  '${_session.currentRound} shared rounds.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text(
                    'Return to Play Together',
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (_session.status == 'ended') {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Session ended'),
        ),
        body: Center(
          child: FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Return'),
          ),
        ),
      );
    }

    final prompt = _session.currentPrompt;

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
            padding: const EdgeInsets.all(18),
            children: [
              Row(
                children: [
                  Expanded(
                    child: LinearProgressIndicator(
                      value: _session.maxRounds <= 0
                          ? 0
                          : (_session.currentRound / _session.maxRounds)
                              .clamp(0.0, 1.0),
                      minHeight: 8,
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '${_session.currentRound}/'
                    '${_session.maxRounds}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              if (prompt == null)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Column(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 14),
                        Text(
                          'Preparing the next round...',
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                )
              else
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF7B4EFF),
                        Color(0xFFFF4D91),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Column(
                    children: [
                      Text(
                        prompt.type.toUpperCase(),
                        style: const TextStyle(
                          color: Colors.white70,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        prompt.text,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          height: 1.35,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _session.effectiveComfort.toUpperCase(),
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 18),
              if (_myResponse == null) ...[
                TextField(
                  controller: _answerController,
                  enabled: !_busy && prompt != null,
                  minLines: 2,
                  maxLines: 6,
                  maxLength: 1000,
                  decoration: const InputDecoration(
                    labelText: 'Your response',
                    hintText: 'Answer freely or choose Skip.',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                FilledButton.icon(
                  onPressed: _busy || prompt == null ? null : _submit,
                  icon: const Icon(Icons.send),
                  label: const Text('Submit response'),
                ),
                const SizedBox(height: 9),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _busy || prompt == null ? null : _skip,
                        icon: const Icon(Icons.skip_next),
                        label: const Text('Skip'),
                      ),
                    ),
                    const SizedBox(width: 9),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _busy ||
                                prompt == null ||
                                _session.replacementCount >= 5
                            ? null
                            : _replace,
                        icon: const Icon(Icons.refresh),
                        label: Text(
                          'Replace '
                          '${_session.replacementCount}/5',
                        ),
                      ),
                    ),
                  ],
                ),
              ] else
                _ResponseCard(
                  title: 'Your response',
                  response: _myResponse!,
                ),
              const SizedBox(height: 12),
              if (_partnerResponse == null)
                const Card(
                  child: ListTile(
                    leading: CircularProgressIndicator(),
                    title: Text(
                      'Waiting for partner',
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    subtitle: Text(
                      'They can answer or skip.',
                    ),
                  ),
                )
              else
                _ResponseCard(
                  title: 'Partner response',
                  response: _partnerResponse!,
                ),
              if (_bothResponded) ...[
                const SizedBox(height: 14),
                FilledButton.icon(
                  onPressed: _busy ? null : _next,
                  icon: const Icon(Icons.arrow_forward),
                  label: Text(
                    _session.currentRound >= _session.maxRounds
                        ? 'Complete session'
                        : 'Next round',
                  ),
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 14),
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.red,
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

class _ResponseCard extends StatelessWidget {
  const _ResponseCard({
    required this.title,
    required this.response,
  });

  final String title;
  final PlayResponse response;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(
          response.skipped ? Icons.skip_next : Icons.check_circle,
          color: response.skipped ? Colors.orange : Colors.green,
        ),
        title: Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
        subtitle: Text(
          response.skipped ? 'Skipped' : response.text,
        ),
      ),
    );
  }
}
