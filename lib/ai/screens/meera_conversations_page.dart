import 'package:flutter/material.dart';

import '../models/meera_message.dart';
import '../services/meera_service.dart';

class MeeraConversationsPage extends StatefulWidget {
  const MeeraConversationsPage({
    super.key,
  });

  @override
  State<MeeraConversationsPage> createState() => _MeeraConversationsPageState();
}

class _MeeraConversationsPageState extends State<MeeraConversationsPage> {
  final MeeraService _service = MeeraService();

  bool _loading = true;
  String? _error;

  List<MeeraConversationSummary> _items = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final items = await _service.listConversations();

      if (!mounted) return;

      setState(() {
        _items = items;
      });
    } on MeeraServiceException catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.message;
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _rename(
    MeeraConversationSummary item,
  ) async {
    final controller = TextEditingController(
      text: item.title,
    );

    final title = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text(
            'Rename conversation',
          ),
          content: TextField(
            controller: controller,
            autofocus: true,
            maxLength: 100,
            decoration: const InputDecoration(
              labelText: 'Title',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(
                dialogContext,
                controller.text.trim(),
              ),
              child: const Text('Save'),
            ),
          ],
        );
      },
    );

    controller.dispose();

    if (title == null || title.isEmpty) return;

    await _service.renameConversation(
      conversationId: item.id,
      title: title,
    );

    await _load();
  }

  Future<void> _delete(
    MeeraConversationSummary item,
  ) async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) {
            return AlertDialog(
              title: const Text('Delete conversation?'),
              content: Text(
                '"${item.title}" and all its '
                'messages will be permanently deleted.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(
                    dialogContext,
                    false,
                  ),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.red,
                  ),
                  onPressed: () => Navigator.pop(
                    dialogContext,
                    true,
                  ),
                  child: const Text('Delete'),
                ),
              ],
            );
          },
        ) ??
        false;

    if (!confirmed) return;

    await _service.deleteConversation(item.id);
    await _load();
  }

  String _dateLabel(DateTime? value) {
    if (value == null) return '';

    final now = DateTime.now();
    final difference = now.difference(value);

    if (difference.inMinutes < 1) return 'Now';
    if (difference.inHours < 1) {
      return '${difference.inMinutes}m';
    }
    if (difference.inDays < 1) {
      return '${difference.inHours}h';
    }
    if (difference.inDays < 7) {
      return '${difference.inDays}d';
    }

    return '${value.day}/${value.month}/${value.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F4FC),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF8F4FC),
        title: const Text(
          'Meera conversations',
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.of(context).pop('new'),
        icon: const Icon(Icons.add_rounded),
        label: const Text('New conversation'),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : _error != null
              ? _ErrorState(
                  message: _error!,
                  onRetry: _load,
                )
              : _items.isEmpty
                  ? const _EmptyState()
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(
                          12,
                          10,
                          12,
                          100,
                        ),
                        itemCount: _items.length,
                        itemBuilder: (context, index) {
                          final item = _items[index];

                          return Card(
                            elevation: 0,
                            margin: const EdgeInsets.only(
                              bottom: 8,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(
                                20,
                              ),
                            ),
                            child: ListTile(
                              contentPadding: const EdgeInsets.fromLTRB(
                                15,
                                8,
                                5,
                                8,
                              ),
                              leading: const CircleAvatar(
                                backgroundColor: Color(0xFFE9DFFF),
                                child: Icon(
                                  Icons.auto_awesome_rounded,
                                  color: Color(0xFF7B4EFF),
                                ),
                              ),
                              title: Text(
                                item.title,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              subtitle: Text(
                                item.lastMessage.isEmpty
                                    ? 'No messages yet'
                                    : item.lastMessage,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    _dateLabel(
                                      item.updatedAt,
                                    ),
                                    style: const TextStyle(
                                      color: Colors.black45,
                                      fontSize: 11,
                                    ),
                                  ),
                                  PopupMenuButton<String>(
                                    onSelected: (value) {
                                      if (value == 'rename') {
                                        _rename(item);
                                      } else if (value == 'delete') {
                                        _delete(item);
                                      }
                                    },
                                    itemBuilder: (_) => const [
                                      PopupMenuItem(
                                        value: 'rename',
                                        child: Text('Rename'),
                                      ),
                                      PopupMenuItem(
                                        value: 'delete',
                                        child: Text(
                                          'Delete',
                                          style: TextStyle(
                                            color: Colors.red,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              onTap: () => Navigator.of(context).pop(item),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.forum_outlined,
              size: 60,
              color: Color(0xFF9A83BE),
            ),
            SizedBox(height: 14),
            Text(
              'No saved conversations',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w900,
              ),
            ),
            SizedBox(height: 7),
            Text(
              'Your conversations with Meera '
              'will appear here.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.black54,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: onRetry,
              child: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}
