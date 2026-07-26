# App Config — making admin edits control the live app

The admin panel now writes all pricing/economy config to Firestore:
`appConfig/current` (fields: `coinPackages`, `membershipPlans`, `callCosts`,
`conversionRates`, `withdrawalMin`, `settings`).

To make edits take effect in the mobile app, the Flutter **Cloud Functions** must
READ this document instead of the hardcoded constants in `functions/config.js`.

### Change required in the Flutter repo (functions/config.js consumers)
Add a helper that loads and caches the config, and use it in payments/wallet/calls/
withdrawals instead of the static constants:

```js
// functions/appConfig.js
const admin = require("firebase-admin");
let _cache = null, _ts = 0;
async function getAppConfig() {
  if (_cache && Date.now() - _ts < 60000) return _cache; // 60s cache
  const snap = await admin.firestore().doc("appConfig/current").get();
  _cache = snap.exists ? snap.data() : require("./config"); // fallback to defaults
  _ts = Date.now();
  return _cache;
}
module.exports = { getAppConfig };
```

Then in `payments.js` use `cfg.coinPackages` / `cfg.membershipPlans`, in `calls.js`
use `cfg.callCosts`, in `wallet.js` use `cfg.conversionRates` + `cfg.settings`
(conversionCooldownSeconds), and in `withdrawals.js` use `cfg.withdrawalMin`.

The Flutter client should also read `appConfig/current` (or a public mirror) to
display prices/packages, so screens never hardcode pricing.

> Deploy note: `appConfig/current` is admin-write-only. Add a Firestore rule:
> `match /appConfig/{doc} { allow read: if request.auth != null; allow write: if false; }`
> (writes happen via the admin backend Admin SDK / a future admin Cloud Function).
