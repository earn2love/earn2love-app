import 'dart:async';

import 'package:flutter/material.dart';

import '../models/play_experience.dart';
import '../services/play_together_service.dart';
import '../widgets/play_experience_card.dart';
import 'play_lobby_page.dart';

class PlayTogetherPage extends StatefulWidget {
  const PlayTogetherPage({
    super.key,
    this.callId,
  });

  final String? callId;

  bool get isInCall => callId != null && callId!.trim().isNotEmpty;

  @override
  State<PlayTogetherPage> createState() => _PlayTogetherPageState();
}

class _PlayTogetherPageState extends State<PlayTogetherPage> {
  final PlayTogetherService _service = PlayTogetherService();

  late Future<PlayTogetherCatalog> _catalogFuture;
  final TextEditingController _searchController = TextEditingController();

  String _selectedCategory = 'all';
  String _searchQuery = '';
  bool _creating = false;
  bool _openingLinkedSession = false;
  Timer? _inCallSessionTimer;

  @override
  void initState() {
    super.initState();
    _catalogFuture = _service.getExperiences();

    if (widget.isInCall) {
      _inCallSessionTimer = Timer.periodic(
        const Duration(seconds: 2),
        (_) => _checkLinkedSession(),
      );

      unawaited(_checkLinkedSession());
    }
  }

