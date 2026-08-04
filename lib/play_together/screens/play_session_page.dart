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

  bool get _isGenerating => _session.isGenerating;

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
    if (_leaving) return;

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
              if (_isGenerating)
                const _GeneratingRoundCard()
              else if (prompt == null)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Column(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 14),
                        Text(
                          'Preparing your shared experience...',
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                )
              else ...[
                if (_session.hostReaction != null)
                  _AiReactionCard(
                    reaction: _session.hostReaction!,
                  ),
                if (_session.hostReaction != null) const SizedBox(height: 14),
                if (prompt.hostIntroduction.isNotEmpty)
                  _AiHostIntroduction(
                    introduction: prompt.hostIntroduction,
                  ),
                if (prompt.hostIntroduction.isNotEmpty)
                  const SizedBox(height: 14),
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
                    boxShadow: const [
                      BoxShadow(
                        blurRadius: 18,
                        offset: Offset(0, 8),
                        color: Color(0x22000000),
                      ),
                    ],
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.auto_awesome,
                            color: Colors.white70,
                            size: 18,
                          ),
                          const SizedBox(width: 7),
                          Text(
                            prompt.type.toUpperCase(),
                            style: const TextStyle(
                              color: Colors.white70,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
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
                      if (prompt.followUpHint.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.white12,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Text(
                            prompt.followUpHint,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              height: 1.3,
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 13),
                      Text(
                        _comfortLabel(
                          _session.effectiveComfort,
                        ),
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
                if (prompt.consentReminder.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _ConsentReminderCard(
                    reminder: prompt.consentReminder,
                  ),
                ],
                if (prompt.visualTheme.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _VisualThemeCard(
                    visualTheme: prompt.visualTheme,
                  ),
                ],
              ],
              const SizedBox(height: 18),
              if (_myResponse == null) ...[
                TextField(
                  controller: _answerController,
                  enabled: !_busy && !_isGenerating && prompt != null,
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
                  onPressed:
                      _busy || _isGenerating || prompt == null ? null : _submit,
                  icon: const Icon(Icons.send),
                  label: const Text('Submit response'),
                ),
                const SizedBox(height: 9),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _busy || _isGenerating || prompt == null
                            ? null
                            : _skip,
                        icon: const Icon(Icons.skip_next),
                        label: const Text('Skip'),
                      ),
                    ),
                    const SizedBox(width: 9),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _busy ||
                                _isGenerating ||
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
                  onPressed: _busy || _isGenerating ? null : _next,
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

class _GeneratingRoundCard extends StatelessWidget {
  const _GeneratingRoundCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFF34234A),
            Color(0xFF6C3D78),
          ],
        ),
        borderRadius: BorderRadius.circular(24),
      ),
      child: const Column(
        children: [
          SizedBox(
            width: 42,
            height: 42,
            child: CircularProgressIndicator(
              color: Colors.white,
              strokeWidth: 3,
            ),
          ),
          SizedBox(height: 18),
          Text(
            'Luna is creating your next round...',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 19,
              fontWeight: FontWeight.w900,
            ),
          ),
          SizedBox(height: 7),
          Text(
            'The experience is being shaped around your '
            'game, language and shared comfort level.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white70,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }
}

class _AiHostIntroduction extends StatelessWidget {
  const _AiHostIntroduction({
    required this.introduction,
  });

  final String introduction;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const CircleAvatar(
              backgroundColor: Color(0xFFFFE5F0),
              child: Icon(
                Icons.auto_awesome,
                color: Color(0xFFFF4D91),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Luna',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      color: Color(0xFFFF4D91),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    introduction,
                    style: const TextStyle(height: 1.35),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ConsentReminderCard extends StatelessWidget {
  const _ConsentReminderCard({
    required this.reminder,
  });

  final String reminder;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: ListTile(
        leading: const Icon(
          Icons.shield_outlined,
          color: Color(0xFF2EAD77),
        ),
        title: const Text(
          'Your choice always matters',
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
        subtitle: Text(reminder),
      ),
    );
  }
}

class _VisualThemeCard extends StatelessWidget {
  const _VisualThemeCard({
    required this.visualTheme,
  });

  final String visualTheme;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        dense: true,
        leading: const Icon(
          Icons.landscape_outlined,
          color: Color(0xFF7B4EFF),
        ),
        title: const Text(
          'Tonight’s atmosphere',
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
        subtitle: Text(visualTheme),
      ),
    );
  }
}

class _AiReactionCard extends StatelessWidget {
  const _AiReactionCard({
    required this.reaction,
  });

  final PlayHostReaction reaction;

  String get _toneLabel {
    switch (reaction.nextRoundTone) {
      case 'deeper':
        return 'Going a little deeper';
      case 'lighter':
        return 'Keeping the next round light';
      default:
        return 'Continuing at the same mood';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF2F7),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFFFFC5DD),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.auto_awesome,
                color: Color(0xFFFF4D91),
              ),
              SizedBox(width: 8),
              Text(
                'Luna’s reflection',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  color: Color(0xFFFF4D91),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            reaction.reaction,
            style: const TextStyle(height: 1.35),
          ),
          if (reaction.sharedInsight.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text(
              'Shared insight',
              style: TextStyle(
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              reaction.sharedInsight,
              style: const TextStyle(height: 1.35),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(
                Icons.arrow_forward_rounded,
                size: 17,
                color: Color(0xFF7B4EFF),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _toneLabel,
                  style: const TextStyle(
                    color: Color(0xFF7B4EFF),
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ],
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
