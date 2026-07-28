import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class WalletHistoryPage extends StatefulWidget {
  const WalletHistoryPage({super.key});

  @override
  State<WalletHistoryPage> createState() => _WalletHistoryPageState();
}

class _WalletHistoryPageState extends State<WalletHistoryPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get historyRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('walletHistory');

  String filter = 'all';
  final filters = const [
    'all',
    'ads',
    'topup',
    'audio_call',
    'video_call',
    'tasks',
    'conversion',
  ];

  String rangeMode = '7d';
  DateTime? fromDate;
  DateTime? toDate;

  double asDouble(dynamic v, {double def = 0}) {
    if (v == null) return def;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v.trim()) ?? def;
    return def;
  }

  String _two(int n) => n.toString().padLeft(2, '0');

  String _monthShort(int m) {
    const names = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec"
    ];
    if (m < 1 || m > 12) return "";
    return names[m - 1];
  }

  String _fmtTs(dynamic ts) {
    if (ts is! Timestamp) return '';
    final d = ts.toDate();
    return "${_two(d.day)} ${_monthShort(d.month)} ${d.year} • ${_two(d.hour)}:${_two(d.minute)}";
  }

  IconData _iconFor(String type) {
    if (type == 'conversion') return Icons.swap_horiz;
    if (type == 'ads') return Icons.play_circle_fill;
    if (type == 'topup') return Icons.add_card;
    if (type == 'tasks') return Icons.task_alt;
    if (type == 'audio_call') return Icons.call;
    if (type == 'video_call') return Icons.videocam;
    return Icons.account_balance_wallet;
  }

  Color _chipColor(String f) {
    if (f == 'all') return Colors.grey;
    if (f == 'ads') return Colors.purple;
    if (f == 'topup') return Colors.green;
    if (f == 'conversion') return Colors.blue;
    if (f.contains('call')) return Colors.orange;
    if (f == 'tasks') return Colors.teal;
    return Colors.grey;
  }

  String _titleFor(Map<String, dynamic> data) {
    final type = (data['type'] ?? '').toString();
    final title = (data['title'] ?? '').toString().trim();
    if (title.isNotEmpty) return title;
    return type.isEmpty ? "HISTORY" : type.toUpperCase();
  }

  String _buildLine(Map<String, dynamic> data) {
    final fromCoin = (data['fromCoin'] ?? '').toString();
    final toCoin = (data['toCoin'] ?? '').toString();

    final fromAmount = asDouble(data['fromAmount']).toStringAsFixed(0);
    final toAmount = asDouble(data['toAmount']).toStringAsFixed(0);
    final bonusPct = asDouble(data['bonusPct']).toStringAsFixed(0);

    if (fromCoin.isNotEmpty && toCoin.isNotEmpty) {
      var line = "$fromAmount $fromCoin  →  $toAmount $toCoin";
      if (bonusPct != "0") line += "  (+$bonusPct%)";
      return line;
    }
    if (toCoin.isNotEmpty) return "+$toAmount $toCoin";
    if (fromCoin.isNotEmpty) return "-$fromAmount $fromCoin";
    return "";
  }

  DateTime _startOfDay(DateTime d) => DateTime(d.year, d.month, d.day);
  DateTime _endOfDay(DateTime d) =>
      DateTime(d.year, d.month, d.day, 23, 59, 59, 999);

  DateTime get _rangeStart {
    final now = DateTime.now();
    if (rangeMode == 'custom' && fromDate != null) {
      return _startOfDay(fromDate!);
    }
    if (rangeMode == '14d') {
      return _startOfDay(now.subtract(const Duration(days: 14)));
    }
    if (rangeMode == '30d') {
      return _startOfDay(now.subtract(const Duration(days: 30)));
    }
    return _startOfDay(now.subtract(const Duration(days: 7)));
  }

  DateTime get _rangeEnd {
    final now = DateTime.now();
    if (rangeMode == 'custom' && toDate != null) return _endOfDay(toDate!);
    return _endOfDay(now);
  }

  String _rangeLabel() {
    if (rangeMode == '7d') return "Last 7 days";
    if (rangeMode == '14d') return "Last 14 days";
    if (rangeMode == '30d') return "Last 30 days";
    final f = fromDate;
    final t = toDate;
    if (f == null || t == null) return "Custom (pick dates)";
    return "${_two(f.day)} ${_monthShort(f.month)} ${f.year}  →  ${_two(t.day)} ${_monthShort(t.month)} ${t.year}";
  }

  Future<void> _pickFrom() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: fromDate ?? now,
      firstDate: DateTime(2000),
      lastDate: DateTime(now.year + 1),
    );
    if (picked == null) return;
    setState(() {
      fromDate = picked;
      if (toDate != null && toDate!.isBefore(picked)) {
        toDate = picked;
      }
      rangeMode = 'custom';
    });
  }

  Future<void> _pickTo() async {
    final now = DateTime.now();
    final init = toDate ?? fromDate ?? now;
    final picked = await showDatePicker(
      context: context,
      initialDate: init,
      firstDate: DateTime(2000),
      lastDate: DateTime(now.year + 1),
    );
    if (picked == null) return;
    setState(() {
      toDate = picked;
      if (fromDate != null && picked.isBefore(fromDate!)) {
        fromDate = picked;
      }
      rangeMode = 'custom';
    });
  }

  Widget _rangePill(String key, String text) {
    final selected = rangeMode == key;
    return ChoiceChip(
      label: Text(text),
      selected: selected,
      onSelected: (_) => setState(() => rangeMode = key),
      labelStyle: TextStyle(
        fontWeight: FontWeight.w800,
        color: selected ? Colors.white : null,
      ),
      selectedColor: Colors.black87,
      backgroundColor: Colors.grey.shade100,
      side: BorderSide(color: Colors.grey.shade300),
    );
  }

  @override
  Widget build(BuildContext context) {
    final q = historyRef
        .where('createdAt',
            isGreaterThanOrEqualTo: Timestamp.fromDate(_rangeStart))
        .where('createdAt', isLessThanOrEqualTo: Timestamp.fromDate(_rangeEnd))
        .orderBy('createdAt', descending: true)
        .limit(400);

    return Scaffold(
      appBar: AppBar(title: const Text("Wallet History")),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Date Range",
                    style: TextStyle(fontWeight: FontWeight.w900)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _rangePill('7d', '7 days'),
                    _rangePill('14d', '14 days'),
                    _rangePill('30d', '30 days'),
                    _rangePill('custom', 'Custom'),
                    if (rangeMode == 'custom') ...[
                      OutlinedButton.icon(
                        onPressed: _pickFrom,
                        icon: const Icon(Icons.calendar_month),
                        label: Text(fromDate == null
                            ? "From"
                            : "${_two(fromDate!.day)} ${_monthShort(fromDate!.month)}"),
                      ),
                      OutlinedButton.icon(
                        onPressed: _pickTo,
                        icon: const Icon(Icons.calendar_month),
                        label: Text(toDate == null
                            ? "To"
                            : "${_two(toDate!.day)} ${_monthShort(toDate!.month)}"),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _rangeLabel(),
                  style: TextStyle(
                      color: Colors.grey.shade700,
                      fontWeight: FontWeight.w700,
                      fontSize: 12),
                ),
              ],
            ),
          ),
          SizedBox(
            height: 54,
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
              scrollDirection: Axis.horizontal,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemCount: filters.length,
              itemBuilder: (context, i) {
                final f = filters[i];
                final selected = filter == f;
                final c = _chipColor(f);

                return ChoiceChip(
                  label: Text(f.toUpperCase()),
                  selected: selected,
                  onSelected: (_) => setState(() => filter = f),
                  labelStyle: TextStyle(
                    fontWeight: FontWeight.w800,
                    color: selected ? Colors.white : null,
                  ),
                  selectedColor: c,
                  backgroundColor: Colors.grey.shade100,
                  side: BorderSide(color: Colors.grey.shade300),
                );
              },
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: q.snapshots(),
              builder: (context, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snap.hasError) {
                  return Center(child: Text("Error: ${snap.error}"));
                }

                final docs = snap.data?.docs ?? [];
                final items = (filter == 'all')
                    ? docs
                    : docs
                        .where((d) =>
                            (d.data()['type'] ?? '').toString() == filter)
                        .toList();

                double totalIn = 0;
                double totalOut = 0;
                for (final d in items) {
                  final data = d.data();
                  final toCoin = (data['toCoin'] ?? '').toString();
                  final fromCoin = (data['fromCoin'] ?? '').toString();
                  final toAmt = asDouble(data['toAmount']);
                  final fromAmt = asDouble(data['fromAmount']);

                  if (toCoin.isNotEmpty && toAmt > 0) totalIn += toAmt;
                  if (fromCoin.isNotEmpty && fromAmt > 0) totalOut += fromAmt;
                }

                if (items.isEmpty) {
                  return const Center(
                      child: Text("No history in selected range"));
                }

                return ListView(
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 16),
                  children: [
                    Card(
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16)),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(14),
                                  color: Colors.green.shade50,
                                  border:
                                      Border.all(color: Colors.green.shade200),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text("Total Earned",
                                        style: TextStyle(
                                            fontWeight: FontWeight.w900)),
                                    const SizedBox(height: 4),
                                    Text(
                                      "+${totalIn.toStringAsFixed(0)}",
                                      style: TextStyle(
                                        fontWeight: FontWeight.w900,
                                        fontSize: 18,
                                        color: Colors.green.shade800,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(14),
                                  color: Colors.red.shade50,
                                  border:
                                      Border.all(color: Colors.red.shade200),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text("Total Spent",
                                        style: TextStyle(
                                            fontWeight: FontWeight.w900)),
                                    const SizedBox(height: 4),
                                    Text(
                                      "-${totalOut.toStringAsFixed(0)}",
                                      style: TextStyle(
                                        fontWeight: FontWeight.w900,
                                        fontSize: 18,
                                        color: Colors.red.shade800,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    ...items.map((doc) {
                      final data = doc.data();
                      final type = (data['type'] ?? '').toString();
                      final title = _titleFor(data);
                      final line = _buildLine(data);
                      final time = _fmtTs(data['createdAt']);

                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Card(
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16)),
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 10),
                            leading: CircleAvatar(
                              backgroundColor: Colors.grey.shade100,
                              child:
                                  Icon(_iconFor(type), color: Colors.black87),
                            ),
                            title: Text(title,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w900)),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (line.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text(line,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w700)),
                                ],
                                if (time.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Text(time,
                                      style: TextStyle(
                                          color: Colors.grey.shade700,
                                          fontSize: 12)),
                                ],
                              ],
                            ),
                          ),
                        ),
                      );
                    }),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
