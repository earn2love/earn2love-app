import 'package:flutter/material.dart';

class HeartAvatar extends StatelessWidget {
  final String? imageUrl;
  final double size;
  final Widget? fallback;

  const HeartAvatar({
    super.key,
    required this.imageUrl,
    this.size = 44,
    this.fallback,
  });

  @override
  Widget build(BuildContext context) {
    final hasImage = imageUrl != null && imageUrl!.trim().isNotEmpty;

    return SizedBox(
      width: size,
      height: size,
      child: ClipPath(
        clipper: _HeartClipper(),
        child: Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
          ),
          child: hasImage
              ? Image.network(
                  imageUrl!,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) =>
                      Center(child: fallback ?? const Icon(Icons.person)),
                )
              : Center(child: fallback ?? const Icon(Icons.person)),
        ),
      ),
    );
  }
}

class _HeartClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final w = size.width;
    final h = size.height;

    final p = Path();

    // Start at bottom tip
    p.moveTo(w * 0.5, h * 0.92);

    // Left bottom curve up to left top
    p.cubicTo(w * 0.10, h * 0.78, w * 0.02, h * 0.48, w * 0.20, h * 0.32);

    // Left top bump
    p.cubicTo(w * 0.35, h * 0.18, w * 0.50, h * 0.28, w * 0.50, h * 0.40);

    // Right top bump
    p.cubicTo(w * 0.50, h * 0.28, w * 0.65, h * 0.18, w * 0.80, h * 0.32);

    // Right bottom curve back to bottom tip
    p.cubicTo(w * 0.98, h * 0.48, w * 0.90, h * 0.78, w * 0.50, h * 0.92);

    p.close();
    return p;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}
