import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:earn2love_app/screens/settings/settings_page.dart';

import 'archived_chats_page.dart';
import 'chat_room_page.dart';

class ChatListPage extends StatefulWidget {
  const ChatListPage({super.key});

  @override
  State<ChatListPage> createState() => _ChatListPageState();
}

enum _TopTab {
  all,
  unread,
  received,
  sent,
}

class _ChatListPageState extends State<ChatListPage> {
  _TopTab _selectedTab = _TopTab.all;

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get roomsRef =>
      FirebaseFirestore.instance.collection('chatRooms');

  CollectionReference<Map<String, dynamic>> get friendReqRef =>
      FirebaseFirestore.instance.collection('friendRequests');

  CollectionReference<Map<String, dynamic>> get myPrefsCollection =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('chatPrefs');

  DocumentReference<Map<String, dynamic>> _myPrefsRef(String roomId) {
    return myPrefsCollection.doc(roomId);
  }

  String _otherUidFromParticipants(List<dynamic> participants) {
    final list = participants.map((e) => e.toString()).toList();
    return list.firstWhere((e) => e != uid, orElse: () => '');
  }

  String _fmtTime(Timestamp? ts) {
    if (ts == null) return '';
    final dt = ts.toDate();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(dt.year, dt.month, dt.day);

    if (d == today) {
      final hh = dt.hour.toString().padLeft(2, '0');
      final mm = dt.minute.toString().padLeft(2, '0');
      return '$hh:$mm';
    }

    if (d == today.subtract(const Duration(days: 1))) {
      return 'Yesterday';
    }

    return '${dt.day}/${dt.month}/${dt.year}';
  }

  String _fmtLastSeen(Timestamp? ts, bool online) {
    if (online) return 'online';
    if (ts == null) return 'offline';

    final dt = ts.toDate();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(dt.year, dt.month, dt.day);

    if (d == today) {
      final hh = dt.hour.toString().padLeft(2, '0');
      final mm = dt.minute.toString().padLeft(2, '0');
      return 'last seen $hh:$mm';
    }

    if (d == today.subtract(const Duration(days: 1))) {
      final hh = dt.hour.toString().padLeft(2, '0');
      final mm = dt.minute.toString().padLeft(2, '0');
      return 'last seen yesterday $hh:$mm';
    }

    return 'offline';
  }

