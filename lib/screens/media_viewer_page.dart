import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

class MediaViewerPage extends StatefulWidget {
  final List<Map<String, dynamic>> mediaList;
  final int initialIndex;

  const MediaViewerPage({
    super.key,
    required this.mediaList,
    required this.initialIndex,
  });

  @override
  State<MediaViewerPage> createState() => _MediaViewerPageState();
}

class _MediaViewerPageState extends State<MediaViewerPage> {

  late PageController _controller;
  int currentIndex = 0;

  @override
  void initState() {
    super.initState();
    currentIndex = widget.initialIndex;
    _controller = PageController(initialPage: widget.initialIndex);
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        onVerticalDragUpdate: (details) {
          if (details.delta.dy > 12) {
            Navigator.pop(context);
          }
        },
        child: PageView.builder(
          controller: _controller,
          itemCount: widget.mediaList.length,
          onPageChanged: (i) {
            setState(() {
              currentIndex = i;
            });
          },
          itemBuilder: (context, index) {

            final media = widget.mediaList[index];
            final type = media['type'];
            final url = media['url'];

            if (type == 'video') {
              return Center(
                child: VideoViewer(url: url),
              );
            }

            return ImageViewer(url: url);
          },
        ),
      ),
    );
  }
}

class ImageViewer extends StatefulWidget {

  final String url;

  const ImageViewer({super.key, required this.url});

  @override
  State<ImageViewer> createState() => _ImageViewerState();
}

class _ImageViewerState extends State<ImageViewer> {

  bool liked = false;
  bool showHeart = false;

  void _doubleTapLike() {

    setState(() {
      liked = !liked;
      showHeart = true;
    });

    Future.delayed(const Duration(milliseconds: 800), () {
      if (mounted) {
        setState(() {
          showHeart = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {

    return GestureDetector(
      onDoubleTap: _doubleTapLike,
      child: Stack(
        alignment: Alignment.center,
        children: [

          InteractiveViewer(
            minScale: 1,
            maxScale: 4,
            child: Center(
              child: Image.network(widget.url),
            ),
          ),

          if (showHeart)
            const Icon(
              Icons.favorite,
              color: Colors.white,
              size: 120,
            )
        ],
      ),
    );
  }
}

class VideoViewer extends StatefulWidget {

  final String url;

  const VideoViewer({super.key, required this.url});

  @override
  State<VideoViewer> createState() => _VideoViewerState();
}

class _VideoViewerState extends State<VideoViewer> {

  late VideoPlayerController controller;

  @override
  void initState() {
    super.initState();

    controller = VideoPlayerController.network(widget.url)
      ..initialize().then((_) {

        setState(() {});
        controller.play();
      });
  }

  @override
  Widget build(BuildContext context) {

    if (!controller.value.isInitialized) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    return Center(
      child: AspectRatio(
        aspectRatio: controller.value.aspectRatio,
        child: VideoPlayer(controller),
      ),
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }
}