import 'package:cloud_functions/cloud_functions.dart';

import '../models/meera_message.dart';

class MeeraServiceException implements Exception {
  const MeeraServiceException(this.message);

  final String message;

  @override
  String toString() => message;
}

class MeeraService {
  MeeraService({
    FirebaseFunctions? functions,
  }) : _functions = functions ??
            FirebaseFunctions.instanceFor(
              region: 'us-central1',
            );

  final FirebaseFunctions _functions;

  Future<MeeraAssistantResult> ask({
    required String message,
    required List<MeeraMessage> history,
    required String languageMode,
    String requestedLanguage = '',
    String currentScreen = 'ask_meera',
  }) async {
    try {
      final callable = _functions.httpsCallable(
        'askMeeraAssistant',
      );

      final result = await callable.call<Map<String, dynamic>>({
        'message': message,
        'history': history
            .where(
              (item) => item.content.trim().isNotEmpty,
            )
            .take(12)
            .map((item) => item.toHistoryMap())
            .toList(growable: false),
        'languageMode': languageMode,
        if (requestedLanguage.trim().isNotEmpty)
          'requestedLanguage': requestedLanguage.trim(),
        'currentScreen': currentScreen,
      });

      return MeeraAssistantResult.fromMap(
        Map<String, dynamic>.from(
          result.data,
        ),
      );
    } on FirebaseFunctionsException catch (error) {
      throw MeeraServiceException(
        error.message ?? 'Meera is temporarily unavailable.',
      );
    } catch (error) {
      throw MeeraServiceException(
        'Meera request failed: $error',
      );
    }
  }
}
