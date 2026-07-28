import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ChatRoomSettingsPage extends StatefulWidget {
  final String roomId;
  final String otherUid;

  const ChatRoomSettingsPage({
    super.key,
    required this.roomId,
    required this.otherUid,
  });

  @override
  State<ChatRoomSettingsPage> createState() => _ChatRoomSettingsPageState();
}

class _ChatRoomSettingsPageState extends State<ChatRoomSettingsPage> {
  static const Color _pink = Color(0xFFE91E63);
  static const Color _muted = Color(0xFF9CA3AF);
  static const Color _card = Color(0xFF171A21);
  static const Color _border = Color(0xFF2A3140);
  static const Color _bg = Color(0xFF0B0F17);

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get _otherRef =>
      FirebaseFirestore.instance.collection('users').doc(widget.otherUid);

  DocumentReference<Map<String, dynamic>> get _roomRef =>
      FirebaseFirestore.instance.collection('chatRooms').doc(widget.roomId);

  DocumentReference<Map<String, dynamic>> get _chatPrefRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('chatPrefs')
          .doc(widget.roomId);

  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _prefSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _roomSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _otherSub;

  bool _loading = true;
  bool _saving = false;

  String _otherName = 'User';
  String _otherPhoto = '';

  bool _muteNotifications = false;
  bool _readReceipts = true;
  bool _showOnlineStatus = true;
  bool _allowImageRequests = true;
  bool _allowAudioRequests = true;
  bool _allowVideoRequests = true;
  bool _mediaAutoDownload = true;
  String _disappearMode = 'off';

  bool _blockedByMe = false;
  bool _blockedByOther = false;

  bool get _anyBlocked => _blockedByMe || _blockedByOther;

  @override
  void initState() {
    super.initState();
    _listenOtherUser();
    _listenPrefs();
    _listenRoom();
    _ensureDefaults();
  }

  @override
  void dispose() {
    _prefSub?.cancel();
    _roomSub?.cancel();
    _otherSub?.cancel();
    super.dispose();
  }

