# API Deprecations and Migrations

This document tracks deprecated API endpoints and provides their replacements.

Updated: 2025-09-25

- Category: Agent API

Deprecated Endpoints (return 410):
- POST `/api/v1/agent/execute-stream`
  - Replacement:
    - Start: POST `/api/agent/run-async`
    - Status: GET `/api/agent/run-async/{task_id}/status`
    - Stream: GET `/api/agent/run-async/{task_id}/stream`
- POST `/api/v1/agent/execute`
  - Replacement: POST `/api/agent/run`
- GET `/api/v1/agent/status/{task_id}`
  - Replacement: GET `/api/agent/run-async/{task_id}/status`
- GET `/api/v1/agent/coordinator/status`
  - Replacement: GET `/api/agent/system/async-status`

Compatibility Alias:
- All new Agent Run APIs are now available at both versioned and unversioned paths:
  - Versioned (existing): `/api/v1/agent/*`
  - Stable alias (new): `/api/agent/*`

Notes:
- The unversioned alias is intended as a stable integration surface for external clients.
- The versioned paths remain supported; migrations can be performed incrementally.
