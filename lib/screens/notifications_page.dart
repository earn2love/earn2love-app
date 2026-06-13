import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  String _filter = 'all';

  CollectionReference<Map<String, dynamic>> get _notificationsRef =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(FirebaseAuth.instance.currentUser!.uid)
          .collection('notifications');

  Future<void> _markAllAsRead() async {
    final unread = await _notificationsRef.where('isRead', isEqualTo: false).get();

    if (unread.docs.isEmpty) return;

    final batch = FirebaseFirestore.instance.batch();

    for (final doc in unread.docs) {
      batch.update(doc.reference, {
        'isRead': true,
        'readAt': FieldValue.serverTimestamp(),
      });
    }

    final userRef = FirebaseFirestore.instance
        .collection('users')
        .doc(FirebaseAuth.instance.currentUser!.uid);

    batch.set(userRef, {
      'counters': {
        'unreadBellNotifications': 0,
      },
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await batch.commit();
  }

  Future<void> _markOneAsRead(DocumentReference<Map<String, dynamic>> ref) async {
    final snap = await ref.get();
    final data = snap.data() ?? {};
    final alreadyRead = data['isRead'] == true;
    if (alreadyRead) return;

    final batch = FirebaseFirestore.instance.batch();
    batch.update(ref, {
      'isRead': true,
      'readAt': FieldValue.serverTimestamp(),
    });

    final userRef = FirebaseFirestore.instance
        .collection('users')
        .doc(FirebaseAuth.instance.currentUser!.uid);

    batch.update(userRef, {
      'counters.unreadBellNotifications': FieldValue.increment(-1),
      'updatedAt': FieldValue.serverTimestamp(),
    });

    await batch.commit();
  }

  IconData _iconForType(String type) {
    switch (type) {
      case 'payment_success':
      case 'topup_success':
        return Icons.payments_rounded;
      case 'payment_failed':
      case 'topup_failed':
        return Icons.error_outline_rounded;
      case 'withdraw_requested':
      case 'withdraw_success':
      case 'withdraw_failed':
        return Icons.account_balance_wallet_rounded;
      case 'conversion_success':
      case 'conversion_failed':
        return Icons.swap_horiz_rounded;
      case 'subscription_activated':
      case 'subscription_expired':
        return Icons.workspace_premium_rounded;
      case 'admin_alert':
        return Icons.admin_panel_settings_rounded;
      case 'report_update':
        return Icons.flag_rounded;
      case 'system_alert':
        return Icons.info_outline_rounded;
      case 'follow_accepted':
        return Icons.favorite_rounded;
      default:
        return Icons.notifications_active_rounded;
    }
  }

  Color _iconBgForType(String type) {
    switch (type) {
      case 'payment_success':
      case 'topup_success':
      case 'subscription_activated':
        return const Color(0xFFE9F9EE);
      case 'payment_failed':
      case 'topup_failed':
      case 'withdraw_failed':
      case 'conversion_failed':
      case 'report_update':
        return const Color(0xFFFFEFEF);
      case 'withdraw_requested':
      case 'withdraw_success':
      case 'conversion_success':
        return const Color(0xFFFFF6E5);
      case 'admin_alert':
      case 'system_alert':
        return const Color(0xFFEFF3FF);
      case 'follow_accepted':
        return const Color(0xFFFFEEF7);
      default:
        return const Color(0xFFF2EEFF);
    }
  }

  Color _iconColorForType(String type) {
    switch (type) {
      case 'payment_success':
      case 'topup_success':
      case 'subscription_activated':
        return const Color(0xFF1E8E3E);
      case 'payment_failed':
      case 'topup_failed':
      case 'withdraw_failed':
      case 'conversion_failed':
      case 'report_update':
        return const Color(0xFFD93025);
      case 'withdraw_requested':
      case 'withdraw_success':
      case 'conversion_success':
        return const Color(0xFFB26A00);
      case 'admin_alert':
      case 'system_alert':
        return const Color(0xFF3367D6);
      case 'follow_accepted':
        return const Color(0xFFE91E63);
      default:
        return const Color(0xFF7B4EFF);
    }
  }

  String _timeAgo(Timestamp? ts) {
    if (ts == null) return '';
    final dt = ts.toDate();
    final diff = DateTime.now().difference(dt);

    if (diff.inSeconds < 60) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return '${dt.day}/${dt.month}/${dt.year}';
  }

  String _sectionLabel(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(dt.year, dt.month, dt.day);

    if (day == today) return 'Today';
    if (day == today.subtract(const Duration(days: 1))) return 'Yesterday';
    if (day.isAfter(today.subtract(const Duration(days: 7)))) return 'This Week';
    return 'Earlier';
  }

  bool _matchesFilter(Map<String, dynamic> data) {
    if (_filter == 'all') return true;
    final category = (data['category'] ?? '').toString().trim();
    return category == _filter;
  }

  Widget _filterChip(String id, String label) {
    final selected = _filter == id;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => setState(() => _filter = id),
        labelStyle: TextStyle(
          color: selected ? Colors.white : const Color(0xFF4A465F),
          fontWeight: FontWeight.w700,
          fontSize: 12.5,
        ),
        selectedColor: const Color(0xFF7B4EFF),
        backgroundColor: Colors.white,
        side: BorderSide(
          color: selected ? const Color(0xFF7B4EFF) : const Color(0xFFE5DDF4),
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
        ),
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: const VisualDensity(horizontal: -1, vertical: -1),
      ),
    );
  }

  Widget _buildHeader(int unreadCount) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 14, 16, 10),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF8A63FF), Color(0xFFFF5FA2)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFAE8BFF).withOpacity(0.26),
            blurRadius: 22,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              borderRadius: BorderRadius.circular(18),
            ),
            alignment: Alignment.center,
            child: const Icon(
              Icons.notifications_active_rounded,
              color: Colors.white,
              size: 28,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Notifications',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 21,
                    fontWeight: FontWeight.w900,
                    height: 1.05,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  unreadCount > 0
                      ? '$unreadCount unread alerts waiting for you'
                      : 'You are all caught up',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.92),
                    fontSize: 12.8,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          if (unreadCount > 0)
            TextButton(
              onPressed: _markAllAsRead,
              style: TextButton.styleFrom(
                backgroundColor: Colors.white.withOpacity(0.18),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              child: const Text(
                'Mark all',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 12.5,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    return SizedBox(
      height: 40,
      child: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        scrollDirection: Axis.horizontal,
        children: [
          _filterChip('all', 'All'),
          _filterChip('payment', 'Payments'),
          _filterChip('wallet', 'Wallet'),
          _filterChip('subscription', 'Premium'),
          _filterChip('admin', 'Admin'),
          _filterChip('report', 'Reports'),
          _filterChip('system', 'System'),
          _filterChip('request', 'Requests'),
        ],
      ),
    );
  }

  Widget _emptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 26),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFD8C9F4).withOpacity(0.30),
                    blurRadius: 18,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.notifications_none_rounded,
                size: 48,
                color: Color(0xFF7B4EFF),
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'No notifications yet',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w900,
                color: Color(0xFF3F355B),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Payment alerts, admin updates, report status, subscription info and other system updates will appear here.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13.5,
                height: 1.45,
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _notificationTile(QueryDocumentSnapshot<Map<String, dynamic>> doc) {
    final data = doc.data();
    final isRead = data['isRead'] == true;
    final type = (data['type'] ?? '').toString();
    final title = (data['title'] ?? 'Notification').toString();
    final body = (data['body'] ?? '').toString();
    final createdAt = data['createdAt'] as Timestamp?;
    final timeText = _timeAgo(createdAt);

    final icon = _iconForType(type);
    final bg = _iconBgForType(type);
    final iconColor = _iconColorForType(type);

    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () async {
        await _markOneAsRead(doc.reference);
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
        decoration: BoxDecoration(
          color: isRead ? Colors.white.withOpacity(0.88) : Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: isRead ? const Color(0xFFF0EAF8) : const Color(0xFFE8DDFC),
            width: 1.1,
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFD8CBEF).withOpacity(isRead ? 0.14 : 0.20),
              blurRadius: 16,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: bg,
                borderRadius: BorderRadius.circular(16),
              ),
              alignment: Alignment.center,
              child: Icon(icon, color: iconColor, size: 25),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: TextStyle(
                            fontSize: 14.7,
                            fontWeight: isRead ? FontWeight.w800 : FontWeight.w900,
                            color: const Color(0xFF31284A),
                            height: 1.2,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        timeText,
                        style: TextStyle(
                          fontSize: 11.3,
                          color: Colors.grey.shade600,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  if (body.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      body,
                      style: TextStyle(
                        fontSize: 12.9,
                        height: 1.35,
                        color: Colors.grey.shade800,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (!isRead)
              Container(
                width: 10,
                height: 10,
                margin: const EdgeInsets.only(top: 6),
                decoration: const BoxDecoration(
                  color: Color(0xFFFF4D94),
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _groupedList(List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) {
    final filtered = docs.where((d) => _matchesFilter(d.data())).toList();

    if (filtered.isEmpty) return _emptyState();

    String? lastSection;

    return ListView.builder(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 18),
      itemCount: filtered.length,
      itemBuilder: (context, index) {
        final doc = filtered[index];
        final data = doc.data();
        final createdAt = data['createdAt'] as Timestamp?;
        final date = createdAt?.toDate() ?? DateTime.now();
        final section = _sectionLabel(date);

        final showHeader = section != lastSection;
        lastSection = section;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (showHeader) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 12, 4, 10),
                child: Text(
                  section,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF4C4068),
                  ),
                ),
              ),
            ],
            _notificationTile(doc),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      return const Scaffold(
        backgroundColor: Color(0xFFF7F2FB),
        body: Center(
          child: Text(
            'Please login again',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF7F2FB),
      body: SafeArea(
        child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: FirebaseFirestore.instance
              .collection('users')
              .doc(uid)
              .collection('notifications')
              .orderBy('createdAt', descending: true)
              .snapshots(),
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(
                child: CircularProgressIndicator.adaptive(),
              );
            }

            final docs = snap.data?.docs ?? [];
            final unreadCount =
                docs.where((d) => d.data()['isRead'] != true).length;

            return Column(
              children: [
                _buildHeader(unreadCount),
                _buildFilters(),
                const SizedBox(height: 6),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: () async {},
                    child: docs.isEmpty ? _emptyState() : _groupedList(docs),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}