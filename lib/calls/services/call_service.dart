import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../models/call_session.dart';

class CallServiceException implements Exception {
  const CallServiceException(
    this.message, {
    this.code,
    this.originalError,
  });

  final String message;
  final String? code;
  final Object? originalError;

  @override
  String toString() => message;
}

class CallService {
  CallService({
    FirebaseFunctions? functions,
    FirebaseAuth? auth,
  })  : _functions = functions ??
            FirebaseFunctions.instanceFor(
              region: 'us-central1',
            ),
        _auth = auth ?? FirebaseAuth.instance;

  final FirebaseFunctions _functions;
  final FirebaseAuth _auth;

  String get currentUid {
    final uid = _auth.currentUser?.uid;

    if (uid == null || uid.trim().isEmpty) {
      throw const CallServiceException(
        'You must be signed in to make a call.',
        code: 'unauthenticated',
      );
    }

    return uid;
  }

  Future<CallPricingConfig> getCallConfig() async {
    try {
      final callable = _functions.httpsCallable('getCallConfig');

      final response = await callable.call<Map<String, dynamic>>();

      return CallPricingConfig.fromMap(
        Map<String, dynamic>.from(
          response.data,
        ),
      );
    } on FirebaseFunctionsException catch (error) {
      throw CallServiceException(
        error.message ?? 'Call configuration could not be loaded.',
        code: error.code,
        originalError: error,
      );
    } catch (error) {
      if (error is CallServiceException) rethrow;

      throw CallServiceException(
        'Call configuration could not be loaded: $error',
        originalError: error,
      );
    }
  }

  Future<CallSession> startCall({
    required String calleeUid,
    required CallType type,
  }) async {
    final cleanCalleeUid = calleeUid.trim();

    if (cleanCalleeUid.isEmpty) {
      throw const CallServiceException(
        'The call recipient is invalid.',
        code: 'invalid-callee',
      );
    }

    try {
      final callable = _functions.httpsCallable('startCall');

      final response = await callable.call<Map<String, dynamic>>(
        <String, dynamic>{
          'calleeUid': cleanCalleeUid,
          'type': type.apiValue,
        },
      );

      final data = Map<String, dynamic>.from(response.data);

      return CallSession(
        callId: _requiredString(data['callId'], 'callId'),
        channelName: _requiredString(
          data['channelName'],
          'channelName',
        ),
        type: CallType.fromValue(data['type']),
        callerUid: currentUid,
        calleeUid: cleanCalleeUid,
        ratePerMinute: _asInt(data['ratePerMin']),
        isCaller: true,
      );
    } on FirebaseFunctionsException catch (error) {
      throw CallServiceException(
        error.message ?? 'The call could not be started.',
        code: error.code,
        originalError: error,
      );
    } catch (error) {
      if (error is CallServiceException) rethrow;

      throw CallServiceException(
        'The call could not be started: $error',
        originalError: error,
      );
    }
  }

  Future<AgoraCredentials> generateAgoraToken({
    required String channelName,
    required int agoraUid,
  }) async {
    final cleanChannelName = channelName.trim();

    if (cleanChannelName.isEmpty) {
      throw const CallServiceException(
        'The Agora channel is invalid.',
        code: 'invalid-channel',
      );
    }

    try {
      final callable = _functions.httpsCallable(
        'generateAgoraToken',
      );

      final response = await callable.call<Map<String, dynamic>>(
        <String, dynamic>{
          'channelName': cleanChannelName,
          'agoraUid': agoraUid,
        },
      );

      return AgoraCredentials.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } on FirebaseFunctionsException catch (error) {
      throw CallServiceException(
        error.message ?? 'The call token could not be created.',
        code: error.code,
        originalError: error,
      );
    } catch (error) {
      if (error is CallServiceException) rethrow;

      throw CallServiceException(
        'The call token could not be created: $error',
        originalError: error,
      );
    }
  }

  Future<CallSession> acceptCall({
    required String callId,
  }) async {
    final cleanCallId = callId.trim();

    if (cleanCallId.isEmpty) {
      throw const CallServiceException(
        'The call ID is invalid.',
        code: 'invalid-call',
      );
    }

    try {
      final callable = _functions.httpsCallable('acceptCall');

      final response = await callable.call<Map<String, dynamic>>(
        <String, dynamic>{
          'callId': cleanCallId,
        },
      );

      final data = Map<String, dynamic>.from(response.data);

      return CallSession(
        callId: _requiredString(data['callId'], 'callId'),
        channelName: _requiredString(
          data['channelName'],
          'channelName',
        ),
        type: CallType.fromValue(data['type']),
        callerUid: _requiredString(
          data['callerUid'],
          'callerUid',
        ),
        calleeUid: _requiredString(
          data['calleeUid'],
          'calleeUid',
        ),
        ratePerMinute: 0,
        isCaller: false,
      );
    } on FirebaseFunctionsException catch (error) {
      throw CallServiceException(
        error.message ?? 'The call could not be accepted.',
        code: error.code,
        originalError: error,
      );
    } catch (error) {
      if (error is CallServiceException) rethrow;

      throw CallServiceException(
        'The call could not be accepted: $error',
        originalError: error,
      );
    }
  }

  Future<void> rejectCall({
    required String callId,
  }) async {
    await _updateCallState(
      functionName: 'rejectCall',
      callId: callId,
    );
  }

  Future<void> cancelCall({
    required String callId,
  }) async {
    await _updateCallState(
      functionName: 'cancelCall',
      callId: callId,
    );
  }

  Future<void> _updateCallState({
    required String functionName,
    required String callId,
  }) async {
    final cleanCallId = callId.trim();

    if (cleanCallId.isEmpty) {
      throw const CallServiceException(
        'The call ID is invalid.',
        code: 'invalid-call',
      );
    }

    try {
      final callable = _functions.httpsCallable(functionName);

      await callable.call<Map<String, dynamic>>(
        <String, dynamic>{
          'callId': cleanCallId,
        },
      );
    } on FirebaseFunctionsException catch (error) {
      throw CallServiceException(
        error.message ?? 'The call could not be updated.',
        code: error.code,
        originalError: error,
      );
    } catch (error) {
      if (error is CallServiceException) rethrow;

      throw CallServiceException(
        'The call could not be updated: $error',
        originalError: error,
      );
    }
  }

  Future<EndCallResult> endCall({
    required String callId,
    required int durationSeconds,
  }) async {
    final cleanCallId = callId.trim();

    if (cleanCallId.isEmpty) {
      throw const CallServiceException(
        'The call ID is invalid.',
        code: 'invalid-call',
      );
    }

    try {
      final callable = _functions.httpsCallable('endCall');

      final response = await callable.call<Map<String, dynamic>>(
        <String, dynamic>{
          'callId': cleanCallId,
          'durationSeconds': durationSeconds < 0 ? 0 : durationSeconds,
        },
      );

      return EndCallResult.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } on FirebaseFunctionsException catch (error) {
      throw CallServiceException(
        error.message ?? 'The call could not be ended.',
        code: error.code,
        originalError: error,
      );
    } catch (error) {
      if (error is CallServiceException) rethrow;

      throw CallServiceException(
        'The call could not be ended correctly: $error',
        originalError: error,
      );
    }
  }
}

String _requiredString(dynamic value, String field) {
  final result = value?.toString().trim() ?? '';

  if (result.isEmpty) {
    throw StateError('Missing call response field: $field');
  }

  return result;
}

int _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}