  Future<void> _checkLinkedSession() async {
    if (!widget.isInCall || _openingLinkedSession || !mounted) {
      return;
    }

    try {
      final session = await _service.getInCallSession(
        callId: widget.callId!,
      );

      if (session == null || !mounted || _openingLinkedSession) {
        return;
      }

      _openingLinkedSession = true;

      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PlayLobbyPage(
            initialSession: session,
            service: _service,
          ),
        ),
      );
    } catch (_) {
      // No linked game may exist yet.
    } finally {
      _openingLinkedSession = false;
    }
  }

  @override
  void dispose() {
    _inCallSessionTimer?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() {
      _catalogFuture = _service.getExperiences();
    });

    await _catalogFuture;
  }

  Future<void> _createSession(
    PlayExperience experience,
  ) async {
    if (_creating) return;

    final language = Localizations.localeOf(context).languageCode;

    setState(() => _creating = true);

    try {
      final comfortLevel = await _selectComfortLevel(
        adultEligible: experience.adultEligible,
      );

      if (comfortLevel == null || !mounted) return;

      final session = widget.isInCall
          ? await _service.createInCallSession(
              callId: widget.callId!,
              experienceId: experience.id,
              language: language,
              comfortLevel: comfortLevel,
            )
          : await _service.createSession(
              experienceId: experience.id,
              language: language,
              comfortLevel: comfortLevel,
            );

      if (!mounted) return;

      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PlayLobbyPage(
            initialSession: session,
            service: _service,
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  Future<String?> _selectComfortLevel({
    required bool adultEligible,
  }) {
    return showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        Widget option(
          String value,
          String title,
          String subtitle,
        ) {
          return ListTile(
            title: Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w800,
              ),
            ),
            subtitle: Text(subtitle),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).pop(value),
          );
        }

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Choose your comfort level',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                option(
                  'standard',
                  'Friendly',
                  'Fun, comfortable and easy-going.',
                ),
                option(
                  'romantic',
                  'Romantic',
                  'Affection, relationships and deeper connection.',
                ),
                if (adultEligible)
                  option(
                    'mature',
                    'Mature 18+',
                    'Mutual consent is required. Every prompt can be skipped.',
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _showJoinDialog() async {
    final controller = TextEditingController();

    final code = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Join Play Together'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.characters,
          decoration: const InputDecoration(
            labelText: 'Invitation code',
            hintText: 'Example: 12AB34CD',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(
              controller.text.trim(),
            ),
            child: const Text('Join'),
          ),
        ],
      ),
    );

    controller.dispose();

    if (code == null || code.isEmpty || !mounted) return;

    try {
      final session = await _service.joinSession(
        inviteCode: code,
      );

      if (!mounted) return;

      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PlayLobbyPage(
            initialSession: session,
            service: _service,
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Games',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          if (!widget.isInCall)
            IconButton(
              tooltip: 'Join with code',
              onPressed: _showJoinDialog,
              icon: const Icon(Icons.group_add_outlined),
            ),
        ],
      ),
      body: FutureBuilder<PlayTogetherCatalog>(
        future: _catalogFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(30),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 44),
                    const SizedBox(height: 12),
                    Text(
                      snapshot.error?.toString() ??
                          'Games could not be loaded.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 15),
                    FilledButton(
                      onPressed: _refresh,
                      child: const Text('Try again'),
                    ),
                  ],
                ),
              ),
            );
          }

          final catalog = snapshot.data!;

          final normalizedQuery = _searchQuery.trim().toLowerCase();

          final experiences = catalog.experiences.where((experience) {
            final categoryMatches = _selectedCategory == 'all' ||
                experience.category == _selectedCategory;

            if (!categoryMatches) {
              return false;
            }

            if (normalizedQuery.isEmpty) {
              return true;
            }

            return experience.title.toLowerCase().contains(normalizedQuery) ||
                experience.description
                    .toLowerCase()
                    .contains(normalizedQuery) ||
                experience.theme.toLowerCase().contains(normalizedQuery);
          }).toList(growable: false);

          return RefreshIndicator(
            onRefresh: _refresh,
            child: CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: Container(
                    margin: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                    padding: const EdgeInsets.all(20),
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
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '37 games. One shared experience.',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 23,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          widget.isInCall
                              ? 'Choose a game for this call. '
                                  'Your partner will join automatically.'
                              : 'Play casual, friendship and love games '
                                  'hosted by Meera. Your current plan is '
                                  '${catalog.userTier.toUpperCase()}.',
                          style: const TextStyle(
                            color: Colors.white,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(
                      16,
                      0,
                      16,
                      14,
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: _StatPill(
                            value: '${catalog.experiences.length}',
                            label: 'Games',
                            icon: Icons.sports_esports_rounded,
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Expanded(
                          child: _StatPill(
                            value: '2',
                            label: 'Players',
                            icon: Icons.people_alt_rounded,
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Expanded(
                          child: _StatPill(
                            value: 'Meera',
                            label: 'AI Host',
                            icon: Icons.auto_awesome_rounded,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(
                      16,
                      0,
                      16,
                      12,
                    ),
                    child: TextField(
                      controller: _searchController,
                      textInputAction: TextInputAction.search,
                      onChanged: (value) {
                        setState(() {
                          _searchQuery = value;
                        });
                      },
                      decoration: InputDecoration(
                        hintText: 'Search all 37 games',
                        prefixIcon: const Icon(Icons.search_rounded),
                        suffixIcon: _searchQuery.isEmpty
                            ? null
                            : IconButton(
                                tooltip: 'Clear search',
                                onPressed: () {
                                  _searchController.clear();

                                  setState(() {
                                    _searchQuery = '';
                                  });
                                },
                                icon: const Icon(
                                  Icons.close_rounded,
                                ),
                              ),
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18),
                          borderSide: BorderSide.none,
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18),
                          borderSide: const BorderSide(
                            color: Color(0xFFE9E0F5),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: SizedBox(
                    height: 48,
                    child: ListView(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      scrollDirection: Axis.horizontal,
                      children: [
                        _CategoryChip(
                          label: 'All 37',
                          value: 'all',
                          selected: _selectedCategory,
                          onSelected: _selectCategory,
                        ),
                        _CategoryChip(
                          label: 'Casual 7',
                          value: 'casual',
                          selected: _selectedCategory,
                          onSelected: _selectCategory,
                        ),
                        _CategoryChip(
                          label: 'Friendship 10',
                          value: 'friendship',
                          selected: _selectedCategory,
                          onSelected: _selectCategory,
                        ),
                        _CategoryChip(
                          label: 'Love 20',
                          value: 'love',
                          selected: _selectedCategory,
                          onSelected: _selectCategory,
                        ),
                      ],
                    ),
                  ),
                ),
                if (experiences.isEmpty)
                  const SliverFillRemaining(
                    hasScrollBody: false,
                    child: _EmptyGamesState(),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(
                      14,
                      14,
                      14,
                      28,
                    ),
                    sliver: SliverGrid(
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        childAspectRatio: 0.68,
                        crossAxisSpacing: 11,
                        mainAxisSpacing: 11,
                      ),
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final experience = experiences[index];

                          return PlayExperienceCard(
                            experience: experience,
                            onTap: () => _createSession(experience),
                          );
                        },
                        childCount: experiences.length,
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _selectCategory(String category) {
    setState(() => _selectedCategory = category);
  }
}

class _StatPill extends StatelessWidget {
  const _StatPill({
    required this.value,
    required this.label,
    required this.icon,
  });

  final String value;
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 10,
        vertical: 12,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFE9E0F5),
        ),
      ),
      child: Column(
        children: [
          Icon(
            icon,
            size: 20,
            color: const Color(0xFF7B4EFF),
          ),
          const SizedBox(height: 5),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(
              fontSize: 10.5,
              color: Colors.black54,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyGamesState extends StatelessWidget {
  const _EmptyGamesState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(34),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.search_off_rounded,
              size: 54,
              color: Color(0xFF9B87BE),
            ),
            const SizedBox(height: 14),
            const Text(
              'No games found',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Try another search or category.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey.shade700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({
    required this.label,
    required this.value,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final String value;
  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: ChoiceChip(
        label: Text(label),
        selected: selected == value,
        onSelected: (_) => onSelected(value),
      ),
    );
  }
}
