import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  ApiClient({required this.baseUrl}) : _storage = const FlutterSecureStorage() {
    dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      contentType: 'application/json',
    ));
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final t = await _storage.read(key: _kAccess);
        if (t != null) options.headers['Authorization'] = 'Bearer $t';
        handler.next(options);
      },
      onError: (e, handler) async {
        // Single retry after a refresh on 401.
        if (e.response?.statusCode == 401 && e.requestOptions.extra['retried'] != true) {
          final refreshed = await _refresh();
          if (refreshed) {
            final t = await _storage.read(key: _kAccess);
            final req = e.requestOptions;
            req.headers['Authorization'] = 'Bearer $t';
            req.extra['retried'] = true;
            try {
              final r = await dio.fetch(req);
              return handler.resolve(r);
            } catch (_) {}
          }
        }
        handler.next(e);
      },
    ));
  }

  static const _kAccess = 'pc.access';
  static const _kRefresh = 'pc.refresh';
  static const _kServerUrl = 'pc.server_url';

  String baseUrl;
  late final Dio dio;
  final FlutterSecureStorage _storage;

  /// Normalize a user-entered server URL: trim, default to http://, drop trailing slash.
  static String normalizeUrl(String raw) {
    var u = raw.trim();
    if (u.isEmpty) return u;
    if (!u.startsWith('http://') && !u.startsWith('https://')) u = 'http://$u';
    while (u.endsWith('/')) {
      u = u.substring(0, u.length - 1);
    }
    return u;
  }

  /// The server URL the user last saved, or null if they never changed it.
  static Future<String?> loadSavedServerUrl() =>
      const FlutterSecureStorage().read(key: _kServerUrl);

  /// Point the client at a new backend and persist the choice.
  Future<void> setBaseUrl(String url) async {
    baseUrl = normalizeUrl(url);
    dio.options.baseUrl = baseUrl;
    await _storage.write(key: _kServerUrl, value: baseUrl);
  }

  Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }

  Future<String?> currentAccessToken() => _storage.read(key: _kAccess);

  Future<bool> _refresh() async {
    final rt = await _storage.read(key: _kRefresh);
    if (rt == null) return false;
    try {
      final r = await Dio(BaseOptions(baseUrl: baseUrl)).post(
        '/api/v1/auth/refresh',
        data: {'refresh_token': rt},
      );
      await saveTokens(r.data['access_token'], r.data['refresh_token']);
      return true;
    } catch (_) {
      await clearTokens();
      return false;
    }
  }

  Future<String?> wsTicket() async {
    final r = await dio.post('/api/v1/auth/ws-ticket');
    return r.data['token'] as String?;
  }
}
