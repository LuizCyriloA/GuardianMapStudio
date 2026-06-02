export interface GeoPoint { lat: number; lng: number }

export interface ProjectResponse {
  id: number; name: string; description: string
  created_at: string; updated_at: string
}

export interface VersionResponse {
  id: number; project_id: number; version_number: number; name: string
  published_at: string; road_count: number; waypoint_count: number
  crossroad_count: number; restricted_area_count: number
}

export interface WorkspaceResponse {
  id: number; project_id: number; state: 'draft' | 'published'
  base_version_id: number | null
  has_validation_errors: boolean
  last_validated_at: string | null
  created_at: string; updated_at: string
}

export interface RoadResponse {
  id: number; workspace_id: number; name: string
  coordinates: GeoPoint[]; speed_limit_kmh: number
  direction: 'two_way' | 'one_way'; width_meters: number
  created_at: string; updated_at: string
}

export interface WaypointResponse {
  id: number; workspace_id: number; name: string
  waypoint_type: string; lat: number; lng: number
  road_name: string | null; heading_degrees: number | null
  extra_data: Record<string, unknown>; active: boolean
  created_at: string; updated_at: string
}

export interface CrossroadResponse {
  id: number; workspace_id: number
  road_a_name: string; road_b_name: string
  lat: number; lng: number; created_at: string
}

export interface RestrictedAreaResponse {
  id: number; workspace_id: number; name: string
  polygon: GeoPoint[]; restriction_type: string
  speed_limit_kmh: number | null; active: boolean
  created_at: string; updated_at: string
}

export interface ValidationResultResponse {
  id: number; severity: 'error' | 'warning'
  rule_id: string; message: string
  affected_entity_type: string; affected_entity_id: number
}

export interface ValidationSummaryResponse {
  workspace_id: number; error_count: number; warning_count: number
  can_publish: boolean; results: ValidationResultResponse[]
  validated_at: string
}

export interface MapResponse {
  roads: RoadResponse[]
  waypoints: WaypointResponse[]
  crossroads: CrossroadResponse[]
  restricted_areas: RestrictedAreaResponse[]
}

export interface SnapResponse {
  original: GeoPoint
  snapped_to: GeoPoint
  snapped: boolean
  distance_meters: number
}

export interface ExportResponse {
  export_id: number
  version_id: number
  file_path: string
  file_size_bytes: number
  exported_at: string
}
