import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'profile_personal_page.dart';
import 'profile_contact_page.dart';
import 'support_page.dart';
import 'withdraw_page.dart';
import 'profile_page.dart';

class ProfileMenuPage extends StatelessWidget {
  const ProfileMenuPage({super.key});

  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  // ------- safe helpers -------
  String asString(dynamic v, {String def = ''}) {
    if (v == null) return def;
    final s = v.toString().trim();
    return s.isEmpty ? def : s;
  }

  List<String> asStringList(dynamic v) {
    if (v is List) {
      return v.map((e) => e.toString()).where((e) => e.trim().isNotEmpty).toList();
    }
    return [];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Account Settings"),
      ),
      body: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: userRef.snapshots(),
        builder: (context, snap) {
          final data = snap.data?.data() ?? {};

          final name = asString(data['displayName'], def: 'My Account');
          final bio = asString(data['bio'], def: 'Tap to set bio');
          final photos = asStringList(data['photoUrls']);
          final photo = photos.isNotEmpty ? photos.first : '';

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              // ---------- TOP PROFILE CARD ----------
              Card(
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      InkWell(
                        borderRadius: BorderRadius.circular(999),
                        onTap: () {
                          Navigator.push(context, MaterialPageRoute(builder: (_) => ProfilePage()));
                        },
                        child: CircleAvatar(
                          radius: 30,
                          backgroundColor: Colors.grey.shade200,
                          backgroundImage: photo.isEmpty ? null : NetworkImage(photo),
                          child: photo.isEmpty
                              ? const Icon(Icons.person, size: 30)
                              : null,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: InkWell(
                          onTap: () {
                            Navigator.push(context, MaterialPageRoute(builder: (_) => ProfilePage()));
                          },
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                name,
                                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                bio,
                                style: TextStyle(color: Colors.grey.shade700, fontWeight: FontWeight.w600),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(999),
                                      color: Colors.pink.shade50,
                                      border: Border.all(color: Colors.pink.shade200),
                                    ),
                                    child: Text(
                                      "My Profile",
                                      style: TextStyle(
                                        fontWeight: FontWeight.w900,
                                        color: Colors.pink.shade800,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Text(
                                    "Tap to edit",
                                    style: TextStyle(color: Colors.grey.shade600, fontWeight: FontWeight.w700, fontSize: 12),
                                  ),
                                ],
                              )
                            ],
                          ),
                        ),
                      ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 14),

              // ---------- MENU ----------
              const Text(
                "Account Settings",
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 10),

              _menuTile(
                context,
                icon: Icons.person,
                title: "My Profile",
                subtitle: "Profile pic, display name, bio, privacy settings",
                page: ProfilePage(),
              ),

              _menuTile(
                context,
                icon: Icons.badge,
                title: "Personal Info",
                subtitle: "DOB, gender, address, languages, education, hobbies",
                page: const ProfilePersonalPage(),
              ),

              _menuTile(
                context,
                icon: Icons.call,
                title: "Contact Info",
                subtitle: "Phone, email, emergency contact",
                page: const ProfileContactPage(),
              ),

              _menuTile(
                context,
                icon: Icons.account_balance,
                title: "Bank Account Details",
                subtitle: "Account holder, number, IFSC / sort code, etc.",
                page: const BankDetailsPage(),
              ),

              _menuTile(
                context,
                icon: Icons.wallet,
                title: "Withdrawals",
                subtitle: "Diamond → currency • withdrawals • pending",
                page: const WithdrawPage(),
              ),

              _menuTile(
                context,
                icon: Icons.gavel,
                title: "Rules & Regulations",
                subtitle: "Rates, policies, conditions (language support later)",
                page: const RulesPage(),
              ),

              _menuTile(
                context,
                icon: Icons.support_agent,
                title: "Help & Support",
                subtitle: "FAQs, reviews, quick help, support bot later",
                page: const SupportPage(),
              ),

              const SizedBox(height: 20),
            ],
          );
        },
      ),
    );
  }

  Widget _menuTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required Widget page,
  }) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.grey.shade100,
          child: Icon(icon, color: Colors.black87),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => page));
        },
      ),
    );
  }
}

// ======================================================
// Dummy pages (so app won’t crash with missing files)
// Later you can replace with real pages.
// ======================================================

class BankDetailsPage extends StatelessWidget {
  const BankDetailsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Bank Account Details")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            child: const ListTile(
              leading: Icon(Icons.info_outline),
              title: Text("Coming soon"),
              subtitle: Text("We’ll connect this with Withdrawals page later."),
            ),
          ),
          const SizedBox(height: 10),
          _field("Account Holder Name"),
          _field("Account Number"),
          _field("Bank Name"),
          _field("IFSC / Sort Code"),
          _field("City / Branch"),
          const SizedBox(height: 14),
          ElevatedButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Saved (dummy) ✅")),
              );
            },
            child: const Text("Save"),
          ),
        ],
      ),
    );
  }

  Widget _field(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }
}

class RulesPage extends StatelessWidget {
  const RulesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Rules & Regulations")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text("Conversion & Policies", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  SizedBox(height: 8),
                  Text("• Silver → Gold (country based rates)"),
                  Text("• Gold → Diamond (country based rates)"),
                  Text("• Direct Silver → Diamond not allowed"),
                  SizedBox(height: 10),
                  Text("More rules, terms, conditions and language-based display later."),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
