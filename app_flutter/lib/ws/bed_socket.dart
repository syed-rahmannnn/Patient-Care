import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

class BedSocket {
  BedSocket({
    required this.baseUrl,
    required this.bedId,
    required this.fetchTicket,
    required this.onEvent,
  });

  final String baseUrl;
  final String bedId;
  // Called every time we (re)connect; tickets have a 60s TTL so we can't reuse one.
  final Future<String?> Function() fetchTicket;
  final void Function(Map<String, dynamic>) onEvent;

  WebSocketChannel? _ch;
  StreamSubscription<dynamic>? _sub;
  Timer? _retryTimer;
  bool _closed = false;
  int _backoff = 1;

  Future<void> connect() async {
    if (_closed) return;
    String? ticket;
    try {
      ticket = await fetchTicket();
    } catch (_) {
      ticket = null;
    }
    if (_closed) return;
    if (ticket == null || ticket.isEmpty) {
      _scheduleRetry();
      return;
    }
    final wsUrl =
        '${baseUrl.replaceFirst(RegExp(r'^https'), 'wss').replaceFirst(RegExp(r'^http'), 'ws')}'
        '/ws/beds/$bedId?token=$ticket';
    try {
      _ch = WebSocketChannel.connect(Uri.parse(wsUrl));
    } catch (_) {
      _scheduleRetry();
      return;
    }
    _sub = _ch!.stream.listen(
      (raw) {
        _backoff = 1;
        try {
          onEvent(jsonDecode(raw as String) as Map<String, dynamic>);
        } catch (_) {}
      },
      onError: (_) => _scheduleRetry(),
      onDone: _scheduleRetry,
      cancelOnError: true,
    );
  }

  void _scheduleRetry() {
    _sub?.cancel();
    _sub = null;
    _ch = null;
    if (_closed) return;
    _retryTimer?.cancel();
    final delay = Duration(seconds: _backoff);
    _backoff = (_backoff * 2).clamp(1, 30);
    _retryTimer = Timer(delay, connect);
  }

  void close() {
    _closed = true;
    _retryTimer?.cancel();
    _sub?.cancel();
    _ch?.sink.close();
  }
}
