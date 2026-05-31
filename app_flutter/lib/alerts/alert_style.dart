import 'package:flutter/material.dart';

class AlertStyle {
  const AlertStyle({
    required this.icon,
    required this.color,
    required this.label,
  });
  final IconData icon;
  final Color color;
  final String label;
}

const _styles = <String, AlertStyle>{
  'WATER': AlertStyle(
    icon: Icons.water_drop_rounded,
    color: Color(0xFF1E88E5),
    label: 'Water',
  ),
  'MEDICINE': AlertStyle(
    icon: Icons.medication_rounded,
    color: Color(0xFF43A047),
    label: 'Medicine',
  ),
  'BATHROOM': AlertStyle(
    icon: Icons.wc_rounded,
    color: Color(0xFFFB8C00),
    label: 'Bathroom',
  ),
  'HELP': AlertStyle(
    icon: Icons.pan_tool_alt_rounded,
    color: Color(0xFFFDD835),
    label: 'Help',
  ),
  'EMERGENCY': AlertStyle(
    icon: Icons.warning_amber_rounded,
    color: Color(0xFFE53935),
    label: 'Emergency',
  ),
};

AlertStyle styleFor(String type) =>
    _styles[type] ??
    const AlertStyle(
      icon: Icons.notifications_active_rounded,
      color: Color(0xFF6A1B9A),
      label: 'Alert',
    );
