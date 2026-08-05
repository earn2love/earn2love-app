import 'package:cloud_functions/cloud_functions.dart';

import '../models/meera_chat_assist.dart';
import '../models/meera_message.dart';
import '../models/meera_profile_coach.dart';

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
    String conversationId = '',
    String conversationTitle = '',
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
        if (conversationId.trim().isNotEmpty)
          'conversationId': conversationId.trim(),
        if (conversationTitle.trim().isNotEmpty)
          'conversationTitle': conversationTitle.trim(),
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

  Future<MeeraChatAssistResult> generateChatAssist({
    required String mode,
    required String text,
    List<Map<String, String>> recentMessages = const [],
    String languageMode = 'auto',
    String requestedLanguage = '',
  }) async {
    final result = await _call(
      'generateMeeraChatAssist',
      {
        'mode': mode,
        'text': text,
        'recentMessages': recentMessages.take(8).toList(
              growable: false,
            ),
        'languageMode': languageMode,
        if (requestedLanguage.trim().isNotEmpty)
          'requestedLanguage': requestedLanguage.trim(),
      },
    );

    return MeeraChatAssistResult.fromMap(
      result,
    );
  }

  Future<MeeraProfileCoachResult> analyseProfile({
    String languageMode = 'auto',
    String requestedLanguage = '',
  }) async {
    final result = await _call(
      'analyseMeeraProfile',
      {
        'languageMode': languageMode,
        if (requestedLanguage.trim().isNotEmpty)
          'requestedLanguage': requestedLanguage.trim(),
      },
    );

    return MeeraProfileCoachResult.fromMap(
      result,
    );
  }

  Future<List<MeeraConversationSummary>> listConversations() async {
    final result = await _call(
      'listMeeraConversations',
      const <String, dynamic>{'limit': 50},
    );

    final raw = result['conversations'] is List
        ? result['conversations'] as List
        : const [];

    return raw
        .whereType<Map>()
        .map(
          (item) => MeeraConversationSummary.fromMap(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList(growable: false);
  }

  Future<List<MeeraMessage>> getConversation(
    String conversationId,
  ) async {
    final result = await _call(
      'getMeeraConversation',
      {
        'conversationId': conversationId,
        'limit': 100,
      },
    );

    final rawMessages =
        result['messages'] is List ? result['messages'] as List : const [];

    return rawMessages
        .whereType<Map>()
        .map((item) {
          final map = Map<String, dynamic>.from(item);

          return MeeraMessage(
            role: (map['role'] ?? 'assistant').toString(),
            content: (map['content'] ?? '').toString(),
            createdAt: _dateFromValue(map['createdAt']) ?? DateTime.now(),
            detectedLanguage:
                (map['detectedLanguage'] ?? '').toString().trim().isEmpty
                    ? null
                    : map['detectedLanguage'].toString(),
            responseLanguage:
                (map['responseLanguage'] ?? '').toString().trim().isEmpty
                    ? null
                    : map['responseLanguage'].toString(),
            category: (map['category'] ?? '').toString().trim().isEmpty
                ? null
                : map['category'].toString(),
            requiresHumanSupport: map['requiresHumanSupport'] == true,
          );
        })
        .where(
          (message) => message.content.trim().isNotEmpty,
        )
        .toList(growable: false);
  }

  Future<void> renameConversation({
    required String conversationId,
    required String title,
  }) async {
    await _call(
      'renameMeeraConversation',
      {
        'conversationId': conversationId,
        'title': title,
      },
    );
  }

  Future<void> deleteConversation(
    String conversationId,
  ) async {
    await _call(
      'deleteMeeraConversation',
      {'conversationId': conversationId},
    );
  }

  Future<MeeraMemory> saveMemory({
    required String content,
    String category = 'preference',
  }) async {
    final result = await _call(
      'saveMeeraMemory',
      {
        'content': content,
        'category': category,
        'source': 'user_confirmed',
      },
    );

    return MeeraMemory.fromMap(result);
  }

  Future<List<MeeraMemory>> listMemories() async {
    final result = await _call(
      'listMeeraMemories',
      const <String, dynamic>{'limit': 50},
    );

    final raw =
        result['memories'] is List ? result['memories'] as List : const [];

    return raw
        .whereType<Map>()
        .map(
          (item) => MeeraMemory.fromMap(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList(growable: false);
  }

  Future<void> deleteMemory(
    String memoryId,
  ) async {
    await _call(
      'deleteMeeraMemory',
      {'memoryId': memoryId},
    );
  }

  Future<void> clearMemories() async {
    await _call(
      'clearMeeraMemories',
      const <String, dynamic>{},
    );
  }

  Future<Map<String, dynamic>> _call(
    String functionName,
    Map<String, dynamic> data,
  ) async {
    try {
      final callable = _functions.httpsCallable(functionName);

      final result = await callable.call<Map<String, dynamic>>(
        data,
      );

      return Map<String, dynamic>.from(
        result.data,
      );
    } on FirebaseFunctionsException catch (error) {
      throw MeeraServiceException(
        error.message ?? 'Meera service is temporarily unavailable.',
      );
    } catch (error) {
      throw MeeraServiceException(
        'Meera service failed: $error',
      );
    }
  }

  DateTime? _dateFromValue(dynamic value) {
    if (value == null) return null;

    try {
      final dynamic date = value.toDate();
      return date as DateTime;
    } catch (_) {
      return DateTime.tryParse(value.toString());
    }
  }
}
