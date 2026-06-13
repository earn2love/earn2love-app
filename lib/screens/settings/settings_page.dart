import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'blocked_users_page.dart';
import 'report_history_page.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  static const _bg = Color(0xFF0F1115);
  static const _card = Color(0xFF171A21);
  static const _tile = Color(0xFF1D212B);
  static const _border = Color(0xFF2A3140);
  static const _muted = Color(0xFF9AA3B2);
  static const _pink = Color(0xFFFF4D8D);
  static const _purple = Color(0xFF8B5CFF);
  static const _blue = Color(0xFF58B7FF);
  static const _green = Color(0xFF48D597);
  static const _gold = Color(0xFFFFC84B);
  static const _red = Color(0xFFFF7272);

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get _meRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _meSub;

  bool _loading = true;
  final Map<String, bool> _busy = {};

  Map<String, dynamic> _user = {};
  Map<String, dynamic> _settings = {};

  @override
  void initState() {
    super.initState();
    _listenMe();
  }

  @override
  void dispose() {
    _meSub?.cancel();
    super.dispose();
  }

  void _listenMe() {
    _meSub?.cancel();
    _meSub = _meRef.snapshots().listen((snap) {
      final data = snap.data() ?? {};
      final settings = Map<String, dynamic>.from(data['settings'] ?? {});

      if (!mounted) return;
      setState(() {
        _user = data;
        _settings = settings;
        _loading = false;
      });
    });
  }

  bool _bool(String key, {bool def = false}) {
    final v = _settings[key];
    if (v is bool) return v;
    if (v is num) return v != 0;
    if (v is String) {
      final s = v.trim().toLowerCase();
      if (s == 'true' || s == '1' || s == 'yes') return true;
      if (s == 'false' || s == '0' || s == 'no') return false;
    }
    return def;
  }

  String _strFromUser(String key, {String def = ''}) {
    final v = _user[key];
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  bool _isBusy(String key) => _busy[key] == true;

  Future<void> _saveSetting(String key, dynamic value) async {
    final old = _settings[key];

    if (mounted) {
      setState(() {
        _settings[key] = value;
        _busy[key] = true;
      });
    }

    try {
      await _meRef.set({
        'settings': {
          key: value,
        },
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _settings[key] = old;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Update failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _busy[key] = false;
        });
      }
    }
  }

  Widget _sectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
      child: Text(
        title,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 15,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _groupCard(List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: _card,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.18),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(children: children),
    );
  }

  Widget _profileHeader() {
    final name = _strFromUser('displayName', def: 'User');
    final photo = _strFromUser('photoUrl', def: _strFromUser('profilePhoto'));
    final email = _strFromUser('email', def: 'No email');
    final phone = _strFromUser('phone', def: 'No phone');
    final subtitle = email != 'No email' ? email : phone;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF8B5CFF), Color(0xFFFF4D8D)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: _purple.withOpacity(0.28),
            blurRadius: 22,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 74,
            height: 74,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              borderRadius: BorderRadius.circular(22),
              image: photo.isNotEmpty
                  ? DecorationImage(
                      image: NetworkImage(photo),
                      fit: BoxFit.cover,
                    )
                  : null,
            ),
            child: photo.isEmpty
                ? const Icon(Icons.person_rounded, color: Colors.white, size: 38)
                : null,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 21,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.92),
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Privacy • Requests • Calls • Notifications',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.86),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _dividerLine() {
    return Container(
      margin: const EdgeInsets.only(left: 68),
      height: 1,
      color: _border,
    );
  }

  Widget _navTile({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: _tile,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: iconColor, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 12.8,
                        height: 1.28,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.keyboard_arrow_right_rounded,
                color: _muted,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _switchTile({
    required String settingKey,
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required bool value,
  }) {
    final busy = _isBusy(settingKey);

    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
      child: Container(
        decoration: BoxDecoration(
          color: _tile,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: const Color(0xFF262C38),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: iconColor, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 12.6,
                        height: 1.28,
                      ),
                    ),
                  ],
                ),
              ),
              if (busy)
                const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: _pink,
                  ),
                )
              else
                Switch.adaptive(
                  value: value,
                  onChanged: (v) => _saveSetting(settingKey, v),
                  activeColor: _pink,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _logoutTile() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF191419),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0x33FF6B81)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(22),
          onTap: () async {
            await FirebaseAuth.instance.signOut();
          },
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 21,
                  backgroundColor: Color(0x22FF6B81),
                  child: Icon(
                    Icons.power_settings_new_rounded,
                    color: Color(0xFFFF6B81),
                  ),
                ),
                SizedBox(width: 14),
                Expanded(
                  child: Text(
                    'Logout',
                    style: TextStyle(
                      color: Color(0xFFFF6B81),
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                Icon(
                  Icons.keyboard_arrow_right_rounded,
                  color: Color(0xFFFF6B81),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final privateProfile = _bool('privateProfile');
    final showOnlineStatus = _bool('showOnlineStatus', def: true);
    final readReceipts = _bool('readReceipts', def: true);

    final allowImageRequests = _bool('allowImageRequests', def: false);
    final allowAudioCalls = _bool('allowAudioCalls', def: true);
    final allowVideoCalls = _bool('allowVideoCalls', def: true);

    final aiChatEnabled = _bool('aiChatEnabled', def: true);
    final mediaAutoDownload = _bool('mediaAutoDownload', def: true);
    final pinImportantChats = _bool('pinImportantChats', def: false);

    final messageNotifications = _bool('messageNotifications', def: true);
    final requestNotifications = _bool('requestNotifications', def: true);
    final callNotifications = _bool('callNotifications', def: true);

    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleSpacing: 20,
        title: const Text(
          'Settings',
          style: TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: ListView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  _profileHeader(),
                  const SizedBox(height: 18),

                  _sectionTitle('Profile & Privacy'),
                  _groupCard([
                    _switchTile(
                      settingKey: 'privateProfile',
                      icon: Icons.lock_outline_rounded,
                      iconColor: _gold,
                      title: 'Private profile',
                      subtitle: 'Limit profile visibility to approved users',
                      value: privateProfile,
                    ),
                    _switchTile(
                      settingKey: 'showOnlineStatus',
                      icon: Icons.circle_outlined,
                      iconColor: _green,
                      title: 'Show online status',
                      subtitle: 'Let others see when you are online',
                      value: showOnlineStatus,
                    ),
                    _switchTile(
                      settingKey: 'readReceipts',
                      icon: Icons.done_all_rounded,
                      iconColor: _blue,
                      title: 'Read receipts',
                      subtitle: 'Show when messages are seen',
                      value: readReceipts,
                    ),
                  ]),

                  const SizedBox(height: 16),

                  _sectionTitle('Requests & Calls'),
                  _groupCard([
                    _switchTile(
                      settingKey: 'allowImageRequests',
                      icon: Icons.image_outlined,
                      iconColor: _blue,
                      title: 'Image requests',
                      subtitle: 'Allow users to send image requests',
                      value: allowImageRequests,
                    ),
                    _switchTile(
                      settingKey: 'allowAudioCalls',
                      icon: Icons.phone_outlined,
                      iconColor: _green,
                      title: 'Audio call requests',
                      subtitle: 'Allow users to send audio call requests',
                      value: allowAudioCalls,
                    ),
                    _switchTile(
                      settingKey: 'allowVideoCalls',
                      icon: Icons.video_call_outlined,
                      iconColor: _pink,
                      title: 'Video call requests',
                      subtitle: 'Allow users to send video call requests',
                      value: allowVideoCalls,
                    ),
                  ]),

                  const SizedBox(height: 16),

                  _sectionTitle('Chat Settings'),
                  _groupCard([
                    _switchTile(
                      settingKey: 'aiChatEnabled',
                      icon: Icons.smart_toy_outlined,
                      iconColor: _gold,
                      title: 'AI Chat',
                      subtitle: 'Enable AI chat access and suggestions',
                      value: aiChatEnabled,
                    ),
                    _switchTile(
                      settingKey: 'mediaAutoDownload',
                      icon: Icons.download_outlined,
                      iconColor: _blue,
                      title: 'Media auto download',
                      subtitle: 'Download media automatically',
                      value: mediaAutoDownload,
                    ),
                    _switchTile(
                      settingKey: 'pinImportantChats',
                      icon: Icons.push_pin_outlined,
                      iconColor: _green,
                      title: 'Pin important chats',
                      subtitle: 'Keep priority conversations at the top',
                      value: pinImportantChats,
                    ),
                  ]),

                  const SizedBox(height: 16),

                  _sectionTitle('Notification Settings'),
                  _groupCard([
                    _switchTile(
                      settingKey: 'messageNotifications',
                      icon: Icons.chat_bubble_outline_rounded,
                      iconColor: _pink,
                      title: 'Message notifications',
                      subtitle: 'Popup or banner for new messages',
                      value: messageNotifications,
                    ),
                    _switchTile(
                      settingKey: 'requestNotifications',
                      icon: Icons.mark_email_unread_outlined,
                      iconColor: _blue,
                      title: 'Request notifications',
                      subtitle: 'Image and call request alerts',
                      value: requestNotifications,
                    ),
                    _switchTile(
                      settingKey: 'callNotifications',
                      icon: Icons.notifications_active_outlined,
                      iconColor: _green,
                      title: 'Call notifications',
                      subtitle: 'Incoming call and response alerts',
                      value: callNotifications,
                    ),
                  ]),

                  const SizedBox(height: 16),

                  _sectionTitle('Safety'),
                  _groupCard([
                    _navTile(
                      icon: Icons.block_outlined,
                      iconColor: _red,
                      title: 'Blocked users',
                      subtitle: 'View and unblock blocked profiles',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const BlockedUsersPage(),
                          ),
                        );
                      },
                    ),
                    _dividerLine(),
                    _navTile(
                      icon: Icons.flag_outlined,
                      iconColor: _blue,
                      title: 'Report history',
                      subtitle: 'Reports made by you and against you',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const ReportHistoryPage(),
                          ),
                        );
                      },
                    ),
                  ]),

                  const SizedBox(height: 20),
                  _logoutTile(),
                ],
              ),
            ),
    );
  }
}