import 'package:flutter/material.dart';

class VideoPlayerPage extends StatelessWidget {
  final String videoUrl;
  const VideoPlayerPage({super.key, required this.videoUrl});

  @override
  Widget build(BuildContext context) {
    // Next step: add video_player package and implement proper playback
    return Scaffold(
      appBar: AppBar(title: const Text("Video")),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            "Video player coming next ✅\n\nURL:\n$videoUrl",
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
        ),
      ),
    );
  }
}