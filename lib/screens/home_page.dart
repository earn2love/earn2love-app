import 'dart:async';
import 'dart:math';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'payment_page.dart';
import 'profile_menu_page.dart';
import 'user_profile_page.dart';
import 'chat_room_page.dart';
import 'top_up_page.dart';
import 'notifications_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

enum _HomeFilter { all, online, nearby, newest }

class _HomePageState extends State<HomePage> {
  String get uid => FirebaseAuth.instance.currentUser?.uid ?? '';

  DocumentReference<Map<String, dynamic>> userRefFor(String id) =>
      FirebaseFirestore.instance.collection('users').doc(id);

  bool _planSheetShown = false;
  _HomeFilter _selectedFilter = _HomeFilter.all;

  final List<String> _dummyPhotos = const [
    'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517841905240-472988babdf9?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=1200&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1517365830460-955ce3ccd263?q=80&w=1200&auto=format&fit=crop',
  ];

  double asDouble(dynamic v, {double def = 0}) {
    if (v == null) return def;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v.trim()) ?? def;
    return def;
  }

  int asInt(dynamic v, {int def = 0}) {
    if (v == null) return def;
    if (v is int) return v;
    if (v is double) return v.round();
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v.trim()) ?? def;
    return def;
  }

  bool asBool(dynamic v, {bool def = false}) {
    if (v == null) return def;
    if (v is bool) return v;
    if (v is String) {
      final s = v.trim().toLowerCase();
      if (s == 'true') return true;
      if (s == 'false') return false;
    }
    return def;
  }

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ensurePlanSelected());
  }

  Future<void> _ensurePlanSelected() async {
    if (_planSheetShown) return;

    final u = FirebaseAuth.instance.currentUser;
    if (u == null) return;

    _planSheetShown = true;

    final ref = userRefFor(u.uid);
    final snap = await ref.get();
    final data = snap.data() ?? {};
    final tier = (data['tier'] ?? data['subTier'] ?? '').toString().trim();
    if (tier.isNotEmpty) return;

    if (!mounted) return;
    await showModalBottomSheet(
      context: context,
      isDismissible: false,
      enableDrag: false,
      backgroundColor: Colors.transparent,
      builder: (_) => _PlanSelectSheet(
        onSelect: (choice) async {
          if (choice == 'casual') {
            await ref.set({
              'tier': 'casual',
              'subTier': 'casual',
              'tierSelectedAt': FieldValue.serverTimestamp(),
              'updatedAt': FieldValue.serverTimestamp(),
            }, SetOptions(merge: true));
            if (mounted) Navigator.pop(context);
            return;
          }

          final ok = await Navigator.push<bool>(
            context,
            MaterialPageRoute(builder: (_) => PaymentPage(targetTier: choice)),
          );
          if (!mounted) return;
          if (ok == true) Navigator.pop(context);
        },
      ),
    );
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> _usersStream() {
    return FirebaseFirestore.instance
        .collection('users')
        .orderBy('updatedAt', descending: true)
        .limit(300)
        .snapshots();
  }

  String _pairId(String a, String b) {
    final ids = [a, b]..sort();
    return "${ids[0]}__${ids[1]}";
  }

  DocumentReference<Map<String, dynamic>> _friendReqDoc(String a, String b) {
    return FirebaseFirestore.instance
        .collection('friendRequests')
        .doc(_pairId(a, b));
  }

  Future<void> _sendRequest(String myUid, String toUid) async {
    if (toUid == myUid) return;

    if (toUid.startsWith('dummy_')) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Dummy user (UI test)")),
      );
      return;
    }

    final reqRef = _friendReqDoc(myUid, toUid);
    final snap = await reqRef.get();
    final existing = snap.data();
    final status = (existing?['status'] ?? '').toString();

    if (status == 'accepted') {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Already friends ✅")),
      );
      return;
    }

    if (status == 'pending' && (existing?['fromUid'] ?? '') == myUid) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Request already sent ⏳")),
      );
      return;
    }

    await reqRef.set({
      'fromUid': myUid,
      'toUid': toUid,
      'status': 'pending',
      'createdAt': existing?['createdAt'] ?? FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Request sent ✅")),
    );
  }

  Future<void> _acceptFriendRequest(String myUid, String otherUid) async {
    final reqRef = _friendReqDoc(myUid, otherUid);
    await reqRef.set({
      'status': 'accepted',
      'acceptedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Request accepted ✅")),
    );
  }

  Future<void> _openChatWithStarter({
    required String myUid,
    required String otherUid,
    required String otherName,
  }) async {
    if (otherUid.startsWith('dummy_')) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Dummy user (UI test)")),
      );
      return;
    }

    final rooms = FirebaseFirestore.instance.collection('chatRooms');
    final q = await rooms
        .where('participants', arrayContains: myUid)
        .limit(100)
        .get();

    String? roomId;
    for (final d in q.docs) {
      final p = (d.data()['participants'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          [];
      if (p.contains(otherUid) && p.length == 2) {
        roomId = d.id;
        break;
      }
    }

    roomId ??= rooms.doc().id;
    final roomRef = rooms.doc(roomId);

    await roomRef.set({
      'participants': [myUid, otherUid],
      'updatedAt': FieldValue.serverTimestamp(),
      'lastMessage': '',
      'lastMessageAt': FieldValue.serverTimestamp(),
      'unread': {
        myUid: 0,
        otherUid: 0,
      },
    }, SetOptions(merge: true));

    final existingMsgs = await roomRef.collection('messages').limit(1).get();
    if (existingMsgs.docs.isEmpty) {
      final text = 'Hello $otherName, how are you?';

      await roomRef.collection('messages').add({
        'senderId': myUid,
        'text': text,
        'type': 'text',
        'createdAt': FieldValue.serverTimestamp(),
        'deletedFor': <String>[],
      });

      await roomRef.set({
        'lastMessage': text,
        'lastMessageAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
        'unread.$otherUid': FieldValue.increment(1),
        'unread.$myUid': 0,
      }, SetOptions(merge: true));
    }

    if (!mounted) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatRoomPage(roomId: roomId!, otherUid: otherUid),
      ),
    );
  }

  List<Map<String, dynamic>> _makeDummyUsers(int count) {
    final rand = Random(12);
    final names = [
      "Priya",
      "Neha",
      "Anjali",
      "Sneha",
      "Divya",
      "Pooja",
      "Aanya",
      "Riya",
      "Meera",
      "Kavya",
      "Sara",
      "Nisha",
      "Diya",
      "Isha",
      "Saanvi",
      "Tanvi",
      "Myra",
      "Kiara",
    ];
    final tiers = ["love", "friendship", "casual"];

    return List.generate(count, (i) {
      return {
        'uid': 'dummy_$i',
        'displayName': names[i % names.length],
        'age': 21 + (i % 5),
        'distanceKm': 1 + (i % 7),
        'tier': tiers[i % tiers.length],
        'subTier': tiers[i % tiers.length],
        'photoUrl': _dummyPhotos[i % _dummyPhotos.length],
        'profilePhoto': _dummyPhotos[i % _dummyPhotos.length],
        'isOnline': rand.nextBool(),
        'isNew': i % 4 == 0,
        'ratingPercent': 82 + (i % 17),
      };
    });
  }

  List<Map<String, dynamic>> _applyFilter(List<Map<String, dynamic>> users) {
    final list = [...users];
    switch (_selectedFilter) {
      case _HomeFilter.all:
        return list;
      case _HomeFilter.online:
        return list.where((u) => asBool(u['isOnline'], def: true)).toList();
      case _HomeFilter.nearby:
        list.sort((a, b) => asInt(a['distanceKm'], def: 99)
            .compareTo(asInt(b['distanceKm'], def: 99)));
        return list;
      case _HomeFilter.newest:
        return list.where((u) => asBool(u['isNew'], def: false)).toList();
    }
  }

  String _resolvePhoto(Map<String, dynamic> u, int index) {
    final photo = asString(u['photoUrl'] ?? u['profilePhoto']);
    if (photo.isNotEmpty) return photo;
    return _dummyPhotos[index % _dummyPhotos.length];
  }

  int _resolveAge(Map<String, dynamic> u, int index) {
    final age = asInt(u['age'], def: 0);
    if (age > 0) return age;
    return 21 + (index % 5);
  }

  int _resolveDistance(Map<String, dynamic> u, int index) {
    final d = asInt(u['distanceKm'], def: 0);
    if (d > 0) return d;
    return 1 + (index % 7);
  }

  bool _resolveOnline(Map<String, dynamic> u, int index) {
    if (u.containsKey('isOnline')) return asBool(u['isOnline'], def: true);
    return index % 2 == 0;
  }

  int _resolveRating(Map<String, dynamic> u, int index) {
    final r = asInt(u['ratingPercent'], def: 0);
    if (r > 0) return r.clamp(1, 100);
    return 85 + (index % 13);
  }

  String _resolveTier(Map<String, dynamic> u) {
    return asString(u['tier'] ?? u['subTier'], def: 'casual').toLowerCase();
  }

  Widget _header(Map<String, dynamic> me) {
    final myName = asString(me['displayName'], def: 'mouli');
    final myTier =
        asString(me['tier'] ?? me['subTier'], def: 'LOVE').toUpperCase();
    final myPhoto = asString(me['photoUrl'] ?? me['profilePhoto']);
    final silver = asDouble(me['silverBalance']).toStringAsFixed(0);

    final rawCountry = asString(me['country'], def: 'IN').toUpperCase();
    final country = rawCountry == 'UK' ? 'UK' : 'IN';

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
      decoration: BoxDecoration(
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(34)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.pink.shade400,
            Colors.purple.shade500,
            Colors.indigo.shade500,
          ],
        ),
        boxShadow: [
          BoxShadow(
            blurRadius: 16,
            offset: const Offset(0, 8),
            color: Colors.purple.withOpacity(0.18),
          ),
        ],
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(999),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const ProfileMenuPage()),
                );
              },
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white.withOpacity(0.95),
                    width: 2,
                  ),
                ),
                child: CircleAvatar(
                  radius: 28,
                  backgroundColor: Colors.white.withOpacity(0.12),
                  backgroundImage:
                      myPhoto.isEmpty ? null : NetworkImage(myPhoto),
                  child: myPhoto.isEmpty
                      ? const Icon(Icons.person, color: Colors.white, size: 30)
                      : null,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Earn2Love',
                        style: TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                          height: 1,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                            color: Color(0xFF25D366),
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '${myName.toLowerCase()} · $myTier',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: Colors.white.withOpacity(0.95),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            // RIGHT SIDE
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => TopUpPage(country: country),
                      ),
                    );
                  },
                  child: SizedBox(
                    width: 56,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.96),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                blurRadius: 10,
                                offset: const Offset(0, 4),
                                color: Colors.black.withOpacity(0.10),
                              ),
                            ],
                          ),
                          child: Stack(
                            clipBehavior: Clip.none,
                            alignment: Alignment.center,
                            children: [
                              Container(
                                width: 24,
                                height: 24,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: LinearGradient(
                                    colors: [
                                      Colors.blueGrey.shade200,
                                      Colors.grey.shade100,
                                      Colors.blueGrey.shade300,
                                    ],
                                  ),
                                ),
                                alignment: Alignment.center,
                                child: const Text(
                                  '₹',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w900,
                                    color: Color(0xFF535B67),
                                  ),
                                ),
                              ),
                              Positioned(
                                right: -1,
                                top: -1,
                                child: Container(
                                  width: 20,
                                  height: 20,
                                  decoration: const BoxDecoration(
                                    color: Color(0xFFFFD948),
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Icon(
                                    Icons.add,
                                    size: 14,
                                    color: Color(0xFF222431),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 4),
                        SizedBox(
                          height: 16,
                          child: Text(
                            silver,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w900,
                              color: Colors.white.withOpacity(0.98),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                  stream: FirebaseFirestore.instance
                      .collection('users')
                      .doc(uid)
                      .snapshots(),
                  builder: (context, snap) {
                    final data = snap.data?.data() ?? {};
                    final counters =
                        (data['counters'] as Map<String, dynamic>?) ?? {};
                    final unread =
                        asInt(counters['unreadBellNotifications'], def: 0);

                    return InkWell(
                      borderRadius: BorderRadius.circular(999),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const NotificationsPage(),
                          ),
                        );
                      },
                      child: Container(
                        width: 48,
                        height: 48,
                        margin: const EdgeInsets.only(top: 0),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.96),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                              color: Colors.black.withOpacity(0.10),
                            ),
                          ],
                        ),
                        child: Stack(
                          clipBehavior: Clip.none,
                          alignment: Alignment.center,
                          children: [
                            const Icon(
                              Icons.notifications_none_rounded,
                              size: 24,
                              color: Color(0xFF3E3753),
                            ),
                            if (unread > 0)
                              Positioned(
                                right: -2,
                                top: -2,
                                child: Container(
                                  constraints: const BoxConstraints(
                                    minWidth: 18,
                                    minHeight: 18,
                                  ),
                                  padding:
                                      const EdgeInsets.symmetric(horizontal: 4),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFFF4D6D),
                                    borderRadius: BorderRadius.circular(999),
                                    border: Border.all(
                                      color: Colors.white,
                                      width: 1.4,
                                    ),
                                  ),
                                  alignment: Alignment.center,
                                  child: Text(
                                    unread > 99 ? '99+' : '$unread',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 9,
                                      fontWeight: FontWeight.w900,
                                      height: 1,
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip({
    required String title,
    required bool selected,
    bool showDot = false,
    required VoidCallback onTap,
  }) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Container(
        height: 38,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          gradient: selected
              ? const LinearGradient(
                  colors: [Color(0xFF6B3EFF), Color(0xFFE14AA9)],
                )
              : null,
          color: selected ? null : const Color(0xFFF0EAF6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showDot) ...[
              Container(
                width: 10,
                height: 10,
                decoration: const BoxDecoration(
                  color: Color(0xFF2ECC71),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
            ],
            Text(
              title,
              style: TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : const Color(0xFF2E2A41),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _filtersRow() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 2),
      child: Row(
        children: [
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _chip(
                    title: 'All',
                    selected: _selectedFilter == _HomeFilter.all,
                    onTap: () =>
                        setState(() => _selectedFilter = _HomeFilter.all),
                  ),
                  const SizedBox(width: 8),
                  _chip(
                    title: 'Online',
                    selected: _selectedFilter == _HomeFilter.online,
                    showDot: true,
                    onTap: () =>
                        setState(() => _selectedFilter = _HomeFilter.online),
                  ),
                  const SizedBox(width: 8),
                  _chip(
                    title: 'Nearby',
                    selected: _selectedFilter == _HomeFilter.nearby,
                    onTap: () =>
                        setState(() => _selectedFilter = _HomeFilter.nearby),
                  ),
                  const SizedBox(width: 8),
                  _chip(
                    title: 'New',
                    selected: _selectedFilter == _HomeFilter.newest,
                    onTap: () =>
                        setState(() => _selectedFilter = _HomeFilter.newest),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
            ),
            child: IconButton(
              padding: EdgeInsets.zero,
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Filter settings coming soon')),
                );
              },
              icon: const Icon(
                Icons.tune_rounded,
                color: Color(0xFF3D3951),
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _subscriptionBadge(String tier) {
    if (tier == 'love') {
      return Container(
        height: 24,
        padding: const EdgeInsets.symmetric(horizontal: 7),
        decoration: BoxDecoration(
          color: const Color(0xFFF7CFE4),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('💗', style: TextStyle(fontSize: 12)),
            SizedBox(width: 3),
            Text(
              'LOVE',
              style: TextStyle(
                fontSize: 9.6,
                fontWeight: FontWeight.w900,
                color: Color(0xFFE43A87),
              ),
            ),
          ],
        ),
      );
    }

    if (tier == 'friendship') {
      return Container(
        height: 24,
        padding: const EdgeInsets.symmetric(horizontal: 6),
        decoration: BoxDecoration(
          color: const Color(0xFFF8E5CC),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('🤝', style: TextStyle(fontSize: 11)),
            SizedBox(width: 2),
            Text(
              'FRIENDSHIP',
              style: TextStyle(
                fontSize: 7.9,
                fontWeight: FontWeight.w900,
                color: Color(0xFFD97817),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      height: 24,
      padding: const EdgeInsets.symmetric(horizontal: 7),
      decoration: BoxDecoration(
        color: const Color(0xFFDCE6FA),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('🔥', style: TextStyle(fontSize: 12)),
          SizedBox(width: 3),
          Text(
            'CASUAL',
            style: TextStyle(
              fontSize: 9.0,
              fontWeight: FontWeight.w900,
              color: Color(0xFF42619E),
            ),
          ),
        ],
      ),
    );
  }

  Widget _ratingChip(int rating) {
    return Container(
      height: 24,
      padding: const EdgeInsets.symmetric(horizontal: 7),
      decoration: BoxDecoration(
        color: const Color(0xFFF1EEF8),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.star_rounded,
            size: 13,
            color: Color(0xFFFFB300),
          ),
          const SizedBox(width: 3),
          Text(
            '$rating%',
            style: const TextStyle(
              fontSize: 9.4,
              fontWeight: FontWeight.w900,
              color: Color(0xFF4C4463),
            ),
          ),
        ],
      ),
    );
  }

  Widget _requestActionButton({
    required String myUid,
    required String otherUid,
    required String status,
    required String fromUid,
  }) {
    Color bg = const Color(0xFFF2ECFA);
    Color fg = const Color(0xFF564D6B);
    IconData icon = Icons.person_add_alt_1_rounded;
    String label = 'Request';
    VoidCallback? onTap = () => _sendRequest(myUid, otherUid);

    if (status == 'accepted') {
      bg = const Color(0xFFE7F8EC);
      fg = const Color(0xFF228B4E);
      icon = Icons.people_alt_rounded;
      label = 'Friends';
      onTap = null;
    } else if (status == 'pending' && fromUid == myUid) {
      bg = const Color(0xFFEAF0FB);
      fg = const Color(0xFF48638B);
      icon = Icons.schedule_rounded;
      label = 'Sent';
      onTap = null;
    } else if (status == 'pending' && fromUid == otherUid) {
      bg = const Color(0xFFE7F8EC);
      fg = const Color(0xFF228B4E);
      icon = Icons.check_circle_rounded;
      label = 'Accept';
      onTap = () => _acceptFriendRequest(myUid, otherUid);
    }

    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Ink(
            height: 30,
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 13, color: fg),
                const SizedBox(width: 4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 9.4,
                    fontWeight: FontWeight.w800,
                    color: fg,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _textButton(String myUid, String otherUid, String otherName) {
    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _openChatWithStarter(
            myUid: myUid,
            otherUid: otherUid,
            otherName: otherName,
          ),
          child: Ink(
            height: 30,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFFF7A2E), Color(0xFFFF2F79)],
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.chat_bubble_rounded,
                  size: 12,
                  color: Colors.white,
                ),
                SizedBox(width: 4),
                Text(
                  'Text',
                  style: TextStyle(
                    fontSize: 9.6,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _userCard(Map<String, dynamic> u, String myUid, int index) {
    final id = asString(u['uid']);
    final name = asString(u['displayName'], def: 'User');
    final age = _resolveAge(u, index);
    final distance = _resolveDistance(u, index);
    final isOnline = _resolveOnline(u, index);
    final photo = _resolvePhoto(u, index);
    final tier = _resolveTier(u);
    final rating = _resolveRating(u, index);
    final isDummy = id.startsWith('dummy_');

    if (isDummy) {
      return _userCardBody(
        userTap: null,
        name: name,
        age: age,
        distance: distance,
        isOnline: isOnline,
        photo: photo,
        tier: tier,
        rating: rating,
        actionRow: Row(
          children: [
            Expanded(
              child: Container(
                height: 30,
                decoration: BoxDecoration(
                  color: const Color(0xFFF2ECFA),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.person_add_alt_1_rounded,
                        size: 13, color: Color(0xFF564D6B)),
                    SizedBox(width: 4),
                    Text(
                      'Request',
                      style: TextStyle(
                        fontSize: 9.4,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF564D6B),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Container(
                height: 30,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFFF7A2E), Color(0xFFFF2F79)],
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.chat_bubble_rounded,
                        size: 12, color: Colors.white),
                    SizedBox(width: 4),
                    Text(
                      'Text',
                      style: TextStyle(
                        fontSize: 9.6,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _friendReqDoc(myUid, id).snapshots(),
      builder: (context, reqSnap) {
        final req = reqSnap.data?.data() ?? {};
        final status = asString(req['status'], def: '');
        final fromUid = asString(req['fromUid']);

        return _userCardBody(
          userTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => UserProfilePage(userId: id)),
          ),
          name: name,
          age: age,
          distance: distance,
          isOnline: isOnline,
          photo: photo,
          tier: tier,
          rating: rating,
          actionRow: Row(
            children: [
              _requestActionButton(
                myUid: myUid,
                otherUid: id,
                status: status,
                fromUid: fromUid,
              ),
              const SizedBox(width: 6),
              _textButton(myUid, id, name),
            ],
          ),
        );
      },
    );
  }

  Widget _userCardBody({
    required VoidCallback? userTap,
    required String name,
    required int age,
    required int distance,
    required bool isOnline,
    required String photo,
    required String tier,
    required int rating,
    required Widget actionRow,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
        boxShadow: [
          BoxShadow(
            blurRadius: 14,
            offset: const Offset(0, 8),
            color: const Color(0xFFC6B5DC).withOpacity(0.25),
          ),
        ],
      ),
      child: Column(
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: userTap,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(26)),
              child: ClipPath(
                clipper: _TopPhotoClipper(),
                child: SizedBox(
                  height: 140,
                  width: double.infinity,
                  child: Image.network(
                    photo,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) {
                      return Container(
                        color: const Color(0xFFF0E9F8),
                        alignment: Alignment.center,
                        child: const Icon(Icons.person,
                            size: 48, color: Colors.deepPurple),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(11, 9, 11, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: userTap,
                    borderRadius: BorderRadius.circular(12),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              color: isOnline
                                  ? const Color(0xFF2ECC71)
                                  : const Color(0xFFB7C0CC),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 5),
                          Expanded(
                            child: Text(
                              '$name · $age · ${distance}km',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 12.8,
                                fontWeight: FontWeight.w900,
                                color: Color(0xFF1F2030),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 7),
                Row(
                  children: [
                    Flexible(child: _subscriptionBadge(tier)),
                    const SizedBox(width: 5),
                    _ratingChip(rating),
                  ],
                ),
                const SizedBox(height: 8),
                actionRow,
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final u = FirebaseAuth.instance.currentUser;

    if (u == null) {
      return const Scaffold(
        backgroundColor: Color(0xFFF8F2FF),
        body: SizedBox.shrink(),
      );
    }

    final myUid = u.uid;
    final myRef = userRefFor(myUid);

    return Scaffold(
      backgroundColor: const Color(0xFFF7F2FB),
      body: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: myRef.snapshots(),
        builder: (context, meSnap) {
          final me = meSnap.data?.data() ?? {};

          return Column(
            children: [
              _header(me),
              _filtersRow(),
              Expanded(
                child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                  stream: _usersStream(),
                  builder: (context, snap) {
                    if (!snap.hasData) {
                      return const Center(child: CircularProgressIndicator());
                    }

                    final users = snap.data!.docs
                        .map((d) {
                          final m = d.data();
                          m['uid'] = d.id;
                          return m;
                        })
                        .where((m) => (m['uid']?.toString() ?? '') != myUid)
                        .toList();

                    final displayUsers = <Map<String, dynamic>>[...users];
                    if (displayUsers.length < 30) {
                      displayUsers
                          .addAll(_makeDummyUsers(30 - displayUsers.length));
                    }

                    final filtered = _applyFilter(displayUsers);

                    return GridView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
                      itemCount: filtered.length,
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 14,
                        mainAxisSpacing: 14,
                        childAspectRatio: 0.602,
                      ),
                      itemBuilder: (context, index) {
                        return _userCard(filtered[index], myUid, index);
                      },
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _TopPhotoClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();
    path.moveTo(0, 20);
    path.quadraticBezierTo(0, 0, 20, 0);
    path.lineTo(size.width - 20, 0);
    path.quadraticBezierTo(size.width, 0, size.width, 20);
    path.lineTo(size.width, size.height - 8);
    path.quadraticBezierTo(
      size.width * 0.78,
      size.height + 6,
      size.width * 0.56,
      size.height - 4,
    );
    path.quadraticBezierTo(
      size.width * 0.28,
      size.height - 14,
      0,
      size.height,
    );
    path.close();
    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}

class _PlanSelectSheet extends StatelessWidget {
  final FutureOr<void> Function(String choice) onSelect;
  const _PlanSelectSheet({required this.onSelect});

  @override
  Widget build(BuildContext context) {
    Widget planTile({
      required IconData icon,
      required String title,
      required String subtitle,
      required String value,
      bool premium = false,
    }) {
      return Card(
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        child: ListTile(
          leading: CircleAvatar(
            backgroundColor:
                premium ? Colors.pink.shade50 : Colors.green.shade50,
            child: Icon(
              icon,
              color: premium ? Colors.pink.shade400 : Colors.green.shade600,
            ),
          ),
          title:
              Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
          subtitle: Text(subtitle),
          trailing: premium
              ? const Icon(Icons.lock)
              : const Icon(Icons.check_circle_outline),
          onTap: () => onSelect(value),
        ),
      );
    }

    return SafeArea(
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          boxShadow: [
            BoxShadow(
              blurRadius: 22,
              offset: const Offset(0, 12),
              color: Colors.black.withOpacity(0.15),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              "Select your mode",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            planTile(
              icon: Icons.person_outline,
              title: "Casual",
              subtitle: "Free mode • browse & basic chat",
              value: "casual",
            ),
            planTile(
              icon: Icons.group_outlined,
              title: "Friendship",
              subtitle: "Subscription required • extra features",
              value: "friendship",
              premium: true,
            ),
            planTile(
              icon: Icons.favorite_border,
              title: "Love",
              subtitle: "Subscription required • full access",
              value: "love",
              premium: true,
            ),
            const SizedBox(height: 8),
            Text(
              "Friendship/Love → payment page opens.",
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
