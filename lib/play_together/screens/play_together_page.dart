import 'package:flutter/material.dart';

import '../models/play_experience.dart';
import '../services/play_together_service.dart';
import '../widgets/play_experience_card.dart';
import 'play_lobby_page.dart';

class PlayTogetherPage extends StatefulWidget {
  const PlayTogetherPage({super.key});

  @override
  State<PlayTogetherPage> createState() => _PlayTogetherPageState();
}

class _PlayTogetherPageState extends State<PlayTogetherPage> {
  final PlayTogetherService _service = PlayTogetherService();

  late Future<PlayTogetherCatalog> _catalogFuture;
  String _selectedCategory = 'all';
  bool _creating = false;

  @override
  void initState() {
    super.initState();
    _catalogFuture = _service.getExperiences();
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

    setState(() => _creating = true);

    try {
      final comfortLevel = await _selectComfortLevel(
        adultEligible: experience.adultEligible,
      );

      if (comfortLevel == null || !mounted) return;

      final session = await _service.createSession(
        experienceId: experience.id,
        language: Localizations.localeOf(context).languageCode,
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
          'Play Together',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
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
                          'Play Together could not be loaded.',
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
          final experiences = _selectedCategory == 'all'
              ? catalog.experiences
              : catalog.experiences
                  .where(
                    (experience) => experience.category == _selectedCategory,
                  )
                  .toList(growable: false);

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
                          'Spend meaningful time together',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 23,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          '37 free AI-powered social experiences. '
                          'Your current plan is ${catalog.userTier.toUpperCase()}.',
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
                SliverPadding(
                  padding: const EdgeInsets.all(14),
                  sliver: SliverGrid(
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      childAspectRatio: 0.72,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
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
