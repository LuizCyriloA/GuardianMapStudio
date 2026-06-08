import type {
  ExportResponse,
  GeoPoint,
  MapResponse,
  ProjectResponse,
  SnapResponse,
  ValidationSummaryResponse,
  VersionResponse,
  WorkspaceResponse,
  RoadResponse,
  WaypointResponse,
  CrossroadResponse,
  RestrictedAreaResponse,
} from './types'

// --- OSM Import types ---

export interface ParsedRoadDTO {
  osm_way_id: number
  name: string
  coordinates: GeoPoint[]
  direction: 'two_way' | 'one_way'
  speed_limit_kmh: number
  width_meters: number
  highway_tag: string
  had_name: boolean
  osm_warnings: string[]
}

export interface OsmPreviewResponse {
  roads: ParsedRoadDTO[]
  total_ways_in_file: number
  skipped_ways: number
  skipped_reasons: Record<string, number>
}

export interface OsmImportResponse {
  workspace_id: number
  created_count: number
  deleted_existing: number
  renamed: { from: string; to: string }[]
}

const API = ''

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(`${API}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'unknown', message: res.statusText }))
    throw err
  }
  if (res.status === 204) return {} as T
  return res.json()
}

export const api = {
  // Projects
  getProjects: () =>
    request<{ items: ProjectResponse[]; total: number }>('GET', '/api/v1/projects'),
  createProject: (name: string, description = '') =>
    request<ProjectResponse>('POST', '/api/v1/projects', { name, description }),
  getProject: (id: number) =>
    request<ProjectResponse>('GET', `/api/v1/projects/${id}`),
  updateProject: (id: number, name: string, description: string) =>
    request<ProjectResponse>('PATCH', `/api/v1/projects/${id}`, { name, description }),

  // Versions
  getVersions: (projectId: number) =>
    request<{ items: VersionResponse[]; total: number }>('GET', `/api/v1/projects/${projectId}/versions`),

  // Workspace
  getWorkspace: (projectId: number) =>
    request<WorkspaceResponse>('GET', `/api/v1/projects/${projectId}/workspace`),
  validate: (workspaceId: number) =>
    request<ValidationSummaryResponse>('POST', `/api/v1/workspaces/${workspaceId}/validate`, {}),
  getValidation: (workspaceId: number) =>
    request<ValidationSummaryResponse>('GET', `/api/v1/workspaces/${workspaceId}/validation`),
  publish: (workspaceId: number, versionName: string) =>
    request<VersionResponse>('POST', `/api/v1/workspaces/${workspaceId}/publish`, { version_name: versionName }),
  snap: (workspaceId: number, lat: number, lng: number) =>
    request<SnapResponse>('POST', `/api/v1/workspaces/${workspaceId}/snap`, { lat, lng }),

  // Map (bulk)
  getMap: (workspaceId: number) =>
    request<MapResponse>('GET', `/api/v1/workspaces/${workspaceId}/map`),

  // Roads
  getRoads: (wsId: number) =>
    request<RoadResponse[]>('GET', `/api/v1/workspaces/${wsId}/roads`),
  createRoad: (wsId: number, data: object) =>
    request<RoadResponse>('POST', `/api/v1/workspaces/${wsId}/roads`, data),
  updateRoad: (wsId: number, id: number, data: object) =>
    request<RoadResponse>('PATCH', `/api/v1/workspaces/${wsId}/roads/${id}`, data),
  deleteRoad: (wsId: number, id: number) =>
    request<void>('DELETE', `/api/v1/workspaces/${wsId}/roads/${id}`),

  // Waypoints
  getWaypoints: (wsId: number) =>
    request<WaypointResponse[]>('GET', `/api/v1/workspaces/${wsId}/waypoints`),
  createWaypoint: (wsId: number, data: object) =>
    request<WaypointResponse>('POST', `/api/v1/workspaces/${wsId}/waypoints`, data),
  updateWaypoint: (wsId: number, id: number, data: object) =>
    request<WaypointResponse>('PATCH', `/api/v1/workspaces/${wsId}/waypoints/${id}`, data),
  deleteWaypoint: (wsId: number, id: number) =>
    request<void>('DELETE', `/api/v1/workspaces/${wsId}/waypoints/${id}`),

  // Crossroads
  getCrossroads: (wsId: number) =>
    request<CrossroadResponse[]>('GET', `/api/v1/workspaces/${wsId}/crossroads`),
  createCrossroad: (wsId: number, data: object) =>
    request<CrossroadResponse>('POST', `/api/v1/workspaces/${wsId}/crossroads`, data),
  deleteCrossroad: (wsId: number, id: number) =>
    request<void>('DELETE', `/api/v1/workspaces/${wsId}/crossroads/${id}`),
  detectCrossroads: (wsId: number) =>
    request<CrossroadResponse[]>('POST', `/api/v1/workspaces/${wsId}/crossroads/detect`),

  // Restricted areas
  getAreas: (wsId: number) =>
    request<RestrictedAreaResponse[]>('GET', `/api/v1/workspaces/${wsId}/restricted-areas`),
  createArea: (wsId: number, data: object) =>
    request<RestrictedAreaResponse>('POST', `/api/v1/workspaces/${wsId}/restricted-areas`, data),
  updateArea: (wsId: number, id: number, data: object) =>
    request<RestrictedAreaResponse>('PATCH', `/api/v1/workspaces/${wsId}/restricted-areas/${id}`, data),
  deleteArea: (wsId: number, id: number) =>
    request<void>('DELETE', `/api/v1/workspaces/${wsId}/restricted-areas/${id}`),

  // Export
  exportVersion: (versionId: number) =>
    request<ExportResponse>('POST', `/api/v1/versions/${versionId}/export`, {}),
  getExports: (projectId: number) =>
    request<{ items: ExportResponse[]; total: number }>('GET', `/api/v1/projects/${projectId}/exports`),
  downloadExportUrl: (versionId: number) =>
    `/api/v1/versions/${versionId}/export/download`,

  // OSM Import — previewOsm sends raw bytes directly (not JSON/multipart)
  previewOsm: async (
    wsId: number,
    file: File,
    opts: { includePedestrian?: boolean; includeUnnamed?: boolean } = {},
  ): Promise<OsmPreviewResponse> => {
    const params = new URLSearchParams()
    if (opts.includePedestrian) params.set('include_pedestrian', 'true')
    if (opts.includeUnnamed) params.set('include_unnamed', 'true')
    const url = `/api/v1/workspaces/${wsId}/osm/preview?${params.toString()}`
    const res = await fetch(url, {
      method: 'POST',
      body: file,
      headers: { 'Content-Type': 'application/octet-stream' },
    })
    if (!res.ok) throw await res.json()
    return res.json()
  },

  importOsm: (wsId: number, payload: {
    roads: ParsedRoadDTO[]
    replace_existing: boolean
  }): Promise<OsmImportResponse> =>
    request<OsmImportResponse>(
      'POST', `/api/v1/workspaces/${wsId}/osm/import`, payload,
    ),

  // Road merge
  getDuplicateGroups: (wsId: number) =>
    request<{ groups: Array<{
      base_name: string
      road_ids: number[]
      road_names: string[]
      total_points: number
    }> }>('GET', `/api/v1/workspaces/${wsId}/roads/duplicate-groups`),

  mergeRoads: (wsId: number, groups: Array<{
    target_name: string
    source_road_ids: number[]
  }>) =>
    request<{ workspace_id: number; results: Array<{
      target_name: string
      merged_road_id: number
      source_road_ids: number[]
      deleted_road_ids: number[]
      total_coordinates: number
      reversed_road_ids: number[]
      gaps_meters: number[]
      reassigned_waypoints: number
      reassigned_crossroads: number
    }> }>(
      'POST', `/api/v1/workspaces/${wsId}/roads/merge`, { groups },
    ),
}