  Widget _tickWidget({
    required bool isMine,
    required bool delivered,
    required bool seen,
  }) {
    if (!isMine) return const SizedBox.shrink();

    Color color;
    if (seen) {
      color = const Color(0xFF34B7F1);
    } else if (delivered) {
      color = const Color(0xFF6A5B88);
    } else {
      color = const Color(0xFF9E95B3);
    }

    return SizedBox(
      width: 18,
      height: 14,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: Icon(
              Icons.done,
              size: 14,
              color: color,
            ),
          ),
          Positioned(
            left: 5,
            top: 0,
            child: Icon(
              Icons.done,
              size: 14,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _setMute(String roomId, Duration d) async {
    final until = Timestamp.fromDate(DateTime.now().add(d));
    await _myPrefsRef(roomId).set({
      'muteChatUntil': until,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> _clearMute(String roomId) async {
    await _myPrefsRef(roomId).set({
      'muteChatUntil': null,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> _setArchive(String roomId, bool value) async {
    await _myPrefsRef(roomId).set({
      'archived': value,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> _deleteChatForMe(String roomId) async {
    await _myPrefsRef(roomId).set({
      'deleted': true,
      'deletedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Widget _sheetActionTile({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
    Color iconColor = const Color(0xFF43365F),
    Color textColor = const Color(0xFF2F2747),
  }) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        child: Row(
          children: [
            Icon(icon, color: iconColor, size: 22),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: textColor,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openChatActions({
    required String roomId,
    required bool archived,
    required bool isMutedActive,
  }) async {
    final action = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: const Color(0xFFF7F2FB),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 10),
              Container(
                width: 44,
                height: 5,
                decoration: BoxDecoration(
                  color: const Color(0xFFD5C7EA),
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
              const SizedBox(height: 10),
              _sheetActionTile(
                icon:
                    archived ? Icons.unarchive_outlined : Icons.archive_outlined,
                title: archived ? 'Unarchive' : 'Archive',
                onTap: () => Navigator.pop(context, 'archive'),
              ),
              if (isMutedActive)
                _sheetActionTile(
                  icon: Icons.notifications_active_outlined,
                  title: 'Unmute',
                  onTap: () => Navigator.pop(context, 'unmute'),
                )
              else ...[
                _sheetActionTile(
                  icon: Icons.notifications_off_outlined,
                  title: 'Mute 8 hours',
                  onTap: () => Navigator.pop(context, 'mute8'),
                ),
                _sheetActionTile(
                  icon: Icons.notifications_paused_outlined,
                  title: 'Mute 24 hours',
                  onTap: () => Navigator.pop(context, 'mute24'),
                ),
              ],
              _sheetActionTile(
                icon: Icons.delete_outline,
                title: 'Delete chat for me',
                iconColor: Colors.redAccent,
                textColor: Colors.redAccent,
                onTap: () => Navigator.pop(context, 'delete'),
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );

    if (action == 'archive') {
      await _setArchive(roomId, !archived);
    } else if (action == 'mute8') {
      await _setMute(roomId, const Duration(hours: 8));
    } else if (action == 'mute24') {
      await _setMute(roomId, const Duration(hours: 24));
    } else if (action == 'unmute') {
      await _clearMute(roomId);
    } else if (action == 'delete') {
      await _deleteChatForMe(roomId);
    }
  }

  Future<void> _showProfilePreview({
    required String photo,
    required String name,
  }) async {
    if (photo.isEmpty) return;

    await showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.28),
      builder: (_) {
        return Dialog(
          backgroundColor: Colors.transparent,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 40, vertical: 100),
          child: Center(
            child: Container(
              width: 255,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(22),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.14),
                    blurRadius: 22,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(14, 12, 10, 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF2F2747),
                            ),
                          ),
                        ),
                        InkWell(
                          borderRadius: BorderRadius.circular(20),
                          onTap: () => Navigator.pop(context),
                          child: const Padding(
                            padding: EdgeInsets.all(4),
                            child: Icon(Icons.close, size: 20),
                          ),
                        ),
                      ],
                    ),
                  ),
                  ClipRRect(
                    borderRadius: const BorderRadius.vertical(
                      bottom: Radius.circular(22),
                    ),
                    child: AspectRatio(
                      aspectRatio: 1,
                      child: Image.network(
                        photo,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) {
                          return Container(
                            color: Colors.black12,
                            alignment: Alignment.center,
                            child: const Text('Image failed'),
                          );
                        },
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
  }

  Widget _chip({
    required String text,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: selected
              ? const LinearGradient(
                  colors: [Color(0xFF8D67FF), Color(0xFFFF5DA2)],
                )
              : null,
          color: selected ? null : Colors.white,
          border: Border.all(
            color: selected ? Colors.transparent : const Color(0xFFE9DDF8),
          ),
          boxShadow: [
            BoxShadow(
              color: selected
                  ? const Color(0xFF8D67FF).withOpacity(0.14)
                  : Colors.black.withOpacity(0.025),
              blurRadius: selected ? 10 : 6,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Text(
          text,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w800,
            color: selected ? Colors.white : const Color(0xFF43365F),
            height: 1.0,
          ),
        ),
      ),
    );
  }

  bool _matchesTopTab({
    required _TopTab tab,
    required int unreadCount,
    required int receivedFriendReqCount,
    required int sentFriendReqCount,
  }) {
    switch (tab) {
      case _TopTab.all:
        return true;
      case _TopTab.unread:
        return unreadCount > 0;
      case _TopTab.received:
        return receivedFriendReqCount > 0;
      case _TopTab.sent:
        return sentFriendReqCount > 0;
    }
  }

  Widget _buildHeader() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF7F2FB),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 8, 6),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Earn2Love',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 28,
                        color: Color(0xFF2F2747),
                        letterSpacing: -0.4,
                      ),
                    ),
                  ),
                  PopupMenuButton<String>(
                    icon: const Icon(
                      Icons.more_vert,
                      color: Color(0xFF2F2747),
                    ),
                    onSelected: (v) {
                      if (v == 'settings') {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const SettingsPage(),
                          ),
                        );
                      }
                    },
                    itemBuilder: (_) => const [
                      PopupMenuItem(
                        value: 'settings',
                        child: Text('Settings'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          Container(
            width: double.infinity,
            height: 1,
            color: const Color(0xFFEADFF7),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _chip(
                    text: 'All',
                    selected: _selectedTab == _TopTab.all,
                    onTap: () => setState(() => _selectedTab = _TopTab.all),
                  ),
                  const SizedBox(width: 7),
                  _chip(
                    text: 'Unread',
                    selected: _selectedTab == _TopTab.unread,
                    onTap: () => setState(() => _selectedTab = _TopTab.unread),
                  ),
                  const SizedBox(width: 7),
                  _chip(
                    text: 'Received',
                    selected: _selectedTab == _TopTab.received,
                    onTap: () =>
                        setState(() => _selectedTab = _TopTab.received),
                  ),
                  const SizedBox(width: 7),
                  _chip(
                    text: 'Sent',
                    selected: _selectedTab == _TopTab.sent,
                    onTap: () => setState(() => _selectedTab = _TopTab.sent),
                  ),
                ],
              ),
            ),
          ),
          Container(
            width: double.infinity,
            height: 10,
            decoration: const BoxDecoration(
              color: Color(0xFFF2EBF8),
              border: Border(
                top: BorderSide(color: Color(0xFFEADFF7)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildArchiveHeader({
    required int archivedCount,
    required List<Widget> archivedTiles,
  }) {
    if (archivedCount <= 0) return const SizedBox.shrink();

    return InkWell(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ArchivedChatsPage(
              archivedTiles: archivedTiles,
            ),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.fromLTRB(14, 8, 14, 4),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
        child: Row(
          children: [
            const Icon(
              Icons.archive_outlined,
              size: 22,
              color: Color(0xFF6A5B88),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Archived',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF4A3E64),
                ),
              ),
            ),
            Text(
              '$archivedCount',
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w800,
                color: Color(0xFF6A5B88),
              ),
            ),
            const SizedBox(width: 6),
            const Icon(
              Icons.arrow_forward_ios_rounded,
              size: 14,
              color: Color(0xFF6A5B88),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChatTile({
    required String roomId,
    required String otherUid,
    required String displayName,
    required String photo,
    required bool online,
    required Timestamp? lastSeen,
    required String lastMessage,
    required Timestamp? lastMessageAt,
    required bool isMine,
    required bool delivered,
    required bool seen,
    required Timestamp? mutedUntil,
    required int totalBadgeCount,
    required bool archived,
  }) {
    final subtitleText = lastMessage.trim().isEmpty ? '' : lastMessage;
    final statusText = _fmtLastSeen(lastSeen, online);

    final isMutedActive =
        mutedUntil != null && mutedUntil.toDate().isAfter(DateTime.now());

    return Material(
      color: Colors.white,
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ChatRoomPage(
                roomId: roomId,
                otherUid: otherUid,
              ),
            ),
          );
        },
        onLongPress: () => _openChatActions(
          roomId: roomId,
          archived: archived,
          isMutedActive: isMutedActive,
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              GestureDetector(
                onTap: () {
                  _showProfilePreview(
                    photo: photo,
                    name: displayName,
                  );
                },
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    CircleAvatar(
                      radius: 27,
                      backgroundColor: const Color(0xFFF1E9FF),
                      backgroundImage:
                          photo.isNotEmpty ? NetworkImage(photo) : null,
                      child: photo.isEmpty
                          ? const Icon(
                              Icons.person,
                              color: Color(0xFF7B4EFF),
                            )
                          : null,
                    ),
                    Positioned(
                      right: -1,
                      bottom: -1,
                      child: Container(
                        width: 14,
                        height: 14,
                        decoration: BoxDecoration(
                          color: online ? Colors.green : Colors.grey.shade400,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.white,
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Text(
                              displayName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 15.6,
                                fontWeight: FontWeight.w900,
                                color: Color(0xFF2F2747),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(
                                _fmtTime(lastMessageAt),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                textAlign: TextAlign.end,
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: totalBadgeCount > 0
                                      ? const Color(0xFF8D67FF)
                                      : Colors.grey.shade600,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                statusText,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                textAlign: TextAlign.end,
                                style: TextStyle(
                                  fontSize: 11.0,
                                  color: online
                                      ? const Color(0xFF1FA855)
                                      : Colors.grey.shade500,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 5),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          if (isMine && subtitleText.isNotEmpty) ...[
                            _tickWidget(
                              isMine: isMine,
                              delivered: delivered,
                              seen: seen,
                            ),
                            const SizedBox(width: 6),
                          ],
                          Expanded(
                            child: Text(
                              subtitleText.isEmpty ? statusText : subtitleText,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 13.1,
                                color: Colors.grey.shade700,
                                fontWeight: totalBadgeCount > 0
                                    ? FontWeight.w800
                                    : FontWeight.w600,
                              ),
                            ),
                          ),
                          if (isMutedActive) ...[
                            const SizedBox(width: 8),
                            Icon(
                              Icons.notifications_off_outlined,
                              size: 16,
                              color: Colors.grey.shade500,
                            ),
                          ],
                          if (totalBadgeCount > 0) ...[
                            const SizedBox(width: 8),
                            Container(
                              constraints: const BoxConstraints(
                                minWidth: 22,
                                minHeight: 22,
                              ),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: const BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    Color(0xFF8D67FF),
                                    Color(0xFFFF5DA2),
                                  ],
                                ),
                                borderRadius:
                                    BorderRadius.all(Radius.circular(11)),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                totalBadgeCount > 99
                                    ? '99+'
                                    : '$totalBadgeCount',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool _isDeletedForMe({
    required Map<String, dynamic> pref,
    required Timestamp? roomUpdatedAt,
  }) {
    final deleted = pref['deleted'] == true;
    final deletedAt = pref['deletedAt'] as Timestamp?;
    if (!deleted || deletedAt == null || roomUpdatedAt == null) return false;
    return !roomUpdatedAt.toDate().isAfter(deletedAt.toDate());
  }

  int _sortMillis(Map<String, dynamic> room) {
    final updatedAt = room['updatedAt'] as Timestamp?;
    final lastMessageAt = room['lastMessageAt'] as Timestamp?;
    return updatedAt?.millisecondsSinceEpoch ??
        lastMessageAt?.millisecondsSinceEpoch ??
        0;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF2EBF8),
      body: Column(
        children: [
          _buildHeader(),
          Expanded(
            child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: friendReqRef.snapshots(),
              builder: (context, friendReqSnap) {
                final receivedMap = <String, int>{};
                final sentMap = <String, int>{};

                if (friendReqSnap.hasData) {
                  for (final doc in friendReqSnap.data!.docs) {
                    final d = doc.data();
                    final fromUid = (d['fromUid'] ?? '').toString();
                    final toUid = (d['toUid'] ?? '').toString();
                    final status = (d['status'] ?? '').toString();

                    if (status != 'pending') continue;

                    if (toUid == uid) {
                      receivedMap[fromUid] = (receivedMap[fromUid] ?? 0) + 1;
                    }
                    if (fromUid == uid) {
                      sentMap[toUid] = (sentMap[toUid] ?? 0) + 1;
                    }
                  }
                }

                return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                  stream: myPrefsCollection.snapshots(),
                  builder: (context, prefsSnap) {
                    final prefsMap = <String, Map<String, dynamic>>{};
                    final archivedIds = <String>{};

                    if (prefsSnap.hasData) {
                      for (final d in prefsSnap.data!.docs) {
                        final data = d.data();
                        prefsMap[d.id] = data;
                        if (data['archived'] == true) {
                          archivedIds.add(d.id);
                        }
                      }
                    }

                    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                      stream: roomsRef
                          .where('participants', arrayContains: uid)
                          .snapshots(),
                      builder: (context, roomSnap) {
                        if (!roomSnap.hasData) {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        }

                        final allDocs = [...roomSnap.data!.docs];
                        allDocs.sort((a, b) {
                          final ams = _sortMillis(a.data());
                          final bms = _sortMillis(b.data());
                          return bms.compareTo(ams);
                        });

                        final normalTiles = <Widget>[];
                        final archivedTiles = <Widget>[];

                        for (final roomDoc in allDocs) {
                          final room = roomDoc.data();
                          final roomId = roomDoc.id;
                          final participants = (room['participants'] as List?) ?? [];
                          final otherUid = _otherUidFromParticipants(participants);
                          if (otherUid.isEmpty) continue;

                          final pref = prefsMap[roomId] ?? {};
                          final roomUpdatedAt = room['updatedAt'] as Timestamp? ??
                              room['lastMessageAt'] as Timestamp?;

                          if (_isDeletedForMe(
                            pref: pref,
                            roomUpdatedAt: roomUpdatedAt,
                          )) {
                            continue;
                          }

                          final unreadMap = room['unread'];
                          int unreadCount = 0;
                          if (unreadMap is Map) {
                            final v = unreadMap[uid];
                            if (v is int) unreadCount = v;
                            if (v is num) unreadCount = v.toInt();
                          }

                          final receivedFriendReqCount =
                              receivedMap[otherUid] ?? 0;
                          final sentFriendReqCount = sentMap[otherUid] ?? 0;

                          final showBySelectedTab = _matchesTopTab(
                            tab: _selectedTab,
                            unreadCount: unreadCount,
                            receivedFriendReqCount: receivedFriendReqCount,
                            sentFriendReqCount: sentFriendReqCount,
                          );

                          if (!showBySelectedTab) continue;

                          final lastMessage = (room['lastMessage'] ?? '').toString();
                          final lastMessageAt = room['lastMessageAt'] as Timestamp?;
                          final lastSenderId =
                              (room['lastMessageSenderId'] ?? '').toString();

                          final deliveredTo =
                              (room['lastMessageDeliveredTo'] as List?)
                                      ?.map((e) => e.toString())
                                      .toList() ??
                                  [];
                          final seenBy =
                              (room['lastMessageSeenBy'] as List?)
                                      ?.map((e) => e.toString())
                                      .toList() ??
                                  [];

                          final isMine = lastSenderId == uid;
                          final delivered = deliveredTo.contains(otherUid);
                          final seen = seenBy.contains(otherUid);
                          final mutedUntil = pref['muteChatUntil'] as Timestamp?;
                          final archived = archivedIds.contains(roomId);

                          final tile = StreamBuilder<
                              DocumentSnapshot<Map<String, dynamic>>>(
                            stream: FirebaseFirestore.instance
                                .collection('users')
                                .doc(otherUid)
                                .snapshots(),
                            builder: (context, otherSnap) {
                              final other = otherSnap.data?.data() ?? {};

                              final rawName =
                                  (other['displayName'] ?? '').toString().trim();
                              final displayName =
                                  rawName.isEmpty ? 'User' : rawName;

                              final photo =
                                  (other['photoUrl'] ?? other['profilePhoto'] ?? '')
                                      .toString();
                              final online = other['online'] == true;
                              final lastSeen = other['lastSeenAt'] as Timestamp?;

                              return StreamBuilder<
                                  QuerySnapshot<Map<String, dynamic>>>(
                                stream: FirebaseFirestore.instance
                                    .collection('chatRooms')
                                    .doc(roomId)
                                    .collection('requests')
                                    .snapshots(),
                                builder: (context, reqSnap) {
                                  int requestCount = 0;

                                  if (reqSnap.hasData) {
                                    final now = DateTime.now();

                                    for (final d in reqSnap.data!.docs) {
                                      final r = d.data();
                                      final toUid =
                                          (r['toUid'] ?? '').toString();
                                      final status =
                                          (r['status'] ?? '').toString();
                                      final expiresAt =
                                          r['expiresAt'] as Timestamp?;

                                      final notExpired = expiresAt == null
                                          ? true
                                          : expiresAt.toDate().isAfter(now);

                                      if (!notExpired) continue;
                                      if (status != 'pending') continue;

                                      if (toUid == uid) {
                                        requestCount++;
                                      }
                                    }
                                  }

                                  final totalBadgeCount =
                                      unreadCount + requestCount;

                                  return Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      _buildChatTile(
                                        roomId: roomId,
                                        otherUid: otherUid,
                                        displayName: displayName,
                                        photo: photo,
                                        online: online,
                                        lastSeen: lastSeen,
                                        lastMessage: lastMessage,
                                        lastMessageAt: lastMessageAt,
                                        isMine: isMine,
                                        delivered: delivered,
                                        seen: seen,
                                        mutedUntil: mutedUntil,
                                        totalBadgeCount: totalBadgeCount,
                                        archived: archived,
                                      ),
                                      Container(
                                        margin: const EdgeInsets.only(left: 78),
                                        height: 1,
                                        color: const Color(0xFFF0E7F8),
                                      ),
                                    ],
                                  );
                                },
                              );
                            },
                          );

                          if (archived) {
                            archivedTiles.add(tile);
                          } else {
                            normalTiles.add(tile);
                          }
                        }

                        if (normalTiles.isEmpty && archivedTiles.isEmpty) {
                          return const Center(
                            child: Text(
                              'No chats yet',
                              style: TextStyle(fontWeight: FontWeight.w800),
                            ),
                          );
                        }

                        return ListView(
                          padding: const EdgeInsets.fromLTRB(0, 0, 0, 12),
                          children: [
                            _buildArchiveHeader(
                              archivedCount: archivedTiles.length,
                              archivedTiles: archivedTiles,
                            ),
                            if (normalTiles.isNotEmpty)
                              Container(
                                color: Colors.white,
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: normalTiles,
                                ),
                              ),
                          ],
                        );
                      },
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