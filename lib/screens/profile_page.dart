import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:video_player/video_player.dart';
import 'package:visibility_detector/visibility_detector.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  CollectionReference<Map<String, dynamic>> get mediaRef =>
      userRef.collection('media');

  final TextEditingController _nameCtrl = TextEditingController();
  final TextEditingController _bioCtrl = TextEditingController();
  final TextEditingController _interestCtrl = TextEditingController();

  bool _savingName = false;
  bool _nameDirty = false;
  bool _isEditingName = false;

  bool _savingBio = false;
  bool _bioDirty = false;
  bool _isEditingBio = false;

  List<String> _interests = [];
  int _tabIndex = 0;

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  List<String> asStringList(dynamic v) {
    if (v is List) {
      return v
          .map((e) => e.toString().trim())
          .where((e) => e.isNotEmpty)
          .toList();
    }
    if (v is String) {
      return v
          .split(',')
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
    }
    return [];
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _bioCtrl.dispose();
    _interestCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveNameIfNeeded() async {
    if (!_nameDirty || _savingName) return;

    final value = _nameCtrl.text.trim();
    if (value.isEmpty) return;

    _savingName = true;
    try {
      await userRef.set({
        'displayName': value,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
      _nameDirty = false;
    } finally {
      _savingName = false;
    }
  }

  Future<void> _saveBioIfNeeded() async {
    if (!_bioDirty || _savingBio) return;

    _savingBio = true;
    try {
      await userRef.set({
        'bio': _bioCtrl.text.trim(),
        'interests': _interests,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
      _bioDirty = false;
    } finally {
      _savingBio = false;
    }
  }

  void _snack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _openUploadSheet({required bool hasProfilePic}) async {
    await showModalBottomSheet(
      context: context,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (_) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.person)),
                  title: Text(
                    hasProfilePic ? 'Change profile pic' : 'Upload profile pic',
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                  subtitle: const Text('Shows on profile, users list & chats'),
                  onTap: () async {
                    Navigator.pop(context);
                    await _pickAndUploadProfilePic();
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.photo)),
                  title: const Text(
                    'Upload photo',
                    style: TextStyle(fontWeight: FontWeight.w900),
                  ),
                  subtitle: const Text('Adds to photos tab'),
                  onTap: () async {
                    Navigator.pop(context);
                    await _pickAndUploadMedia(type: 'photo');
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.videocam)),
                  title: const Text(
                    'Upload video',
                    style: TextStyle(fontWeight: FontWeight.w900),
                  ),
                  subtitle: const Text('Adds to videos & reels'),
                  onTap: () async {
                    Navigator.pop(context);
                    await _pickAndUploadMedia(type: 'video');
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _pickAndUploadProfilePic() async {
    try {
      final x = await ImagePicker().pickImage(
        source: ImageSource.gallery,
        imageQuality: 82,
      );
      if (x == null) return;

      final file = File(x.path);
      if (!await file.exists()) {
        _snack('Selected file not found');
        return;
      }

      _snack('Uploading profile pic...');

      final id = 'profile_${DateTime.now().millisecondsSinceEpoch}';
      final path = 'users/$uid/profile/$id.jpg';
      final ref = FirebaseStorage.instance.ref().child(path);

      final metadata = SettableMetadata(contentType: 'image/jpeg');
      final task = ref.putFile(file, metadata);
      final snap = await task;
      final url = await snap.ref.getDownloadURL();

      await userRef.set({
        'photoUrl': url,
        'profilePhoto': url,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      _snack('Profile pic updated ✅');
    } on FirebaseException catch (e) {
      _snack('Upload failed: ${e.code}');
    } catch (e) {
      _snack('Upload failed: $e');
    }
  }

  Future<void> _pickAndUploadMedia({required String type}) async {
    try {
      XFile? x;

      if (type == 'photo') {
        x = await ImagePicker().pickImage(
          source: ImageSource.gallery,
          imageQuality: 82,
        );
      } else {
        x = await ImagePicker().pickVideo(source: ImageSource.gallery);
      }

      if (x == null) return;

      final file = File(x.path);
      if (!await file.exists()) {
        _snack('Selected file not found');
        return;
      }

      final bytes = await file.length();
      if (bytes <= 0) {
        _snack('Invalid file');
        return;
      }

      if (type == 'photo' && bytes > 5 * 1024 * 1024) {
        _snack('Photo too large. Use under 5MB.');
        return;
      }

      if (type == 'video' && bytes > 50 * 1024 * 1024) {
        _snack('Video too large. Use under 50MB.');
        return;
      }

      _snack('Uploading $type...');

      final userSnap = await userRef.get();
      final userData = userSnap.data() ?? {};
      final ownerName = asString(userData['displayName'], def: 'User');
      final ownerPhoto = asString(userData['photoUrl'] ?? userData['profilePhoto']);

      final mediaId = FirebaseFirestore.instance.collection('tmp').doc().id;
      final ext = type == 'photo' ? 'jpg' : 'mp4';
      final storagePath = 'users/$uid/media/$type/$mediaId.$ext';
      final sref = FirebaseStorage.instance.ref().child(storagePath);

      final metadata = SettableMetadata(
        contentType: type == 'photo' ? 'image/jpeg' : 'video/mp4',
      );

      final task = sref.putFile(file, metadata);
      final snap = await task;
      final url = await snap.ref.getDownloadURL();

      await mediaRef.doc(mediaId).set({
        'type': type,
        'url': url,
        'thumbUrl': '',
        'flagged': false,
        'ownerUid': uid,
        'ownerName': ownerName,
        'ownerPhotoUrl': ownerPhoto,
        'createdAt': FieldValue.serverTimestamp(),
        'likeCount': 0,
      });

      await userRef.set({
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      _snack('${type.toUpperCase()} uploaded ✅');
    } on FirebaseException catch (e) {
      _snack('Upload failed: ${e.code}');
    } catch (e) {
      _snack('Upload failed: $e');
    }
  }

  Future<void> _openNameEditor() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Edit name'),
        content: TextField(
          controller: _nameCtrl,
          autofocus: true,
          maxLength: 30,
          decoration: const InputDecoration(hintText: 'Enter your name'),
          onChanged: (_) => _nameDirty = true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Done'),
          ),
        ],
      ),
    );

    if (ok == true) {
      setState(() => _isEditingName = false);
      await _saveNameIfNeeded();
      _snack('Name updated ✅');
    }
  }

  Future<void> _openProfileEditor() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) {
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
              16,
              10,
              16,
              MediaQuery.of(context).viewInsets.bottom + 16,
            ),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Edit profile',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _nameCtrl,
                    autofocus: true,
                    maxLength: 30,
                    decoration: InputDecoration(
                      labelText: 'User name',
                      hintText: 'Enter your name',
                      filled: true,
                      fillColor: Colors.grey.shade50,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    onChanged: (_) => _nameDirty = true,
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _bioCtrl,
                    maxLines: 4,
                    maxLength: 140,
                    decoration: InputDecoration(
                      labelText: 'Bio',
                      hintText: 'Write something simple...',
                      filled: true,
                      fillColor: Colors.grey.shade50,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    onChanged: (_) => _bioDirty = true,
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('Save'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );

    if (ok == true) {
      await _saveNameIfNeeded();
      await _saveBioIfNeeded();
      _isEditingName = false;
      _isEditingBio = false;
      _snack('Profile updated ✅');
      if (mounted) setState(() {});
    }
  }

  Future<void> _openBioEditor() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            void addInterest() {
              final raw = _interestCtrl.text.trim();
              if (raw.isEmpty) return;

              final items = raw
                  .split(',')
                  .map((e) => e.trim())
                  .where((e) => e.isNotEmpty)
                  .toList();

              for (final item in items) {
                if (!_interests.contains(item)) {
                  _interests.add(item);
                }
              }
              _interestCtrl.clear();
              _bioDirty = true;
              setSheetState(() {});
            }

            void removeInterest(String value) {
              _interests.remove(value);
              _bioDirty = true;
              setSheetState(() {});
            }

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                  16,
                  10,
                  16,
                  MediaQuery.of(context).viewInsets.bottom + 16,
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Edit bio',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _bioCtrl,
                        maxLines: 4,
                        maxLength: 140,
                        decoration: InputDecoration(
                          hintText: 'Write something simple and attractive...',
                          filled: true,
                          fillColor: Colors.grey.shade50,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        onChanged: (_) => _bioDirty = true,
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _interestCtrl,
                              decoration: InputDecoration(
                                hintText: 'music, travel, gym',
                                filled: true,
                                fillColor: Colors.grey.shade50,
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                              ),
                              onSubmitted: (_) => addInterest(),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: addInterest,
                            child: const Text('Add'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (_interests.isEmpty)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade50,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: Colors.grey.shade200),
                          ),
                          child: const Text(
                            'No interests added yet.',
                            style: TextStyle(fontWeight: FontWeight.w700),
                          ),
                        )
                      else
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _interests.map((i) {
                            return Chip(
                              label: Text(i),
                              onDeleted: () => removeInterest(i),
                            );
                          }).toList(),
                        ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: const Text('Save Bio'),
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

    if (ok == true) {
      setState(() => _isEditingBio = false);
      await _saveBioIfNeeded();
      _snack('Bio updated ✅');
    }
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _mediaStream(String type) {
    return mediaRef
        .where('type', isEqualTo: type)
        .orderBy('createdAt', descending: true)
        .limit(120)
        .snapshots();
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _allMediaStream() {
    return mediaRef.orderBy('createdAt', descending: true).limit(300).snapshots();
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _followersStream() {
    return userRef.collection('followers').limit(500).snapshots();
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _followingStream() {
    return userRef.collection('following').limit(500).snapshots();
  }

  Widget _buildTabBody() {
    if (_tabIndex == 0) {
      return _MediaGridStream(
        stream: _mediaStream('photo'),
        ownerUid: uid,
        type: 'photo',
      );
    }
    if (_tabIndex == 1) {
      return _MediaGridStream(
        stream: _mediaStream('video'),
        ownerUid: uid,
        type: 'video',
      );
    }
    return _ReelsStream(
      ownerUid: uid,
      stream: _mediaStream('video'),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, result) async {
        await _saveNameIfNeeded();
        await _saveBioIfNeeded();
      },
      child: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: userRef.snapshots(),
        builder: (context, userSnap) {
          if (!userSnap.hasData) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }

          final me = userSnap.data!.data() ?? {};
          final name = asString(me['displayName'], def: 'User');
          final photo = asString(me['photoUrl'] ?? me['profilePhoto']);
          final bio = asString(me['bio']);
          final interests = asStringList(me['interests']);
          final hasProfilePic = photo.isNotEmpty;

          if (!_isEditingName && _nameCtrl.text.trim() != name) {
            _nameCtrl.text = name;
          }

          if (!_isEditingBio && _bioCtrl.text.trim() != bio) {
            _bioCtrl.text = bio;
          }

          if (!_isEditingBio) {
            _interests = List<String>.from(interests);
          }

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
                              InkWell(
                                borderRadius: BorderRadius.circular(999),
                                onTap: () async {
                                  _isEditingName = true;
                                  _isEditingBio = true;
                                  await _openProfileEditor();
                                },
                                child: Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.18),
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: Colors.white.withOpacity(0.30),
                                    ),
                                  ),
                                  child: const Icon(
                                    Icons.edit,
                                    size: 16,
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
                                  child: Stack(
                                    alignment: Alignment.center,
                                    children: [
                                      GestureDetector(
                                        onTap: () {
                                          if (photo.isEmpty) return;
                                          Navigator.push(
                                            context,
                                            MaterialPageRoute(
                                              builder: (_) => _ProfileGalleryPage(
                                                ownerUid: uid,
                                                mediaList: [
                                                  {
                                                    'id': 'profile_$uid',
                                                    'type': 'photo',
                                                    'url': photo,
                                                    'ownerUid': uid,
                                                    'ownerName': name,
                                                    'ownerPhotoUrl': photo,
                                                    'likeCount': 0,
                                                    'virtualProfile': true,
                                                  }
                                                ],
                                                initialIndex: 0,
                                                title: 'Profile photo',
                                              ),
                                            ),
                                          );
                                        },
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
                                      Positioned(
                                        bottom: 0,
                                        child: GestureDetector(
                                          onTap: () => _openUploadSheet(
                                            hasProfilePic: hasProfilePic,
                                          ),
                                          child: Container(
                                            padding: const EdgeInsets.all(7),
                                            decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              color: Colors.black.withOpacity(0.82),
                                              border: Border.all(
                                                color: Colors.white,
                                                width: 2,
                                              ),
                                            ),
                                            child: const Icon(
                                              Icons.add_a_photo,
                                              color: Colors.white,
                                              size: 13,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
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
                                              ? 'Add a beautiful bio to make your profile stand out.'
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
                                _HeaderTabButton(
                                  text: 'Reels',
                                  selected: _tabIndex == 2,
                                  onTap: () => setState(() => _tabIndex = 2),
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

class _MediaGridStream extends StatelessWidget {
  final Stream<QuerySnapshot<Map<String, dynamic>>> stream;
  final String type;
  final String ownerUid;

  const _MediaGridStream({
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
            'flagged': (m['flagged'] ?? false) == true,
            'ownerUid': asString(m['ownerUid']),
            'ownerName': asString(m['ownerName'], def: 'User'),
            'ownerPhotoUrl': asString(m['ownerPhotoUrl']),
            'likeCount': (m['likeCount'] is num) ? (m['likeCount'] as num).toInt() : 0,
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
            final flagged = (item['flagged'] ?? false) == true;

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
                            builder: (_) => _ProfileGalleryPage(
                              ownerUid: ownerUid,
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
                      if (flagged)
                        Container(
                          color: Colors.black.withOpacity(0.35),
                          child: const Center(
                            child: Text(
                              'Warning',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
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

class _ReelsStream extends StatelessWidget {
  final Stream<QuerySnapshot<Map<String, dynamic>>> stream;
  final String ownerUid;

  const _ReelsStream({
    required this.stream,
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
          return const Center(
            child: Text(
              'No reels yet.',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
          );
        }

        final reels = docs.map((doc) {
          final m = doc.data();
          return <String, dynamic>{
            'id': doc.id,
            'type': 'video',
            'url': asString(m['url']),
            'ownerUid': asString(m['ownerUid']),
            'ownerName': asString(m['ownerName'], def: 'User'),
            'ownerPhotoUrl': asString(m['ownerPhotoUrl']),
          };
        }).toList();

        return PageView.builder(
          scrollDirection: Axis.vertical,
          itemCount: reels.length,
          itemBuilder: (context, i) {
            return _ReelCard(
              ownerUid: ownerUid,
              item: reels[i],
            );
          },
        );
      },
    );
  }
}

class _ReelCard extends StatelessWidget {
  final String ownerUid;
  final Map<String, dynamic> item;

  const _ReelCard({
    required this.ownerUid,
    required this.item,
  });

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  @override
  Widget build(BuildContext context) {
    final mediaId = asString(item['id']);
    final ownerName = asString(item['ownerName'], def: 'User');
    final ownerPhoto = asString(item['ownerPhotoUrl']);

    return Stack(
      fit: StackFit.expand,
      children: [
        _AutoPlayVideo(
          url: asString(item['url']),
          fit: BoxFit.cover,
          showPlayPauseOnTap: true,
        ),
        Positioned(
          left: 14,
          right: 90,
          bottom: 24,
          child: Row(
            children: [
              CircleAvatar(
                radius: 17,
                backgroundImage: ownerPhoto.isEmpty ? null : NetworkImage(ownerPhoto),
                child: ownerPhoto.isEmpty ? const Icon(Icons.person) : null,
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
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
        ),
        Positioned(
          right: 10,
          bottom: 22,
          child: _LikeActionColumn(
            ownerUid: ownerUid,
            mediaId: mediaId,
          ),
        ),
      ],
    );
  }
}

class _LikeActionColumn extends StatelessWidget {
  final String ownerUid;
  final String mediaId;

  const _LikeActionColumn({
    required this.ownerUid,
    required this.mediaId,
  });

  DocumentReference<Map<String, dynamic>> get mediaRef =>
      FirebaseFirestore.instance.collection('users').doc(ownerUid).collection('media').doc(mediaId);

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get likeRef =>
      mediaRef.collection('likes').doc(uid);

  Future<void> _toggleLike(bool alreadyLiked) async {
    await FirebaseFirestore.instance.runTransaction((tx) async {
      final mediaSnap = await tx.get(mediaRef);
      final likeSnap = await tx.get(likeRef);

      if (!mediaSnap.exists) return;

      final currentCount = ((mediaSnap.data()?['likeCount'] ?? 0) as num).toInt();

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

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: mediaRef.snapshots(),
      builder: (context, mediaSnap) {
        final likeCount = ((mediaSnap.data?.data()?['likeCount'] ?? 0) as num).toInt();

        return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
          stream: likeRef.snapshots(),
          builder: (context, likeSnap) {
            final liked = likeSnap.data?.exists == true;

            return Column(
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
                  '$likeCount',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    fontSize: 12,
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }
}

class _ProfileGalleryPage extends StatefulWidget {
  final String ownerUid;
  final List<Map<String, dynamic>> mediaList;
  final int initialIndex;
  final String title;

  const _ProfileGalleryPage({
    required this.ownerUid,
    required this.mediaList,
    required this.initialIndex,
    required this.title,
  });

  @override
  State<_ProfileGalleryPage> createState() => _ProfileGalleryPageState();
}

class _ProfileGalleryPageState extends State<_ProfileGalleryPage> {
  late final PageController _pageController;
  late int _index;
  bool _showHeart = false;

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex;
    _pageController = PageController(initialPage: widget.initialIndex);
  }

  Map<String, dynamic> get current => widget.mediaList[_index];

  DocumentReference<Map<String, dynamic>> get currentMediaRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(widget.ownerUid)
          .collection('media')
          .doc(current['id'].toString());

  DocumentReference<Map<String, dynamic>> get currentLikeRef =>
      currentMediaRef.collection('likes').doc(uid);

  bool get isVirtualProfile => current['virtualProfile'] == true;

  Future<void> _toggleLike(bool alreadyLiked) async {
    if (isVirtualProfile) return;

    await FirebaseFirestore.instance.runTransaction((tx) async {
      final mediaSnap = await tx.get(currentMediaRef);
      final likeSnap = await tx.get(currentLikeRef);

      if (!mediaSnap.exists) return;

      final currentCount = ((mediaSnap.data()?['likeCount'] ?? 0) as num).toInt();

      if (alreadyLiked && likeSnap.exists) {
        tx.delete(currentLikeRef);
        tx.set(
          currentMediaRef,
          {'likeCount': currentCount > 0 ? currentCount - 1 : 0},
          SetOptions(merge: true),
        );
      } else if (!alreadyLiked && !likeSnap.exists) {
        tx.set(currentLikeRef, {
          'uid': uid,
          'createdAt': FieldValue.serverTimestamp(),
        });
        tx.set(
          currentMediaRef,
          {'likeCount': currentCount + 1},
          SetOptions(merge: true),
        );
      }
    });
  }

  Future<void> _doubleTapLike(bool liked) async {
    if (isVirtualProfile) return;
    if (!liked) {
      await _toggleLike(false);
    }
    if (!mounted) return;
    setState(() => _showHeart = true);
    await Future.delayed(const Duration(milliseconds: 700));
    if (!mounted) return;
    setState(() => _showHeart = false);
  }

  @override
  Widget build(BuildContext context) {
    final ownerName = current['ownerName']?.toString() ?? 'User';
    final ownerPhoto = current['ownerPhotoUrl']?.toString() ?? '';

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(widget.title),
      ),
      body: Column(
        children: [
          Container(
            color: Colors.black,
            padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundImage: ownerPhoto.isEmpty ? null : NetworkImage(ownerPhoto),
                  child: ownerPhoto.isEmpty ? const Icon(Icons.person) : null,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    ownerName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 15,
                    ),
                  ),
                ),
                Text(
                  '${_index + 1}/${widget.mediaList.length}',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
          Expanded(
            child: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
              stream: isVirtualProfile ? const Stream.empty() : currentMediaRef.snapshots(),
              builder: (context, mediaSnap) {
                final likeCount =
                    isVirtualProfile ? 0 : ((mediaSnap.data?.data()?['likeCount'] ?? 0) as num).toInt();

                return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                  stream: isVirtualProfile ? const Stream.empty() : currentLikeRef.snapshots(),
                  builder: (context, likeSnap) {
                    final liked = isVirtualProfile ? false : (likeSnap.data?.exists == true);

                    return Stack(
                      children: [
                        PageView.builder(
                          controller: _pageController,
                          itemCount: widget.mediaList.length,
                          onPageChanged: (i) {
                            setState(() => _index = i);
                          },
                          itemBuilder: (context, i) {
                            final item = widget.mediaList[i];
                            final type = item['type']?.toString() ?? 'photo';
                            final url = item['url']?.toString() ?? '';

                            if (type == 'video') {
                              return _GalleryVideoPage(url: url);
                            }

                            return GestureDetector(
                              onDoubleTap: () => _doubleTapLike(liked),
                              child: Stack(
                                alignment: Alignment.center,
                                children: [
                                  InteractiveViewer(
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
                                  ),
                                  if (_showHeart)
                                    const Icon(
                                      Icons.favorite,
                                      size: 120,
                                      color: Colors.white,
                                    ),
                                ],
                              ),
                            );
                          },
                        ),
                        if (!isVirtualProfile)
                          Positioned(
                            left: 16,
                            bottom: 16,
                            child: Row(
                              children: [
                                IconButton(
                                  onPressed: () => _toggleLike(liked),
                                  icon: Icon(
                                    liked ? Icons.favorite : Icons.favorite_border,
                                    color: liked ? Colors.redAccent : Colors.white,
                                    size: 30,
                                  ),
                                ),
                                Text(
                                  '$likeCount likes',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    );
                  },
                );
              },
            ),
          ),
        ],
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
      child: _AutoPlayVideo(
        url: url,
        fit: BoxFit.contain,
        showPlayPauseOnTap: true,
      ),
    );
  }
}

class _AutoPlayVideo extends StatefulWidget {
  final String url;
  final BoxFit fit;
  final bool showPlayPauseOnTap;

  const _AutoPlayVideo({
    required this.url,
    required this.fit,
    this.showPlayPauseOnTap = false,
  });

  @override
  State<_AutoPlayVideo> createState() => _AutoPlayVideoState();
}

class _AutoPlayVideoState extends State<_AutoPlayVideo> {
  late VideoPlayerController controller;
  bool _showPlayIcon = false;

  @override
  void initState() {
    super.initState();
    controller = VideoPlayerController.network(widget.url)
      ..initialize().then((_) {
        if (!mounted) return;
        controller.setLooping(true);
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
      onTap: widget.showPlayPauseOnTap ? _togglePlay : null,
      child: Stack(
        alignment: Alignment.center,
        children: [
          VisibilityDetector(
            key: Key(widget.url),
            onVisibilityChanged: (info) {
              if (!controller.value.isInitialized) return;
              if (info.visibleFraction > 0.60) {
                controller.play();
              } else {
                controller.pause();
              }
            },
            child: SizedBox.expand(
              child: FittedBox(
                fit: widget.fit,
                child: SizedBox(
                  width: controller.value.size.width,
                  height: controller.value.size.height,
                  child: VideoPlayer(controller),
                ),
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