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

  Future<PlayTogetherCatalog> getExperiences() async {
    try {
      final response = await _functions
          .httpsCallable('getPlayExperiences')
          .call<Map<String, dynamic>>();

      final data = Map<String, dynamic>.from(response.data);
      final rawItems = data['experiences'] as List<dynamic>? ?? const [];

      return PlayTogetherCatalog(
        userTier: (data['userTier'] ?? 'casual').toString(),
        experiences: rawItems
            .whereType<Map>()
            .map(
              (item) => PlayExperience.fromMap(
                Map<String, dynamic>.from(item),
              ),
            )
            .toList(growable: false),
      );
    } on FirebaseFunctionsException catch (error) {
      throw PlayTogetherServiceException(
        error.message ?? 'Play experiences could not be loaded.',
      );
    } catch (error) {
      throw PlayTogetherServiceException(
        'Play experiences could not be loaded: $error',
      );
    }
  }

  Future<PlaySession> createSession({
    required String experienceId,
    required String language,
    required String comfortLevel,
  }) async {
    try {
      final response = await _functions
          .httpsCallable('createPlaySession')
          .call<Map<String, dynamic>>({
        'experienceId': experienceId,
        'language': language,
        'comfortLevel': comfortLevel,
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } on FirebaseFunctionsException catch (error) {
      throw PlayTogetherServiceException(
        error.message ?? 'Session could not be created.',
      );
    }
  }

  Future<PlaySession> joinSession({
    required String inviteCode,
  }) async {
    try {
      final response = await _functions
          .httpsCallable('joinPlaySession')
          .call<Map<String, dynamic>>({
        'inviteCode': inviteCode.trim(),
      });

      return PlaySession.fromMap(
        Map<String, dynamic>.from(response.data),
      );
    } on FirebaseFunctionsException catch (error) {
      throw PlayTogetherServiceException(
        error.message ?? 'Session could not be joined.',
      );
    }
  }

  Future<PlaySession> setReady({
    required String sessionId,
    required bool ready,
  }) async {
    final response = await _functions
        .httpsCallable('setPlayReady')
        .call<Map<String, dynamic>>({
      'sessionId': sessionId,
      'ready': ready,
    });

    return PlaySession.fromMap(
      Map<String, dynamic>.from(response.data),
    );
  }

  Future<PlaySession> getSession({
    required String sessionId,
  }) async {
    final response = await _functions
        .httpsCallable('getPlaySession')
        .call<Map<String, dynamic>>({
      'sessionId': sessionId,
    });

    return PlaySession.fromMap(
      Map<String, dynamic>.from(response.data),
    );
  }

  Future<void> leaveSession({
    required String sessionId,
  }) async {
    await _functions.httpsCallable('leavePlaySession').call<void>({
      'sessionId': sessionId,
    });
  }
}
