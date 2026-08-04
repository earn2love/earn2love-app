import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

class ChatVoiceMessagePlayer extends StatelessWidget {
  const ChatVoiceMessagePlayer({
    super.key,
    required this.audioPlayer,
    required this.audioUrl,
    required this.activeAudioUrl,
    required this.fallbackDurationSeconds,
    required this.onToggle,
    required this.onSeek,
    required this.onChangeSpeed,
  });

  final AudioPlayer audioPlayer;
  final String audioUrl;
  final String? activeAudioUrl;
  final int fallbackDurationSeconds;

  final Future<void> Function(String audioUrl) onToggle;
  final Future<void> Function(Duration position) onSeek;
  final Future<void> Function(double speed) onChangeSpeed;

  bool get _isActive => audioUrl.isNotEmpty && activeAudioUrl == audioUrl;

  String _formatDuration(Duration duration) {
    final safeDuration = duration.isNegative ? Duration.zero : duration;

    final minutes = safeDuration.inMinutes;
    final seconds = safeDuration.inSeconds.remainder(60);

    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  double _nextSpeed(double currentSpeed) {
    if (currentSpeed < 1.25) return 1.5;
    if (currentSpeed < 1.75) return 2.0;
    return 1.0;
  }

  Duration _safePosition(
    Duration position,
    Duration duration,
  ) {
    if (position < Duration.zero) return Duration.zero;
    if (duration > Duration.zero && position > duration) {
      return duration;
    }
    return position;
  }

  @override
  Widget build(BuildContext context) {
    if (audioUrl.isEmpty) {
      return const Text(
        'Voice unavailable',
        style: TextStyle(
          fontSize: 11.5,
          fontWeight: FontWeight.w700,
        ),
      );
    }

    return StreamBuilder<PlayerState>(
      stream: audioPlayer.playerStateStream,
      builder: (context, stateSnapshot) {
        final playerState = stateSnapshot.data;
        final processingState =
            playerState?.processingState ?? ProcessingState.idle;

        final isLoading = _isActive &&
            (processingState == ProcessingState.loading ||
                processingState == ProcessingState.buffering);

        final isPlaying = _isActive && (playerState?.playing ?? false);

        return StreamBuilder<Duration?>(
          stream: audioPlayer.durationStream,
          builder: (context, durationSnapshot) {
            final fallbackDuration = Duration(
              seconds: fallbackDurationSeconds,
            );

            final duration = _isActive
                ? durationSnapshot.data ??
                    audioPlayer.duration ??
                    fallbackDuration
                : fallbackDuration;

            return StreamBuilder<Duration>(
              stream: audioPlayer.positionStream,
              builder: (context, positionSnapshot) {
                final rawPosition = _isActive
                    ? positionSnapshot.data ?? Duration.zero
                    : Duration.zero;

                final position = _safePosition(
                  rawPosition,
                  duration,
                );

                final maximum = duration.inMilliseconds > 0
                    ? duration.inMilliseconds.toDouble()
                    : 1.0;

                final value =
                    position.inMilliseconds.toDouble().clamp(0.0, maximum);

                return StreamBuilder<double>(
                  stream: audioPlayer.speedStream,
                  initialData: audioPlayer.speed,
                  builder: (context, speedSnapshot) {
                    final speed = speedSnapshot.data ?? 1.0;

                    return SizedBox(
                      width: 220,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(
                            width: 34,
                            height: 34,
                            child: isLoading
                                ? const Padding(
                                    padding: EdgeInsets.all(8),
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(
                                      minWidth: 34,
                                      minHeight: 34,
                                    ),
                                    tooltip: isPlaying ? 'Pause' : 'Play',
                                    onPressed: () => onToggle(audioUrl),
                                    icon: Icon(
                                      isPlaying
                                          ? Icons.pause_circle_filled
                                          : Icons.play_circle_fill,
                                      size: 27,
                                    ),
                                  ),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SliderTheme(
                                  data: SliderTheme.of(context).copyWith(
                                    trackHeight: 3,
                                    thumbShape: const RoundSliderThumbShape(
                                      enabledThumbRadius: 6,
                                    ),
                                    overlayShape: const RoundSliderOverlayShape(
                                      overlayRadius: 12,
                                    ),
                                  ),
                                  child: Slider(
                                    min: 0,
                                    max: maximum,
                                    value: value,
                                    onChanged: !_isActive ||
                                            duration <= Duration.zero
                                        ? null
                                        : (newValue) {
                                            onSeek(
                                              Duration(
                                                milliseconds: newValue.round(),
                                              ),
                                            );
                                          },
                                  ),
                                ),
                                Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 4,
                                  ),
                                  child: Row(
                                    children: [
                                      Text(
                                        _formatDuration(position),
                                        style: const TextStyle(
                                          fontSize: 10,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                      const Spacer(),
                                      Text(
                                        _formatDuration(duration),
                                        style: const TextStyle(
                                          fontSize: 10,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 4),
                          TextButton(
                            style: TextButton.styleFrom(
                              minimumSize: const Size(38, 30),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 5,
                              ),
                              visualDensity: VisualDensity.compact,
                            ),
                            onPressed: !_isActive
                                ? null
                                : () => onChangeSpeed(
                                      _nextSpeed(speed),
                                    ),
                            child: Text(
                              '${speed.toStringAsFixed(
                                speed == speed.roundToDouble() ? 0 : 1,
                              )}x',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            );
          },
        );
      },
    );
  }
}
