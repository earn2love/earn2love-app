import 'package:cloud_functions/cloud_functions.dart';
import 'package:flutter_stripe/flutter_stripe.dart';

class PaymentService {
  static final FirebaseFunctions _functions =
      FirebaseFunctions.instanceFor(region: 'us-central1');

  static Future<void> buyPack(String packId) async {
    final createPayment = _functions.httpsCallable('createStripePaymentIntent');

    final result = await createPayment.call({'packId': packId});

    final clientSecret = result.data['clientSecret'] as String;
    final paymentIntentId = result.data['paymentIntentId'] as String;

    await Stripe.instance.initPaymentSheet(
      paymentSheetParameters: SetupPaymentSheetParameters(
        merchantDisplayName: 'Earn2Love',
        paymentIntentClientSecret: clientSecret,
      ),
    );

    await Stripe.instance.presentPaymentSheet();

    final confirmPayment = _functions.httpsCallable('confirmStripeTopupDev');

    await confirmPayment.call({
      'paymentIntentId': paymentIntentId,
    });
  }
}
