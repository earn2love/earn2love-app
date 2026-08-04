import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../controllers/chat_pagination_controller.dart';

class ChatMessageList extends StatelessWidget {
  const ChatMessageList({
    super.key,
    required this.paginationController,
    required this.scrollController,
    required this.searchText,
    required this.currentUid,
    required this.clearedAt,
    required this.onMessagesVisible,
    required this.buildDateChip,
    required this.buildMessageBubble,
    required this.isSameDay,
  });

  final ChatPaginationController paginationController;
  final ScrollController scrollController;
  final String searchText;
  final String currentUid;
  final Timestamp? clearedAt;

  final void Function(
    List<QueryDocumentSnapshot<Map<String, dynamic>>> documents,
  ) onMessagesVisible;

  final Widget Function(Timestamp? timestamp) buildDateChip;

  final Widget Function(
    String messageId,
    Map<String, dynamic> message,
    Timestamp? clearedAt,
  ) buildMessageBubble;

  final bool Function(DateTime first, DateTime second) isSameDay;

  String _asString(dynamic value) {
    if (value == null) return '';
    return value.toString().trim();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: paginationController,
      builder: (context, _) {
        if (paginationController.initialLoading) {
          return const Center(
            child: CircularProgressIndicator(),
          );
        }

        if (paginationController.error != null &&
            paginationController.messages.isEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'Unable to load messages. Please check your connection.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.red.shade700,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          );
        }

        var documents = List<QueryDocumentSnapshot<Map<String, dynamic>>>.from(
          paginationController.messages,
        );

        final normalizedSearch = searchText.trim().toLowerCase();

        if (normalizedSearch.isNotEmpty) {
          documents = documents.where((document) {
            final message = document.data();

            final text = _asString(message['text']).toLowerCase();

            final type = _asString(message['type']).toLowerCase();

            final replyText = message['replyTo'] is Map
                ? _asString(
                    (message['replyTo'] as Map)['text'],
                  ).toLowerCase()
                : '';

            return text.contains(normalizedSearch) ||
                type.contains(normalizedSearch) ||
                replyText.contains(normalizedSearch);
          }).toList();
        }

        onMessagesVisible(documents);

        return ListView.builder(
          controller: scrollController,
          reverse: true,
          padding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 10,
          ),
          itemCount: documents.length,
          itemBuilder: (context, index) {
            final document = documents[index];
            final message = document.data();

            final deletedFor = (message['deletedFor'] as List?)
                    ?.map((value) => value.toString())
                    .toList() ??
                <String>[];

            if (deletedFor.contains(currentUid)) {
              return const SizedBox.shrink();
            }

            final timestamp = message['createdAt'] as Timestamp?;
            var showDateChip = false;

            if (index == documents.length - 1) {
              showDateChip = true;
            } else {
              final nextTimestamp =
                  documents[index + 1].data()['createdAt'] as Timestamp?;

              final currentDate = timestamp?.toDate();
              final nextDate = nextTimestamp?.toDate();

              if (currentDate != null && nextDate != null) {
                showDateChip = !isSameDay(
                  currentDate,
                  nextDate,
                );
              }
            }

            return Column(
              children: [
                if (showDateChip) buildDateChip(timestamp),
                buildMessageBubble(
                  document.id,
                  message,
                  clearedAt,
                ),
              ],
            );
          },
        );
      },
    );
  }
}
