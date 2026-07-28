import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ReportHistoryPage extends StatefulWidget {
  const ReportHistoryPage({super.key});

  @override
  State<ReportHistoryPage> createState() => _ReportHistoryPageState();
}

class _ReportHistoryPageState extends State<ReportHistoryPage> {
  static const _bg = Color(0xFF0F1115);
  static const _card = Color(0xFF171A21);
  static const _border = Color(0xFF2A3140);
  static const _muted = Color(0xFF9AA3B2);

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  bool showMadeByMe = true;

  Stream<QuerySnapshot<Map<String, dynamic>>> _stream() {
    final ref = FirebaseFirestore.instance.collection('reports');

    if (showMadeByMe) {
      return ref
          .where('reporterUid', isEqualTo: uid)
          .orderBy('createdAt', descending: true)
          .snapshots();
    } else {
      return ref
          .where('targetUid', isEqualTo: uid)
          .orderBy('createdAt', descending: true)
          .snapshots();
    }
  }

  Widget _chip(String text, bool selected, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: selected
              ? const LinearGradient(
                  colors: [Color(0xFF8B5CFF), Color(0xFFFF4D8D)],
                )
              : null,
          color: selected ? null : _card,
          border: Border.all(color: selected ? Colors.transparent : _border),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: selected ? Colors.white : _muted,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }

  void _openDetails(BuildContext context, Map<String, dynamic> m) {
    final issue = (m['issue'] ?? m['reason'] ?? 'Issue').toString();
    final status = (m['status'] ?? 'pending').toString();
    final description = (m['description'] ?? '').toString();
    final createdAt = m['createdAt'] as Timestamp?;
    final time = createdAt?.toDate().toString() ?? 'Unknown';

    showModalBottomSheet(
      context: context,
      backgroundColor: _card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
      ),
      builder: (_) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Report Details',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 14),
                Text('Issue: $issue',
                    style: const TextStyle(color: Colors.white)),
                const SizedBox(height: 8),
                Text('Status: $status', style: const TextStyle(color: _muted)),
                const SizedBox(height: 8),
                Text('Created: $time', style: const TextStyle(color: _muted)),
                if (description.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(description,
                      style: const TextStyle(color: Colors.white70)),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        title: const Text('Report History'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 8),
            child: Row(
              children: [
                _chip('Made by me', showMadeByMe, () {
                  setState(() => showMadeByMe = true);
                }),
                const SizedBox(width: 8),
                _chip('Against me', !showMadeByMe, () {
                  setState(() => showMadeByMe = false);
                }),
              ],
            ),
          ),
          Expanded(
            child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: _stream(),
              builder: (context, snap) {
                if (!snap.hasData) {
                  return const Center(child: CircularProgressIndicator());
                }

                final docs = snap.data!.docs;

                if (docs.isEmpty) {
                  return const Center(
                    child: Text(
                      'No reports found',
                      style: TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  );
                }

                return ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: docs.length,
                  itemBuilder: (context, i) {
                    final m = docs[i].data();
                    final issue =
                        (m['issue'] ?? m['reason'] ?? 'Issue').toString();
                    final status = (m['status'] ?? 'pending').toString();

                    final otherUid = showMadeByMe
                        ? (m['targetUid'] ?? '').toString()
                        : (m['reporterUid'] ?? '').toString();

                    if (otherUid.isEmpty) {
                      return Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        decoration: BoxDecoration(
                          color: _card,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: _border),
                        ),
                        child: ListTile(
                          onTap: () => _openDetails(context, m),
                          title: const Text(
                            'User',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          subtitle: Text(
                            '$issue\nStatus: $status',
                            style: const TextStyle(
                              color: _muted,
                              height: 1.35,
                            ),
                          ),
                          trailing: const Icon(
                            Icons.keyboard_arrow_right,
                            color: Colors.white54,
                          ),
                        ),
                      );
                    }

                    return FutureBuilder<
                        DocumentSnapshot<Map<String, dynamic>>>(
                      future: FirebaseFirestore.instance
                          .collection('users')
                          .doc(otherUid)
                          .get(),
                      builder: (context, userSnap) {
                        final user = userSnap.data?.data() ?? {};
                        final name =
                            (user['displayName'] ?? user['name'] ?? 'User')
                                .toString();

                        return Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(
                            color: _card,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: _border),
                          ),
                          child: ListTile(
                            onTap: () => _openDetails(context, m),
                            title: Text(
                              name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            subtitle: Text(
                              '$issue\nStatus: $status',
                              style: const TextStyle(
                                color: _muted,
                                height: 1.35,
                              ),
                            ),
                            trailing: const Icon(
                              Icons.keyboard_arrow_right,
                              color: Colors.white54,
                            ),
                          ),
                        );
                      },
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
