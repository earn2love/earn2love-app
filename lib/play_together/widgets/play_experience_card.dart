import 'package:flutter/material.dart';

import '../models/play_experience.dart';

class PlayExperienceCard extends StatelessWidget {
  const PlayExperienceCard({
    super.key,
    required this.experience,
    required this.onTap,
  });

  final PlayExperience experience;
  final VoidCallback onTap;

  Color get _tierColor {
    switch (experience.tier) {
      case 'love':
        return const Color(0xFFFF4D91);
      case 'friendship':
        return const Color(0xFF6C63FF);
      default:
        return const Color(0xFF2EAD77);
    }
  }

  List<Color> get _gradientColors {
    switch (experience.category) {
      case 'love':
        return const [
          Color(0xFFFFEEF5),
          Color(0xFFFFF8FB),
        ];
      case 'friendship':
        return const [
          Color(0xFFF1EFFF),
          Color(0xFFF9F8FF),
        ];
      default:
        return const [
          Color(0xFFEAFBF3),
          Color(0xFFF8FFFB),
        ];
    }
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      enabled: experience.accessible,
      label: '${experience.title}, ${experience.tier} game',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: experience.accessible
              ? onTap
              : () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        '${experience.tier.toUpperCase()} '
                        'membership is required for '
                        '${experience.title}.',
                      ),
                    ),
                  );
                },
          borderRadius: BorderRadius.circular(24),
          child: Ink(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: _gradientColors,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: _tierColor.withValues(
                  alpha: 0.22,
                ),
              ),
              boxShadow: [
                BoxShadow(
                  color: _tierColor.withValues(
                    alpha: 0.08,
                  ),
                  blurRadius: 14,
                  offset: const Offset(0, 7),
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(
                            alpha: 0.82,
                          ),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(
                          experience.icon,
                          style: const TextStyle(
                            fontSize: 27,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 9,
                          vertical: 5,
                        ),
                        decoration: BoxDecoration(
                          color: _tierColor.withValues(
                            alpha: 0.13,
                          ),
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (!experience.accessible) ...[
                              Icon(
                                Icons.lock_rounded,
                                size: 12,
                                color: _tierColor,
                              ),
                              const SizedBox(width: 3),
                            ],
                            Text(
                              experience.tier.toUpperCase(),
                              style: TextStyle(
                                color: _tierColor,
                                fontSize: 9.5,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 13),
                  Text(
                    experience.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF241D31),
                      fontSize: 16.5,
                      height: 1.12,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Text(
                    experience.description,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF6E6677),
                      fontSize: 12.2,
                      height: 1.28,
                    ),
                  ),
                  const Spacer(),
                  Wrap(
                    spacing: 5,
                    runSpacing: 5,
                    children: [
                      _GameFeatureBadge(
                        icon: Icons.schedule_rounded,
                        label: '${experience.estimatedMinutes}m',
                      ),
                      const _GameFeatureBadge(
                        icon: Icons.people_alt_rounded,
                        label: '2 players',
                      ),
                      const _GameFeatureBadge(
                        icon: Icons.auto_awesome_rounded,
                        label: 'Meera',
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: Container(
                      height: 36,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: experience.accessible
                            ? _tierColor
                            : Colors.grey.shade300,
                        borderRadius: BorderRadius.circular(13),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            experience.accessible
                                ? Icons.play_arrow_rounded
                                : Icons.lock_rounded,
                            size: 18,
                            color: experience.accessible
                                ? Colors.white
                                : Colors.grey.shade700,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            experience.accessible ? 'Play' : 'Locked',
                            style: TextStyle(
                              color: experience.accessible
                                  ? Colors.white
                                  : Colors.grey.shade700,
                              fontSize: 12,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GameFeatureBadge extends StatelessWidget {
  const _GameFeatureBadge({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 6,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 11,
            color: const Color(0xFF756B80),
          ),
          const SizedBox(width: 3),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF756B80),
              fontSize: 9.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
