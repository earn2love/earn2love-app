import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class SupportPage extends StatefulWidget {
  const SupportPage({super.key});

  @override
  State<SupportPage> createState() => _SupportPageState();
}

class _SupportPageState extends State<SupportPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  CollectionReference<Map<String, dynamic>> get ticketsRef =>
      FirebaseFirestore.instance.collection('supportTickets');

  final subjectCtrl = TextEditingController();
  final messageCtrl = TextEditingController();

  bool sending = false;
  String? status;

  Future<void> submitTicket() async {
    final subject = subjectCtrl.text.trim();
    final msg = messageCtrl.text.trim();

    if (subject.isEmpty || msg.isEmpty) {
      setState(() => status = "Enter subject & message");
      return;
    }

    setState(() {
      sending = true;
      status = null;
    });

    try {
      await ticketsRef.add({
        'uid': uid,
        'subject': subject,
        'message': msg,
        'status': 'open',
        'createdAt': FieldValue.serverTimestamp(),
      });

      subjectCtrl.clear();
      messageCtrl.clear();
      status = "Ticket submitted ✅";
    } catch (e) {
      status = "Failed: $e";
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  @override
  void dispose() {
    subjectCtrl.dispose();
    messageCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Help & Support")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Safety & Help",
                      style:
                          TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  SizedBox(height: 8),
                  Text(
                      "• Report abuse → we review\n• After 3 reports → 24hrs freeze (Phase 2)\n• Help center & rules will be added"),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text("Contact Support",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          TextField(
            controller: subjectCtrl,
            decoration: const InputDecoration(
              labelText: "Subject",
              border: OutlineInputBorder(),
              hintText: "Login / Coins / Chat / Abuse report",
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: messageCtrl,
            maxLines: 5,
            decoration: const InputDecoration(
              labelText: "Message",
              border: OutlineInputBorder(),
              hintText: "Explain the issue clearly...",
            ),
          ),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            onPressed: sending ? null : submitTicket,
            icon: const Icon(Icons.send),
            label: Text(sending ? "Sending..." : "Submit Ticket"),
          ),
          if (status != null) ...[
            const SizedBox(height: 12),
            Text(
              status!,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontWeight: FontWeight.w800,
                color:
                    status!.toLowerCase().contains("fail") ? Colors.red : null,
              ),
            ),
          ],
          const SizedBox(height: 20),
          const Divider(),
          const SizedBox(height: 10),
          const Text("Quick FAQs (Phase 1)",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          const Text(
              "Q: Coins not updating?\nA: Check internet + reload. WalletHistory shows changes."),
          const SizedBox(height: 8),
          const Text(
              "Q: Permission denied?\nA: Firestore Rules must allow your UID access."),
        ],
      ),
    );
  }
}
