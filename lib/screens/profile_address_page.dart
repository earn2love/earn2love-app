import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

class ProfileAddressPage extends StatefulWidget {
  const ProfileAddressPage({super.key});

  @override
  State<ProfileAddressPage> createState() => _ProfileAddressPageState();
}

class _ProfileAddressPageState extends State<ProfileAddressPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  final countryCtrl = TextEditingController();
  final postcodeCtrl = TextEditingController();
  final cityCtrl = TextEditingController();
  final houseCtrl = TextEditingController();
  final streetCtrl = TextEditingController();

  bool saving = false;

  // Simple country list (expand later)
  static const countries = [
    "United Kingdom",
    "India",
    "United States",
    "Australia",
    "UAE",
    "Other",
  ];

  String selectedCountry = "United Kingdom";

  String asString(dynamic v, {String def = ""}) =>
      v == null ? def : v.toString();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final snap = await userRef.get();
    final data = snap.data() ?? {};

    final addr = (data["address"] is Map) ? (data["address"] as Map) : {};

    selectedCountry = asString(addr["country"], def: selectedCountry);
    postcodeCtrl.text = asString(addr["postcode"]);
    cityCtrl.text = asString(addr["city"]);
    houseCtrl.text = asString(addr["house"]);
    streetCtrl.text = asString(addr["street"]);

    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    countryCtrl.dispose();
    postcodeCtrl.dispose();
    cityCtrl.dispose();
    houseCtrl.dispose();
    streetCtrl.dispose();
    super.dispose();
  }

  Future<void> save() async {
    setState(() => saving = true);

    await userRef.set({
      "address": {
        "country": selectedCountry.trim(),
        "postcode": postcodeCtrl.text.trim(),
        "city": cityCtrl.text.trim(),
        "house": houseCtrl.text.trim(),
        "street": streetCtrl.text.trim(),
      },
      "updatedAt": FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    if (!mounted) return;
    setState(() => saving = false);
    Navigator.pop(context);
  }

  Widget _field(String label, TextEditingController ctrl,
      {TextInputType? type}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: ctrl,
        keyboardType: type,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Address"),
      ),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Card(
            elevation: 0,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: Colors.orange.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.location_on, color: Colors.orange),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      "Fill your address (optional).\nLater we can use this for nearby matching.",
                      style: TextStyle(
                          color: Colors.grey.shade800,
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: selectedCountry,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: "Country",
            ),
            items: countries
                .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                .toList(),
            onChanged: saving
                ? null
                : (v) => setState(() => selectedCountry = v ?? selectedCountry),
          ),
          const SizedBox(height: 10),
          _field("Postcode", postcodeCtrl, type: TextInputType.text),
          _field("City / Town", cityCtrl, type: TextInputType.text),
          _field("House No / Flat", houseCtrl, type: TextInputType.text),
          _field("Street", streetCtrl, type: TextInputType.text),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            onPressed: saving ? null : save,
            icon: const Icon(Icons.save),
            label: Text(saving ? "Saving..." : "Save Address"),
          ),
          const SizedBox(height: 18),
        ],
      ),
    );
  }
}
