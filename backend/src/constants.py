"""
Application-wide constants for backend
Centralizes magic numbers and configuration values
"""

# API Configuration
class APIConfig:
    """API-related configuration constants"""
    REQUEST_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 2  # seconds for exponential backoff

# Pagination
class Pagination:
    """Pagination defaults and limits"""
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 500
    REQUIREMENTS_DEFAULT = 100
    REQUIREMENTS_MAX = 500

# Graph Limits
class GraphLimits:
    """Graph query limits"""
    MAX_NODES = 1000
    DEFAULT_NODES = 100
    MAX_DEPTH = 5

# Rate Limiting (requests per minute)
class RateLimits:
    """Rate limiting configuration"""
    SEARCH_RPM = 60
    CYPHER_RPM = 30
    UPLOAD_RPM = 10
    DEFAULT_RPM = 100

# Cache TTL (seconds)
class CacheTTL:
    """Cache time-to-live values"""
    STATS = 60  # 1 minute
    REQUIREMENTS = 300  # 5 minutes
    PARTS = 300  # 5 minutes
    UPLOAD_JOB = 86400  # 24 hours

# Neo4j Configuration
class Neo4jConfig:
    """Neo4j connection and query settings"""
    MAX_CONNECTION_LIFETIME = 3600  # 1 hour
    MAX_CONNECTION_POOL_SIZE = 50
    QUERY_TIMEOUT = 30  # seconds
    KEEP_ALIVE = True
    
    # Retry settings
    MAX_RETRY_ATTEMPTS = 3
    RETRY_BASE_DELAY = 2  # seconds
    RETRY_MAX_DELAY = 10  # seconds

# Upload Configuration
class UploadConfig:
    """File upload settings"""
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'.xmi', '.xml', '.csv', '.uml'}
    CHUNK_SIZE = 8192  # bytes
    JOB_TTL_HOURS = 24

# Redis Configuration
class RedisConfig:
    """Redis cache and session settings"""
    DEFAULT_TTL = 3600  # 1 hour
    SESSION_TTL = 86400  # 24 hours
    JOB_TTL = 86400  # 24 hours
    KEY_PREFIX_JOB = "upload_job:"
    KEY_PREFIX_CACHE = "cache:"
    KEY_PREFIX_SESSION = "session:"

# Logging
class LoggingConfig:
    """Logging configuration"""
    LOG_FORMAT = "[%(request_id)s] %(method)s %(path)s - %(message)s"
    LOG_LEVEL = "INFO"
    REQUEST_ID_HEADER = "X-Request-ID"

# Security
class SecurityConfig:
    """Security-related settings"""
    TOKEN_EXPIRY_HOURS = 24
    BCRYPT_ROUNDS = 12
    MIN_PASSWORD_LENGTH = 8
    SESSION_TIMEOUT = 3600  # 1 hour

# Export Configuration
class ExportConfig:
    """Export format settings"""
    MAX_EXPORT_SIZE = 100000  # max nodes/relationships
    CHUNK_SIZE = 1000  # records per chunk
    TIMEOUT = 300  # 5 minutes

# SMRL API Version
class SMRLConfig:
    """SMRL standard configuration"""
    API_VERSION = "v1"
    SUPPORTED_RESOURCE_TYPES = [
        "Requirement",
        "Part",
        "Interface",
        "Function",
        "Verification",
        "Validation",
        "Person",
        "Organization",
        "ChangeRequest",
        "Document",
        "TestCase"
    ]

# HTTP Status Codes (for clarity)
class HTTPStatus:
    """Common HTTP status codes"""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503

# Export all configs
__all__ = [
    'APIConfig',
    'Pagination',
    'GraphLimits',
    'RateLimits',
    'CacheTTL',
    'Neo4jConfig',
    'UploadConfig',
    'RedisConfig',
    'LoggingConfig',
    'SecurityConfig',
    'ExportConfig',
    'SMRLConfig',
    'HTTPStatus',
]
