import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class SupportPage extends StatefulWidget {
  const SupportPage({super.key});

  @override
  State<SupportPage> createState() => _SupportPageState();
}

class _SupportPageState extends State<SupportPage> {
  static const _background = Color(0xFFF8F4FC);
  static const _purple = Color(0xFF7B4EFF);
  static const _pink = Color(0xFFFF4D91);

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get _ticketsReference =>
      FirebaseFirestore.instance.collection('supportTickets');

  final TextEditingController _subjectController = TextEditingController();

  final TextEditingController _messageController = TextEditingController();

  bool _sending = false;
  String? _status;

  Future<void> _submitTicket() async {
    final subject = _subjectController.text.trim();
    final message = _messageController.text.trim();

    if (subject.isEmpty || message.isEmpty) {
      setState(() {
        _status = 'Enter a subject and describe the issue.';
      });
      return;
    }

    setState(() {
      _sending = true;
      _status = null;
    });

    try {
      await _ticketsReference.add({
        'uid': uid,
        'subject': subject,
        'message': message,
        'source': 'mobile_app',
        'status': 'open',
        'createdAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      });

      _subjectController.clear();
      _messageController.clear();

      if (!mounted) return;

      setState(() {
        _status = 'Your support ticket was submitted.';
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _status = 'Ticket submission failed: $error';
      });
    } finally {
      if (mounted) {
        setState(() => _sending = false);
      }
    }
  }

  void _applyCategory(String category) {
    _subjectController.text = category;
    _messageController.clear();
  }

  @override
  void dispose() {
    _subjectController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _background,
      appBar: AppBar(
        backgroundColor: _background,
        elevation: 0,
        scrolledUnderElevation: 0,
        title: const Text(
          'Meera Support',
          style: TextStyle(
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
          16,
          8,
          16,
          30,
        ),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [_purple, _pink],
              ),
              borderRadius: BorderRadius.circular(26),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      backgroundColor: Colors.white24,
                      child: Icon(
                        Icons.auto_awesome,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(width: 12),
                    Text(
                      'Hello, I’m Meera',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 21,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 12),
                Text(
                  'Choose a topic or submit a detailed '
                  'ticket. A support agent can review '
                  'account-specific issues.',
                  style: TextStyle(
                    color: Colors.white,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'Popular topics',
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _TopicChip(
                label: 'Account',
                icon: Icons.person_outline,
                onTap: () => _applyCategory('Account issue'),
              ),
              _TopicChip(
                label: 'Chat',
                icon: Icons.chat_bubble_outline,
                onTap: () => _applyCategory('Chat issue'),
              ),
              _TopicChip(
                label: 'Calls',
                icon: Icons.call_outlined,
                onTap: () => _applyCategory('Call issue'),
              ),
              _TopicChip(
                label: 'Games',
                icon: Icons.sports_esports_outlined,
                onTap: () => _applyCategory('Games issue'),
              ),
              _TopicChip(
                label: 'Wallet',
                icon: Icons.account_balance_wallet_outlined,
                onTap: () => _applyCategory('Wallet issue'),
              ),
              _TopicChip(
                label: 'Safety',
                icon: Icons.shield_outlined,
                onTap: () => _applyCategory('Safety issue'),
              ),
            ],
          ),
          const SizedBox(height: 22),
          Card(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(22),
            ),
            child: Padding(
              padding: const EdgeInsets.all(17),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Open a support ticket',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Do not include passwords, payment '
                    'card details or identity-document '
                    'numbers.',
                    style: TextStyle(
                      color: Colors.black54,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: 15),
                  TextField(
                    controller: _subjectController,
                    decoration: const InputDecoration(
                      labelText: 'Subject',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _messageController,
                    minLines: 5,
                    maxLines: 8,
                    decoration: const InputDecoration(
                      labelText: 'Describe the issue',
                      alignLabelWithHint: true,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: _sending ? null : _submitTicket,
                      icon: _sending
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Icon(Icons.send_outlined),
                      label: Text(
                        _sending ? 'Submitting...' : 'Submit ticket',
                      ),
                    ),
                  ),
                  if (_status != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _status!,
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: _status!.toLowerCase().contains('failed')
                            ? Colors.red
                            : Colors.green.shade700,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TopicChip extends StatelessWidget {
  const _TopicChip({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
      onPressed: onTap,
    );
  }
}
