import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/locale_service.dart';
import 'profile_address_page.dart';

class ProfilePersonalPage extends StatefulWidget {
  const ProfilePersonalPage({super.key});

  @override
  State<ProfilePersonalPage> createState() => _ProfilePersonalPageState();
}

class _ProfilePersonalPageState extends State<ProfilePersonalPage> {
  String get uid => FirebaseAuth.instance.currentUser!.uid;

  DocumentReference<Map<String, dynamic>> get userRef =>
      FirebaseFirestore.instance.collection('users').doc(uid);

  // ---------- language list (22 scheduled + English) ----------
  static const List<Map<String, String>> _languages = [
    {"code": "en", "name": "English"},
    {"code": "as", "name": "Assamese"},
    {"code": "bn", "name": "Bengali"},
    {"code": "brx", "name": "Bodo"},
    {"code": "doi", "name": "Dogri"},
    {"code": "gu", "name": "Gujarati"},
    {"code": "hi", "name": "Hindi"},
    {"code": "kn", "name": "Kannada"},
    {"code": "ks", "name": "Kashmiri"},
    {"code": "kok", "name": "Konkani"},
    {"code": "mai", "name": "Maithili"},
    {"code": "ml", "name": "Malayalam"},
    {"code": "mni", "name": "Meitei (Manipuri)"},
    {"code": "mr", "name": "Marathi"},
    {"code": "ne", "name": "Nepali"},
    {"code": "or", "name": "Odia"},
    {"code": "pa", "name": "Punjabi"},
    {"code": "sa", "name": "Sanskrit"},
    {"code": "sat", "name": "Santali"},
    {"code": "sd", "name": "Sindhi"},
    {"code": "ta", "name": "Tamil"},
    {"code": "te", "name": "Telugu"},
    {"code": "ur", "name": "Urdu"},
  ];

