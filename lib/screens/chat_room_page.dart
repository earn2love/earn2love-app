import 'dart:async';
import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../chat/services/chat_references.dart';
import '../chat/services/presence_service.dart';
import '../chat/services/typing_service.dart';

import 'package:earn2love_app/screens/settings/chat_room_settings_page.dart';
import 'package:earn2love_app/screens/settings/report_page.dart';
import 'package:earn2love_app/screens/settings/rules_page.dart';

import 'user_profile_page.dart';

class ChatRoomPage extends StatefulWidget {
  final String roomId;
  final String otherUid;

  const ChatRoomPage({
    super.key,
    required this.roomId,
    required this.otherUid,
  });

  @override
  State<ChatRoomPage> createState() => _ChatRoomPageState();
}

class _ChatRoomPageState extends State<ChatRoomPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  late final ChatReferences _chatReferences;
  late final PresenceService _presenceService;
  late final TypingService _typingService;

  final TextEditingController msgCtrl = TextEditingController();
  final FocusNode _msgFocusNode = FocusNode();
  final ScrollController scrollCtrl = ScrollController();
  final ImagePicker _picker = ImagePicker();
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();

  final ValueKey _composerFieldKey = const ValueKey('chat_composer_field');

  Timer? _bannerTimer;
  Timer? _typingTimer;

  Map<String, dynamic>? _activeBanner;
  Map<String, dynamic>? _replyingTo;

  bool _sendingImage = false;
  bool _sendingText = false;
  bool _acceptBusy = false;
  bool _markingSeen = false;
  bool _isRecording = false;
  bool _searchMode = false;
  bool _hasTypedText = false;

  String _searchText = '';
  String? _recordingPath;
  String? _playingAudioUrl;
  String _lastMarkSeenSignature = '';

  int _pageSize = 30;
  static const int _pageStep = 30;
  static const int _maxImageBytes = 5 * 1024 * 1024;
  static const int _maxAudioBytes = 10 * 1024 * 1024;

  static const Duration _requestBannerDuration = Duration(seconds: 20);
  static const Duration _requestExpiryDuration = Duration(hours: 24);

  bool _meHasEligiblePlan = false;
  bool _blockedByMe = false;
  bool _blockedByOther = false;
  String _friendStatus = '';

  Map<String, dynamic> _myGlobalSettings = <String, dynamic>{};
  Map<String, dynamic> _myChatPrefs = <String, dynamic>{};

  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _meSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _roomSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _friendSub;
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _prefsSub;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _reqSub;
  StreamSubscription<PlayerState>? _audioPlayerStateSub;

  bool get _anyBlocked => _blockedByMe || _blockedByOther;
  bool get _isFriends => _friendStatus == 'accepted';
  bool get _canUseLockedFeatures => _isFriends && _meHasEligiblePlan;

  DocumentReference<Map<String, dynamic>> get meRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  DocumentReference<Map<String, dynamic>> get otherRef =>
      FirebaseFirestore.instance.collection('users').doc(widget.otherUid);

  DocumentReference<Map<String, dynamic>> get roomRef =>
      FirebaseFirestore.instance.collection('chatRooms').doc(widget.roomId);

  CollectionReference<Map<String, dynamic>> get msgRef =>
      roomRef.collection('messages');

  CollectionReference<Map<String, dynamic>> get reqRef =>
      roomRef.collection('requests');

  DocumentReference<Map<String, dynamic>> get friendReqRef =>
      FirebaseFirestore.instance
          .collection('friendRequests')
          .doc(_pairId(uid, widget.otherUid));

  DocumentReference<Map<String, dynamic>> get myChatPrefsRef =>
      meRef.collection('chatPrefs').doc(widget.roomId);

  DocumentReference<Map<String, dynamic>> get myBlockedUserRef =>
      meRef.collection('blockedUsers').doc(widget.otherUid);

  String _pairId(String a, String b) {
    final ids = [a, b]..sort();
    return '${ids[0]}__${ids[1]}';
  }

  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

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
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v.trim()) ?? def;
    return def;
  }

  bool asBool(dynamic v, {bool def = false}) {
    if (v is bool) return v;
    if (v is num) return v != 0;
    if (v is String) {
      final s = v.trim().toLowerCase();
      if (s == 'true' || s == '1' || s == 'yes') return true;
      if (s == 'false' || s == '0' || s == 'no') return false;
    }
    return def;
  }

  Map<String, dynamic> asMap(dynamic v) {
    if (v is Map) {
      return v.map((k, value) => MapEntry(k.toString(), value));
    }
    return <String, dynamic>{};
  }

  bool hasFriendshipOrLove(String tier) =>
      tier == 'friendship' || tier == 'love';

  @override
  void initState() {
    super.initState();

    _chatReferences = ChatReferences(
      firestore: FirebaseFirestore.instance,
      currentUid: uid,
      otherUid: widget.otherUid,
      roomId: widget.roomId,
    );
    _presenceService = PresenceService(
      userReference: _chatReferences.currentUser,
    );
    _typingService = TypingService(
      roomReference: _chatReferences.room,
      currentUid: uid,
    );

    _setOnline(true);
    _listenMyDoc();
    _listenMyPrefs();
    _listenRequests();
    _listenMyTier();
    _listenRoomBlockState();
    _listenFriendStatus();
    _markRoomRead();
    _cleanupExpiredRequests();

    scrollCtrl.addListener(_onScrollLoadMore);

    msgCtrl.addListener(() {
      final nowHasText = msgCtrl.text.trim().isNotEmpty;
      if (nowHasText != _hasTypedText && mounted) {
        setState(() => _hasTypedText = nowHasText);
      }
    });

    _audioPlayerStateSub = _audioPlayer.playerStateStream.listen((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _setOnline(false);
    _bannerTimer?.cancel();
    _typingTimer?.cancel();
    _meSub?.cancel();
    _roomSub?.cancel();
    _friendSub?.cancel();
    _prefsSub?.cancel();
    _reqSub?.cancel();
    _audioPlayerStateSub?.cancel();
    msgCtrl.dispose();
    _msgFocusNode.dispose();
    scrollCtrl.dispose();
    _audioPlayer.dispose();
    _recorder.dispose();
    super.dispose();
  }

  void _listenMyDoc() {
    _meSub?.cancel();
    _meSub = meRef.snapshots().listen((snap) {
      final data = snap.data() ?? <String, dynamic>{};
      final settings = asMap(data['settings']);
      final tier = asString(data['tier'] ?? data['subTier'], def: 'casual');
      final can = hasFriendshipOrLove(tier);

      if (!mounted) return;
      setState(() {
        _myGlobalSettings = settings;
        _meHasEligiblePlan = can;
      });
    });
  }

  void _listenMyPrefs() {
    _prefsSub?.cancel();
    _prefsSub = myChatPrefsRef.snapshots().listen((snap) {
      final data = snap.data() ?? <String, dynamic>{};
      if (!mounted) return;
      setState(() {
        _myChatPrefs = data;
      });
    });
  }

  bool _globalAllowImageRequests() =>
      asBool(_myGlobalSettings['allowImageRequests'], def: true);

  bool _globalAllowAudioCalls() =>
      asBool(_myGlobalSettings['allowAudioCalls'], def: true);

  bool _globalAllowVideoCalls() =>
      asBool(_myGlobalSettings['allowVideoCalls'], def: true);

  bool _globalReadReceipts() =>
      asBool(_myGlobalSettings['readReceipts'], def: true);

  bool _globalShowOnlineStatus() =>
      asBool(_myGlobalSettings['showOnlineStatus'], def: true);

  bool _chatAllowImageRequests() {
    if (_myChatPrefs.containsKey('allowImageRequests')) {
      return asBool(_myChatPrefs['allowImageRequests'], def: true);
    }
    return _globalAllowImageRequests();
  }

  bool _chatAllowAudioRequests() {
    if (_myChatPrefs.containsKey('allowAudioRequests')) {
      return asBool(_myChatPrefs['allowAudioRequests'], def: true);
    }
    return _globalAllowAudioCalls();
  }

  bool _chatAllowVideoRequests() {
    if (_myChatPrefs.containsKey('allowVideoRequests')) {
      return asBool(_myChatPrefs['allowVideoRequests'], def: true);
    }
    return _globalAllowVideoCalls();
  }

  bool _chatReadReceiptsEnabled() {
    if (_myChatPrefs.containsKey('readReceipts')) {
      return asBool(_myChatPrefs['readReceipts'], def: true);
    }
    return _globalReadReceipts();
  }

  bool _chatShowOnlineStatusEnabled() {
    if (_myChatPrefs.containsKey('showOnlineStatus')) {
      return asBool(_myChatPrefs['showOnlineStatus'], def: true);
    }
    return _globalShowOnlineStatus();
  }

  bool _canReceiveRequestType(String type) {
    switch (type) {
      case 'photo_request':
        return _chatAllowImageRequests();
      case 'audio_call_request':
        return _chatAllowAudioRequests();
      case 'video_call_request':
        return _chatAllowVideoRequests();
      default:
        return true;
    }
  }

  String _blockedComposerHint() {
    if (_blockedByMe) return 'You blocked this user';
    if (_blockedByOther) return 'You cannot send messages to this user';
    return 'Message';
  }

  Future<void> _openChatRoomSettings() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatRoomSettingsPage(
          roomId: widget.roomId,
          otherUid: widget.otherUid,
        ),
      ),
    );
  }

  Future<void> _openReportPage() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ReportPage(targetUid: widget.otherUid),
      ),
    );
  }

  Future<void> _openRulesPage() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => const RulesPage(),
      ),
    );
  }

  void _onScrollLoadMore() {
    if (!scrollCtrl.hasClients) return;
    if (scrollCtrl.position.pixels >=
        scrollCtrl.position.maxScrollExtent - 280) {
      setState(() {
        _pageSize += _pageStep;
      });
    }
  }

  void _scheduleMarkSeen(
    List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
  ) {
    final signature =
        docs.isEmpty ? 'empty' : '${docs.first.id}_${docs.length}';
    if (_markingSeen || _lastMarkSeenSignature == signature) return;

    _lastMarkSeenSignature = signature;

    Future.microtask(() {
      if (!mounted) return;
      _markSeenAndDelivered(docs);
    });
  }

  Future<void> _setOnline(bool on) async {
    await _presenceService.setOnline(on);
  }

  Future<void> _markRoomRead() async {
    await roomRef.set({
      'unread.$uid': 0,
      'updatedAt': FieldValue.serverTimestamp(),
      'lastMessageSeenBy': FieldValue.arrayUnion([uid]),
      'lastMessageDeliveredTo': FieldValue.arrayUnion([uid]),
    }, SetOptions(merge: true));
  }

  Future<void> _setTyping(bool value) async {
    await _typingService.setTyping(value);
  }

  void _onTypingChanged(String text) {
    _setTyping(true);
    _typingTimer?.cancel();
    _typingTimer = Timer(const Duration(seconds: 2), () async {
      await _setTyping(false);
    });
  }

  void _listenMyTier() {
    // kept intentionally because original logic used this listener too
    meRef.snapshots().listen((snap) {
      final me = snap.data() ?? {};
      final tier = asString(me['tier'] ?? me['subTier'], def: 'casual');
      final can = hasFriendshipOrLove(tier);
      if (mounted && can != _meHasEligiblePlan) {
        setState(() => _meHasEligiblePlan = can);
      }
    });
  }

  void _listenFriendStatus() {
    _friendSub?.cancel();
    _friendSub = friendReqRef.snapshots().listen((snap) {
      final data = snap.data() ?? {};
      final status = asString(data['status']);
      if (!mounted) return;
      if (status != _friendStatus) {
        setState(() => _friendStatus = status);
      }
    });
  }

  void _listenRoomBlockState() {
    _roomSub?.cancel();
    _roomSub = roomRef.snapshots().listen((snap) {
      final data = snap.data() ?? {};
      final blockedBy = asMap(data['blockedBy']);

      final byMe = blockedBy[uid] == true;
      final byOther = blockedBy[widget.otherUid] == true;

      if (!mounted) return;
      if (byMe != _blockedByMe || byOther != _blockedByOther) {
        setState(() {
          _blockedByMe = byMe;
          _blockedByOther = byOther;
        });
      }
    });
  }

  Future<void> _cleanupExpiredRequests() async {
    try {
      final snap = await reqRef.get();
      final now = DateTime.now();
      final batch = FirebaseFirestore.instance.batch();

      for (final doc in snap.docs) {
        final data = doc.data();
        final status = asString(data['status']);
        if (status != 'pending') continue;

        final expiresAt = data['expiresAt'] as Timestamp?;
        if (expiresAt == null) continue;

        if (expiresAt.toDate().isBefore(now)) {
          final type = asString(data['type']);
          final toUid = asString(data['toUid']);

          batch.delete(doc.reference);

          if (toUid.isNotEmpty) {
            final receiverRef =
                FirebaseFirestore.instance.collection('users').doc(toUid);

            if (type == 'audio_call_request' || type == 'video_call_request') {
              batch.set(
                receiverRef,
                {
                  'counters.pendingCallRequests': FieldValue.increment(-1),
                  'updatedAt': FieldValue.serverTimestamp(),
                },
                SetOptions(merge: true),
              );
            } else if (type == 'photo_request') {
              batch.set(
                receiverRef,
                {
                  'counters.pendingImageRequests': FieldValue.increment(-1),
                  'updatedAt': FieldValue.serverTimestamp(),
                },
                SetOptions(merge: true),
              );
            }
          }
        }
      }

      await batch.commit();
    } catch (_) {}
  }

  void _listenRequests() {
    _reqSub?.cancel();
    _reqSub = reqRef.snapshots().listen((snap) async {
      Map<String, dynamic>? latestPending;
      Timestamp? latestTs;
      final now = DateTime.now();
      final expiredDocs = <QueryDocumentSnapshot<Map<String, dynamic>>>[];

      for (final doc in snap.docs) {
        final data = doc.data();
        final status = asString(data['status']);
        final expiresAt = data['expiresAt'] as Timestamp?;

        if (status == 'pending' &&
            expiresAt != null &&
            expiresAt.toDate().isBefore(now)) {
          expiredDocs.add(doc);
          continue;
        }

        final toUid = asString(data['toUid']);
        final type = asString(data['type']);

        if (toUid != uid || status != 'pending') continue;
        if (!_canReceiveRequestType(type)) continue;

        if (latestPending == null) {
          latestPending = {...data, '_id': doc.id};
          latestTs = data['createdAt'] as Timestamp?;
        } else {
          final ts = data['createdAt'] as Timestamp?;
          final current = ts?.millisecondsSinceEpoch ?? 0;
          final prev = latestTs?.millisecondsSinceEpoch ?? 0;
          if (current >= prev) {
            latestPending = {...data, '_id': doc.id};
            latestTs = ts;
          }
        }
      }

      if (expiredDocs.isNotEmpty) {
        final batch = FirebaseFirestore.instance.batch();
        for (final doc in expiredDocs) {
          final data = doc.data();
          final type = asString(data['type']);
          final toUid = asString(data['toUid']);
          batch.delete(doc.reference);

          if (toUid.isNotEmpty) {
            final receiverRef =
                FirebaseFirestore.instance.collection('users').doc(toUid);

            if (type == 'audio_call_request' || type == 'video_call_request') {
              batch.set(
                receiverRef,
                {
                  'counters.pendingCallRequests': FieldValue.increment(-1),
                  'updatedAt': FieldValue.serverTimestamp(),
                },
                SetOptions(merge: true),
              );
            } else if (type == 'photo_request') {
              batch.set(
                receiverRef,
                {
                  'counters.pendingImageRequests': FieldValue.increment(-1),
                  'updatedAt': FieldValue.serverTimestamp(),
                },
                SetOptions(merge: true),
              );
            }
          }
        }
        try {
          await batch.commit();
        } catch (_) {}
      }

      if (!mounted) return;

      setState(() {
        _activeBanner = latestPending;
      });

      _bannerTimer?.cancel();
      if (latestPending != null) {
        _bannerTimer = Timer(_requestBannerDuration, () {
          if (!mounted) return;
          setState(() {
            _activeBanner = null;
          });
        });
      }
    }, onError: (e) {
      debugPrint('Request listener error: $e');
    });
  }

  Future<void> _incrementCounter(
    DocumentReference<Map<String, dynamic>> ref,
    String field,
  ) async {
    try {
      await ref.set({
        'counters.$field': FieldValue.increment(1),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (_) {}
  }

  Future<void> _decrementCounter(
    DocumentReference<Map<String, dynamic>> ref,
    String field,
  ) async {
    try {
      await ref.set({
        'counters.$field': FieldValue.increment(-1),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (_) {}
  }

  Future<bool> _deductAndRewardOnAccept({
    required String callerUid,
    required String receiverUid,
    required int cost,
    required String reason,
  }) async {
    final db = FirebaseFirestore.instance;
    final callerRef = db.collection('users').doc(callerUid);
    final receiverRef = db.collection('users').doc(receiverUid);

    final reward = (cost * 0.20).floor();

    final callerHistoryRef = callerRef.collection('walletHistory').doc();
    final receiverHistoryRef = receiverRef.collection('walletHistory').doc();

    try {
      await db.runTransaction((tx) async {
        final callerSnap = await tx.get(callerRef);
        final callerData = callerSnap.data() ?? {};
        final callerBal = asDouble(callerData['silverBalance']);

        if (callerBal < cost) {
          throw Exception('INSUFFICIENT');
        }

        tx.set(
            callerRef,
            {
              'silverBalance': FieldValue.increment(-cost),
              'updatedAt': FieldValue.serverTimestamp(),
            },
            SetOptions(merge: true));

        if (reward > 0) {
          tx.set(
              receiverRef,
              {
                'silverBalance': FieldValue.increment(reward),
                'updatedAt': FieldValue.serverTimestamp(),
              },
              SetOptions(merge: true));
        }

        tx.set(callerHistoryRef, {
          'type': reason,
          'title': reason.toUpperCase(),
          'fromCoin': 'Silver',
          'fromAmount': cost.toDouble(),
          'toCoin': '',
          'toAmount': 0.0,
          'bonusPct': 0.0,
          'meta': {
            'roomId': widget.roomId,
            'otherUid': receiverUid,
          },
          'createdAt': FieldValue.serverTimestamp(),
        });

        if (reward > 0) {
          tx.set(receiverHistoryRef, {
            'type': 'call_earning',
            'title': 'CALL EARNING',
            'fromCoin': '',
            'fromAmount': 0.0,
            'toCoin': 'Silver',
            'toAmount': reward.toDouble(),
            'bonusPct': 0.0,
            'meta': {
              'roomId': widget.roomId,
              'otherUid': callerUid,
              'callType': reason,
            },
            'createdAt': FieldValue.serverTimestamp(),
          });
        }
      });

      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> _acceptRequest(String id) async {
    if (_anyBlocked) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              _blockedByMe ? 'You blocked this user.' : 'You are blocked.'),
        ),
      );
      return;
    }

    if (_acceptBusy) return;
    setState(() => _acceptBusy = true);

    try {
      final snap = await reqRef.doc(id).get();
      final data = snap.data() ?? {};
      final type = asString(data['type']);
      final fromUid = asString(data['fromUid']);
      final toUid = asString(data['toUid']);
      final status = asString(data['status']);
      final expiresAt = data['expiresAt'] as Timestamp?;

      if (toUid != uid || status != 'pending') {
        if (!mounted) return;
        setState(() => _activeBanner = null);
        return;
      }

      if (!_canReceiveRequestType(type)) {
        await reqRef.doc(id).set({
          'status': 'rejected_permission',
          'handledAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));

        if (type == 'audio_call_request' || type == 'video_call_request') {
          await _decrementCounter(meRef, 'pendingCallRequests');
        } else if (type == 'photo_request') {
          await _decrementCounter(meRef, 'pendingImageRequests');
        }

        if (!mounted) return;
        setState(() => _activeBanner = null);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('This request type is disabled in your settings'),
          ),
        );
        return;
      }

      if (expiresAt != null && expiresAt.toDate().isBefore(DateTime.now())) {
        await reqRef.doc(id).delete();

        if (type == 'audio_call_request' || type == 'video_call_request') {
          await _decrementCounter(meRef, 'pendingCallRequests');
        } else if (type == 'photo_request') {
          await _decrementCounter(meRef, 'pendingImageRequests');
        }

        if (!mounted) return;
        setState(() => _activeBanner = null);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Request expired')),
        );
        return;
      }

      int cost = 0;
      String reason = '';

      if (type == 'audio_call_request') {
        cost = 10;
        reason = 'audio_call';
      } else if (type == 'video_call_request') {
        cost = 25;
        reason = 'video_call';
      }

      if (cost > 0) {
        final ok = await _deductAndRewardOnAccept(
          callerUid: fromUid,
          receiverUid: uid,
          cost: cost,
          reason: reason,
        );

        if (!ok) {
          await reqRef.doc(id).set({
            'status': 'rejected_insufficient',
            'handledAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          if (type == 'audio_call_request' || type == 'video_call_request') {
            await _decrementCounter(meRef, 'pendingCallRequests');
          } else if (type == 'photo_request') {
            await _decrementCounter(meRef, 'pendingImageRequests');
          }

          if (!mounted) return;
          setState(() => _activeBanner = null);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Call cannot start. Caller doesn’t have $cost 🥈'),
            ),
          );
          return;
        }
      }

      await reqRef.doc(id).set({
        'status': 'accepted',
        'handledAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (type == 'audio_call_request' || type == 'video_call_request') {
        await _decrementCounter(meRef, 'pendingCallRequests');
      } else if (type == 'photo_request') {
        await _decrementCounter(meRef, 'pendingImageRequests');
      }

      if (!mounted) return;
      setState(() => _activeBanner = null);

      if (type == 'photo_request') {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Image request accepted ✅')),
        );
      } else if (cost > 0) {
        final reward = (cost * 0.20).floor();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Accepted ✅ Caller paid $cost 🥈 • You earned +$reward 🥈',
            ),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Accepted ✅')),
        );
      }
    } finally {
      if (mounted) setState(() => _acceptBusy = false);
    }
  }

  Future<void> _rejectRequest(String id) async {
    final snap = await reqRef.doc(id).get();
    final data = snap.data() ?? {};
    final type = asString(data['type']);
    final toUid = asString(data['toUid']);
    final status = asString(data['status']);

    if (status == 'pending') {
      await reqRef.doc(id).set({
        'status': 'rejected',
        'handledAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (toUid == uid) {
        if (type == 'audio_call_request' || type == 'video_call_request') {
          await _decrementCounter(meRef, 'pendingCallRequests');
        } else if (type == 'photo_request') {
          await _decrementCounter(meRef, 'pendingImageRequests');
        }
      }
    }

    if (!mounted) return;
    setState(() => _activeBanner = null);
  }

  String _requestLabel(String type) {
    if (type == 'photo_request') return 'Photo request';
    if (type == 'audio_call_request') return 'Audio call request';
    if (type == 'video_call_request') return 'Video call request';
    return 'Request';
  }

  Future<bool> _hasActivePendingSameType(String type) async {
    final snap = await reqRef
        .where('fromUid', isEqualTo: uid)
        .where('toUid', isEqualTo: widget.otherUid)
        .where('type', isEqualTo: type)
        .where('status', isEqualTo: 'pending')
        .get();

    final now = DateTime.now();
    for (final doc in snap.docs) {
      final data = doc.data();
      final expiresAt = data['expiresAt'] as Timestamp?;
      if (expiresAt != null && expiresAt.toDate().isAfter(now)) {
        return true;
      }
    }
    return false;
  }

  Future<void> _sendRequestToOther(String type) async {
    if (_anyBlocked) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              _blockedByMe ? 'You blocked this user.' : 'You are blocked.'),
        ),
      );
      return;
    }

    await _cleanupExpiredRequests();

    final alreadyPending = await _hasActivePendingSameType(type);
    if (alreadyPending) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${_requestLabel(type)} already pending. Wait for accept/reject/expiry.',
          ),
        ),
      );
      return;
    }

    bool allowed = true;
    String denyMessage = '';

    if (type == 'photo_request') {
      allowed = _chatAllowImageRequests();
      denyMessage = 'Image requests are disabled for this chat';
    } else if (type == 'audio_call_request') {
      allowed = _chatAllowAudioRequests();
      denyMessage = 'Audio call requests are disabled for this chat';
    } else if (type == 'video_call_request') {
      allowed = _chatAllowVideoRequests();
      denyMessage = 'Video call requests are disabled for this chat';
    }

    if (!allowed) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(denyMessage)),
      );
      return;
    }

    await reqRef.add({
      'fromUid': uid,
      'toUid': widget.otherUid,
      'type': type,
      'status': 'pending',
      'createdAt': FieldValue.serverTimestamp(),
      'expiresAt': Timestamp.fromDate(
        DateTime.now().add(_requestExpiryDuration),
      ),
    });

    if (type == 'audio_call_request' || type == 'video_call_request') {
      await _incrementCounter(otherRef, 'pendingCallRequests');
    } else if (type == 'photo_request') {
      await _incrementCounter(otherRef, 'pendingImageRequests');
    }

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${_requestLabel(type)} sent ✅')),
    );
  }

  Future<void> _openRequestsSheet() async {
    await _cleanupExpiredRequests();

    if (!mounted) return;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFFF7F2FB),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) {
        return SafeArea(
          child: SizedBox(
            height: MediaQuery.of(context).size.height * 0.72,
            child: Column(
              children: [
                const SizedBox(height: 10),
                Container(
                  width: 44,
                  height: 5,
                  decoration: BoxDecoration(
                    color: Colors.black12,
                    borderRadius: BorderRadius.circular(99),
                  ),
                ),
                const SizedBox(height: 14),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      Text(
                        'Requests',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                    stream: reqRef
                        .orderBy('createdAt', descending: true)
                        .snapshots(),
                    builder: (context, snap) {
                      if (!snap.hasData) {
                        return const Center(
                          child: CircularProgressIndicator(),
                        );
                      }

                      final docs = snap.data!.docs.where((doc) {
                        final d = doc.data();
                        final fromUid = asString(d['fromUid']);
                        final toUid = asString(d['toUid']);

                        if (fromUid != widget.otherUid || toUid != uid) {
                          return false;
                        }

                        final expiresAt = d['expiresAt'] as Timestamp?;
                        final status = asString(d['status']);
                        final notExpired = expiresAt == null
                            ? true
                            : expiresAt.toDate().isAfter(DateTime.now());

                        return status == 'pending' && notExpired;
                      }).toList();

                      if (docs.isEmpty) {
                        return const Center(
                          child: Text(
                            'No incoming requests',
                            style: TextStyle(fontWeight: FontWeight.w800),
                          ),
                        );
                      }

                      return ListView.builder(
                        padding: const EdgeInsets.fromLTRB(14, 8, 14, 16),
                        itemCount: docs.length,
                        itemBuilder: (context, i) {
                          final doc = docs[i];
                          final d = doc.data();

                          final type = asString(d['type']);
                          final createdAt = d['createdAt'] as Timestamp?;
                          final expiresAt = d['expiresAt'] as Timestamp?;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(color: Colors.black12),
                              boxShadow: [
                                BoxShadow(
                                  color: const Color(0xFFD8CBEF)
                                      .withValues(alpha: 0.12),
                                  blurRadius: 14,
                                  offset: const Offset(0, 8),
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(
                                      type == 'photo_request'
                                          ? Icons.image_outlined
                                          : (type == 'video_call_request'
                                              ? Icons.videocam_outlined
                                              : Icons.call_outlined),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        _requestLabel(type),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w900,
                                          fontSize: 15,
                                        ),
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 10,
                                        vertical: 5,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.orange.shade50,
                                        borderRadius:
                                            BorderRadius.circular(999),
                                      ),
                                      child: const Text(
                                        'pending',
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w900,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Created: ${_formatFullDateTime(createdAt)}',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: Colors.black54,
                                  ),
                                ),
                                if (expiresAt != null) ...[
                                  const SizedBox(height: 2),
                                  Text(
                                    'Expires: ${_formatFullDateTime(expiresAt)}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: Colors.black54,
                                    ),
                                  ),
                                ],
                                const SizedBox(height: 12),
                                Row(
                                  children: [
                                    Expanded(
                                      child: OutlinedButton(
                                        style: OutlinedButton.styleFrom(
                                          minimumSize: const Size(0, 48),
                                        ),
                                        onPressed: () async {
                                          Navigator.pop(context);
                                          await _rejectRequest(doc.id);
                                        },
                                        child: const Text('Reject'),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: ElevatedButton(
                                        style: ElevatedButton.styleFrom(
                                          minimumSize: const Size(0, 48),
                                        ),
                                        onPressed: () async {
                                          Navigator.pop(context);
                                          await _acceptRequest(doc.id);
                                        },
                                        child: const Text('Accept'),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _sendMessageInternal({
    required String type,
    required String text,
    String? imageUrl,
    String? audioUrl,
    int? audioDurationSec,
    Map<String, dynamic>? replyTo,
  }) async {
    final now = FieldValue.serverTimestamp();

    bool otherOnline = false;
    try {
      final otherSnap = await otherRef.get();
      otherOnline = (otherSnap.data()?['online'] ?? false) == true;
    } catch (_) {}

    final initialDelivered = otherOnline ? [widget.otherUid] : <String>[];

    await msgRef.add({
      'senderId': uid,
      'text': text,
      'type': type,
      'imageUrl': imageUrl ?? '',
      'audioUrl': audioUrl ?? '',
      'audioDurationSec': audioDurationSec ?? 0,
      'replyTo': replyTo,
      'createdAt': now,
      'deletedFor': <String>[],
      'deletedForEveryone': false,
      'deliveredTo': initialDelivered,
      'seenBy': <String>[],
      'reactions': <String, dynamic>{},
    });

    await roomRef.set({
      'lastMessage': switch (type) {
        'image' => '📷 Photo',
        'voice' => '🎤 Voice message',
        'call_log' => text,
        _ => text,
      },
      'lastMessageAt': now,
      'updatedAt': now,
      'lastMessageSenderId': uid,
      'lastMessageType': type,
      'lastMessageDeliveredTo': initialDelivered,
      'lastMessageSeenBy': <String>[],
      'unread.${widget.otherUid}': FieldValue.increment(1),
      'unread.$uid': 0,
    }, SetOptions(merge: true));

    await meRef.set({
      'counters.unreadChats': 0,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (_replyingTo != null && mounted) {
      setState(() => _replyingTo = null);
    }
  }

  Future<void> _send() async {
    if (_anyBlocked) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              _blockedByMe ? 'You blocked this user.' : 'You are blocked.'),
        ),
      );
      return;
    }

    final text = msgCtrl.text.trim();
    if (text.isEmpty || _sendingText) return;

    setState(() => _sendingText = true);

    try {
      await _setTyping(false);
      _typingTimer?.cancel();

      final reply = _replyingTo;
      msgCtrl.clear();

      if (_hasTypedText && mounted) {
        setState(() => _hasTypedText = false);
      }

      await _sendMessageInternal(
        type: 'text',
        text: text,
        replyTo: reply,
      );
    } finally {
      if (mounted) {
        setState(() => _sendingText = false);
        Future.delayed(const Duration(milliseconds: 10), () {
          if (mounted && !_isRecording) {
            _msgFocusNode.requestFocus();
          }
        });
      }
    }
  }

  Future<void> _pickAndSendImageOrRequest() async {
    if (_anyBlocked) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              _blockedByMe ? 'You blocked this user.' : 'You are blocked.'),
        ),
      );
      return;
    }

    if (_isFriends && _meHasEligiblePlan) {
      await _pickAndSendImage();
      return;
    }

    await _sendRequestToOther('photo_request');
  }

  Future<void> _pickAndSendImage() async {
    if (_sendingImage) return;

    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Camera'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Gallery'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    try {
      final picked = await _picker.pickImage(
        source: source,
        imageQuality: 75,
      );
      if (picked == null) return;

      final bytes = await picked.length();
      if (bytes > _maxImageBytes) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Image too large. Please choose under 5 MB.'),
          ),
        );
        return;
      }

      setState(() => _sendingImage = true);

      final file = File(picked.path);
      final ext = picked.name.split('.').last.toLowerCase();
      final safeExt = ext.isEmpty ? 'jpg' : ext;
      final path =
          'chat_uploads/${widget.roomId}/${DateTime.now().millisecondsSinceEpoch}_$uid.$safeExt';

      final ref = FirebaseStorage.instance.ref().child(path);
      await ref.putFile(file);
      final url = await ref.getDownloadURL();

      await _sendMessageInternal(
        type: 'image',
        text: '📷 Photo',
        imageUrl: url,
        replyTo: _replyingTo,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Image sent ✅')),
      );
      _msgFocusNode.requestFocus();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Image send failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _sendingImage = false);
    }
  }

  void _showUpgradeSnack() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Direct media available only after friendship approval + eligible plan 🔒',
        ),
      ),
    );
  }

  Future<void> _startVoiceRecording() async {
    if (_anyBlocked) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              _blockedByMe ? 'You blocked this user.' : 'You are blocked.'),
        ),
      );
      return;
    }

    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Microphone permission denied')),
      );
      return;
    }

    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}_$uid.m4a';

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 128000,
        sampleRate: 44100,
      ),
      path: path,
    );

    if (!mounted) return;
    setState(() {
      _recordingPath = path;
      _isRecording = true;
    });
  }

  Future<void> _stopAndSendVoice() async {
    if (!_isRecording) return;

    final path = await _recorder.stop();
    if (!mounted) return;

    setState(() => _isRecording = false);

    final finalPath = path ?? _recordingPath;
    if (finalPath == null || finalPath.isEmpty) return;

    final file = File(finalPath);
    if (!await file.exists()) return;

    final bytes = await file.length();
    if (!mounted) return;

    if (bytes > _maxAudioBytes) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Voice message too large')),
      );
      return;
    }

    try {
      final storagePath =
          'voice_uploads/${widget.roomId}/${DateTime.now().millisecondsSinceEpoch}_$uid.m4a';
      final ref = FirebaseStorage.instance.ref().child(storagePath);
      await ref.putFile(file);
      final url = await ref.getDownloadURL();

      await _sendMessageInternal(
        type: 'voice',
        text: '🎤 Voice message',
        audioUrl: url,
        audioDurationSec: 0,
        replyTo: _replyingTo,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Voice message sent ✅')),
      );
      _msgFocusNode.requestFocus();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Voice send failed: $e')),
      );
    }
  }

  Future<void> _cancelVoiceRecording() async {
    if (!_isRecording) return;
    await _recorder.stop();
    if (!mounted) return;
    setState(() {
      _isRecording = false;
      _recordingPath = null;
    });
    _msgFocusNode.requestFocus();
  }

  Future<void> _togglePlayAudio(String url) async {
    try {
      if (_playingAudioUrl == url && _audioPlayer.playing) {
        await _audioPlayer.stop();
        if (mounted) setState(() => _playingAudioUrl = null);
        return;
      }

      _playingAudioUrl = url;
      await _audioPlayer.setUrl(url);
      await _audioPlayer.play();
      if (mounted) setState(() {});
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Audio play failed: $e')),
      );
    }
  }

  Future<void> _clearChatForMe() async {
    await myChatPrefsRef.set({
      'clearedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Chat cleared for you ✅')),
    );
  }

  Future<void> _deleteMessageForMe(String messageId) async {
    await msgRef.doc(messageId).set({
      'deletedFor': FieldValue.arrayUnion([uid]),
    }, SetOptions(merge: true));

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Message removed for you ✅')),
    );
  }

  Future<void> _deleteMessageForEveryone(String messageId) async {
    await msgRef.doc(messageId).set({
      'deletedForEveryone': true,
      'deletedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Deleted for everyone ✅')),
    );
  }

  Future<void> _setReaction(String messageId, String emoji) async {
    await msgRef.doc(messageId).set({
      'reactions.$uid': emoji,
    }, SetOptions(merge: true));
  }

  Future<void> _removeReaction(String messageId) async {
    await msgRef.doc(messageId).set({
      'reactions.$uid': FieldValue.delete(),
    }, SetOptions(merge: true));
  }

  Future<void> _openReactionSheet(String messageId) async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (_) => SafeArea(
        child: Wrap(
          children: [
            _reactionTile('❤️'),
            _reactionTile('😍'),
            _reactionTile('😂'),
            _reactionTile('🔥'),
            _reactionTile('👍'),
            _reactionTile('🙏'),
            ListTile(
              leading: const Icon(Icons.remove_circle_outline),
              title: const Text('Remove reaction'),
              onTap: () => Navigator.pop(context, 'remove'),
            ),
          ],
        ),
      ),
    );

    if (choice == null) return;
    if (choice == 'remove') {
      await _removeReaction(messageId);
    } else {
      await _setReaction(messageId, choice);
    }
  }

  Future<void> _showMessageInfo(Map<String, dynamic> m) async {
    final ts = m['createdAt'] as Timestamp?;
    final type = asString(m['type'], def: 'text');
    final text = asString(m['text']);
    final deliveredTo =
        (m['deliveredTo'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final seenBy =
        (m['seenBy'] as List?)?.map((e) => e.toString()).toList() ?? [];

    String status = 'Sent';
    Color dotColor = Colors.black;

    if (seenBy.contains(widget.otherUid)) {
      status = 'Seen';
      dotColor = Colors.green;
    } else if (deliveredTo.contains(widget.otherUid)) {
      status = 'Delivered';
      dotColor = Colors.blue;
    }

    await showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFFF7F2FB),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.black12,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
              const SizedBox(height: 16),
              const Row(
                children: [
                  Text(
                    'Message info',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE7DDF8)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      type == 'image'
                          ? '📷 Photo'
                          : type == 'voice'
                              ? '🎤 Voice message'
                              : text,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        const Text(
                          'Type',
                          style: TextStyle(color: Colors.black54),
                        ),
                        const Spacer(),
                        Text(
                          type,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text(
                          'Sent at',
                          style: TextStyle(color: Colors.black54),
                        ),
                        const Spacer(),
                        Text(
                          _formatFullDateTime(ts),
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text(
                          'Status',
                          style: TextStyle(color: Colors.black54),
                        ),
                        const Spacer(),
                        Container(
                          width: 9,
                          height: 9,
                          decoration: BoxDecoration(
                            color: dotColor,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          status,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _reactionTile(String emoji) {
    return ListTile(
      title: Text(
        emoji,
        style: const TextStyle(fontSize: 24),
        textAlign: TextAlign.center,
      ),
      onTap: () => Navigator.pop(context, emoji),
    );
  }

  Future<void> _blockOrUnblock() async {
    if (_blockedByMe) {
      await roomRef.set({
        'blockedBy.$uid': FieldValue.delete(),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      await meRef.collection('blocks').doc(widget.otherUid).delete();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('User unblocked ✅')),
      );
    } else {
      await roomRef.set({
        'blockedBy.$uid': true,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      await meRef.collection('blocks').doc(widget.otherUid).set({
        'roomId': widget.roomId,
        'blockedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('User blocked ✅')),
      );
    }
  }

  Future<void> _markSeenAndDelivered(
    List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
  ) async {
    if (_markingSeen) return;
    _markingSeen = true;

    try {
      final batch = FirebaseFirestore.instance.batch();
      bool changed = false;

      for (final doc in docs) {
        final m = doc.data();
        final sender = asString(m['senderId']);
        if (sender == uid) continue;

        final deliveredTo =
            (m['deliveredTo'] as List?)?.map((e) => e.toString()).toList() ??
                [];
        final seenBy =
            (m['seenBy'] as List?)?.map((e) => e.toString()).toList() ?? [];

        final updates = <String, dynamic>{};

        if (!deliveredTo.contains(uid)) {
          updates['deliveredTo'] = FieldValue.arrayUnion([uid]);
        }
        if (!seenBy.contains(uid)) {
          updates['seenBy'] = FieldValue.arrayUnion([uid]);
        }

        if (updates.isNotEmpty) {
          batch.set(doc.reference, updates, SetOptions(merge: true));
          changed = true;
        }
      }

      if (changed) {
        await batch.commit();
      }

      await roomRef.set({
        'lastMessageDeliveredTo': FieldValue.arrayUnion([uid]),
        'lastMessageSeenBy': FieldValue.arrayUnion([uid]),
        'unread.$uid': 0,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      await meRef.set({
        'counters.unreadChats': 0,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } finally {
      _markingSeen = false;
    }
  }

  String _fmtTs(Timestamp? t) {
    if (t == null) return '';
    final dt = t.toDate();
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    return '$hh:$mm';
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  String _formatDateChip(Timestamp? t) {
    if (t == null) return '';
    final dt = t.toDate();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(dt.year, dt.month, dt.day);

    if (d == today) return 'Today';
    if (d == today.subtract(const Duration(days: 1))) return 'Yesterday';

    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${dt.day} ${months[dt.month - 1]} ${dt.year}';
  }

  String _formatFullDateTime(Timestamp? t) {
    if (t == null) return '';
    final dt = t.toDate();
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    return '${dt.day} ${months[dt.month - 1]} ${dt.year}, $hh:$mm';
  }

  String _formatLastSeenLine(Timestamp? t) {
    if (t == null) return 'last seen recently';

    final dt = t.toDate();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(dt.year, dt.month, dt.day);
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');

    if (d == today) return 'last seen today at $hh:$mm';
    if (d == today.subtract(const Duration(days: 1))) {
      return 'last seen yesterday at $hh:$mm';
    }

    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return 'last seen ${dt.day} ${months[dt.month - 1]} at $hh:$mm';
  }

  Widget _messageStatus(Map<String, dynamic> m) {
    final deliveredTo =
        (m['deliveredTo'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final seenBy =
        (m['seenBy'] as List?)?.map((e) => e.toString()).toList() ?? [];

    Color color = Colors.black;
    if (seenBy.contains(widget.otherUid)) {
      color = Colors.green;
    } else if (deliveredTo.contains(widget.otherUid)) {
      color = Colors.blue;
    }

    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
    );
  }

  Widget _buildReactionBar(Map<String, dynamic> m) {
    final raw = m['reactions'];
    if (raw is! Map) return const SizedBox.shrink();

    final map = raw.map((k, v) => MapEntry(k.toString(), v.toString()));
    if (map.isEmpty) return const SizedBox.shrink();

    final counts = <String, int>{};
    for (final emoji in map.values) {
      counts[emoji] = (counts[emoji] ?? 0) + 1;
    }

    return Container(
      margin: const EdgeInsets.only(top: 3),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.black12),
      ),
      child: Wrap(
        spacing: 6,
        children: counts.entries
            .map(
              (e) => Text(
                '${e.key} ${e.value}',
                style:
                    const TextStyle(fontSize: 10, fontWeight: FontWeight.w700),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _topBanner() {
    final b = _activeBanner;
    if (b == null) return const SizedBox.shrink();

    final id = asString(b['_id']);
    final type = asString(b['type']);

    String label = 'Request';
    if (type == 'photo_request') label = 'Image request';
    if (type == 'video_call_request') label = 'Video call request (25 🥈)';
    if (type == 'audio_call_request') label = 'Audio call request (10 🥈)';

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.amber.shade50,
            Colors.orange.shade50,
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.amber.shade200),
      ),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                alignment: Alignment.center,
                child: const Icon(Icons.notifications_active_outlined),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    '$label received',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(0, 46),
                    side: BorderSide(color: Colors.orange.shade200),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  onPressed: _acceptBusy ? null : () => _rejectRequest(id),
                  child: const Text('Reject'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(0, 46),
                    elevation: 0,
                    backgroundColor: const Color(0xFF8D67FF),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  onPressed: _acceptBusy ? null : () => _acceptRequest(id),
                  child: Text(_acceptBusy ? '...' : 'Accept'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _blockedBanner() {
    if (_blockedByMe) {
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: Colors.red.shade50,
          border: Border.all(color: Colors.red.shade200),
        ),
        child: const Text(
          'You blocked this user. You cannot send messages or requests.',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      );
    }

    if (_blockedByOther) {
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: Colors.orange.shade50,
          border: Border.all(color: Colors.orange.shade200),
        ),
        child: const Text(
          'You are blocked. Messaging and media are restricted.',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _limitedChatBanner() {
    if (_anyBlocked) return const SizedBox.shrink();

    if (!_isFriends && !_meHasEligiblePlan) {
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: Colors.blue.shade50,
          border: Border.all(color: Colors.blue.shade200),
        ),
        child: const Text(
          'Image and direct premium features may be limited in this chat until friendship/eligible plan is active.',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _replyPreview() {
    if (_replyingTo == null) return const SizedBox.shrink();

    final senderId = asString(_replyingTo!['senderId']);
    final senderName = senderId == uid ? 'You' : 'Reply';
    final type = asString(_replyingTo!['type'], def: 'text');
    final text = type == 'image'
        ? '📷 Photo'
        : type == 'voice'
            ? '🎤 Voice message'
            : asString(_replyingTo!['text']);

    return Container(
      margin: const EdgeInsets.fromLTRB(10, 0, 10, 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.deepPurple.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.deepPurple.withValues(alpha: 0.18)),
      ),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 38,
            decoration: BoxDecoration(
              color: Colors.deepPurple,
              borderRadius: BorderRadius.circular(10),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  senderName,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                    color: Colors.deepPurple,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  text,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: () => setState(() => _replyingTo = null),
            icon: const Icon(Icons.close),
          ),
        ],
      ),
    );
  }

  Widget _typingLine(bool online, Timestamp? lastSeen) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: roomRef.snapshots(),
      builder: (context, snap) {
        final typingRaw = snap.data?.data()?['typing'];
        final typingMap = typingRaw is Map
            ? typingRaw.map((k, v) => MapEntry(k.toString(), v))
            : <String, dynamic>{};

        final otherTyping = typingMap[widget.otherUid] == true;

        return Text(
          otherTyping
              ? 'typing...'
              : (online ? 'online' : _formatLastSeenLine(lastSeen)),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 12,
            color: otherTyping ? Colors.green : Colors.black54,
            fontWeight: otherTyping ? FontWeight.w700 : FontWeight.w500,
          ),
        );
      },
    );
  }

  void _openImagePreview(String url) {
    showDialog(
      context: context,
      builder: (_) => Dialog(
        insetPadding: const EdgeInsets.all(12),
        child: InteractiveViewer(
          minScale: 1,
          maxScale: 4,
          child: Image.network(
            url,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => const SizedBox(
              height: 240,
              child: Center(child: Text('Image failed to load')),
            ),
          ),
        ),
      ),
    );
  }

  Widget _replySnippet(Map<String, dynamic>? replyTo) {
    if (replyTo == null) return const SizedBox.shrink();

    final senderId = asString(replyTo['senderId']);
    final senderName = senderId == uid ? 'You' : 'Reply';
    final type = asString(replyTo['type'], def: 'text');
    final text = type == 'image'
        ? '📷 Photo'
        : type == 'voice'
            ? '🎤 Voice message'
            : asString(replyTo['text']);

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            senderName,
            style: const TextStyle(
              fontSize: 10.5,
              fontWeight: FontWeight.w800,
              color: Colors.deepPurple,
            ),
          ),
          Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 10.5),
          ),
        ],
      ),
    );
  }

  Widget _buildVoiceBubble(Map<String, dynamic> m) {
    final audioUrl = asString(m['audioUrl']);
    final durationSec = asInt(m['audioDurationSec']);
    final mins = durationSec ~/ 60;
    final secs = durationSec % 60;
    final durationLabel =
        '${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';

    final playingThis = _playingAudioUrl == audioUrl && _audioPlayer.playing;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
          onPressed: () => _togglePlayAudio(audioUrl),
          icon: Icon(
            playingThis ? Icons.stop_circle : Icons.play_circle_fill,
            size: 24,
          ),
        ),
        const SizedBox(width: 4),
        Container(
          width: 96,
          height: 5,
          decoration: BoxDecoration(
            color: Colors.grey.shade300,
            borderRadius: BorderRadius.circular(999),
          ),
        ),
        const SizedBox(width: 6),
        Text(
          durationSec > 0 ? durationLabel : 'Voice',
          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
        ),
      ],
    );
  }

  Widget _buildDateChip(Timestamp? ts) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.88),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: const Color(0xFFE6DDF7)),
          ),
          child: Text(
            _formatDateChip(ts),
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              color: Color(0xFF5B4D79),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildChatWallpaper() {
    return IgnorePointer(
      child: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFFFBF7FF),
                  Color(0xFFF7F2FB),
                  Color(0xFFFDFBFF),
                ],
              ),
            ),
          ),
          Positioned(
            top: -30,
            right: -20,
            child: Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF8D67FF).withValues(alpha: 0.05),
              ),
            ),
          ),
          Positioned(
            top: 180,
            left: -40,
            child: Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFFFF5DA2).withValues(alpha: 0.045),
              ),
            ),
          ),
          Positioned(
            bottom: 140,
            right: -30,
            child: Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF8D67FF).withValues(alpha: 0.04),
              ),
            ),
          ),
          Positioned.fill(
            child: Opacity(
              opacity: 0.035,
              child: CustomPaint(
                painter: _ChatPatternPainter(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(
    String messageId,
    Map<String, dynamic> m,
    Timestamp? clearedAt,
  ) {
    final sender = asString(m['senderId']);
    final text = asString(m['text']);
    final type = asString(m['type'], def: 'text');
    final imageUrl = asString(m['imageUrl']);
    final ts = m['createdAt'] as Timestamp?;
    final isMe = sender == uid;
    final deletedForEveryone = m['deletedForEveryone'] == true;
    final seenBy =
        (m['seenBy'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final replyTo = m['replyTo'] is Map
        ? (m['replyTo'] as Map).map((k, v) => MapEntry(k.toString(), v))
        : null;

    if (clearedAt != null && ts != null) {
      if (ts.toDate().isBefore(clearedAt.toDate())) {
        return const SizedBox.shrink();
      }
    }

    final bubble = ConstrainedBox(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.of(context).size.width * 0.72,
      ),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 2),
        padding: type == 'image'
            ? const EdgeInsets.all(5)
            : const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: isMe ? const Color(0xFFEAFBF2) : const Color(0xFFF2EEFF),
          border: Border.all(
            color: isMe ? const Color(0xFFC7EED7) : const Color(0xFFE0D6FF),
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFD8CBEF).withValues(alpha: 0.08),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            _replySnippet(replyTo),
            if (deletedForEveryone)
              const Text(
                'This message was deleted',
                style: TextStyle(
                  fontStyle: FontStyle.italic,
                  color: Colors.grey,
                  fontSize: 12,
                ),
              )
            else if (type == 'image' && imageUrl.isNotEmpty)
              GestureDetector(
                onTap: () => _openImagePreview(imageUrl),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      maxWidth: 220,
                      maxHeight: 260,
                    ),
                    child: Image.network(
                      imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        width: 180,
                        height: 120,
                        alignment: Alignment.center,
                        color: Colors.black12,
                        child: const Text('Image failed'),
                      ),
                    ),
                  ),
                ),
              )
            else if (type == 'voice')
              _buildVoiceBubble(m)
            else if (type == 'call_log')
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    text,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                  if (asString(m['durationLabel']).isNotEmpty)
                    Text(
                      asString(m['durationLabel']),
                      style: const TextStyle(fontSize: 11.5),
                    ),
                  if (asString(m['costLabel']).isNotEmpty)
                    Text(
                      asString(m['costLabel']),
                      style: const TextStyle(fontSize: 11.5),
                    ),
                ],
              )
            else
              Text(
                text,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  height: 1.15,
                ),
              ),
            const SizedBox(height: 3),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _fmtTs(ts),
                  style: const TextStyle(fontSize: 9.5),
                ),
                if (isMe) ...[
                  const SizedBox(width: 5),
                  _messageStatus(m),
                ],
              ],
            ),
            _buildReactionBar(m),
          ],
        ),
      ),
    );

    return Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onTap: () async {
          if (!mounted) return;

          final items = <Widget>[
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('Info'),
              onTap: () => Navigator.pop(context, 'info'),
            ),
            ListTile(
              leading: const Icon(Icons.reply),
              title: const Text('Reply'),
              onTap: () => Navigator.pop(context, 'reply'),
            ),
            ListTile(
              leading: const Icon(Icons.emoji_emotions_outlined),
              title: const Text('React'),
              onTap: () => Navigator.pop(context, 'react'),
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline),
              title: const Text('Remove for me'),
              onTap: () => Navigator.pop(context, 'deleteForMe'),
            ),
          ];

          if (isMe &&
              !deletedForEveryone &&
              !seenBy.contains(widget.otherUid)) {
            items.add(
              ListTile(
                leading: const Icon(Icons.delete_forever_outlined),
                title: const Text('Delete for everyone'),
                onTap: () => Navigator.pop(context, 'deleteForEveryone'),
              ),
            );
          }

          final choice = await showModalBottomSheet<String>(
            context: context,
            builder: (_) => SafeArea(
              child: Column(mainAxisSize: MainAxisSize.min, children: items),
            ),
          );

          if (choice == 'deleteForMe') {
            await _deleteMessageForMe(messageId);
          } else if (choice == 'deleteForEveryone') {
            await _deleteMessageForEveryone(messageId);
          } else if (choice == 'reply') {
            setState(() {
              _replyingTo = {
                'messageId': messageId,
                'senderId': sender,
                'text': text,
                'type': type,
              };
            });
          } else if (choice == 'react') {
            await _openReactionSheet(messageId);
          } else if (choice == 'info') {
            await _showMessageInfo(m);
          }
        },
        onHorizontalDragEnd: (_) {
          setState(() {
            _replyingTo = {
              'messageId': messageId,
              'senderId': sender,
              'text': text,
              'type': type,
            };
          });
        },
        child: bubble,
      ),
    );
  }

  Future<void> _addCallLog({
    required String callType,
    required int durationSeconds,
    required int cost,
  }) async {
    final mins = durationSeconds ~/ 60;
    final secs = durationSeconds % 60;
    final durationLabel =
        'Duration ${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
    final costLabel = 'Cost $cost 🥈';
    final title = callType == 'video' ? '🎥 Video Call' : '📞 Audio Call';

    await _sendMessageInternal(
      type: 'call_log',
      text: title,
    );

    final latest =
        await msgRef.orderBy('createdAt', descending: true).limit(1).get();
    if (latest.docs.isNotEmpty) {
      await latest.docs.first.reference.set({
        'type': 'call_log',
        'durationLabel': durationLabel,
        'costLabel': costLabel,
      }, SetOptions(merge: true));
    }
  }

  @override
  Widget build(BuildContext context) {
    final messagesStream = msgRef
        .orderBy('createdAt', descending: true)
        .limit(_pageSize)
        .snapshots();

    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: otherRef.snapshots(),
      builder: (context, os) {
        final other = os.data?.data() ?? {};
        final rawName = asString(other['displayName'], def: 'User');
        final name = rawName.isEmpty ? 'User' : rawName;
        final photo =
            asString(other['photoUrl'] ?? other['profilePhoto'], def: '');
        final online = (other['online'] ?? false) == true;
        final lastSeen = other['lastSeenAt'] as Timestamp?;

        return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
          stream: myChatPrefsRef.snapshots(),
          builder: (context, prefsSnap) {
            final prefs = prefsSnap.data?.data() ?? {};
            final clearedAt = prefs['clearedAt'] as Timestamp?;

            return Scaffold(
              backgroundColor: const Color(0xFFF7F2FB),
              appBar: AppBar(
                titleSpacing: 0,
                toolbarHeight: 62,
                backgroundColor: const Color(0xFFF7F2FB),
                elevation: 0,
                title: _searchMode
                    ? TextField(
                        autofocus: true,
                        onChanged: (v) => setState(
                            () => _searchText = v.trim().toLowerCase()),
                        decoration: const InputDecoration(
                          hintText: 'Search chat',
                          border: InputBorder.none,
                          isDense: true,
                        ),
                      )
                    : Row(
                        children: [
                          GestureDetector(
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) =>
                                      UserProfilePage(userId: widget.otherUid),
                                ),
                              );
                            },
                            child: CircleAvatar(
                              radius: 18,
                              backgroundImage:
                                  photo.isEmpty ? null : NetworkImage(photo),
                              child: photo.isEmpty
                                  ? const Icon(Icons.person, size: 18)
                                  : null,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: GestureDetector(
                              behavior: HitTestBehavior.opaque,
                              onTap: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => UserProfilePage(
                                        userId: widget.otherUid),
                                  ),
                                );
                              },
                              child: SizedBox(
                                height: 40,
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      name,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.w900,
                                      ),
                                    ),
                                    const SizedBox(height: 1),
                                    _typingLine(online, lastSeen),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                actions: [
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    constraints:
                        const BoxConstraints(minWidth: 38, minHeight: 38),
                    onPressed: () {
                      setState(() {
                        _searchMode = !_searchMode;
                        if (!_searchMode) _searchText = '';
                      });
                    },
                    icon: Icon(_searchMode ? Icons.close : Icons.search,
                        size: 21),
                  ),
                  if (!_searchMode) ...[
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      constraints:
                          const BoxConstraints(minWidth: 38, minHeight: 38),
                      tooltip: 'Audio call request',
                      onPressed: _anyBlocked
                          ? null
                          : () => _sendRequestToOther('audio_call_request'),
                      icon: const Icon(Icons.call, size: 21),
                    ),
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      constraints:
                          const BoxConstraints(minWidth: 38, minHeight: 38),
                      tooltip: 'Video call request',
                      onPressed: _anyBlocked
                          ? null
                          : () => _sendRequestToOther('video_call_request'),
                      icon: const Icon(Icons.videocam, size: 21),
                    ),
                    PopupMenuButton<String>(
                      padding: EdgeInsets.zero,
                      constraints:
                          const BoxConstraints(minWidth: 38, minHeight: 38),
                      onSelected: (v) async {
                        if (v == 'requests') {
                          await _openRequestsSheet();
                        } else if (v == 'settings') {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => ChatRoomSettingsPage(
                                roomId: widget.roomId,
                                otherUid: widget.otherUid,
                              ),
                            ),
                          );
                        } else if (v == 'blockToggle') {
                          await _blockOrUnblock();
                        } else if (v == 'report') {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) =>
                                  ReportPage(targetUid: widget.otherUid),
                            ),
                          );
                        } else if (v == 'rules') {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const RulesPage(),
                            ),
                          );
                        }
                      },
                      itemBuilder: (_) => [
                        const PopupMenuItem(
                          value: 'requests',
                          child: Text('Requests'),
                        ),
                        const PopupMenuItem(
                          value: 'settings',
                          child: Text('Settings'),
                        ),
                        PopupMenuItem(
                          value: 'blockToggle',
                          child: Text(_blockedByMe ? 'Unblock' : 'Block'),
                        ),
                        const PopupMenuItem(
                          value: 'report',
                          child: Text('Report'),
                        ),
                        const PopupMenuItem(
                          value: 'rules',
                          child: Text('Rules'),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
              body: Stack(
                children: [
                  _buildChatWallpaper(),
                  Column(
                    children: [
                      _topBanner(),
                      _blockedBanner(),
                      _limitedChatBanner(),
                      _replyPreview(),
                      if (_isRecording)
                        Container(
                          width: double.infinity,
                          margin: const EdgeInsets.fromLTRB(10, 0, 10, 6),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: Colors.red.shade200),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.mic, color: Colors.red),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Recording voice message...',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(fontWeight: FontWeight.w900),
                                ),
                              ),
                            ],
                          ),
                        ),
                      Expanded(
                        child:
                            StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                          stream: messagesStream,
                          builder: (context, snap) {
                            if (!snap.hasData) {
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            }

                            var docs = snap.data!.docs;

                            if (_searchText.isNotEmpty) {
                              docs = docs.where((doc) {
                                final m = doc.data();
                                final text = asString(m['text']).toLowerCase();
                                final type = asString(m['type']).toLowerCase();
                                final replyText = m['replyTo'] is Map
                                    ? asString((m['replyTo'] as Map)['text'])
                                        .toLowerCase()
                                    : '';
                                return text.contains(_searchText) ||
                                    type.contains(_searchText) ||
                                    replyText.contains(_searchText);
                              }).toList();
                            }

                            _scheduleMarkSeen(docs);

                            return ListView.builder(
                              controller: scrollCtrl,
                              reverse: true,
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 10,
                              ),
                              itemCount: docs.length,
                              itemBuilder: (context, i) {
                                final doc = docs[i];
                                final m = doc.data();
                                final deletedFor = (m['deletedFor'] as List?)
                                        ?.map((e) => e.toString())
                                        .toList() ??
                                    [];

                                if (deletedFor.contains(uid)) {
                                  return const SizedBox.shrink();
                                }

                                final ts = m['createdAt'] as Timestamp?;
                                bool showDateChip = false;

                                if (i == docs.length - 1) {
                                  showDateChip = true;
                                } else {
                                  final nextTs = docs[i + 1].data()['createdAt']
                                      as Timestamp?;
                                  final currentDate = ts?.toDate();
                                  final nextDate = nextTs?.toDate();
                                  if (currentDate != null && nextDate != null) {
                                    showDateChip =
                                        !_isSameDay(currentDate, nextDate);
                                  }
                                }

                                return Column(
                                  children: [
                                    if (showDateChip) _buildDateChip(ts),
                                    _buildMessageBubble(doc.id, m, clearedAt),
                                  ],
                                );
                              },
                            );
                          },
                        ),
                      ),
                      SafeArea(
                        top: false,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(8, 6, 8, 10),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withValues(alpha: 0.98),
                                    borderRadius: BorderRadius.circular(28),
                                    border: Border.all(
                                      color: const Color(0xFFE5D8FA),
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black
                                            .withValues(alpha: 0.04),
                                        blurRadius: 10,
                                        offset: const Offset(0, 4),
                                      ),
                                    ],
                                  ),
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      IconButton(
                                        tooltip: 'Colors',
                                        visualDensity: VisualDensity.compact,
                                        onPressed: _anyBlocked
                                            ? null
                                            : () {
                                                ScaffoldMessenger.of(context)
                                                    .showSnackBar(
                                                  const SnackBar(
                                                    content:
                                                        Text('Coming soon'),
                                                  ),
                                                );
                                                _msgFocusNode.requestFocus();
                                              },
                                        icon: Icon(
                                          Icons.palette_outlined,
                                          color: Colors.grey.shade600,
                                        ),
                                      ),
                                      Expanded(
                                        child: ConstrainedBox(
                                          constraints: const BoxConstraints(
                                            minHeight: 40,
                                            maxHeight: 120,
                                          ),
                                          child: TextField(
                                            key: _composerFieldKey,
                                            controller: msgCtrl,
                                            focusNode: _msgFocusNode,
                                            enabled:
                                                !_anyBlocked && !_isRecording,
                                            minLines: 1,
                                            maxLines: 5,
                                            textCapitalization:
                                                TextCapitalization.sentences,
                                            keyboardType:
                                                TextInputType.multiline,
                                            textInputAction:
                                                TextInputAction.newline,
                                            onChanged: _onTypingChanged,
                                            decoration: InputDecoration(
                                              hintText: _anyBlocked
                                                  ? (_blockedByMe
                                                      ? 'You blocked this user'
                                                      : 'You are blocked')
                                                  : 'Message',
                                              border: InputBorder.none,
                                              isDense: true,
                                              contentPadding:
                                                  const EdgeInsets.symmetric(
                                                horizontal: 2,
                                                vertical: 10,
                                              ),
                                            ),
                                          ),
                                        ),
                                      ),
                                      if (!_hasTypedText)
                                        IconButton(
                                          tooltip: _sendingImage
                                              ? 'Sending...'
                                              : 'Camera',
                                          visualDensity: VisualDensity.compact,
                                          onPressed:
                                              (_anyBlocked || _sendingImage)
                                                  ? null
                                                  : _pickAndSendImageOrRequest,
                                          icon: Icon(
                                            Icons.camera_alt_outlined,
                                            color: _anyBlocked
                                                ? Colors.grey.shade400
                                                : Colors.grey.shade700,
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              SizedBox(
                                width: 48,
                                height: 48,
                                child: DecoratedBox(
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: (_hasTypedText ||
                                            _sendingText ||
                                            !_isRecording)
                                        ? const LinearGradient(
                                            colors: [
                                              Color(0xFF8D67FF),
                                              Color(0xFFFF5DA2),
                                            ],
                                          )
                                        : null,
                                    color: _isRecording ? Colors.red : null,
                                  ),
                                  child: Material(
                                    color: Colors.transparent,
                                    child: InkWell(
                                      customBorder: const CircleBorder(),
                                      onTap: (_anyBlocked || _sendingText)
                                          ? null
                                          : () async {
                                              if (_hasTypedText) {
                                                await _send();
                                                return;
                                              }

                                              if (_isRecording) {
                                                await _stopAndSendVoice();
                                                if (mounted) {
                                                  _msgFocusNode.requestFocus();
                                                }
                                              } else {
                                                await _startVoiceRecording();
                                              }
                                            },
                                      child: Center(
                                        child: _sendingText
                                            ? const SizedBox(
                                                width: 18,
                                                height: 18,
                                                child:
                                                    CircularProgressIndicator(
                                                  strokeWidth: 2,
                                                  color: Colors.white,
                                                ),
                                              )
                                            : Icon(
                                                _hasTypedText
                                                    ? Icons.send_rounded
                                                    : (_isRecording
                                                        ? Icons.stop
                                                        : Icons.mic),
                                                color: Colors.white,
                                                size: 22,
                                              ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              if (_isRecording) ...[
                                const SizedBox(width: 6),
                                IconButton(
                                  tooltip: 'Cancel recording',
                                  onPressed: _cancelVoiceRecording,
                                  icon: const Icon(Icons.close),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _ChatPatternPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0
      ..color = const Color(0xFF8D67FF).withValues(alpha: 0.35);

    const gap = 42.0;

    for (double x = -gap; x < size.width + gap; x += gap) {
      for (double y = -gap; y < size.height + gap; y += gap) {
        canvas.drawCircle(Offset(x, y), 8, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
