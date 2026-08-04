class PlayExperience {
  const PlayExperience({
    required this.id,
    required this.title,
    required this.tier,
    required this.category,
    required this.icon,
    required this.description,
    required this.theme,
    required this.estimatedMinutes,
    required this.accessible,
    required this.adultEligible,
  });

  final String id;
  final String title;
  final String tier;
  final String category;
  final String icon;
  final String description;
  final String theme;
  final int estimatedMinutes;
  final bool accessible;
  final bool adultEligible;

  factory PlayExperience.fromMap(
    Map<String, dynamic> map,
  ) {
    return PlayExperience(
      id: (map['id'] ?? '').toString(),
      title: (map['title'] ?? 'Experience').toString(),
      tier: (map['tier'] ?? 'casual').toString(),
      category: (map['category'] ?? 'casual').toString(),
      icon: (map['icon'] ?? '🎮').toString(),
      description: (map['description'] ?? '').toString(),
      theme: (map['theme'] ?? 'friendly').toString(),
      estimatedMinutes: (map['estimatedMinutes'] as num?)?.toInt() ?? 10,
      accessible: map['accessible'] == true,
      adultEligible: map['adultEligible'] == true,
    );
  }
}
