import 'package:flutter/material.dart';

import '../screens/play_together_page.dart';

class InCallPlayOverlay extends StatefulWidget {
  const InCallPlayOverlay({
    super.key,
    required this.visible,
    required this.minimized,
    required this.callTypeLabel,
    required this.onClose,
    required this.onMinimize,
    required this.onRestore,
  });

  final bool visible;
  final bool minimized;
  final String callTypeLabel;
  final VoidCallback onClose;
  final VoidCallback onMinimize;
  final VoidCallback onRestore;

  @override
  State<InCallPlayOverlay> createState() => _InCallPlayOverlayState();
}

class _InCallPlayOverlayState extends State<InCallPlayOverlay> {
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    if (!widget.visible) {
      return const SizedBox.shrink();
    }

    if (widget.minimized) {
      return Positioned(
        left: 16,
        right: 16,
        bottom: 104,
        child: SafeArea(
          top: false,
          child: Material(
            color: const Color(0xFF2C1B3A),
            elevation: 12,
            borderRadius: BorderRadius.circular(18),
            child: InkWell(
              onTap: widget.onRestore,
              borderRadius: BorderRadius.circular(18),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 13,
                ),
                child: Row(
                  children: [
                    const CircleAvatar(
                      backgroundColor: Color(0xFFFF4D91),
                      child: Icon(
                        Icons.sports_esports_outlined,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Play Together is active',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${widget.callTypeLabel} continues in the background',
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(
                      Icons.open_in_full,
                      color: Colors.white,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    return Positioned.fill(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            10,
            56,
            10,
            92,
          ),
          child: Material(
            elevation: 24,
            clipBehavior: Clip.antiAlias,
            borderRadius: BorderRadius.circular(24),
            color: Theme.of(context).scaffoldBackgroundColor,
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 9,
                  ),
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Color(0xFF7B4EFF),
                        Color(0xFFFF4D91),
                      ],
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.auto_awesome,
                        color: Colors.white,
                      ),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Play Together',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: 'Minimise game',
                        onPressed: widget.onMinimize,
                        icon: const Icon(
                          Icons.minimize,
                          color: Colors.white,
                        ),
                      ),
                      IconButton(
                        tooltip: 'Close game',
                        onPressed: widget.onClose,
                        icon: const Icon(
                          Icons.close,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Navigator(
                    key: _navigatorKey,
                    onGenerateRoute: (_) {
                      return MaterialPageRoute<void>(
                        builder: (_) => const PlayTogetherPage(),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
