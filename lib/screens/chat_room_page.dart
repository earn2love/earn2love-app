import 'dart:async';
import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../chat/controllers/chat_pagination_controller.dart';
import '../chat/services/chat_references.dart';
import '../chat/services/message_service.dart';
import '../chat/services/presence_service.dart';
import '../chat/services/typing_service.dart';
import '../chat/widgets/message_bubble.dart';
import '../chat/widgets/message_input.dart';
import '../chat/widgets/message_list.dart';
import '../chat/widgets/message_status_ticks.dart';
import '../chat/widgets/reply_banner.dart';
import '../chat/widgets/typing_indicator.dart';
import '../chat/widgets/voice_message_player.dart';
import '../calls/models/call_session.dart';
import '../calls/screens/audio_call_page.dart';
import '../calls/screens/video_call_page.dart';
import '../calls/services/agora_service.dart';
import '../calls/services/call_service.dart';
import '../ai/widgets/meera_writing_assistant_sheet.dart';

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
  late final MessageService _messageService;
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
  Timer? _recordingTimer;

  Map<String, dynamic>? _activeBanner;
  Map<String, dynamic>? _replyingTo;

  bool _sendingImage = false;
  bool _sendingText = false;
  bool _acceptBusy = false;
  bool _markingSeen = false;
  bool _isRecording = false;
  bool _recordingBusy = false;
  bool _searchMode = false;
  bool _hasTypedText = false;
  bool _meeraAssistBusy = false;

  String _searchText = '';
  String? _recordingPath;
  String? _playingAudioUrl;
  int _recordingElapsedSeconds = 0;
  String _lastMarkSeenSignature = '';

  int _audioCallPrice = 10;
  int _videoCallPrice = 25;
  bool _callsEnabled = true;

  late final ChatPaginationController _paginationController;
  static const int _maxImageBytes = 5 * 1024 * 1024;
  static const int _maxAudioBytes = 10 * 1024 * 1024;

  static const Duration _requestBannerDuration = Duration(seconds: 20);
  static const Duration _requestExpiryDuration = Duration(hours: 24);

  bool _meHasEligiblePlan = false;
  bool _blockedByMe = false;
  bool _blockedByOther = false;
  bool _otherTyping = false;
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
  // ignore: unused_element
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
    _paginationController = ChatPaginationController(
      messagesReference: _chatReferences.messages,
      pageSize: 30,
    )..start();

    _messageService = MessageService(
      firestore: FirebaseFirestore.instance,
      currentUid: uid,
      otherUid: widget.otherUid,
      currentUserReference: _chatReferences.currentUser,
      otherUserReference: _chatReferences.otherUser,
      roomReference: _chatReferences.room,
      messagesReference: _chatReferences.messages,
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
    unawaited(_loadCallPricing());
    _listenMyPrefs();
    _listenRequests();
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

    _audioPlayerStateSub = _audioPlayer.playerStateStream.listen((state) {
      if (state.processingState == ProcessingState.completed) {
        _audioPlayer.seek(Duration.zero);
        _audioPlayer.pause();

        if (mounted) {
          setState(() => _playingAudioUrl = null);
        }
        return;
      }

      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _setOnline(false);
    _bannerTimer?.cancel();
    _typingTimer?.cancel();
    _recordingTimer?.cancel();
    _meSub?.cancel();
    _roomSub?.cancel();
    _friendSub?.cancel();
    _prefsSub?.cancel();
    _reqSub?.cancel();
    _audioPlayerStateSub?.cancel();
    _paginationController.dispose();
    msgCtrl.dispose();
    _msgFocusNode.dispose();
    scrollCtrl.dispose();
    _audioPlayer.dispose();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _loadCallPricing() async {
    try {
      final config = await CallService().getCallConfig();

      if (!mounted) return;

      setState(() {
        _audioCallPrice =
            config.audioCallerPerMinute > 0 ? config.audioCallerPerMinute : 10;

        _videoCallPrice =
            config.videoCallerPerMinute > 0 ? config.videoCallerPerMinute : 25;

        _callsEnabled = config.enabled;
      });
    } catch (error) {
      debugPrint(
        'Call configuration load failed: $error',
      );
    }
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

  // ignore: unused_element
  bool _chatReadReceiptsEnabled() {
    if (_myChatPrefs.containsKey('readReceipts')) {
      return asBool(_myChatPrefs['readReceipts'], def: true);
    }
    return _globalReadReceipts();
  }

  // ignore: unused_element
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

  // ignore: unused_element
  String _blockedComposerHint() {
    if (_blockedByMe) return 'You blocked this user';
    if (_blockedByOther) return 'You cannot send messages to this user';
    return 'Message';
  }

  // ignore: unused_element
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

  // ignore: unused_element
  Future<void> _openReportPage() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ReportPage(targetUid: widget.otherUid),
      ),
    );
  }

  // ignore: unused_element
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
      _paginationController.loadOlder();
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
      final data = snap.data() ?? <String, dynamic>{};

      final blockedBy = asMap(data['blockedBy']);
      final typing = asMap(data['typing']);

      final byMe = blockedBy[uid] == true;
      final byOther = blockedBy[widget.otherUid] == true;
      final otherTyping = typing[widget.otherUid] == true;

      if (!mounted) return;

      if (byMe != _blockedByMe ||
          byOther != _blockedByOther ||
          otherTyping != _otherTyping) {
        setState(() {
          _blockedByMe = byMe;
          _blockedByOther = byOther;
          _otherTyping = otherTyping;
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

  Future<Map<String, String>> _loadCallUserIdentity(
    String userId,
  ) async {
    try {
      final snapshot = await FirebaseFirestore.instance
          .collection('users')
          .doc(userId)
          .get();

      final data = snapshot.data() ?? <String, dynamic>{};

      final rawName = asString(
        data['displayName'] ?? data['name'],
        def: 'User',
      );

      final photo = asString(
        data['photoUrl'] ?? data['profilePhoto'],
      );

      return <String, String>{
        'name': rawName.isEmpty ? 'User' : rawName,
        'photo': photo,
      };
    } catch (_) {
      return const <String, String>{
        'name': 'User',
        'photo': '',
      };
    }
  }

  Future<void> _openRealAudioCall(
    CallSession session,
  ) async {
    if (!mounted) return;

    final remoteUid = session.isCaller ? session.calleeUid : session.callerUid;

    final identity = await _loadCallUserIdentity(remoteUid);

    if (!mounted) return;

    final duration = await Navigator.of(context).push<int>(
      MaterialPageRoute<int>(
        builder: (_) => AudioCallPage(
          session: session,
          otherName: identity['name'] ?? 'User',
          otherPhotoUrl: identity['photo'] ?? '',
          callService: CallService(),
          agoraService: AgoraService(),
        ),
      ),
    );

    if (!mounted || duration == null) return;

    try {
      final callSnapshot = await FirebaseFirestore.instance
          .collection('calls')
          .doc(session.callId)
          .get();

      final callData = callSnapshot.data() ?? <String, dynamic>{};

      final storedDuration = asInt(callData['durationSeconds']);

      final charge = session.isCaller ? asInt(callData['charge']) : 0;

      await _addCallLog(
        callType: 'audio',
        durationSeconds: storedDuration > 0 ? storedDuration : duration,
        cost: charge,
      );
    } catch (error) {
      debugPrint('Audio call log creation failed: $error');
    }
  }

  Future<void> _openRealVideoCall(
    CallSession session,
  ) async {
    if (!mounted) return;

    final remoteUid = session.isCaller ? session.calleeUid : session.callerUid;

    final identity = await _loadCallUserIdentity(remoteUid);

    if (!mounted) return;

    final duration = await Navigator.of(context).push<int>(
      MaterialPageRoute<int>(
        builder: (_) => VideoCallPage(
          session: session,
          otherName: identity['name'] ?? 'User',
          otherPhotoUrl: identity['photo'] ?? '',
          callService: CallService(),
          agoraService: AgoraService(),
        ),
      ),
    );

    if (!mounted || duration == null) return;

    try {
      final callSnapshot = await FirebaseFirestore.instance
          .collection('calls')
          .doc(session.callId)
          .get();

      final callData = callSnapshot.data() ?? <String, dynamic>{};

      final storedDuration = asInt(callData['durationSeconds']);

      final charge = session.isCaller ? asInt(callData['charge']) : 0;

      await _addCallLog(
        callType: 'video',
        durationSeconds: storedDuration > 0 ? storedDuration : duration,
        cost: charge,
      );
    } catch (error) {
      debugPrint('Video call log creation failed: $error');
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

      if (type == 'audio_call_request') {
        final callId = asString(data['callId']);

        if (callId.isEmpty) {
          await reqRef.doc(id).set({
            'status': 'rejected_invalid_call',
            'handledAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _decrementCounter(
            meRef,
            'pendingCallRequests',
          );

          if (!mounted) return;

          setState(() => _activeBanner = null);

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'This audio call request is invalid.',
              ),
            ),
          );
          return;
        }

        try {
          final session = await CallService().acceptCall(
            callId: callId,
          );

          await reqRef.doc(id).set({
            'status': 'accepted',
            'handledAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _decrementCounter(
            meRef,
            'pendingCallRequests',
          );

          if (!mounted) return;

          setState(() => _activeBanner = null);

          await _openRealAudioCall(session);
        } on CallServiceException catch (error) {
          if (!mounted) return;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(error.message),
            ),
          );
        }

        return;
      }

      if (type == 'video_call_request') {
        final callId = asString(data['callId']);

        if (callId.isEmpty) {
          await reqRef.doc(id).set({
            'status': 'rejected_invalid_call',
            'handledAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _decrementCounter(
            meRef,
            'pendingCallRequests',
          );

          if (!mounted) return;

          setState(() => _activeBanner = null);

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'This video call request is invalid.',
              ),
            ),
          );
          return;
        }

        try {
          final session = await CallService().acceptCall(
            callId: callId,
          );

          await reqRef.doc(id).set({
            'status': 'accepted',
            'handledAt': FieldValue.serverTimestamp(),
          }, SetOptions(merge: true));

          await _decrementCounter(
            meRef,
            'pendingCallRequests',
          );

          if (!mounted) return;

          setState(() => _activeBanner = null);

          await _openRealVideoCall(session);
        } on CallServiceException catch (error) {
          if (!mounted) return;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(error.message),
            ),
          );
        }

        return;
      }

      int cost = 0;
      String reason = '';

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

    if (status == 'pending' && type == 'audio_call_request') {
      final callId = asString(data['callId']);

      if (callId.isNotEmpty) {
        try {
          await CallService().rejectCall(
            callId: callId,
          );
        } catch (error) {
          debugPrint(
            'Server audio-call rejection failed: $error',
          );
        }
      }
    }

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

    if (type == 'video_call_request') {
      CallSession? session;

      try {
        session = await CallService().startCall(
          calleeUid: widget.otherUid,
          type: CallType.video,
        );

        await reqRef.add({
          'fromUid': uid,
          'toUid': widget.otherUid,
          'type': type,
          'status': 'pending',
          'callId': session.callId,
          'channelName': session.channelName,
          'callType': session.type.apiValue,
          'ratePerMinute': session.ratePerMinute,
          'createdAt': FieldValue.serverTimestamp(),
          'expiresAt': Timestamp.fromDate(
            DateTime.now().add(_requestExpiryDuration),
          ),
        });

        await _incrementCounter(
          otherRef,
          'pendingCallRequests',
        );

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Video call request sent ✅'),
          ),
        );

        await _openRealVideoCall(session);
      } catch (error) {
        if (session != null) {
          try {
            await CallService().cancelCall(
              callId: session.callId,
            );
          } catch (_) {}
        }

        if (!mounted) return;

        final message = error is CallServiceException
            ? error.message
            : 'Video call could not start: $error';

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
      }

      return;
    }

    if (type == 'audio_call_request') {
      CallSession? session;

      try {
        session = await CallService().startCall(
          calleeUid: widget.otherUid,
          type: CallType.audio,
        );

        await reqRef.add({
          'fromUid': uid,
          'toUid': widget.otherUid,
          'type': type,
          'status': 'pending',
          'callId': session.callId,
          'channelName': session.channelName,
          'callType': session.type.apiValue,
          'ratePerMinute': session.ratePerMinute,
          'createdAt': FieldValue.serverTimestamp(),
          'expiresAt': Timestamp.fromDate(
            DateTime.now().add(_requestExpiryDuration),
          ),
        });

        await _incrementCounter(
          otherRef,
          'pendingCallRequests',
        );

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Audio call request sent ✅'),
          ),
        );

        await _openRealAudioCall(session);
      } catch (error) {
        if (session != null) {
          try {
            await CallService().cancelCall(
              callId: session.callId,
            );
          } catch (_) {}
        }

        if (!mounted) return;

        final message = error is CallServiceException
            ? error.message
            : 'Audio call could not start: $error';

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
      }

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
    await _messageService.sendMessage(
      type: type,
      text: text,
      imageUrl: imageUrl,
      audioUrl: audioUrl,
      audioDurationSec: audioDurationSec,
      replyTo: replyTo,
    );

    if (_replyingTo != null && mounted) {
      setState(() => _replyingTo = null);
    }
  }

  Future<void> _openMeeraWritingAssistant() async {
    if (_anyBlocked || _meeraAssistBusy) {
      return;
    }

    setState(() => _meeraAssistBusy = true);

    try {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        useSafeArea: true,
        builder: (sheetContext) {
          return MeeraWritingAssistantSheet(
            initialText: msgCtrl.text,
            onReplace: (value) {
              msgCtrl
                ..text = value
                ..selection = TextSelection.collapsed(
                  offset: value.length,
                );

              _onTypingChanged(value);
              _msgFocusNode.requestFocus();
            },
          );
        },
      );
    } finally {
      if (mounted) {
        setState(
          () => _meeraAssistBusy = false,
        );
      }
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

  // ignore: unused_element
  void _showUpgradeSnack() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Direct media available only after friendship approval + eligible plan 🔒',
        ),
      ),
    );
  }

  String _formatRecordingDuration(int totalSeconds) {
    final safeSeconds = totalSeconds < 0 ? 0 : totalSeconds;
    final minutes = safeSeconds ~/ 60;
    final seconds = safeSeconds % 60;

    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  void _startRecordingTimer() {
    _recordingTimer?.cancel();
    _recordingElapsedSeconds = 0;

    _recordingTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) {
        if (!mounted || !_isRecording) return;

        setState(() {
          _recordingElapsedSeconds++;
        });
      },
    );
  }

  void _stopRecordingTimer() {
    _recordingTimer?.cancel();
    _recordingTimer = null;
  }

  Future<void> _deleteTemporaryRecording(String? path) async {
    if (path == null || path.trim().isEmpty) return;

    try {
      final file = File(path);
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {
      // Temporary-file cleanup must not interrupt the chat flow.
    }
  }

  Future<void> _startVoiceRecording() async {
    if (_recordingBusy || _isRecording) return;

    if (_anyBlocked) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _blockedByMe ? 'You blocked this user.' : 'You are blocked.',
          ),
        ),
      );
      return;
    }

    _recordingBusy = true;

    try {
      final hasPermission = await _recorder.hasPermission();

      if (!hasPermission) {
        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Microphone permission denied'),
          ),
        );
        return;
      }

      final directory = await getTemporaryDirectory();
      final path =
          '${directory.path}/voice_${DateTime.now().millisecondsSinceEpoch}_$uid.m4a';

      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          bitRate: 128000,
          sampleRate: 44100,
        ),
        path: path,
      );

      if (!mounted) {
        await _recorder.stop();
        await _deleteTemporaryRecording(path);
        return;
      }

      setState(() {
        _recordingPath = path;
        _recordingElapsedSeconds = 0;
        _isRecording = true;
      });

      _startRecordingTimer();
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Recording could not start: $error'),
        ),
      );
    } finally {
      _recordingBusy = false;
    }
  }

  Future<void> _stopAndSendVoice() async {
    if (_recordingBusy || !_isRecording) return;

    _recordingBusy = true;
    _stopRecordingTimer();

    String? finalPath;

    try {
      final stoppedPath = await _recorder.stop();
      finalPath = stoppedPath ?? _recordingPath;

      final recordedSeconds =
          _recordingElapsedSeconds > 0 ? _recordingElapsedSeconds : 1;

      if (mounted) {
        setState(() {
          _isRecording = false;
          _recordingPath = null;
          _recordingElapsedSeconds = 0;
        });
      }

      if (finalPath == null || finalPath.trim().isEmpty) {
        throw StateError('Recorded file path is unavailable.');
      }

      final file = File(finalPath);

      if (!await file.exists()) {
        throw StateError('Recorded voice file was not created.');
      }

      final bytes = await file.length();

      if (bytes <= 0) {
        throw StateError('Recorded voice file is empty.');
      }

      if (bytes > _maxAudioBytes) {
        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Voice message too large'),
          ),
        );
        return;
      }

      final storagePath =
          'voice_uploads/${widget.roomId}/${DateTime.now().millisecondsSinceEpoch}_$uid.m4a';

      final storageReference =
          FirebaseStorage.instance.ref().child(storagePath);

      await storageReference.putFile(file);
      final downloadUrl = await storageReference.getDownloadURL();

      await _sendMessageInternal(
        type: 'voice',
        text: '🎤 Voice message',
        audioUrl: downloadUrl,
        audioDurationSec: recordedSeconds,
        replyTo: _replyingTo,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Voice message sent ✅'),
        ),
      );

      _msgFocusNode.requestFocus();
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _isRecording = false;
        _recordingPath = null;
        _recordingElapsedSeconds = 0;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Voice send failed: $error'),
        ),
      );
    } finally {
      _stopRecordingTimer();
      await _deleteTemporaryRecording(finalPath ?? _recordingPath);
      _recordingPath = null;
      _recordingBusy = false;
    }
  }

  Future<void> _cancelVoiceRecording() async {
    if (_recordingBusy || !_isRecording) return;

    _recordingBusy = true;
    _stopRecordingTimer();

    final temporaryPath = _recordingPath;

    try {
      final stoppedPath = await _recorder.stop();

      await _deleteTemporaryRecording(
        stoppedPath ?? temporaryPath,
      );

      if (!mounted) return;

      setState(() {
        _isRecording = false;
        _recordingPath = null;
        _recordingElapsedSeconds = 0;
      });

      _msgFocusNode.requestFocus();
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Recording cancel failed: $error'),
        ),
      );
    } finally {
      _recordingBusy = false;
    }
  }

  Future<void> _togglePlayAudio(String url) async {
    if (url.trim().isEmpty) return;

    try {
      if (_playingAudioUrl == url) {
        if (_audioPlayer.playing) {
          await _audioPlayer.pause();
        } else {
          if (_audioPlayer.processingState == ProcessingState.completed) {
            await _audioPlayer.seek(Duration.zero);
          }

          unawaited(_audioPlayer.play());
        }

        if (mounted) setState(() {});
        return;
      }

      await _audioPlayer.stop();
      await _audioPlayer.setSpeed(1.0);

      if (mounted) {
        setState(() => _playingAudioUrl = url);
      } else {
        _playingAudioUrl = url;
      }

      await _audioPlayer.setUrl(url);
      unawaited(_audioPlayer.play());
    } catch (error) {
      if (mounted) {
        setState(() => _playingAudioUrl = null);

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Audio play failed: $error'),
          ),
        );
      }
    }
  }

  Future<void> _seekAudio(Duration position) async {
    if (_playingAudioUrl == null) return;
    await _audioPlayer.seek(position);
  }

  Future<void> _changeAudioSpeed(double speed) async {
    if (_playingAudioUrl == null) return;
    await _audioPlayer.setSpeed(speed);
  }

  // ignore: unused_element
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
    await _messageService.deleteForCurrentUser(messageId);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Message removed for you ✅')),
    );
  }

  Future<void> _deleteMessageForEveryone(String messageId) async {
    await _messageService.deleteForEveryone(messageId);

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Deleted for everyone ✅')),
    );
  }

  Future<void> _setReaction(String messageId, String emoji) async {
    await _messageService.setReaction(
      messageId: messageId,
      emoji: emoji,
    );
  }

  Future<void> _removeReaction(String messageId) async {
    await _messageService.removeReaction(messageId);
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

  Future<void> _markSeenAndDelivered(
    List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
  ) async {
    if (_markingSeen) return;
    _markingSeen = true;

    try {
      await _messageService.markSeenAndDelivered(docs);
    } finally {
      _markingSeen = false;
    }
  }

  String _fmtTs(Timestamp? timestamp) {
    if (timestamp == null) return '';

    final dateTime = timestamp.toDate();
    final hour = dateTime.hour % 12 == 0 ? 12 : dateTime.hour % 12;

    final minute = dateTime.minute.toString().padLeft(2, '0');

    final period = dateTime.hour >= 12 ? 'PM' : 'AM';

    return '$hour:$minute $period';
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

  Widget _messageStatus(
    Map<String, dynamic> message,
  ) {
    final deliveredTo = (message['deliveredTo'] as List?)
            ?.map((item) => item.toString())
            .toList() ??
        const <String>[];

    final seenBy =
        (message['seenBy'] as List?)?.map((item) => item.toString()).toList() ??
            const <String>[];

    final state = seenBy.contains(widget.otherUid)
        ? ChatMessageDeliveryState.seen
        : deliveredTo.contains(widget.otherUid)
            ? ChatMessageDeliveryState.delivered
            : ChatMessageDeliveryState.sent;

    return ChatMessageStatusTicks(
      state: state,
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
    final requestRate = asInt(b['ratePerMinute']);

    if (type == 'video_call_request') {
      final rate = requestRate > 0 ? requestRate : _videoCallPrice;
      label = 'Video call request ($rate 🥈/min)';
    }

    if (type == 'audio_call_request') {
      final rate = requestRate > 0 ? requestRate : _audioCallPrice;
      label = 'Audio call request ($rate 🥈/min)';
    }

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
    return ChatReplyBanner(
      replyingTo: _replyingTo,
      currentUid: uid,
      onClose: () {
        if (!mounted) return;
        setState(() => _replyingTo = null);
      },
    );
  }

  Widget _typingLine(bool online, Timestamp? lastSeen) {
    return ChatTypingIndicator(
      isTyping: _otherTyping,
      online: online,
      lastSeen: lastSeen,
      formatLastSeen: _formatLastSeenLine,
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
          child: CachedNetworkImage(
            imageUrl: url,
            fit: BoxFit.contain,
            placeholder: (_, __) => const SizedBox(
              height: 240,
              child: Center(
                child: CircularProgressIndicator(),
              ),
            ),
            errorWidget: (_, __, ___) => const SizedBox(
              height: 240,
              child: Center(
                child: Text('Image failed to load'),
              ),
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

  Widget _buildVoiceBubble(
    Map<String, dynamic> message,
  ) {
    return ChatVoiceMessagePlayer(
      audioPlayer: _audioPlayer,
      audioUrl: asString(message['audioUrl']),
      activeAudioUrl: _playingAudioUrl,
      fallbackDurationSeconds: asInt(message['audioDurationSec']),
      onToggle: _togglePlayAudio,
      onSeek: _seekAudio,
      onChangeSpeed: _changeAudioSpeed,
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
    Map<String, dynamic> message,
    Timestamp? clearedAt,
  ) {
    final senderId = asString(message['senderId']);
    final text = asString(message['text']);
    final type = asString(message['type'], def: 'text');

    void replyToMessage() {
      if (!mounted) return;

      setState(() {
        _replyingTo = <String, dynamic>{
          'messageId': messageId,
          'senderId': senderId,
          'text': text,
          'type': type,
        };
      });
    }

    return ChatMessageBubble(
      messageId: messageId,
      message: message,
      currentUid: uid,
      otherUid: widget.otherUid,
      clearedAt: clearedAt,
      replySnippetBuilder: _replySnippet,
      voiceBubbleBuilder: _buildVoiceBubble,
      messageStatusBuilder: _messageStatus,
      reactionBarBuilder: _buildReactionBar,
      formatTimestamp: _fmtTs,
      onOpenImage: _openImagePreview,
      onReply: replyToMessage,
      onDeleteForMe: () => _deleteMessageForMe(messageId),
      onDeleteForEveryone: () => _deleteMessageForEveryone(messageId),
      onReact: () => _openReactionSheet(messageId),
      onShowInfo: () => _showMessageInfo(message),
    );
  }

  // ignore: unused_element
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

        final clearedAt = _myChatPrefs['clearedAt'] as Timestamp?;

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
                    onChanged: (v) =>
                        setState(() => _searchText = v.trim().toLowerCase()),
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
                                builder: (_) =>
                                    UserProfilePage(userId: widget.otherUid),
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
                constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
                onPressed: () {
                  setState(() {
                    _searchMode = !_searchMode;
                    if (!_searchMode) _searchText = '';
                  });
                },
                icon: Icon(_searchMode ? Icons.close : Icons.search, size: 21),
              ),
              if (!_searchMode) ...[
                IconButton(
                  visualDensity: VisualDensity.compact,
                  constraints:
                      const BoxConstraints(minWidth: 38, minHeight: 38),
                  tooltip: 'Audio call request',
                  onPressed: _anyBlocked || !_callsEnabled
                      ? null
                      : () => _sendRequestToOther('audio_call_request'),
                  icon: const Icon(Icons.call, size: 21),
                ),
                IconButton(
                  visualDensity: VisualDensity.compact,
                  constraints:
                      const BoxConstraints(minWidth: 38, minHeight: 38),
                  tooltip: 'Video call request',
                  onPressed: _anyBlocked || !_callsEnabled
                      ? null
                      : () => _sendRequestToOther('video_call_request'),
                  icon: const Icon(Icons.videocam, size: 21),
                ),
                PopupMenuButton<String>(
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(
                    minWidth: 38,
                    minHeight: 38,
                  ),
                  onSelected: (value) async {
                    if (value == 'requests') {
                      await _openRequestsSheet();
                    } else if (value == 'settings') {
                      await _openChatRoomSettings();
                    } else if (value == 'rules') {
                      await _openRulesPage();
                    } else if (value == 'profile') {
                      if (!mounted) return;

                      await Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => UserProfilePage(
                            userId: widget.otherUid,
                          ),
                        ),
                      );
                    }
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(
                      value: 'profile',
                      child: ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.person_outline),
                        title: Text('View profile'),
                      ),
                    ),
                    PopupMenuItem(
                      value: 'requests',
                      child: ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.inbox_outlined),
                        title: Text('Requests'),
                      ),
                    ),
                    PopupMenuItem(
                      value: 'settings',
                      child: ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.tune_rounded),
                        title: Text('Conversation settings'),
                      ),
                    ),
                    PopupMenuItem(
                      value: 'rules',
                      child: ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.rule_outlined),
                        title: Text('Community rules'),
                      ),
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
                      child: Row(
                        children: [
                          const Icon(Icons.mic, color: Colors.red),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Recording voice message... '
                              '${_formatRecordingDuration(_recordingElapsedSeconds)}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  Expanded(
                    child: ChatMessageList(
                      paginationController: _paginationController,
                      scrollController: scrollCtrl,
                      searchText: _searchText,
                      currentUid: uid,
                      clearedAt: clearedAt,
                      onMessagesVisible: _scheduleMarkSeen,
                      buildDateChip: _buildDateChip,
                      buildMessageBubble: _buildMessageBubble,
                      isSameDay: _isSameDay,
                    ),
                  ),
                  ChatMessageInput(
                    fieldKey: _composerFieldKey,
                    controller: msgCtrl,
                    focusNode: _msgFocusNode,
                    isBlocked: _anyBlocked,
                    blockedByCurrentUser: _blockedByMe,
                    isRecording: _isRecording,
                    hasTypedText: _hasTypedText,
                    sendingText: _sendingText,
                    sendingImage: _sendingImage,
                    onTypingChanged: _onTypingChanged,
                    onSend: _send,
                    onPickImage: _pickAndSendImageOrRequest,
                    onStartRecording: _startVoiceRecording,
                    onStopAndSendRecording: _stopAndSendVoice,
                    onCancelRecording: _cancelVoiceRecording,
                    onColorPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Coming soon'),
                        ),
                      );
                      _msgFocusNode.requestFocus();
                    },
                    onAiPressed: _openMeeraWritingAssistant,
                    aiBusy: _meeraAssistBusy,
                  ),
                ],
              ),
            ],
          ),
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