  Future<void> _ensureDefaults() async {
    try {
      final snap = await _chatPrefRef.get();
      if (snap.exists) return;

      await _chatPrefRef.set({
        'readReceipts': true,
        'showOnlineStatus': true,
        'allowImageRequests': true,
        'allowAudioRequests': true,
        'allowVideoRequests': true,
        'mediaAutoDownload': true,
        'disappearMode': 'off',
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (_) {}
  }

  void _listenOtherUser() {
    _otherSub?.cancel();
    _otherSub = _otherRef.snapshots().listen((snap) {
      final data = snap.data() ?? {};
      if (!mounted) return;

      setState(() {
        _otherName = _string(
          data['displayName'],
          fallback: _string(data['name'], fallback: 'User'),
        );
        _otherPhoto = _string(
          data['photoUrl'],
          fallback: _string(data['profilePhoto']),
        );
      });
    });
  }

  void _listenPrefs() {
    _prefSub?.cancel();
    _prefSub = _chatPrefRef.snapshots().listen((snap) {
      final data = snap.data() ?? {};
      final muteUntil = data['muteChatUntil'] as Timestamp?;
      final isMuted =
          muteUntil != null && muteUntil.toDate().isAfter(DateTime.now());

      if (!mounted) return;
      setState(() {
        _muteNotifications = isMuted;
        _readReceipts = _bool(data['readReceipts'], def: true);
        _showOnlineStatus = _bool(data['showOnlineStatus'], def: true);
        _allowImageRequests = _bool(data['allowImageRequests'], def: true);
        _allowAudioRequests = _bool(data['allowAudioRequests'], def: true);
        _allowVideoRequests = _bool(data['allowVideoRequests'], def: true);
        _mediaAutoDownload = _bool(data['mediaAutoDownload'], def: true);
        _disappearMode = _string(data['disappearMode'], fallback: 'off');
        _loading = false;
      });
    });
  }

  void _listenRoom() {
    _roomSub?.cancel();
    _roomSub = _roomRef.snapshots().listen((snap) {
      final data = snap.data() ?? {};
      final blockedRaw = data['blockedBy'];
      final blockedBy = blockedRaw is Map
          ? blockedRaw.map((k, v) => MapEntry(k.toString(), v))
          : <String, dynamic>{};

      if (!mounted) return;
      setState(() {
        _blockedByMe = blockedBy[uid] == true;
        _blockedByOther = blockedBy[widget.otherUid] == true;
      });
    });
  }

  bool _bool(dynamic value, {bool def = false}) {
    if (value is bool) return value;
    if (value is num) return value != 0;
    if (value is String) {
      final s = value.trim().toLowerCase();
      if (s == 'true' || s == '1' || s == 'yes') return true;
      if (s == 'false' || s == '0' || s == 'no') return false;
    }
    return def;
  }

  String _string(dynamic value, {String fallback = ''}) {
    if (value == null) return fallback;
    final s = value.toString().trim();
    return s.isEmpty ? fallback : s;
  }

  Future<void> _savePrefs(Map<String, dynamic> data) async {
    if (mounted) setState(() => _saving = true);

    try {
      await _chatPrefRef.set({
        ...data,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Update failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _setMute(bool value) async {
    await _savePrefs({
      'muteChatUntil': value
          ? Timestamp.fromDate(DateTime.now().add(const Duration(days: 3650)))
          : null,
    });
  }

  Future<void> _clearChatForMe() async {
    await _savePrefs({
      'clearedAt': FieldValue.serverTimestamp(),
    });

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Chat cleared for you')),
    );
  }

  String _disappearLabel(String value) {
    switch (value) {
      case 'h24':
        return '24 hours';
      case 'd7':
        return '7 days';
      case 'd30':
        return '30 days';
      default:
        return 'Off';
    }
  }

  Future<void> _showDisappearPicker() async {
    const options = ['off', 'h24', 'd7', 'd30'];

    await showModalBottomSheet(
      context: context,
      backgroundColor: _card,
      builder: (_) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: options.map((value) {
              return ListTile(
                title: Text(
                  _disappearLabel(value),
                  style: const TextStyle(color: Colors.white),
                ),
                trailing: _disappearMode == value
                    ? const Icon(Icons.check_circle, color: _pink)
                    : null,
                onTap: () async {
                  await _savePrefs({'disappearMode': value});
                  if (!mounted) return;
                  Navigator.pop(context);
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  Widget _sectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(2, 0, 2, 8),
      child: Text(
        title,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 15,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _groupCard(List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: _card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _border),
      ),
      child: Column(children: children),
    );
  }

  Widget _switchTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return SwitchListTile(
      value: value,
      onChanged: _saving ? null : onChanged,
      activeThumbColor: _pink,
      secondary: Icon(icon, color: Colors.white),
      title: Text(
        title,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
      subtitle: Text(
        subtitle,
        style: const TextStyle(color: _muted),
      ),
    );
  }

  Widget _navTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return ListTile(
      onTap: _saving ? null : onTap,
      leading: Icon(icon, color: Colors.white),
      trailing: const Icon(Icons.chevron_right, color: _muted),
      title: Text(
        title,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
      subtitle: Text(
        subtitle,
        style: const TextStyle(color: _muted),
      ),
    );
  }

  Widget _headerCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _border),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 28,
            backgroundImage:
                _otherPhoto.isNotEmpty ? NetworkImage(_otherPhoto) : null,
            child: _otherPhoto.isEmpty ? const Icon(Icons.person) : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _otherName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _blockedInfo() {
    if (!_anyBlocked) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _blockedByMe
            ? Colors.red.shade900.withOpacity(0.2)
            : Colors.orange.shade900.withOpacity(0.2),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _blockedByMe ? Colors.redAccent : Colors.orangeAccent,
        ),
      ),
      child: Text(
        _blockedByMe ? 'You blocked this user.' : 'This user blocked you.',
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: Colors.white,
        elevation: 0,
        title: const Text('Chat Settings'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _headerCard(),
                _blockedInfo(),
                const SizedBox(height: 16),
                _sectionTitle('Notifications & Privacy'),
                _groupCard([
                  _switchTile(
                    icon: Icons.notifications_off_outlined,
                    title: 'Mute notifications',
                    subtitle: 'Silence alerts only for this chat',
                    value: _muteNotifications,
                    onChanged: _setMute,
                  ),
                  _switchTile(
                    icon: Icons.done_all,
                    title: 'Read receipts',
                    subtitle: 'Show seen status in this chat',
                    value: _readReceipts,
                    onChanged: (v) => _savePrefs({'readReceipts': v}),
                  ),
                  _switchTile(
                    icon: Icons.circle_outlined,
                    title: 'Show online status',
                    subtitle: 'Show online / last seen in this chat',
                    value: _showOnlineStatus,
                    onChanged: (v) => _savePrefs({'showOnlineStatus': v}),
                  ),
                  _navTile(
                    icon: Icons.auto_delete_outlined,
                    title: 'Disappear messages',
                    subtitle: 'Current: ${_disappearLabel(_disappearMode)}',
                    onTap: _showDisappearPicker,
                  ),
                ]),
                const SizedBox(height: 16),
                _sectionTitle('Requests & Calls'),
                _groupCard([
                  _switchTile(
                    icon: Icons.image_outlined,
                    title: 'Allow image requests',
                    subtitle: 'This user can send image requests',
                    value: _allowImageRequests,
                    onChanged: (v) => _savePrefs({'allowImageRequests': v}),
                  ),
                  _switchTile(
                    icon: Icons.phone_outlined,
                    title: 'Allow audio call requests',
                    subtitle: 'This user can send audio call requests',
                    value: _allowAudioRequests,
                    onChanged: (v) => _savePrefs({'allowAudioRequests': v}),
                  ),
                  _switchTile(
                    icon: Icons.video_call_outlined,
                    title: 'Allow video call requests',
                    subtitle: 'This user can send video call requests',
                    value: _allowVideoRequests,
                    onChanged: (v) => _savePrefs({'allowVideoRequests': v}),
                  ),
                ]),
                const SizedBox(height: 16),
                _sectionTitle('Media'),
                _groupCard([
                  _switchTile(
                    icon: Icons.download_outlined,
                    title: 'Media auto download',
                    subtitle: 'Download images automatically',
                    value: _mediaAutoDownload,
                    onChanged: (v) => _savePrefs({'mediaAutoDownload': v}),
                  ),
                ]),
                const SizedBox(height: 16),
                _sectionTitle('Chat'),
                _groupCard([
                  _navTile(
                    icon: Icons.delete_sweep_outlined,
                    title: 'Clear chat for me',
                    subtitle: 'Hide old messages only on your side',
                    onTap: _clearChatForMe,
                  ),
                ]),
              ],
            ),
    );
  }
}
