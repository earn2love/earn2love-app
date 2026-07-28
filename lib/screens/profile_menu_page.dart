import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'auth_gate.dart'; // ✅ ADD (same folder lo unte ok)
import 'profile_page.dart';
import 'profile_personal_page.dart';
import 'profile_contact_page.dart';
import 'profile_address_page.dart';
import 'profile_bio_page.dart';
import 'profile_photo_privacy_page.dart';
import 'support_page.dart';

class ProfileMenuPage extends StatelessWidget {
  const ProfileMenuPage({super.key});

  Future<void> _logout(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Logout"),
        content: const Text("Are you sure you want to logout?"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text("Logout"),
          ),
        ],
      ),
    );

    if (ok == true) {
      await FirebaseAuth.instance.signOut();

      if (!context.mounted) return;

      // ✅ IMPORTANT: clear stack so HomePage/AppShell streams stop immediately
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const AuthGate()),
        (r) => false,
      );
    }
  }

  Widget _sectionTitle(String text) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
      child: Text(
        text,
        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14),
      ),
    );
  }

  Widget _tile({
    required BuildContext context,
    required IconData icon,
    required String title,
    String? subtitle,
    required VoidCallback onTap,
    Color? iconColor,
  }) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor:
              (iconColor ?? Colors.deepPurple).withValues(alpha: 0.12),
          child: Icon(icon, color: iconColor ?? Colors.deepPurple),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
        subtitle: subtitle == null ? null : Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Account Settings")),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          _sectionTitle("Profile"),
          _tile(
            context: context,
            icon: Icons.person,
            title: "My Profile",
            subtitle: "Photos, name, bio preview",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfilePage()),
            ),
          ),
          _tile(
            context: context,
            icon: Icons.badge_outlined,
            title: "Personal Details",
            subtitle: "Gender, DOB, etc",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfilePersonalPage()),
            ),
          ),
          _tile(
            context: context,
            icon: Icons.description_outlined,
            title: "Bio",
            subtitle: "Edit your bio & interests",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfileBioPage()),
            ),
          ),
          _sectionTitle("Contact & Address"),
          _tile(
            context: context,
            icon: Icons.phone_outlined,
            title: "Contact",
            subtitle: "Email / Phone / Social links",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfileContactPage()),
            ),
          ),
          _tile(
            context: context,
            icon: Icons.location_on_outlined,
            title: "Address",
            subtitle: "City, state, country",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfileAddressPage()),
            ),
          ),
          _sectionTitle("Privacy & Safety"),
          _tile(
            context: context,
            icon: Icons.privacy_tip_outlined,
            title: "Photo & Privacy",
            subtitle: "Public/private, view options",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (_) => const ProfilePhotoPrivacyPage()),
            ),
          ),
          _sectionTitle("Support"),
          _tile(
            context: context,
            icon: Icons.support_agent,
            title: "Help & Support",
            subtitle: "Contact us / FAQ",
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SupportPage()),
            ),
          ),
          const SizedBox(height: 6),
          Card(
            elevation: 0,
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: Colors.red.withValues(alpha: 0.12),
                child: const Icon(Icons.logout, color: Colors.red),
              ),
              title: const Text("Logout",
                  style: TextStyle(fontWeight: FontWeight.w900)),
              subtitle: const Text("Sign out from this device"),
              onTap: () => _logout(context),
            ),
          ),
        ],
      ),
    );
  }
}
