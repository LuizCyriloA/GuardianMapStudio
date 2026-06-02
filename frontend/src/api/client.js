const API = '';
async function request(method, path, body) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined)
        opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${path}`, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'unknown', message: res.statusText }));
        throw err;
    }
    if (res.status === 204)
        return {};
    return res.json();
}
export const api = {
    // Projects
    getProjects: () => request('GET', '/api/v1/projects'),
    createProject: (name, description = '') => request('POST', '/api/v1/projects', { name, description }),
    getProject: (id) => request('GET', `/api/v1/projects/${id}`),
    updateProject: (id, name, description) => request('PATCH', `/api/v1/projects/${id}`, { name, description }),
    // Versions
    getVersions: (projectId) => request('GET', `/api/v1/projects/${projectId}/versions`),
    // Workspace
    getWorkspace: (projectId) => request('GET', `/api/v1/projects/${projectId}/workspace`),
    validate: (workspaceId) => request('POST', `/api/v1/workspaces/${workspaceId}/validate`, {}),
    getValidation: (workspaceId) => request('GET', `/api/v1/workspaces/${workspaceId}/validation`),
    publish: (workspaceId, versionName) => request('POST', `/api/v1/workspaces/${workspaceId}/publish`, { version_name: versionName }),
    snap: (workspaceId, lat, lng) => request('POST', `/api/v1/workspaces/${workspaceId}/snap`, { lat, lng }),
    // Map (bulk)
    getMap: (workspaceId) => request('GET', `/api/v1/workspaces/${workspaceId}/map`),
    // Roads
    getRoads: (wsId) => request('GET', `/api/v1/workspaces/${wsId}/roads`),
    createRoad: (wsId, data) => request('POST', `/api/v1/workspaces/${wsId}/roads`, data),
    updateRoad: (wsId, id, data) => request('PATCH', `/api/v1/workspaces/${wsId}/roads/${id}`, data),
    deleteRoad: (wsId, id) => request('DELETE', `/api/v1/workspaces/${wsId}/roads/${id}`),
    // Waypoints
    getWaypoints: (wsId) => request('GET', `/api/v1/workspaces/${wsId}/waypoints`),
    createWaypoint: (wsId, data) => request('POST', `/api/v1/workspaces/${wsId}/waypoints`, data),
    updateWaypoint: (wsId, id, data) => request('PATCH', `/api/v1/workspaces/${wsId}/waypoints/${id}`, data),
    deleteWaypoint: (wsId, id) => request('DELETE', `/api/v1/workspaces/${wsId}/waypoints/${id}`),
    // Crossroads
    getCrossroads: (wsId) => request('GET', `/api/v1/workspaces/${wsId}/crossroads`),
    createCrossroad: (wsId, data) => request('POST', `/api/v1/workspaces/${wsId}/crossroads`, data),
    deleteCrossroad: (wsId, id) => request('DELETE', `/api/v1/workspaces/${wsId}/crossroads/${id}`),
    // Restricted areas
    getAreas: (wsId) => request('GET', `/api/v1/workspaces/${wsId}/restricted-areas`),
    createArea: (wsId, data) => request('POST', `/api/v1/workspaces/${wsId}/restricted-areas`, data),
    updateArea: (wsId, id, data) => request('PATCH', `/api/v1/workspaces/${wsId}/restricted-areas/${id}`, data),
    deleteArea: (wsId, id) => request('DELETE', `/api/v1/workspaces/${wsId}/restricted-areas/${id}`),
    // Export
    exportVersion: (versionId) => request('POST', `/api/v1/versions/${versionId}/export`, {}),
    getExports: (projectId) => request('GET', `/api/v1/projects/${projectId}/exports`),
    downloadExportUrl: (versionId) => `/api/v1/versions/${versionId}/export/download`,
    // OSM Import — previewOsm sends raw bytes directly (not JSON/multipart)
    previewOsm: async (wsId, file, opts = {}) => {
        const params = new URLSearchParams();
        if (opts.includePedestrian)
            params.set('include_pedestrian', 'true');
        if (opts.includeUnnamed)
            params.set('include_unnamed', 'true');
        const url = `/api/v1/workspaces/${wsId}/osm/preview?${params.toString()}`;
        const res = await fetch(url, {
            method: 'POST',
            body: file,
            headers: { 'Content-Type': 'application/octet-stream' },
        });
        if (!res.ok)
            throw await res.json();
        return res.json();
    },
    importOsm: (wsId, payload) => request('POST', `/api/v1/workspaces/${wsId}/osm/import`, payload),
};
