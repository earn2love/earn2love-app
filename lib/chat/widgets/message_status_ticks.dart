import 'package:flutter/material.dart';

enum ChatMessageDeliveryState {
  sent,
  delivered,
  seen,
}

class ChatMessageStatusTicks extends StatelessWidget {
  const ChatMessageStatusTicks({
    super.key,
    required this.state,
  });

  final ChatMessageDeliveryState state;

  @override
  Widget build(BuildContext context) {
    final color = switch (state) {
      ChatMessageDeliveryState.seen => const Color(0xFF34B7F1),
      ChatMessageDeliveryState.delivered => const Color(0xFF7A7188),
      ChatMessageDeliveryState.sent => const Color(0xFF8E8797),
    };

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 170),
      switchInCurve: Curves.easeOut,
      switchOutCurve: Curves.easeIn,
      child: CustomPaint(
        key: ValueKey(state),
        size: Size(
          state == ChatMessageDeliveryState.sent ? 13 : 18,
          12,
        ),
        painter: _MessageTicksPainter(
          color: color,
          doubleTick: state != ChatMessageDeliveryState.sent,
        ),
      ),
    );
  }
}

class _MessageTicksPainter extends CustomPainter {
  const _MessageTicksPainter({
    required this.color,
    required this.doubleTick,
  });

  final Color color;
  final bool doubleTick;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.55
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..isAntiAlias = true;

    void drawTick(double offsetX) {
      final path = Path()
        ..moveTo(offsetX + 1.0, 6.1)
        ..lineTo(offsetX + 4.0, 9.0)
        ..lineTo(offsetX + 10.7, 2.2);

      canvas.drawPath(path, paint);
    }

    if (doubleTick) {
      drawTick(0);
      drawTick(5.0);
    } else {
      drawTick(1.0);
    }
  }

  @override
  bool shouldRepaint(
    covariant _MessageTicksPainter oldDelegate,
  ) {
    return oldDelegate.color != color || oldDelegate.doubleTick != doubleTick;
  }
}
