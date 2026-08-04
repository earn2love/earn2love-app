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

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
      ),
      child: InkWell(
        onTap: experience.accessible ? onTap : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    experience.icon,
                    style: const TextStyle(fontSize: 32),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: _tierColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      experience.tier.toUpperCase(),
                      style: TextStyle(
                        color: _tierColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                experience.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 7),
              Text(
                experience.description,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: Colors.grey.shade700,
                  height: 1.3,
                ),
              ),
              const Spacer(),
              Row(
                children: [
                  Icon(
                    Icons.schedule,
                    size: 15,
                    color: Colors.grey.shade600,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    '${experience.estimatedMinutes} min',
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 12,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    experience.accessible
                        ? Icons.arrow_forward_rounded
                        : Icons.lock_rounded,
                    color: experience.accessible ? _tierColor : Colors.grey,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
