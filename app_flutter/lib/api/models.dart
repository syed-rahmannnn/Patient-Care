class BedDto {
  BedDto({
    required this.id,
    required this.roomName,
    required this.label,
    required this.joinCode,
    required this.status,
    required this.connected,
  });
  factory BedDto.fromJson(Map<String, dynamic> j) => BedDto(
        id: j['id'],
        roomName: j['room_name'] ?? '',
        label: j['label'] ?? '',
        joinCode: j['join_code'] ?? '',
        status: j['status'] ?? 'inactive',
        connected: j['connected'] ?? false,
      );
  final String id;
  final String roomName;
  final String label;
  final String joinCode;
  final String status;
  final bool connected;

  bool get isActive => status == 'active';
  String get title => roomName.isEmpty ? label : '$roomName · $label';
}

class AlertDto {
  AlertDto({
    required this.id,
    required this.deviceId,
    required this.bedId,
    required this.type,
    required this.createdAt,
    this.acknowledgedBy,
    this.acknowledgedByName,
    this.acknowledgedAt,
  });
  factory AlertDto.fromJson(Map<String, dynamic> j) => AlertDto(
        id: j['id'],
        deviceId: j['device_id'],
        bedId: j['bed_id'],
        type: j['type'],
        createdAt: DateTime.parse(j['created_at']),
        acknowledgedBy: j['acknowledged_by'],
        acknowledgedByName: j['acknowledged_by_name'],
        acknowledgedAt: j['acknowledged_at'] == null
            ? null
            : DateTime.parse(j['acknowledged_at']),
      );
  final String id;
  final String deviceId;
  final String bedId;
  final String type;
  final DateTime createdAt;
  String? acknowledgedBy;
  String? acknowledgedByName;
  DateTime? acknowledgedAt;
  bool get isAcked => acknowledgedBy != null || acknowledgedByName != null;
}

class DeviceDto {
  DeviceDto({required this.id, required this.serialId, required this.name});
  factory DeviceDto.fromJson(Map<String, dynamic> j) =>
      DeviceDto(id: j['id'], serialId: j['serial_id'], name: j['name']);
  final String id;
  final String serialId;
  final String name;
}
