import 'package:flutter/material.dart';

import 'ai/screens/meera_chat_page.dart';

import 'play_together/screens/play_together_page.dart';
import 'screens/chat_list_page.dart';
import 'screens/home_page.dart';
import 'screens/profile_menu_page.dart';
import 'screens/wallet_page.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;

  final List<Widget> _pages = const [
    HomePage(),
    ChatListPage(),
    PlayTogetherPage(),
    WalletPage(),
    ProfileMenuPage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: _pages,
      ),
      floatingActionButton: FloatingActionButton(
        heroTag: 'global_meera_button',
        tooltip: 'Ask Meera',
        backgroundColor: const Color(0xFF7B4EFF),
        foregroundColor: Colors.white,
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => const MeeraChatPage(),
            ),
          );
        },
        child: const Icon(
          Icons.auto_awesome_rounded,
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) {
          if (value == _index) return;

          setState(() {
            _index = value;
          });
        },
        indicatorColor: const Color(0xFFECE3FF),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.chat_bubble_outline_rounded,
            ),
            selectedIcon: Icon(
              Icons.chat_bubble_rounded,
            ),
            label: 'Chats',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.sports_esports_outlined,
            ),
            selectedIcon: Icon(
              Icons.sports_esports_rounded,
            ),
            label: 'Games',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.account_balance_wallet_outlined,
            ),
            selectedIcon: Icon(
              Icons.account_balance_wallet_rounded,
            ),
            label: 'Wallet',
          ),
          NavigationDestination(
            icon: Icon(
              Icons.person_outline_rounded,
            ),
            selectedIcon: Icon(
              Icons.person_rounded,
            ),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
