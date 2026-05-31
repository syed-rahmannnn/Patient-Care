import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../alerts/alerts_screen.dart';
import '../api/client.dart';
import '../api/models.dart';
import '../auth/auth_service.dart';

class BedsScreen extends StatefulWidget {
  const BedsScreen({super.key});

  @override
  State<BedsScreen> createState() => _BedsScreenState();
}

class _BedsScreenState extends State<BedsScreen> {
  List<BedDto> _beds = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() => _loading = true);
    final api = context.read<ApiClient>();
    try {
      final r = await api.dio.get('/api/v1/beds/me');
      if (!mounted) return;
      setState(() {
        _beds = (r.data as List).map((j) => BedDto.fromJson(j)).toList();
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _joinByCode() async {
    final code = await showDialog<String>(
      context: context,
      builder: (_) {
        final c = TextEditingController();
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          title: const Text('Join a bed'),
          content: TextField(
            controller: c,
            decoration: const InputDecoration(
              hintText: 'ABC-123',
              prefixIcon: Icon(Icons.qr_code_2_rounded),
            ),
            autofocus: true,
            textCapitalization: TextCapitalization.characters,
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
            FilledButton(
                onPressed: () => Navigator.pop(context, c.text.trim()),
                child: const Text('Join')),
          ],
        );
      },
    );
    if (code == null || code.isEmpty) return;
    final api = context.read<ApiClient>();
    try {
      await api.dio.post('/api/v1/beds/join', data: {'join_code': code});
      await _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Join failed: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = context.watch<AuthService>();
    return Scaffold(
      backgroundColor: cs.surfaceContainerLowest,
      appBar: AppBar(
        toolbarHeight: 72,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Patient Care'),
            Text(
              auth.email ?? '',
              style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant, fontWeight: FontWeight.w400),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: 'Sign out',
            onPressed: () => context.read<AuthService>().logout(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _joinByCode,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Join bed'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refresh,
              child: _beds.isEmpty
                  ? _EmptyBeds(onJoin: _joinByCode)
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                      itemCount: _beds.length,
                      itemBuilder: (_, i) => _BedCard(bed: _beds[i]),
                    ),
            ),
    );
  }
}

class _BedCard extends StatelessWidget {
  const _BedCard({required this.bed});
  final BedDto bed;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Material(
        color: cs.surfaceContainer,
        borderRadius: BorderRadius.circular(20),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => AlertsScreen(bed: bed)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: cs.primaryContainer,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  alignment: Alignment.center,
                  child: Icon(Icons.bed_rounded, color: cs.onPrimaryContainer, size: 26),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        bed.title,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          _StatusPill(active: bed.isActive),
                          const SizedBox(width: 8),
                          Icon(Icons.qr_code_2_rounded, size: 14, color: cs.onSurfaceVariant),
                          const SizedBox(width: 4),
                          Text(
                            bed.joinCode,
                            style: TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right_rounded, color: cs.onSurfaceVariant),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.active});
  final bool active;
  @override
  Widget build(BuildContext context) {
    final color = active ? const Color(0xFF2E7D32) : const Color(0xFF757575);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 5),
          Text(
            active ? 'Active' : 'Inactive',
            style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _EmptyBeds extends StatelessWidget {
  const _EmptyBeds({required this.onJoin});
  final VoidCallback onJoin;
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
            decoration: BoxDecoration(color: cs.primaryContainer, shape: BoxShape.circle),
            alignment: Alignment.center,
            child: Icon(Icons.bed_rounded, size: 48, color: cs.onPrimaryContainer),
          ),
        ),
        const SizedBox(height: 24),
        Center(
          child: Text(
            'No beds yet',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        const SizedBox(height: 6),
        Center(
          child: Text(
            'Join a bed using the code from your admin.',
            style: TextStyle(color: cs.onSurfaceVariant),
          ),
        ),
        const SizedBox(height: 24),
        Center(
          child: FilledButton.icon(
            onPressed: onJoin,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Join bed'),
          ),
        ),
      ],
    );
  }
}
