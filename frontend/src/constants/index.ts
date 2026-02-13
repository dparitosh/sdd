/**
 * Application-wide constants
 * Centralizes magic numbers and configuration values
 */

// API Configuration
export const API_CONFIG = {
  /** Base URL for API requests (proxied through Vite) */
  BASE_URL: '/api',
  
  /** Request timeout in milliseconds */
  TIMEOUT: 30000, // 30 seconds for complex queries
  
  /** Short timeout for simple requests */
  SHORT_TIMEOUT: 5000, // 5 seconds
  
  /** Long timeout for uploads and exports */
  LONG_TIMEOUT: 60000, // 60 seconds
} as const;

// Query Configuration
export const QUERY_CONFIG = {
  /** React Query stale time in milliseconds */
  STALE_TIME: 5 * 60 * 1000, // 5 minutes
  
  /** Number of retry attempts for failed queries */
  RETRY_ATTEMPTS: 1,
  
  /** Cache time in milliseconds */
  CACHE_TIME: 10 * 60 * 1000, // 10 minutes
} as const;

// Pagination
export const PAGINATION = {
  /** Default page size */
  DEFAULT_PAGE_SIZE: 20,
  
  /** Maximum page size */
  MAX_PAGE_SIZE: 100,
  
  /** Requirements default limit */
  REQUIREMENTS_DEFAULT_LIMIT: 100,
  
  /** Requirements max limit */
  REQUIREMENTS_MAX_LIMIT: 500,
} as const;

// Graph Visualization
export const GRAPH_CONFIG = {
  /** Maximum nodes to display in graph */
  MAX_NODES: 1000,
  
  /** Default node limit for queries */
  DEFAULT_NODE_LIMIT: 100,
  
  /** Force simulation settings */
  FORCE_STRENGTH: -300,
  DISTANCE: 150,
  
  /** Node sizes */
  NODE_RADIUS: 8,
  NODE_RADIUS_LARGE: 12,
} as const;

// Upload Configuration
export const UPLOAD_CONFIG = {
  /** Max file size in bytes (50MB) */
  MAX_FILE_SIZE: 50 * 1024 * 1024,
  
  /** Allowed file types */
  ALLOWED_FILE_TYPES: ['.xmi', '.xml', '.csv', '.uml'] as const,
  
  /** Status polling interval in milliseconds */
  POLL_INTERVAL: 1000, // 1 second
  
  /** Max polling duration in milliseconds */
  MAX_POLL_DURATION: 300000, // 5 minutes
  
  /** Job TTL in Redis (hours) */
  JOB_TTL_HOURS: 24,
} as const;

// Rate Limiting
export const RATE_LIMITS = {
  /** Search endpoint rate limit (requests per minute) */
  SEARCH_RPM: 60,
  
  /** Cypher endpoint rate limit (requests per minute) */
  CYPHER_RPM: 30,
  
  /** Default rate limit for other endpoints */
  DEFAULT_RPM: 100,
} as const;

// Cache TTL
export const CACHE_TTL = {
  /** Stats cache TTL in seconds */
  STATS: 60,
  
  /** Requirements list cache TTL in seconds */
  REQUIREMENTS: 300, // 5 minutes
  
  /** Parts list cache TTL in seconds */
  PARTS: 300, // 5 minutes
} as const;

// Neo4j Configuration
export const NEO4J_CONFIG = {
  /** Max connection lifetime in seconds */
  MAX_CONNECTION_LIFETIME: 3600, // 1 hour
  
  /** Connection pool size */
  MAX_CONNECTION_POOL_SIZE: 50,
  
  /** Query timeout in milliseconds */
  QUERY_TIMEOUT: 30000, // 30 seconds
  
  /** Retry attempts for failed connections */
  RETRY_ATTEMPTS: 3,
  
  /** Base delay for exponential backoff (ms) */
  RETRY_BASE_DELAY: 2000, // 2 seconds
} as const;

// UI Configuration
export const UI_CONFIG = {
  /** Toast notification duration in milliseconds */
  TOAST_DURATION: 5000,
  
  /** Debounce delay for search inputs in milliseconds */
  SEARCH_DEBOUNCE: 300,
  
  /** Animation duration in milliseconds */
  ANIMATION_DURATION: 200,
  
  /** Sidebar width in pixels */
  SIDEBAR_WIDTH: 256,
  
  /** Sidebar collapsed width in pixels */
  SIDEBAR_COLLAPSED_WIDTH: 64,
} as const;

// Export Formats
export const EXPORT_FORMATS = [
  { value: 'rdf', label: 'RDF/Turtle', extension: '.ttl', endpoint: '/api/export/rdf', description: 'Semantic Web (Turtle)' },
  { value: 'json-ld', label: 'JSON-LD', extension: '.jsonld', endpoint: '/api/export/jsonld', description: 'Linked Data JSON' },
  { value: 'csv', label: 'CSV Archive', extension: '.zip', endpoint: '/api/export/csv', description: 'Tabular Data (ZIP)' },
  { value: 'graphml', label: 'GraphML', extension: '.graphml', endpoint: '/api/export/graphml', description: 'Graph Visualization' },
  { value: 'step', label: 'STEP AP242', extension: '.stp', endpoint: '/api/export/step', description: 'CAD/PLM Exchange' },
  { value: 'plantuml', label: 'PlantUML', extension: '.puml', endpoint: '/api/export/plantuml', description: 'Class Diagrams' },
  { value: 'cytoscape', label: 'Cytoscape', extension: '.json', endpoint: '/api/export/cytoscape', description: 'Web Visualization' },
] as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  AUTH: 'mbse-auth-storage',
  LANGUAGE: 'mbse-language',
  THEME: 'mbse-theme',
  SIDEBAR_STATE: 'mbse-sidebar-state',
} as const;

// WebSocket Events
export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  NODE_CREATED: 'node_created',
  NODE_UPDATED: 'node_updated',
  NODE_DELETED: 'node_deleted',
  RELATIONSHIP_CREATED: 'relationship_created',
  RELATIONSHIP_DELETED: 'relationship_deleted',
  REQUIREMENT_UPDATED: 'requirement_updated',
  PART_UPDATED: 'part_updated',
} as const;

export default {
  API_CONFIG,
  QUERY_CONFIG,
  PAGINATION,
  GRAPH_CONFIG,
  UPLOAD_CONFIG,
  RATE_LIMITS,
  CACHE_TTL,
  NEO4J_CONFIG,
  UI_CONFIG,
  EXPORT_FORMATS,
  STORAGE_KEYS,
  WS_EVENTS,
};
