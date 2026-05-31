import 'package:flutter/foundation.dart';

import '../api/client.dart';
import '../fcm/fcm_setup.dart';

class AuthService extends ChangeNotifier {
  AuthService(this.api);
  final ApiClient api;

  bool _signedIn = false;
  bool get signedIn => _signedIn;
  String? _email;
  String? get email => _email;

  Future<void> bootstrap() async {
    final t = await api.currentAccessToken();
    if (t == null) return;
    try {
      final r = await api.dio.get('/api/v1/auth/me');
      _email = r.data['email'];
      _signedIn = true;
      notifyListeners();
    } catch (_) {
      await api.clearTokens();
    }
  }

  Future<void> login(String email, String password) async {
    final r = await api.dio.post('/api/v1/auth/login', data: {
      'email': email,
      'password': password,
    });
    await api.saveTokens(r.data['access_token'], r.data['refresh_token']);
    final me = await api.dio.get('/api/v1/auth/me');
    _email = me.data['email'];
    _signedIn = true;
    notifyListeners();
    await registerFcmToken(api);
  }

  Future<void> logout() async {
    await api.clearTokens();
    _signedIn = false;
    _email = null;
    notifyListeners();
  }
}
