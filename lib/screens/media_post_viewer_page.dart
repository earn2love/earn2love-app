import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'video_player_page.dart';

class MediaPostViewerPage extends StatelessWidget {
  final String ownerUid;
  final String mediaId;
  final String mediaUrl;
  final String mediaType; // photo / video
  final String title;
  final bool flagged;
  final String ownerName;
  final String ownerPhotoUrl;
  final bool isVirtualProfilePhoto;

  const MediaPostViewerPage({
    super.key,
    required this.ownerUid,
    required this.mediaId,
    required this.mediaUrl,
    required this.mediaType,
    required this.title,
    required this.flagged,
    required this.ownerName,
    required this.ownerPhotoUrl,
    this.isVirtualProfilePhoto = false,
  });

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get mediaRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(ownerUid)
          .collection('media')
          .doc(mediaId);

  DocumentReference<Map<String, dynamic>> get likeRef =>
      mediaRef.collection('likes').doc(uid);

  Future<void> _toggleLike(bool alreadyLiked) async {
    if (isVirtualProfilePhoto) return;

    await FirebaseFirestore.instance.runTransaction((tx) async {
      final mediaSnap = await tx.get(mediaRef);
      final likeSnap = await tx.get(likeRef);

      if (!mediaSnap.exists) return;

      final currentCount =
          ((mediaSnap.data()?['likeCount'] ?? 0) as num).toInt();

      if (alreadyLiked && likeSnap.exists) {
        tx.delete(likeRef);
        tx.set(
          mediaRef,
          {'likeCount': currentCount > 0 ? currentCount - 1 : 0},
          SetOptions(merge: true),
        );
      } else if (!alreadyLiked && !likeSnap.exists) {
        tx.set(likeRef, {
          'uid': uid,
          'createdAt': FieldValue.serverTimestamp(),
        });
        tx.set(
          mediaRef,
          {'likeCount': currentCount + 1},
          SetOptions(merge: true),
        );
      }
    });
  }

  Future<bool> _confirmWarningIfNeeded(BuildContext context) async {
    if (!flagged) return true;

    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Warning"),
        content:
            const Text("This media may be sensitive. Do you want to continue?"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("No"),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text("Open"),
          ),
        ],
      ),
    );

    return ok == true;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(title),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Container(
              color: Colors.black,
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundImage: ownerPhotoUrl.isEmpty
                        ? null
                        : NetworkImage(ownerPhotoUrl),
                    child:
                        ownerPhotoUrl.isEmpty ? const Icon(Icons.person) : null,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      ownerName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Center(
                child: mediaType == 'video'
                    ? FutureBuilder<bool>(
                        future: _confirmWarningIfNeeded(context),
                        builder: (context, snap) {
                          if (!snap.hasData) {
                            return const CircularProgressIndicator(
                                color: Colors.white);
                          }
                          if (snap.data != true) {
                            return const Text(
                              "Video not opened",
                              style: TextStyle(color: Colors.white),
                            );
                          }
                          return VideoPlayerPage(videoUrl: mediaUrl);
                        },
                      )
                    : FutureBuilder<bool>(
                        future: _confirmWarningIfNeeded(context),
                        builder: (context, snap) {
                          if (!snap.hasData) {
                            return const CircularProgressIndicator(
                                color: Colors.white);
                          }
                          if (snap.data != true) {
                            return const Text(
                              "Photo not opened",
                              style: TextStyle(color: Colors.white),
                            );
                          }
                          return InteractiveViewer(
                            minScale: 1,
                            maxScale: 4,
                            child: Image.network(
                              mediaUrl,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const Text(
                                "Failed to load media",
                                style: TextStyle(color: Colors.white),
                              ),
                            ),
                          );
                        },
                      ),
              ),
            ),
            if (!isVirtualProfilePhoto)
              StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                stream: mediaRef.snapshots(),
                builder: (context, mediaSnap) {
                  final mediaData = mediaSnap.data?.data() ?? {};
                  final likeCount =
                      ((mediaData['likeCount'] ?? 0) as num).toInt();

                  return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                    stream: likeRef.snapshots(),
                    builder: (context, likeSnap) {
                      final liked = likeSnap.data?.exists == true;

                      return Container(
                        width: double.infinity,
                        padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
                        color: Colors.black,
                        child: Row(
                          children: [
                            IconButton(
                              onPressed: () => _toggleLike(liked),
                              icon: Icon(
                                liked ? Icons.favorite : Icons.favorite_border,
                                color: liked ? Colors.redAccent : Colors.white,
                                size: 28,
                              ),
                            ),
                            Text(
                              "$likeCount likes",
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
