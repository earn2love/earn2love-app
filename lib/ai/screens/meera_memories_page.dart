import 'package:flutter/material.dart';

import '../models/meera_message.dart';
import '../services/meera_service.dart';

class MeeraMemoriesPage extends StatefulWidget {
  const MeeraMemoriesPage({
    super.key,
  });

  @override
  State<MeeraMemoriesPage> createState() => _MeeraMemoriesPageState();
}

class _MeeraMemoriesPageState extends State<MeeraMemoriesPage> {
  final MeeraService _service = MeeraService();

  bool _loading = true;
  String? _error;
  List<MeeraMemory> _memories = [];

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
      final memories = await _service.listMemories();

      if (!mounted) return;

      setState(() {
        _memories = memories;
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

  Future<void> _addMemory() async {
    final controller = TextEditingController();

    final content = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text(
            'What should Meera remember?',
          ),
          content: TextField(
            controller: controller,
            autofocus: true,
            minLines: 2,
            maxLines: 5,
            maxLength: 500,
            decoration: const InputDecoration(
              hintText: 'Example: I prefer Telugu-English replies.',
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
              child: const Text('Remember'),
            ),
          ],
        );
      },
    );

    controller.dispose();

    if (content == null || content.isEmpty) return;

    await _service.saveMemory(content: content);
    await _load();
  }

  Future<void> _deleteMemory(
    MeeraMemory memory,
  ) async {
    await _service.deleteMemory(memory.id);
    await _load();
  }

  Future<void> _clearAll() async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) {
            return AlertDialog(
              title: const Text(
                'Clear all Meera memories?',
              ),
              content: const Text(
                'This removes every preference '
                'you explicitly asked Meera to remember.',
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
                  child: const Text('Clear all'),
                ),
              ],
            );
          },
        ) ??
        false;

    if (!confirmed) return;

    await _service.clearMemories();
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F4FC),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF8F4FC),
        title: const Text(
          'Meera memory',
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
        actions: [
          if (_memories.isNotEmpty)
            IconButton(
              tooltip: 'Clear all memories',
              onPressed: _clearAll,
              icon: const Icon(
                Icons.delete_sweep_outlined,
              ),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addMemory,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Add memory'),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(30),
                    child: Text(
                      _error!,
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : _memories.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(30),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.psychology_outlined,
                              size: 62,
                              color: Color(0xFF9A83BE),
                            ),
                            SizedBox(height: 14),
                            Text(
                              'No saved memories',
                              style: TextStyle(
                                fontSize: 19,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            SizedBox(height: 7),
                            Text(
                              'Only information you '
                              'explicitly save appears here.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Colors.black54,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(
                        12,
                        12,
                        12,
                        100,
                      ),
                      itemCount: _memories.length,
                      itemBuilder: (context, index) {
                        final memory = _memories[index];

                        return Card(
                          elevation: 0,
                          margin: const EdgeInsets.only(
                            bottom: 8,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(
                              18,
                            ),
                          ),
                          child: ListTile(
                            leading: const CircleAvatar(
                              backgroundColor: Color(0xFFE9DFFF),
                              child: Icon(
                                Icons.memory_rounded,
                                color: Color(0xFF7B4EFF),
                              ),
                            ),
                            title: Text(memory.content),
                            subtitle: Text(memory.category),
                            trailing: IconButton(
                              tooltip: 'Forget',
                              onPressed: () => _deleteMemory(
                                memory,
                              ),
                              icon: const Icon(
                                Icons.delete_outline_rounded,
                              ),
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
