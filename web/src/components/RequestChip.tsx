import { AlertTriangle, Bath, Droplet, HandHelping, Pill, type LucideIcon } from 'lucide-react'
import type { AlertType } from '../api/types'
import { cn } from './ui'

interface Meta {
  Icon: LucideIcon
  label: string
  text: string
  chip: string
  badge: string
}

export const ALERT_META: Record<AlertType, Meta> = {
  WATER: {
    Icon: Droplet,
    label: 'Water',
    text: 'text-water',
    chip: 'text-water bg-water/10 border-water/25',
    badge: 'text-water bg-water/12',
  },
  MEDICINE: {
    Icon: Pill,
    label: 'Medicine',
    text: 'text-medicine',
    chip: 'text-medicine bg-medicine/10 border-medicine/25',
    badge: 'text-medicine bg-medicine/12',
  },
  HELP: {
    Icon: HandHelping,
    label: 'Help',
    text: 'text-help',
    chip: 'text-help bg-help/10 border-help/25',
    badge: 'text-help bg-help/12',
  },
  BATHROOM: {
    Icon: Bath,
    label: 'Restroom',
    text: 'text-restroom',
    chip: 'text-restroom bg-restroom/10 border-restroom/25',
    badge: 'text-restroom bg-restroom/12',
  },
  EMERGENCY: {
    Icon: AlertTriangle,
    label: 'Emergency',
    text: 'text-emergency',
    chip: 'text-emergency bg-emergency/10 border-emergency/30',
    badge: 'text-emergency bg-emergency/14',
  },
}

export function RequestChip({ type }: { type: AlertType }) {
  const m = ALERT_META[type]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[12px] font-semibold',
        m.chip,
      )}
    >
      <m.Icon size={13} />
      {m.label}
    </span>
  )
}

export function AlertIcon({ type, size = 40 }: { type: AlertType; size?: number }) {
  const m = ALERT_META[type]
  return (
    <div
      className={cn('grid shrink-0 place-items-center rounded-xl', m.badge)}
      style={{ width: size, height: size }}
    >
      <m.Icon size={size * 0.45} />
    </div>
  )
}
