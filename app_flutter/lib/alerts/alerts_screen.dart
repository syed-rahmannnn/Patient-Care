import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../auth/auth_service.dart';
import '../util/time_ago.dart';
import '../ws/bed_socket.dart';
import 'alert_style.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key, required this.bed});
  final BedDto bed;

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  List<AlertDto> _alerts = [];
  BedSocket? _ws;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    await _refresh();
    if (!mounted) return;
    final api = context.read<ApiClient>();
    _ws = BedSocket(
      baseUrl: api.baseUrl,
      bedId: widget.bed.id,
      fetchTicket: api.wsTicket,
      onEvent: _onWsEvent,
    );
    await _ws!.connect();
  }

  void _onWsEvent(Map<String, dynamic> e) {
    if (!mounted) return;
    final kind = e['event'];
    if (kind == 'alert.new') {
      setState(() {
        _alerts.insert(
          0,
          AlertDto(
            id: e['alert_id'],
            deviceId: e['device_id'],
            bedId: widget.bed.id,
            type: e['type'],
            createdAt: DateTime.tryParse(e['created_at'] ?? '') ?? DateTime.now(),
          ),
        );
      });
    } else if (kind == 'alert.ack') {
      final id = e['alert_id'];
      setState(() {
        for (final a in _alerts) {
          if (a.id == id) {
            a.acknowledgedByName = e['by_name'];
            a.acknowledgedAt = DateTime.now();
            break;
          }
        }
      });
    }
  }

  Future<void> _refresh() async {
    final api = context.read<ApiClient>();
    final r = await api.dio.get('/api/v1/beds/${widget.bed.id}/alerts');
    if (!mounted) return;
    setState(() {
      _alerts = (r.data as List).map((j) => AlertDto.fromJson(j)).toList();
      _loading = false;
    });
  }

  Future<void> _ack(AlertDto a) async {
    final api = context.read<ApiClient>();
    final me = context.read<AuthService>().email ?? 'you';
    setState(() {
      a.acknowledgedByName = me;
      a.acknowledgedAt = DateTime.now();
    });
    try {
      await api.dio.post('/api/v1/alerts/${a.id}/ack');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        a.acknowledgedByName = null;
        a.acknowledgedAt = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ack failed: $e')));
    }
  }

  @override
  void dispose() {
    _ws?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surfaceContainerLowest,
      appBar: AppBar(
        title: Text(widget.bed.title),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(40),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Row(
              children: [
                Icon(Icons.qr_code_2_rounded, size: 18, color: cs.onSurfaceVariant),
                const SizedBox(width: 6),
                Text(
                  widget.bed.joinCode,
                  style: TextStyle(
                    color: cs.onSurfaceVariant,
                    fontFamily: 'monospace',
                    fontSize: 13,
                  ),
                ),
                const Spacer(),
                Text(
                  '${_alerts.length} alert${_alerts.length == 1 ? '' : 's'}',
                  style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13),
                ),
              ],
            ),
          ),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refresh,
              child: _alerts.isEmpty
                  ? _EmptyState(label: widget.bed.label)
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
                      itemCount: _alerts.length,
                      itemBuilder: (_, i) => _AlertCard(
                        alert: _alerts[i],
                        onAck: () => _ack(_alerts[i]),
                      ),
                    ),
            ),
    );
  }
}

class _AlertCard extends StatelessWidget {
  const _AlertCard({required this.alert, required this.onAck});
  final AlertDto alert;
  final VoidCallback onAck;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final style = styleFor(alert.type);
    final isEmergency = alert.type == 'EMERGENCY';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Card(
        elevation: 0,
        clipBehavior: Clip.antiAlias,
        color: isEmergency
            ? style.color.withValues(alpha: 0.08)
            : cs.surfaceContainer,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: isEmergency
              ? BorderSide(color: style.color.withValues(alpha: 0.6), width: 1.5)
              : BorderSide.none,
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: style.color.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Icon(style.icon, color: style.color, size: 26),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      style.label,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: isEmergency ? style.color : null,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      timeAgo(alert.createdAt),
                      style: TextStyle(
                        color: cs.onSurfaceVariant,
                        fontSize: 13,
                      ),
                    ),
                    if (alert.isAcked) ...[
                      const SizedBox(height: 8),
                      _AckPill(name: alert.acknowledgedByName ?? '', color: style.color),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 10),
              if (!alert.isAcked)
                FilledButton.tonal(
                  onPressed: onAck,
                  style: FilledButton.styleFrom(
                    backgroundColor: style.color.withValues(alpha: 0.15),
                    foregroundColor: style.color,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: const Text('Acknowledge', style: TextStyle(fontWeight: FontWeight.w600)),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AckPill extends StatelessWidget {
  const _AckPill({required this.name, required this.color});
  final String name;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.check_circle_rounded, size: 14, color: color),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              name.isEmpty ? 'Acknowledged' : name,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return ListView(
      children: [
        const SizedBox(height: 80),
        Center(
          child: Container(
            width: 96,
            height: 96,
            decoration: BoxDecoration(
              color: cs.primaryContainer,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(Icons.notifications_paused_rounded,
                size: 48, color: cs.onPrimaryContainer),
          ),
        ),
        const SizedBox(height: 24),
        Center(
          child: Text(
            'All clear',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        const SizedBox(height: 6),
        Center(
          child: Text(
            'No alerts in $label yet.',
            style: TextStyle(color: cs.onSurfaceVariant),
          ),
        ),
      ],
    );
  }
}
