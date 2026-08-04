import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../models/meera_profile_coach.dart';
import '../services/meera_service.dart';

class MeeraProfileCoachPage extends StatefulWidget {
  const MeeraProfileCoachPage({
    super.key,
  });

  @override
  State<MeeraProfileCoachPage> createState() => _MeeraProfileCoachPageState();
}

class _MeeraProfileCoachPageState extends State<MeeraProfileCoachPage> {
  final MeeraService _service = MeeraService();

  bool _loading = true;
  bool _applying = false;
  String? _error;

  MeeraProfileCoachResult? _result;

  DocumentReference<Map<String, dynamic>>? get _userReference {
    final uid = FirebaseAuth.instance.currentUser?.uid;

    if (uid == null || uid.isEmpty) return null;

    return FirebaseFirestore.instance.collection('users').doc(uid);
  }

  @override
  void initState() {
    super.initState();
    _analyse();
  }

  Future<void> _analyse() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await _service.analyseProfile();

      if (!mounted) return;

      setState(() {
        _result = result;
      });
    } on MeeraServiceException catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.message;
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<bool> _confirm({
    required String title,
    required String message,
    required String confirmLabel,
  }) async {
    return await showDialog<bool>(
          context: context,
          builder: (dialogContext) {
            return AlertDialog(
              title: Text(title),
              content: Text(message),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(
                    dialogContext,
                  ).pop(false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(
                    dialogContext,
                  ).pop(true),
                  child: Text(confirmLabel),
                ),
              ],
            );
          },
        ) ??
        false;
  }

  Future<void> _applyBio(
    MeeraBioSuggestion suggestion,
  ) async {
    final reference = _userReference;

    if (reference == null) return;

    final confirmed = await _confirm(
      title: 'Apply this bio?',
      message: '"${suggestion.bio}"\n\n'
          'This will replace your current profile bio.',
      confirmLabel: 'Apply bio',
    );

    if (!confirmed) return;

    setState(() => _applying = true);

    try {
      await reference.set({
        'bio': suggestion.bio,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Profile bio updated'),
        ),
      );
    } on FirebaseException catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Could not update bio: ${error.code}',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _applying = false);
      }
    }
  }

  Future<void> _addInterests(
    List<String> suggestions,
  ) async {
    final reference = _userReference;

    if (reference == null || suggestions.isEmpty) {
      return;
    }

    final selected = <String>{
      ...suggestions.take(12),
    };

    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (
            context,
            setSheetState,
          ) {
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  18,
                  4,
                  18,
                  24,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Add suggested interests',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 7),
                    const Text(
                      'Select only the interests '
                      'that genuinely describe you.',
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: suggestions.take(12).map((interest) {
                        final isSelected = selected.contains(
                          interest,
                        );

                        return FilterChip(
                          label: Text(interest),
                          selected: isSelected,
                          onSelected: (value) {
                            setSheetState(() {
                              if (value) {
                                selected.add(
                                  interest,
                                );
                              } else {
                                selected.remove(
                                  interest,
                                );
                              }
                            });
                          },
                        );
                      }).toList(
                        growable: false,
                      ),
                    ),
                    const SizedBox(height: 18),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: selected.isEmpty
                            ? null
                            : () => Navigator.of(
                                  sheetContext,
                                ).pop(true),
                        child: const Text(
                          'Add selected interests',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    if (confirmed != true || selected.isEmpty) {
      return;
    }

    setState(() => _applying = true);

    try {
      final snapshot = await reference.get();
      final data = snapshot.data() ?? {};

      final current = data['interests'] is List
          ? (data['interests'] as List)
              .map(
                (item) => item.toString().trim(),
              )
              .where(
                (item) => item.isNotEmpty,
              )
              .toList()
          : <String>[];

      final merged = <String>[];

      for (final interest in [
        ...current,
        ...selected,
      ]) {
        final alreadyAdded = merged.any(
          (item) => item.toLowerCase() == interest.toLowerCase(),
        );

        if (!alreadyAdded) {
          merged.add(interest);
        }
      }

      await reference.set({
        'interests': merged.take(30).toList(),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Selected interests added',
          ),
        ),
      );
    } on FirebaseException catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Could not update interests: '
            '${error.code}',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _applying = false);
      }
    }
  }

  Color _scoreColor(int score) {
    if (score >= 80) {
      return const Color(0xFF1F9D68);
    }

    if (score >= 55) {
      return const Color(0xFFE59A24);
    }

    return const Color(0xFFE05767);
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;

    return Scaffold(
      backgroundColor: const Color(0xFFF8F4FC),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF8F4FC),
        title: const Text(
          'Meera Profile Coach',
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Analyse again',
            onPressed: _loading || _applying ? null : _analyse,
            icon: const Icon(
              Icons.refresh_rounded,
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 13),
                  Text(
                    'Meera is reviewing '
                    'your profile…',
                  ),
                ],
              ),
            )
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _error!,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(
                          height: 14,
                        ),
                        FilledButton(
                          onPressed: _analyse,
                          child: const Text(
                            'Try again',
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              : result == null
                  ? const SizedBox.shrink()
                  : Stack(
                      children: [
                        ListView(
                          padding: const EdgeInsets.fromLTRB(
                            14,
                            12,
                            14,
                            30,
                          ),
                          children: [
                            _ScoreCard(
                              score: result.score,
                              summary: result.summary,
                              color: _scoreColor(
                                result.score,
                              ),
                            ),
                            if (result.strengths.isNotEmpty)
                              _TextListSection(
                                title: 'Profile strengths',
                                icon: Icons.star_rounded,
                                values: result.strengths,
                              ),
                            if (result.improvements.isNotEmpty)
                              _ImprovementSection(
                                values: result.improvements,
                              ),
                            if (result.bioSuggestions.isNotEmpty)
                              _BioSection(
                                suggestions: result.bioSuggestions,
                                onApply: _applying ? null : _applyBio,
                              ),
                            if (result.suggestedInterests.isNotEmpty)
                              _InterestSection(
                                interests: result.suggestedInterests,
                                onAdd: _applying
                                    ? null
                                    : () => _addInterests(
                                          result.suggestedInterests,
                                        ),
                              ),
                            if (result.conversationStyle.isNotEmpty)
                              _TextCard(
                                title: 'Conversation style',
                                icon: Icons.forum_rounded,
                                text: result.conversationStyle,
                              ),
                            if (result.photoGuidance.isNotEmpty)
                              _TextListSection(
                                title: 'Photo guidance',
                                icon: Icons.photo_camera_outlined,
                                values: result.photoGuidance,
                              ),
                            const SizedBox(
                              height: 16,
                            ),
                            const Text(
                              'Meera uses your current '
                              'profile fields to provide '
                              'guidance. Profile changes '
                              'are applied only after '
                              'you confirm them.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Colors.black45,
                                fontSize: 11.5,
                              ),
                            ),
                          ],
                        ),
                        if (_applying)
                          const Positioned.fill(
                            child: ColoredBox(
                              color: Color(
                                0x33000000,
                              ),
                              child: Center(
                                child: CircularProgressIndicator(),
                              ),
                            ),
                          ),
                      ],
                    ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({
    required this.score,
    required this.summary,
    required this.color,
  });

  final int score;
  final String summary;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 76,
              height: 76,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: score / 100,
                    strokeWidth: 8,
                    backgroundColor: color.withValues(
                      alpha: 0.15,
                    ),
                    color: color,
                  ),
                  Text(
                    '$score',
                    style: TextStyle(
                      color: color,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Profile score',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    summary,
                    style: const TextStyle(
                      height: 1.4,
                      color: Color(
                        0xFF5E5667,
                      ),
                    ),
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

class _ImprovementSection extends StatelessWidget {
  const _ImprovementSection({
    required this.values,
  });

  final List<MeeraProfileImprovement> values;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.tips_and_updates_outlined,
                  color: Color(0xFF7B4EFF),
                ),
                SizedBox(width: 8),
                Text(
                  'Recommended improvements',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...values.map(
              (item) => Padding(
                padding: const EdgeInsets.only(
                  bottom: 12,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            item.area
                                .replaceAll(
                                  '_',
                                  ' ',
                                )
                                .toUpperCase(),
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              color: Color(
                                0xFF7B4EFF,
                              ),
                            ),
                          ),
                        ),
                        Text(
                          item.priority,
                          style: const TextStyle(
                            fontSize: 11,
                            color: Colors.black45,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.reason,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      item.suggestion,
                      style: const TextStyle(
                        color: Colors.black54,
                      ),
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

class _BioSection extends StatelessWidget {
  const _BioSection({
    required this.suggestions,
    required this.onApply,
  });

  final List<MeeraBioSuggestion> suggestions;
  final Future<void> Function(
    MeeraBioSuggestion suggestion,
  )? onApply;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'AI bio suggestions',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 12),
            ...suggestions.map(
              (suggestion) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(
                  bottom: 10,
                ),
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8F4FC),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: const Color(0xFFE8DDF2),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      suggestion.style.toUpperCase(),
                      style: const TextStyle(
                        color: Color(0xFF7B4EFF),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(suggestion.bio),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.tonal(
                        onPressed: onApply == null
                            ? null
                            : () => onApply!(
                                  suggestion,
                                ),
                        child: const Text('Apply'),
                      ),
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

class _InterestSection extends StatelessWidget {
  const _InterestSection({
    required this.interests,
    required this.onAdd,
  });

  final List<String> interests;
  final VoidCallback? onAdd;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Suggested interests',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 11),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: interests
                  .map(
                    (interest) => Chip(
                      label: Text(interest),
                    ),
                  )
                  .toList(growable: false),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.tonalIcon(
                onPressed: onAdd,
                icon: const Icon(
                  Icons.add_rounded,
                ),
                label: const Text(
                  'Choose interests to add',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TextListSection extends StatelessWidget {
  const _TextListSection({
    required this.title,
    required this.icon,
    required this.values,
  });

  final String title;
  final IconData icon;
  final List<String> values;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: const Color(0xFF7B4EFF),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 11),
            ...values.map(
              (value) => Padding(
                padding: const EdgeInsets.only(
                  bottom: 8,
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(
                        top: 6,
                      ),
                      child: CircleAvatar(
                        radius: 3,
                        backgroundColor: Color(
                          0xFF7B4EFF,
                        ),
                      ),
                    ),
                    const SizedBox(width: 9),
                    Expanded(
                      child: Text(
                        value,
                        style: const TextStyle(
                          height: 1.35,
                        ),
                      ),
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

class _TextCard extends StatelessWidget {
  const _TextCard({
    required this.title,
    required this.icon,
    required this.text,
  });

  final String title;
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: const Color(0xFF7B4EFF),
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              text,
              style: const TextStyle(
                height: 1.4,
                color: Color(0xFF5E5667),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
