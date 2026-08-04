import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';

class ChatPaginationController extends ChangeNotifier {
  ChatPaginationController({
    required CollectionReference<Map<String, dynamic>> messagesReference,
    this.pageSize = 30,
  }) : _messagesReference = messagesReference;

  final CollectionReference<Map<String, dynamic>> _messagesReference;
  final int pageSize;

  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _latestSubscription;

  final List<QueryDocumentSnapshot<Map<String, dynamic>>> _latestMessages =
      <QueryDocumentSnapshot<Map<String, dynamic>>>[];

  final List<QueryDocumentSnapshot<Map<String, dynamic>>> _olderMessages =
      <QueryDocumentSnapshot<Map<String, dynamic>>>[];

  bool _started = false;
  bool _initialLoading = true;
  bool _loadingOlder = false;
  bool _hasMoreOlder = true;
  Object? _error;

  bool get initialLoading => _initialLoading;
  bool get loadingOlder => _loadingOlder;
  bool get hasMoreOlder => _hasMoreOlder;
  Object? get error => _error;

  List<QueryDocumentSnapshot<Map<String, dynamic>>> get messages {
    final byId = <String, QueryDocumentSnapshot<Map<String, dynamic>>>{};

    for (final document in _latestMessages) {
      byId[document.id] = document;
    }

    for (final document in _olderMessages) {
      byId.putIfAbsent(document.id, () => document);
    }

    final result = byId.values.toList()
      ..sort((first, second) {
        final firstTimestamp = first.data()['createdAt'] as Timestamp?;
        final secondTimestamp = second.data()['createdAt'] as Timestamp?;

        if (firstTimestamp == null && secondTimestamp == null) return 0;
        if (firstTimestamp == null) return 1;
        if (secondTimestamp == null) return -1;

        return secondTimestamp.compareTo(firstTimestamp);
      });

    return List<QueryDocumentSnapshot<Map<String, dynamic>>>.unmodifiable(
      result,
    );
  }

  Query<Map<String, dynamic>> get _baseQuery =>
      _messagesReference.orderBy('createdAt', descending: true);

  void start() {
    if (_started) return;
    _started = true;

    _latestSubscription = _baseQuery.limit(pageSize).snapshots().listen(
      (snapshot) {
        _latestMessages
          ..clear()
          ..addAll(snapshot.docs);

        _initialLoading = false;
        _error = null;

        if (snapshot.docs.length < pageSize && _olderMessages.isEmpty) {
          _hasMoreOlder = false;
        }

        notifyListeners();
      },
      onError: (Object error, StackTrace stackTrace) {
        _initialLoading = false;
        _error = error;
        notifyListeners();
      },
    );
  }

  Future<void> loadOlder() async {
    if (_initialLoading || _loadingOlder || !_hasMoreOlder) return;

    final combined = messages;
    if (combined.isEmpty) {
      _hasMoreOlder = false;
      notifyListeners();
      return;
    }

    _loadingOlder = true;
    _error = null;
    notifyListeners();

    try {
      final oldestDocument = combined.last;

      final snapshot = await _baseQuery
          .startAfterDocument(oldestDocument)
          .limit(pageSize)
          .get();

      final existingIds = <String>{
        ..._latestMessages.map((document) => document.id),
        ..._olderMessages.map((document) => document.id),
      };

      for (final document in snapshot.docs) {
        if (existingIds.add(document.id)) {
          _olderMessages.add(document);
        }
      }

      if (snapshot.docs.length < pageSize) {
        _hasMoreOlder = false;
      }
    } catch (error) {
      _error = error;
    } finally {
      _loadingOlder = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _latestSubscription?.cancel();
    super.dispose();
  }
}
