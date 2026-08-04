import 'package:cloud_functions/cloud_functions.dart';

import '../models/play_experience.dart';
import '../models/play_session.dart';

class PlayTogetherCatalog {
  const PlayTogetherCatalog({
    required this.userTier,
    required this.experiences,
  });

  final String userTier;
  final List<PlayExperience> experiences;
}

class PlayTogetherServiceException implements Exception {
  const PlayTogetherServiceException(this.message);

  final String message;

  @override
  String toString() => message;
}

class PlayTogetherService {
  PlayTogetherService({
    FirebaseFunctions? functions,
  }) : _functions = functions ??
            FirebaseFunctions.instanceFor(
              region: 'us-central1',
            );

  final FirebaseFunctions _functions;

  PlayTogetherServiceException _callableError(
    Object error,
    String fallback,
  ) {
    if (error is FirebaseFunctionsException) {
      return PlayTogetherServiceException(
        error.message ?? fallback,
      );
    }

    return PlayTogetherServiceException(
      '$fallback: $error',
    );
  }

  Future<PlayTogetherCatalog> getExperiences() async {
    try {
      final callable = _functions.httpsCallable('getPlayExperiences');

      final response = await callable.call<Map<String, dynamic>>();

      final data = Map<String, dynamic>.from(response.data);

      final rawExperiences = data['experiences'] as List<dynamic>? ?? const [];

      return PlayTogetherCatalog(
        userTier: (data['userTier'] ?? 'casual').toString(),
        experiences: rawExperiences
            .whereType<Map>()
            .map(
              (item) => PlayExperience.fromMap(
                Map<String, dynamic>.from(item),
              ),
            )
            .toList(growable: false),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Play experiences could not be loaded',
      );
    }
  }

  Future<PlaySession> createSession({
    required String experienceId,
    required String language,
    required String comfortLevel,
  }) async {
    try {
      final callable = _functions.httpsCallable('createPlaySession');

      final response = await callable.call<Map<String, dynamic>>({
        'experienceId': experienceId,
        'language': language,
        'comfortLevel': comfortLevel,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Play session could not be created',
      );
    }
  }

  Future<PlaySession> joinSession({
    required String inviteCode,
    String comfortLevel = 'standard',
  }) async {
    try {
      final callable = _functions.httpsCallable('joinPlaySession');

      final response = await callable.call<Map<String, dynamic>>({
        'inviteCode': inviteCode.trim().toUpperCase(),
        'comfortLevel': comfortLevel,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Play session could not be joined',
      );
    }
  }

  Future<PlaySession> setReady({
    required String sessionId,
    required bool ready,
  }) async {
    try {
      final callable = _functions.httpsCallable('setPlayReady');

      final response = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
        'ready': ready,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Ready status could not be updated',
      );
    }
  }

  Future<PlaySession> setComfort({
    required String sessionId,
    required String comfortLevel,
  }) async {
    try {
      final callable = _functions.httpsCallable('setPlayComfort');

      final response = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
        'comfortLevel': comfortLevel,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Comfort level could not be updated',
      );
    }
  }

  Future<PlaySession> getSession({
    required String sessionId,
  }) async {
    try {
      final callable = _functions.httpsCallable('getPlaySession');

      final response = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Play session could not be loaded',
      );
    }
  }

  Future<PlaySession> submitResponse({
    required String sessionId,
    required String response,
  }) async {
    try {
      final callable = _functions.httpsCallable('submitPlayResponse');

      final result = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
        'response': response.trim(),
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(result.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Response could not be submitted',
      );
    }
  }

  Future<PlaySession> skipPrompt({
    required String sessionId,
  }) async {
    try {
      final callable = _functions.httpsCallable('skipPlayPrompt');

      final result = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(result.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Prompt could not be skipped',
      );
    }
  }

  Future<PlaySession> replacePrompt({
    required String sessionId,
  }) async {
    try {
      final callable = _functions.httpsCallable('replacePlayPrompt');

      final result = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(result.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Prompt could not be replaced',
      );
    }
  }

  Future<PlaySession> nextPrompt({
    required String sessionId,
  }) async {
    try {
      final callable = _functions.httpsCallable('nextPlayPrompt');

      final result = await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(result.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'Next round could not be started',
      );
    }
  }

  Future<PlaySession?> getInCallSession({
    required String callId,
  }) async {
    try {
      final callable = _functions.httpsCallable('getInCallPlaySession');

      final result = await callable.call<Map<String, dynamic>>({
        'callId': callId,
      });

      final data = Map<String, dynamic>.from(result.data);

      if (data['found'] != true || data['session'] is! Map) {
        return null;
      }

      return PlaySession.fromMap(
        Map<String, dynamic>.from(
          data['session'] as Map,
        ),
      );
    } catch (error) {
      throw _callableError(
        error,
        'In-call game could not be loaded',
      );
    }
  }

  Future<PlaySession> createInCallSession({
    required String callId,
    required String experienceId,
    required String language,
    required String comfortLevel,
  }) async {
    try {
      final callable = _functions.httpsCallable('createInCallPlaySession');

      final result = await callable.call<Map<String, dynamic>>({
        'callId': callId,
        'experienceId': experienceId,
        'language': language,
        'comfortLevel': comfortLevel,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(result.data),
      );
    } catch (error) {
      throw _callableError(
        error,
        'In-call game could not be created',
      );
    }
  }

  Future<void> endInCallSession({
    required String callId,
  }) async {
    try {
      final callable = _functions.httpsCallable('endInCallPlaySession');

      await callable.call<Map<String, dynamic>>({
        'callId': callId,
      });
    } catch (error) {
      throw _callableError(
        error,
        'In-call game could not be closed',
      );
    }
  }

  Future<void> leaveSession({
    required String sessionId,
  }) async {
    try {
      final callable = _functions.httpsCallable('leavePlaySession');

      await callable.call<Map<String, dynamic>>({
        'sessionId': sessionId,
      });
    } catch (error) {
      throw _callableError(
        error,
        'Play session could not be closed',
      );
    }
  }
}
