import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../api/client.dart';

const _channelDefault = AndroidNotificationChannel(
  'pcs_alerts',
  'Patient alerts',
  description: 'Routine patient requests (water, medicine, bathroom, help).',
  importance: Importance.high,
);

const _channelEmergency = AndroidNotificationChannel(
  'pcs_emergency',
  'Emergency alerts',
  description: 'Critical patient emergencies — bypasses Do Not Disturb.',
  importance: Importance.max,
  playSound: true,
  enableVibration: true,
);

final localNotifs = FlutterLocalNotificationsPlugin();

Future<void> _renderNotification(FlutterLocalNotificationsPlugin plugin, RemoteMessage msg) async {
  final data = msg.data;
  final isEmergency = data['type'] == 'EMERGENCY' || data['emergency'] == '1';
  await plugin.show(
    msg.hashCode,
    data['title'] ?? msg.notification?.title ?? 'Patient alert',
    data['body'] ?? msg.notification?.body ?? '',
    NotificationDetails(
      android: AndroidNotificationDetails(
        isEmergency ? _channelEmergency.id : _channelDefault.id,
        isEmergency ? _channelEmergency.name : _channelDefault.name,
        importance: isEmergency ? Importance.max : Importance.high,
        priority: isEmergency ? Priority.max : Priority.high,
      ),
    ),
    payload: data['alert_id'],
  );
}

// MUST be a top-level function. Runs in a fresh isolate when the app is
// backgrounded or killed, so it has to reinitialize Firebase + the local
// notifications plugin from scratch before rendering.
@pragma('vm:entry-point')
Future<void> firebaseBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  final bgNotifs = FlutterLocalNotificationsPlugin();
  await bgNotifs.initialize(
    const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
  );
  final androidImpl = bgNotifs.resolvePlatformSpecificImplementation<
      AndroidFlutterLocalNotificationsPlugin>();
  await androidImpl?.createNotificationChannel(_channelDefault);
  await androidImpl?.createNotificationChannel(_channelEmergency);
  await _renderNotification(bgNotifs, message);
}

// Fetches the current FCM token and registers it with the backend. Safe to
// call multiple times — call after every successful login (initial registration
// at app start hits 401 before the user has signed in).
Future<void> registerFcmToken(ApiClient api) async {
  final token = await FirebaseMessaging.instance.getToken();
  if (token == null) return;
  try {
    await api.dio.post('/api/v1/me/fcm-tokens',
        data: {'token': token, 'platform': 'android'});
  } catch (_) {}
}

Future<void> initFcm({required ApiClient api}) async {
  await localNotifs.initialize(
    const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
  );
  final androidImpl = localNotifs.resolvePlatformSpecificImplementation<
      AndroidFlutterLocalNotificationsPlugin>();
  await androidImpl?.createNotificationChannel(_channelDefault);
  await androidImpl?.createNotificationChannel(_channelEmergency);

  await FirebaseMessaging.instance.requestPermission(alert: true, badge: true, sound: true);
  FirebaseMessaging.onBackgroundMessage(firebaseBackgroundHandler);

  await registerFcmToken(api);
  FirebaseMessaging.instance.onTokenRefresh.listen((_) => registerFcmToken(api));

  // Foreground — render via local notifications so we control the channel.
  FirebaseMessaging.onMessage.listen((msg) => _renderNotification(localNotifs, msg));
}
