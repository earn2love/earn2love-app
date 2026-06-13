import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import 'chat_room_page.dart';

class UserProfilePage extends StatefulWidget {
  final String userId;
  const UserProfilePage({super.key, required this.userId});

  @override
  State<UserProfilePage> createState() => _UserProfilePageState();
}

class _UserProfilePageState extends State<UserProfilePage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(widget.userId);

  int _tabIndex = 0;

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  String _reqDocId(String a, String b) {
    final ids = [a, b]..sort();
    return "${ids[0]}__${ids[1]}";
  }

  DocumentReference<Map<String, dynamic>> _reqRef() {
    final docId = _reqDocId(uid, widget.userId);
    return FirebaseFirestore.instance.collection('friendRequests').doc(docId);
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _mediaStream(String type) {
    return userRef
        .collection('media')
        .where('type', isEqualTo: type)
        .orderBy('createdAt', descending: true)
        .limit(120)
        .snapshots();
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _allMediaStream() {
    return userRef.collection('media').orderBy('createdAt', descending: true).limit(300).snapshots();
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _followersStream() {
    return userRef.collection('followers').limit(500).snapshots();
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _followingStream() {
    return userRef.collection('following').limit(500).snapshots();
  }

  Future<void> _sendFollowRequest(BuildContext context) async {
    if (widget.userId == uid) return;

    final reqRef = _reqRef();
    final snap = await reqRef.get();
    final existing = snap.data();
    final status = (existing?['status'] ?? '').toString();

    if (status == 'accepted') {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Already friends ✅")),
      );
      return;
    }
    if (status == 'pending') {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Follow request sent ✅")),
      );
      return;
    }

    await reqRef.set({
      'fromUid': uid,
      'toUid': widget.userId,
      'status': 'pending',
      'createdAt': existing?['createdAt'] ?? FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Follow request sent ✅")),
    );
  }

  Future<void> _acceptRequest(BuildContext context) async {
    final reqRef = _reqRef();
    await reqRef.set({
      'status': 'accepted',
      'acceptedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Friends now ✅")),
    );
  }

  Future<void> _declineRequest(BuildContext context) async {
    final reqRef = _reqRef();
    await reqRef.set({
      'status': 'declined',
      'declinedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Request declined")),
    );
  }

  Future<void> _openChat(BuildContext context) async {
    final rooms = FirebaseFirestore.instance.collection('chatRooms');
    final q = await rooms.where('participants', arrayContains: uid).limit(100).get();

    String? roomId;
    for (final d in q.docs) {
      final p = (d.data()['participants'] as List?)?.map((e) => e.toString()).toList() ?? [];
      if (p.contains(widget.userId) && p.length == 2) {
        roomId = d.id;
        break;
      }
    }

    roomId ??= rooms.doc().id;
    await rooms.doc(roomId).set({
      'participants': [uid, widget.userId],
      'updatedAt': FieldValue.serverTimestamp(),
      'lastMessage': '',
      'lastMessageAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!context.mounted) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatRoomPage(roomId: roomId!, otherUid: widget.userId),
      ),
    );
  }

  Widget _buildTabBody() {
    if (_tabIndex == 0) {
      return _UserMediaGridStream(
        stream: _mediaStream('photo'),
        ownerUid: widget.userId,
        type: 'photo',
      );
    }
    return _UserMediaGridStream(
      stream: _mediaStream('video'),
      ownerUid: widget.userId,
      type: 'video',
    );
  }

  @override
  Widget build(BuildContext context) {
    final reqRef = _reqRef();

    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: userRef.snapshots(),
      builder: (context, userSnap) {
        if (!userSnap.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final u = userSnap.data!.data() ?? {};
        final name = asString(u['displayName'], def: 'User');
        final photo = asString(u['photoUrl'] ?? u['profilePhoto']);
        final bio = asString(u['bio']);
        final isMe = widget.userId == uid;

        return Scaffold(
          backgroundColor: Colors.grey.shade50,
          body: Column(
            children: [
              Container(
                height: 230,
                width: double.infinity,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.pink.shade400,
                      Colors.purple.shade500,
                      Colors.indigo.shade600,
                    ],
                  ),
                ),
                child: SafeArea(
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
                    child: Column(
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Text(
                                name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 21,
                                  fontWeight: FontWeight.w900,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Expanded(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Padding(
                                padding: const EdgeInsets.only(top: 16),
                                child: Container(
                                  padding: const EdgeInsets.all(3),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: Colors.white.withOpacity(0.95),
                                      width: 2,
                                    ),
                                  ),
                                  child: CircleAvatar(
                                    radius: 46,
                                    backgroundImage:
                                        photo.isEmpty ? null : NetworkImage(photo),
                                    backgroundColor: Colors.white.withOpacity(0.18),
                                    child: photo.isEmpty
                                        ? const Icon(
                                            Icons.person,
                                            size: 40,
                                            color: Colors.white,
                                          )
                                        : null,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.only(top: 8),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      _StatsRow(
                                        allMediaStream: _allMediaStream(),
                                        followersStream: _followersStream(),
                                        followingStream: _followingStream(),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        bio.isEmpty
                                            ? 'No bio added yet.'
                                            : bio,
                                        maxLines: 3,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          color: bio.isEmpty ? Colors.white70 : Colors.white,
                                          fontSize: 12.5,
                                          height: 1.28,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                                        stream: reqRef.snapshots(),
                                        builder: (context, reqSnap) {
                                          final req = reqSnap.data?.data();
                                          final status = (req?['status'] ?? '').toString();
                                          final fromUid = (req?['fromUid'] ?? '').toString();
                                          final toUid = (req?['toUid'] ?? '').toString();

                                          final isIncomingPending =
                                              status == 'pending' &&
                                              toUid == uid &&
                                              fromUid == widget.userId;
                                          final isOutgoingPending =
                                              status == 'pending' &&
                                              fromUid == uid &&
                                              toUid == widget.userId;
                                          final isAccepted = status == 'accepted';

                                          if (isMe) {
                                            return const SizedBox.shrink();
                                          }

                                          if (isIncomingPending) {
                                            return Row(
                                              children: [
                                                Expanded(
                                                  child: _ActionButton(
                                                    text: 'Accept',
                                                    filled: true,
                                                    onTap: () => _acceptRequest(context),
                                                  ),
                                                ),
                                                const SizedBox(width: 8),
                                                Expanded(
                                                  child: _ActionButton(
                                                    text: 'Decline',
                                                    filled: false,
                                                    onTap: () => _declineRequest(context),
                                                  ),
                                                ),
                                              ],
                                            );
                                          }

                                          return Row(
                                            children: [
                                              Expanded(
                                                child: _ActionButton(
                                                  text: isAccepted
                                                      ? 'Friends'
                                                      : isOutgoingPending
                                                          ? 'Follow request sent'
                                                          : 'Follow request',
                                                  filled: true,
                                                  onTap: (isAccepted || isOutgoingPending)
                                                      ? null
                                                      : () => _sendFollowRequest(context),
                                                ),
                                              ),
                                              const SizedBox(width: 8),
                                              Expanded(
                                                child: _ActionButton(
                                                  text: 'Message',
                                                  filled: false,
                                                  onTap: () => _openChat(context),
                                                ),
                                              ),
                                            ],
                                          );
                                        },
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          decoration: BoxDecoration(
                            border: Border(
                              top: BorderSide(
                                color: Colors.white.withOpacity(0.22),
                                width: 0.8,
                              ),
                            ),
                          ),
                          child: Row(
                            children: [
                              _HeaderTabButton(
                                text: 'Photos',
                                selected: _tabIndex == 0,
                                onTap: () => setState(() => _tabIndex = 0),
                              ),
                              _HeaderTabButton(
                                text: 'Videos',
                                selected: _tabIndex == 1,
                                onTap: () => setState(() => _tabIndex = 1),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Container(
                height: 1,
                color: Colors.black.withOpacity(0.08),
              ),
              Expanded(
                child: _buildTabBody(),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String text;
  final bool filled;
  final VoidCallback? onTap;

  const _ActionButton({
    required this.text,
    required this.filled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bg = filled ? Colors.white.withOpacity(onTap == null ? 0.12 : 0.18) : Colors.transparent;
    final border = Colors.white.withOpacity(0.30);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Container(
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: border),
          ),
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: onTap == null ? Colors.white70 : Colors.white,
              fontSize: 11.5,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ),
    );
  }
}

class _HeaderTabButton extends StatelessWidget {
  final String text;
  final bool selected;
  final VoidCallback onTap;

  const _HeaderTabButton({
    required this.text,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Container(
          height: 42,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: selected ? Colors.white : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Text(
            text,
            style: TextStyle(
              color: selected ? Colors.white : Colors.white70,
              fontWeight: selected ? FontWeight.w900 : FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final Stream<QuerySnapshot<Map<String, dynamic>>> allMediaStream;
  final Stream<QuerySnapshot<Map<String, dynamic>>> followersStream;
  final Stream<QuerySnapshot<Map<String, dynamic>>> followingStream;

  const _StatsRow({
    required this.allMediaStream,
    required this.followersStream,
    required this.followingStream,
  });

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: allMediaStream,
      builder: (context, mediaSnap) {
        final postsCount = mediaSnap.data?.docs.length ?? 0;

        return Row(
          children: [
            Expanded(child: _StatText(value: postsCount.toString(), label: 'Posts')),
            StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: followersStream,
              builder: (context, snap) {
                final count = snap.data?.docs.length ?? 0;
                return Expanded(child: _StatText(value: count.toString(), label: 'Followers'));
              },
            ),
            StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: followingStream,
              builder: (context, snap) {
                final count = snap.data?.docs.length ?? 0;
                return Expanded(child: _StatText(value: count.toString(), label: 'Following'));
              },
            ),
          ],
        );
      },
    );
  }
}

class _StatText extends StatelessWidget {
  final String value;
  final String label;

  const _StatText({
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w900,
            height: 1.0,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Colors.white70,
            fontWeight: FontWeight.w700,
            fontSize: 10.5,
            height: 1.0,
          ),
        ),
      ],
    );
  }
}

class _UserMediaGridStream extends StatelessWidget {
  final Stream<QuerySnapshot<Map<String, dynamic>>> stream;
  final String type;
  final String ownerUid;

  const _UserMediaGridStream({
    required this.stream,
    required this.type,
    required this.ownerUid,
  });

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: stream,
      builder: (context, snap) {
        if (!snap.hasData) {
          return const Center(child: CircularProgressIndicator());
        }

        final docs = snap.data!.docs;
        if (docs.isEmpty) {
          return Center(
            child: Text(
              type == 'photo' ? 'No photos uploaded yet.' : 'No videos uploaded yet.',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          );
        }

        final mediaList = docs.map((doc) {
          final m = doc.data();
          return <String, dynamic>{
            'id': doc.id,
            'type': asString(m['type']),
            'url': asString(m['url']),
            'thumbUrl': asString(m['thumbUrl']),
          };
        }).toList();

        return GridView.builder(
          padding: const EdgeInsets.all(10),
          cacheExtent: 2000,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            mainAxisSpacing: 6,
            crossAxisSpacing: 6,
          ),
          itemCount: mediaList.length,
          itemBuilder: (_, i) {
            final item = mediaList[i];
            final url = asString(item['url']);
            final thumbUrl = asString(item['thumbUrl']);

            return Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: url.isEmpty
                    ? null
                    : () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => _UserProfileGalleryPage(
                              mediaList: mediaList,
                              initialIndex: i,
                              title: type == 'photo' ? 'Photos' : 'Videos',
                            ),
                          ),
                        );
                      },
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      if (type == 'photo')
                        Image.network(
                          url,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Container(
                            color: Colors.grey.shade200,
                            alignment: Alignment.center,
                            child: const Icon(Icons.broken_image_outlined),
                          ),
                        )
                      else if (thumbUrl.isNotEmpty)
                        Image.network(
                          thumbUrl,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => _videoPlaceholder(),
                        )
                      else
                        _videoPlaceholder(),
                      if (type == 'video')
                        Align(
                          alignment: Alignment.center,
                          child: Container(
                            padding: const EdgeInsets.all(7),
                            decoration: BoxDecoration(
                              color: Colors.black.withOpacity(0.40),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.play_arrow, color: Colors.white, size: 20),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _videoPlaceholder() {
    return Container(
      color: Colors.grey.shade200,
      child: Center(
        child: Icon(Icons.videocam, color: Colors.grey.shade600, size: 30),
      ),
    );
  }
}

class _UserProfileGalleryPage extends StatefulWidget {
  final List<Map<String, dynamic>> mediaList;
  final int initialIndex;
  final String title;

  const _UserProfileGalleryPage({
    required this.mediaList,
    required this.initialIndex,
    required this.title,
  });

  @override
  State<_UserProfileGalleryPage> createState() => _UserProfileGalleryPageState();
}

class _UserProfileGalleryPageState extends State<_UserProfileGalleryPage> {
  late final PageController _pageController;
  late int _index;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex;
    _pageController = PageController(initialPage: widget.initialIndex);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(widget.title),
      ),
      body: PageView.builder(
        controller: _pageController,
        itemCount: widget.mediaList.length,
        onPageChanged: (i) => setState(() => _index = i),
        itemBuilder: (context, i) {
          final item = widget.mediaList[i];
          final type = (item['type'] ?? 'photo').toString();
          final url = (item['url'] ?? '').toString();

          if (type == 'video') {
            return _GalleryVideoPage(url: url);
          }

          return InteractiveViewer(
            minScale: 1,
            maxScale: 4,
            child: Center(
              child: Image.network(
                url,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const Text(
                  'Image failed to load',
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _GalleryVideoPage extends StatelessWidget {
  final String url;

  const _GalleryVideoPage({required this.url});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: _SimpleVideoPlayer(url: url),
    );
  }
}

class _SimpleVideoPlayer extends StatefulWidget {
  final String url;

  const _SimpleVideoPlayer({required this.url});

  @override
  State<_SimpleVideoPlayer> createState() => _SimpleVideoPlayerState();
}

class _SimpleVideoPlayerState extends State<_SimpleVideoPlayer> {
  late VideoPlayerController controller;
  bool _showPlayIcon = false;

  @override
  void initState() {
    super.initState();
    controller = VideoPlayerController.network(widget.url)
      ..initialize().then((_) {
        if (!mounted) return;
        controller.setLooping(true);
        controller.play();
        setState(() {});
      });
  }

  void _togglePlay() {
    if (!controller.value.isInitialized) return;
    if (controller.value.isPlaying) {
      controller.pause();
      setState(() => _showPlayIcon = true);
    } else {
      controller.play();
      setState(() => _showPlayIcon = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return GestureDetector(
      onTap: _togglePlay,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox.expand(
            child: FittedBox(
              fit: BoxFit.contain,
              child: SizedBox(
                width: controller.value.size.width,
                height: controller.value.size.height,
                child: VideoPlayer(controller),
              ),
            ),
          ),
          if (_showPlayIcon)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.35),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.play_arrow,
                color: Colors.white,
                size: 34,
              ),
            ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }
}