  // ---------- helpers ----------
  int asInt(dynamic v, {int def = 0}) {
    if (v == null) return def;
    if (v is int) return v;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v.trim()) ?? def;
    return def;
  }

  String asString(dynamic v, {String def = ""}) {
    if (v == null) return def;
    return v.toString();
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

  Color _soft(Color c) => c.withValues(alpha: 0.12);

  // Age output: "25y 7m 26d"
  String _ageText(int y, int m, int d) {
    if (y == 0 && m == 0 && d == 0) return "—";
    return "${y}y ${m}m ${d}d";
  }

  Map<String, int> _calcAgeParts(DateTime dob, DateTime now) {
    int years = now.year - dob.year;
    int months = now.month - dob.month;
    int days = now.day - dob.day;

    if (days < 0) {
      final prevMonth = DateTime(now.year, now.month, 0);
      days += prevMonth.day;
      months -= 1;
    }
    if (months < 0) {
      months += 12;
      years -= 1;
    }
    if (years < 0) years = 0;
    if (days < 0) days = 0;

    return {"y": years, "m": months, "d": days};
  }

  String _langNameByCode(String code) {
    for (final l in _languages) {
      if (l["code"] == code) return l["name"]!;
    }
    return code.isEmpty ? "—" : code;
  }

  Future<void> _mergeUser(Map<String, dynamic> data) async {
    await userRef.set(data, SetOptions(merge: true));
  }

  // ---------- completion ----------
  bool _hasDob(int d, int m, int y) => d > 0 && m > 0 && y > 0;

  // 6 main sections count for completion:
  // name, dob, gender, address, appLanguage, education/hobbies (either filled -> counts as 1)
  // (You can tweak logic anytime)
  Map<String, dynamic> _calcCompletion(Map<String, dynamic> data) {
    final nameOk = asString(data["displayName"]).trim().isNotEmpty;
    final dobOk = _hasDob(
        asInt(data["dobDay"]), asInt(data["dobMonth"]), asInt(data["dobYear"]));
    final genderOk = asString(data["gender"]).trim().isNotEmpty;

    // Address fields (we assume ProfileAddressPage stores these)
    final addrCountry = asString(data["addrCountry"]).trim();
    final addrCity = asString(data["addrCity"]).trim();
    final addrPost = asString(data["addrPostcode"]).trim();
    final addrStreet = asString(data["addrStreet"]).trim();
    final addrOk = addrCountry.isNotEmpty ||
        addrCity.isNotEmpty ||
        addrPost.isNotEmpty ||
        addrStreet.isNotEmpty;

    final appLangOk = asString(data["appLanguage"]).trim().isNotEmpty;

    final edu = asString(data["education"]).trim();
    final hob = asString(data["hobbies"]).trim();
    final extraOk = edu.isNotEmpty || hob.isNotEmpty;

    const total = 6;
    int done = 0;
    if (nameOk) done++;
    if (dobOk) done++;
    if (genderOk) done++;
    if (addrOk) done++;
    if (appLangOk) done++;
    if (extraOk) done++;

    final pct = (done / total);
    return {
      "done": done,
      "total": total,
      "pct": pct,
      "nameOk": nameOk,
      "dobOk": dobOk,
      "genderOk": genderOk,
      "addrOk": addrOk,
      "appLangOk": appLangOk,
      "extraOk": extraOk,
    };
  }

  // ---------- UI: section card ----------
  Widget _sectionCard({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required bool done,
    required VoidCallback onTap,
  }) {
    final heart = done ? "❤️" : "💔";

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: _soft(color),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w900, fontSize: 15)),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: Colors.grey.shade700,
                          fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(heart, style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 6),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }

  // ---------- EDIT SHEETS ----------
  Future<void> _editGenderSheet(String current) async {
    String value = current.isEmpty ? "other" : current;

    await showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (_) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 24),
          child: StatefulBuilder(
            builder: (context, setLocal) {
              return Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text("Select Gender",
                      style:
                          TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 10),
                  RadioListTile(
                    value: "male",
                    groupValue: value,
                    onChanged: (v) => setLocal(() => value = v.toString()),
                    title: const Text("Male"),
                  ),
                  RadioListTile(
                    value: "female",
                    groupValue: value,
                    onChanged: (v) => setLocal(() => value = v.toString()),
                    title: const Text("Female"),
                  ),
                  RadioListTile(
                    value: "other",
                    groupValue: value,
                    onChanged: (v) => setLocal(() => value = v.toString()),
                    title: const Text("Other"),
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () async {
                      await _mergeUser({"gender": value});
                      if (context.mounted) Navigator.pop(context);
                    },
                    icon: const Icon(Icons.save),
                    label: const Text("Save"),
                  ),
                ],
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _editDobSheet({
    required int curDay,
    required int curMonth,
    required int curYear,
  }) async {
    int day = curDay == 0 ? 1 : curDay;
    int month = curMonth == 0 ? 1 : curMonth;
    int year = curYear == 0 ? 2000 : curYear;

    final days = List.generate(31, (i) => i + 1);
    final months = List.generate(12, (i) => i + 1);
    final years = List.generate(201, (i) => 1900 + i); // 1900..2100

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) {
        final w = MediaQuery.of(context).size.width;
        final compact = w < 380; // small phones
        return Padding(
          padding: EdgeInsets.fromLTRB(
              16, 10, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
          child: StatefulBuilder(
            builder: (context, setLocal) {
              DateTime safeDob;
              try {
                safeDob = DateTime(year, month, day);
              } catch (_) {
                safeDob = DateTime(2000, 1, 1);
              }
              final age = _calcAgeParts(safeDob, DateTime.now());

              Widget dropDay() => DropdownButtonFormField<int>(
                    initialValue: day,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        border: OutlineInputBorder(), labelText: "Day"),
                    items: days
                        .map((d) => DropdownMenuItem(
                            value: d, child: Text(d.toString())))
                        .toList(),
                    onChanged: (v) => setLocal(() => day = v ?? day),
                  );

              Widget dropMonth() => DropdownButtonFormField<int>(
                    initialValue: month,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        border: OutlineInputBorder(), labelText: "Month"),
                    items: months
                        .map((m) => DropdownMenuItem(
                            value: m, child: Text(_monthShort(m))))
                        .toList(),
                    onChanged: (v) => setLocal(() => month = v ?? month),
                  );

              Widget dropYear() => DropdownButtonFormField<int>(
                    initialValue: year,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        border: OutlineInputBorder(), labelText: "Year"),
                    items: years
                        .map((y) => DropdownMenuItem(
                            value: y, child: Text(y.toString())))
                        .toList(),
                    onChanged: (v) => setLocal(() => year = v ?? year),
                  );

              return Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text("Date of Birth",
                      style:
                          TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 10),

                  // ✅ overflow safe layout
                  if (compact) ...[
                    dropDay(),
                    const SizedBox(height: 10),
                    dropMonth(),
                    const SizedBox(height: 10),
                    dropYear(),
                  ] else ...[
                    Row(
                      children: [
                        Expanded(child: dropDay()),
                        const SizedBox(width: 10),
                        Expanded(child: dropMonth()),
                        const SizedBox(width: 10),
                        Expanded(child: dropYear()),
                      ],
                    ),
                  ],

                  const SizedBox(height: 12),

                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      color: Colors.pink.shade50,
                      border: Border.all(color: Colors.pink.shade200),
                    ),
                    child: Text(
                      "Auto Age: ${_ageText(age["y"]!, age["m"]!, age["d"]!)}",
                      style: TextStyle(
                          fontWeight: FontWeight.w900,
                          color: Colors.pink.shade800),
                      textAlign: TextAlign.center,
                    ),
                  ),

                  const SizedBox(height: 12),

                  ElevatedButton.icon(
                    onPressed: () async {
                      // validation
                      try {
                        final _ = DateTime(year, month, day);
                      } catch (_) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text(
                                  "Invalid date. Please select correct DOB.")),
                        );
                        return;
                      }
                      await _mergeUser(
                          {"dobDay": day, "dobMonth": month, "dobYear": year});
                      if (context.mounted) Navigator.pop(context);
                    },
                    icon: const Icon(Icons.save),
                    label: const Text("Save DOB"),
                  ),

                  const SizedBox(height: 10),
                ],
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _editAppLanguageSheet({required String current}) async {
    String a = current.isEmpty ? "en" : current;

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
              16, 10, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
          child: StatefulBuilder(
            builder: (context, setLocal) {
              return Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text("App Language",
                      style:
                          TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: a,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        labelText: "Select language"),
                    items: _languages
                        .map((l) => DropdownMenuItem(
                            value: l["code"], child: Text(l["name"]!)))
                        .toList(),
                    onChanged: (v) => setLocal(() => a = v ?? a),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      color: Colors.blue.shade50,
                      border: Border.all(color: Colors.blue.shade200),
                    ),
                    child: Text(
                      "This will update app language instantly.",
                      style: TextStyle(
                          color: Colors.blue.shade800,
                          fontWeight: FontWeight.w700),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ElevatedButton.icon(
                    onPressed: () async {
                      // save to firestore + update locale immediately
                      await _mergeUser({"appLanguage": a});
                      LocaleService.setLocale(a);
                      if (context.mounted) Navigator.pop(context);
                    },
                    icon: const Icon(Icons.language),
                    label: const Text("Apply Language"),
                  ),
                  const SizedBox(height: 10),
                ],
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _editSimpleTextSheet({
    required String title,
    required String fieldKey,
    required String current,
    required String hint,
    int maxLines = 1,
    IconData icon = Icons.edit,
    Color color = Colors.indigo,
  }) async {
    final ctrl = TextEditingController(text: current);

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
              16, 10, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: _soft(color),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(icon, color: color),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w900, fontSize: 16)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: ctrl,
                maxLines: maxLines,
                decoration: InputDecoration(
                  border: const OutlineInputBorder(),
                  hintText: hint,
                ),
              ),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: () async {
                  await _mergeUser({fieldKey: ctrl.text.trim()});
                  if (context.mounted) Navigator.pop(context);
                },
                icon: const Icon(Icons.save),
                label: const Text("Save"),
              ),
              const SizedBox(height: 10),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Personal Information")),
      body: StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: userRef.snapshots(),
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          final data = snap.data?.data() ?? {};

          final displayName = asString(data["displayName"]).trim();
          final gender = asString(data["gender"]).trim();
          final dobDay = asInt(data["dobDay"]);
          final dobMonth = asInt(data["dobMonth"]);
          final dobYear = asInt(data["dobYear"]);

          final appLang = asString(data["appLanguage"]).trim();
          final education = asString(data["education"]).trim();
          final hobbies = asString(data["hobbies"]).trim();

          // DOB preview
          String dobPreview = "—";
          String agePreview = "—";
          if (_hasDob(dobDay, dobMonth, dobYear)) {
            final dob = DateTime(dobYear, dobMonth, dobDay);
            dobPreview = "${_two(dobDay)} ${_monthShort(dobMonth)} $dobYear";
            final age = _calcAgeParts(dob, DateTime.now());
            agePreview = _ageText(age["y"]!, age["m"]!, age["d"]!);
          }

          // completion
          final comp = _calcCompletion(data);
          final done = comp["done"] as int;
          final total = comp["total"] as int;
          final pct = comp["pct"] as double;

          return ListView(
            padding: const EdgeInsets.all(14),
            children: [
              // ✅ Header progress
              Card(
                elevation: 0,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 54,
                            height: 54,
                            decoration: BoxDecoration(
                              color: Colors.pink.shade50,
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(color: Colors.pink.shade200),
                            ),
                            child: Icon(Icons.favorite,
                                color: Colors.pink.shade700),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  "Profile Strength",
                                  style: TextStyle(
                                      fontWeight: FontWeight.w900,
                                      fontSize: 16),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  "$done / $total sections completed",
                                  style: TextStyle(
                                      color: Colors.grey.shade700,
                                      fontWeight: FontWeight.w700),
                                ),
                              ],
                            ),
                          ),
                          Text(
                            "${(pct * 100).round()}%",
                            style: const TextStyle(
                                fontWeight: FontWeight.w900, fontSize: 18),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(999),
                        child:
                            LinearProgressIndicator(value: pct, minHeight: 10),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Complete your profile for better matching & trust 💘",
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: Colors.grey.shade700,
                            fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 10),

              _sectionCard(
                icon: Icons.badge,
                color: Colors.indigo,
                title: "Full Name",
                subtitle: displayName.isEmpty ? "Add your name" : displayName,
                done: comp["nameOk"] as bool,
                onTap: () => _editSimpleTextSheet(
                  title: "Full Name",
                  fieldKey: "displayName",
                  current: displayName,
                  hint: "Enter your full name",
                  icon: Icons.badge,
                  color: Colors.indigo,
                ),
              ),

              _sectionCard(
                icon: Icons.cake,
                color: Colors.pink,
                title: "Date of Birth",
                subtitle: "DOB: $dobPreview   •   Age: $agePreview",
                done: comp["dobOk"] as bool,
                onTap: () => _editDobSheet(
                    curDay: dobDay, curMonth: dobMonth, curYear: dobYear),
              ),

              _sectionCard(
                icon: Icons.wc,
                color: Colors.deepPurple,
                title: "Gender",
                subtitle:
                    gender.isEmpty ? "Select gender" : gender.toUpperCase(),
                done: comp["genderOk"] as bool,
                onTap: () => _editGenderSheet(gender),
              ),

              _sectionCard(
                icon: Icons.location_on,
                color: Colors.orange,
                title: "Address",
                subtitle: "Tap to fill country, city, postcode, street",
                done: comp["addrOk"] as bool,
                onTap: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) => const ProfileAddressPage()),
                  );
                },
              ),

              _sectionCard(
                icon: Icons.language,
                color: Colors.blue,
                title: "App Language",
                subtitle: _langNameByCode(appLang),
                done: comp["appLangOk"] as bool,
                onTap: () => _editAppLanguageSheet(current: appLang),
              ),

              _sectionCard(
                icon: Icons.school,
                color: Colors.teal,
                title: "Education & Hobbies",
                subtitle: [
                  if (education.isNotEmpty) "🎓 $education",
                  if (hobbies.isNotEmpty) "🏀 $hobbies",
                  if (education.isEmpty && hobbies.isEmpty)
                    "Add education / hobbies (optional)",
                ].join("  •  "),
                done: comp["extraOk"] as bool,
                onTap: () async {
                  // Quick sheet with 2 fields
                  await showModalBottomSheet(
                    context: context,
                    isScrollControlled: true,
                    showDragHandle: true,
                    builder: (_) {
                      final eduCtrl = TextEditingController(text: education);
                      final hobCtrl = TextEditingController(text: hobbies);
                      return Padding(
                        padding: EdgeInsets.fromLTRB(16, 10, 16,
                            16 + MediaQuery.of(context).viewInsets.bottom),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Text("Education & Hobbies",
                                style: TextStyle(
                                    fontWeight: FontWeight.w900, fontSize: 16)),
                            const SizedBox(height: 12),
                            TextField(
                              controller: eduCtrl,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                                labelText: "Education",
                                hintText: "Example: B.Tech, MBA, MSc...",
                              ),
                            ),
                            const SizedBox(height: 10),
                            TextField(
                              controller: hobCtrl,
                              maxLines: 2,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                                labelText: "Hobbies",
                                hintText:
                                    "Example: Movies, gym, travel, music...",
                              ),
                            ),
                            const SizedBox(height: 12),
                            ElevatedButton.icon(
                              onPressed: () async {
                                await _mergeUser({
                                  "education": eduCtrl.text.trim(),
                                  "hobbies": hobCtrl.text.trim(),
                                });
                                if (context.mounted) Navigator.pop(context);
                              },
                              icon: const Icon(Icons.save),
                              label: const Text("Save"),
                            ),
                            const SizedBox(height: 10),
                          ],
                        ),
                      );
                    },
                  );
                },
              ),

              const SizedBox(height: 16),

              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  color: Colors.grey.shade50,
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Text(
                  "DOB based age updates automatically every day.\nLater: birthday wishes + chat language 🎉",
                  style: TextStyle(
                      color: Colors.grey.shade800, fontWeight: FontWeight.w700),
                  textAlign: TextAlign.center,
                ),
              ),

              const SizedBox(height: 30),
            ],
          );
        },
      ),
    );
  }
}
