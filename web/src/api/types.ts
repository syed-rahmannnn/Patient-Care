export type Role = 'admin' | 'nurse'
export type AlertType = 'WATER' | 'MEDICINE' | 'HELP' | 'BATHROOM' | 'EMERGENCY'

export interface User {
  id: string
  email: string
  role: Role
  display_name: string
  created_at: string
}

export interface Device {
  id: string
  serial_id: string
  name: string
  bed_id: string
  created_at: string
}

export interface BedNurse {
  id: string
  email: string
  display_name: string
  online: boolean
}

export interface Bed {
  id: string
  room_id: string
  room_name: string
  label: string
  join_code: string
  created_at: string
  device: Device | null
  status: 'active' | 'inactive'
  connected: boolean
  nurses: BedNurse[]
}

export interface Room {
  id: string
  name: string
  created_at: string
  bed_count: number
  active_bed_count: number
}

export interface RoomDetail {
  id: string
  name: string
  created_at: string
  beds: Bed[]
}

export interface NurseAssignment {
  bed_id: string
  bed_label: string
  room_id: string
  room_name: string
  joined_at: string
}

export interface Nurse {
  id: string
  email: string
  display_name: string
  role: Role
  created_at: string
  online: boolean
  assignments: NurseAssignment[]
}

export interface Alert {
  id: string
  device_id: string
  bed_id: string
  type: AlertType
  created_at: string
  acknowledged_by: string | null
  acknowledged_by_name: string | null
  acknowledged_at: string | null
  bed_label: string | null
  room_id: string | null
  room_name: string | null
}

export interface DashboardStats {
  rooms: number
  beds: number
  active_beds: number
  connected_devices: number
  nurses_total: number
  nurses_online: number
  pending_requests: number
}

export interface DeviceToken {
  device_id: string
  serial_id: string
  token: string
}
