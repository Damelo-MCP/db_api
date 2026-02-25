# Dámelo API - Resumen Rápido de Endpoints

**Versión:** 2.0.0
**Base URL:** `http://localhost:8000/fenix`

---

## 🔐 Headers de Autenticación

Todos los endpoints excepto `/health` requieren:

```http
X-MCP-API-Key: {your_mcp_api_key}
X-GitHub-Handle: {github_username}
```

---

## 📋 Tabla de Endpoints (17 Total)

| # | Método | Endpoint | Descripción | Auth | Permisos |
|---|--------|----------|-------------|------|----------|
| **AUTH** | | | | | |
| 1 | `POST` | `/auth/validate-or-create` | Validar/crear usuario | ✅ | - |
| **USERS** | | | | | |
| 2 | `GET` | `/users/me` | Usuario actual | ✅ | - |
| **TEAMS** | | | | | |
| 3 | `POST` | `/teams` | Crear equipo | ✅ | - |
| 4 | `GET` | `/teams` | Listar equipos | ✅ | - |
| 5 | `GET` | `/teams/{team_id}` | Detalles de equipo | ✅ | Member |
| 6 | `POST` | `/teams/{team_id}/members` | Añadir miembro | ✅ | Owner/Admin |
| 7 | `DELETE` | `/teams/{team_id}/members/{github_handle}` | Remover miembro | ✅ | Owner/Admin |
| **SESSIONS** | | | | | |
| 8 | `POST` | `/sessions` | Crear sesión | ✅ | - |
| 9 | `GET` | `/sessions` | Listar sesiones | ✅ | - |
| 10 | `GET` | `/sessions/by-repo?repo=` | Sesiones por repo | ✅ | - |
| 11 | `GET` | `/sessions/{session_id}` | Detalles de sesión | ✅ | Owner/Public/Team |
| 12 | `PATCH` | `/sessions/{session_id}` | Actualizar sesión | ✅ | Owner |
| 13 | `DELETE` | `/sessions/{session_id}` | Eliminar sesión | ✅ | Owner |
| **TEAM SESSIONS** | | | | | |
| 14 | `POST` | `/teams/{team_id}/sessions` | Compartir sesión | ✅ | Member + Owner |
| 15 | `GET` | `/teams/{team_id}/sessions` | Sesiones del equipo | ✅ | Member |
| 16 | `DELETE` | `/teams/{team_id}/sessions/{session_id}` | Dejar de compartir | ✅ | Admin/SessionOwner |
| **HEALTH** | | | | | |
| 17 | `GET` | `/health` | Health check | ❌ | - |

---

## 🎯 Endpoints por Categoría

### Auth (1)
- `POST /auth/validate-or-create`

### Users (1)
- `GET /users/me`

### Teams (5)
- `POST /teams`
- `GET /teams`
- `GET /teams/{team_id}`
- `POST /teams/{team_id}/members`
- `DELETE /teams/{team_id}/members/{github_handle}`

### Sessions (6)
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/by-repo`
- `GET /sessions/{session_id}`
- `PATCH /sessions/{session_id}`
- `DELETE /sessions/{session_id}`

### Team Sessions (3)
- `POST /teams/{team_id}/sessions`
- `GET /teams/{team_id}/sessions`
- `DELETE /teams/{team_id}/sessions/{session_id}`

### Health (1)
- `GET /health`

---

## 📊 Request/Response Quick Reference

### Auth
```bash
# Validar/crear usuario
POST /auth/validate-or-create
Body: {"email": "...", "display_name": "..."}
→ 200/201: {github_handle, email, display_name, is_active, created_at, existed}
```

### Teams
```bash
# Crear equipo
POST /teams
Body: {"name": "...", "description": "..."}
→ 201: {id, name, description, owner, created_at}

# Añadir miembro
POST /teams/{team_id}/members
Body: {"github_handle": "...", "role": "member|admin|owner"}
→ 201: {success, message}

# Remover miembro
DELETE /teams/{team_id}/members/{github_handle}
→ 200: {success, message}
```

### Sessions
```bash
# Crear sesión
POST /sessions
Body: {
  "title": "...",
  "session_data": "...",
  "description": "...",
  "assistant_type": "claude-code",
  "repo": "owner/repo",
  "metadata": {},
  "is_public": false
}
→ 201: {id, title, description, assistant_type, repo, metadata, owner, is_public, created_at}

# Actualizar sesión
PATCH /sessions/{session_id}
Body: {campos opcionales...}
→ 200: SessionOut

# Filtrar sesiones
GET /sessions?assistant_type=claude-code
GET /sessions/by-repo?repo=owner/repo
→ 200: [SessionOut, ...]
```

### Team Sessions
```bash
# Compartir sesión
POST /teams/{team_id}/sessions
Body: {"session_id": "..."}
→ 201: {success, team_id, session_id, message}

# Listar sesiones compartidas
GET /teams/{team_id}/sessions
→ 200: [{id, session: SessionOut, shared_at}, ...]

# Dejar de compartir
DELETE /teams/{team_id}/sessions/{session_id}
→ 200: {success, message}
```

---

## 🔒 Matriz de Permisos

| Acción | Owner | Admin | Member | Public |
|--------|-------|-------|--------|--------|
| **Teams** |
| Ver equipo | ✅ | ✅ | ✅ | ❌ |
| Añadir miembros | ✅ | ✅ | ❌ | ❌ |
| Remover miembros | ✅ | ✅ | ❌ | ❌ |
| Remover owner | ❌ | ❌ | ❌ | ❌ |
| **Sessions** |
| Ver sesión propia | ✅ | - | - | - |
| Ver sesión pública | ✅ | ✅ | ✅ | ✅ |
| Ver sesión de equipo | ✅ | ✅ | ✅ | ❌ |
| Actualizar sesión | ✅ (propia) | ❌ | ❌ | ❌ |
| Eliminar sesión | ✅ (propia) | ❌ | ❌ | ❌ |
| Compartir con equipo | ✅ (propia) | ❌ | ❌ | ❌ |
| Dejar de compartir | ✅ (owner)* | ✅ (admin)* | ❌ | ❌ |

\* Para dejar de compartir: owner de sesión O admin/owner del equipo

---

## 🗄️ Modelos Principales

### User
```
github_handle (PK) | email | display_name | is_active | created_at
```

### Team
```
id (UUID) | name | description | owner_id (FK) | created_at
```

### Session
```
id (UUID) | title | description | session_data | assistant_type |
repo | metadata | owner_id (FK) | is_public | created_at | updated_at
```

### TeamUser
```
id (UUID) | team_id (FK) | user_id (FK) | role | created_at
Unique: (team_id, user_id)
```

### TeamSession
```
id (UUID) | team_id (FK) | session_id (FK) | created_at
Unique: (team_id, session_id)
```

---

## ⚡ Ejemplos de Uso Rápido

### Crear un equipo y compartir sesión
```bash
# 1. Crear equipo
curl -X POST "http://localhost:8000/fenix/teams" \
  -H "X-MCP-API-Key: key" \
  -H "X-GitHub-Handle: user" \
  -H "Content-Type: application/json" \
  -d '{"name": "Dev Team"}'
# → team_id

# 2. Crear sesión
curl -X POST "http://localhost:8000/fenix/sessions" \
  -H "X-MCP-API-Key: key" \
  -H "X-GitHub-Handle: user" \
  -H "Content-Type: application/json" \
  -d '{"title": "Fix", "session_data": "{}", "repo": "me/repo"}'
# → session_id

# 3. Compartir
curl -X POST "http://localhost:8000/fenix/teams/{team_id}/sessions" \
  -H "X-MCP-API-Key: key" \
  -H "X-GitHub-Handle: user" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "{session_id}"}'
```

### Añadir miembro y ver sesiones
```bash
# 1. Añadir miembro
curl -X POST "http://localhost:8000/fenix/teams/{team_id}/members" \
  -H "X-MCP-API-Key: key" \
  -H "X-GitHub-Handle: owner" \
  -H "Content-Type: application/json" \
  -d '{"github_handle": "newmember", "role": "member"}'

# 2. Ver sesiones (como nuevo miembro)
curl -X GET "http://localhost:8000/fenix/teams/{team_id}/sessions" \
  -H "X-MCP-API-Key: key" \
  -H "X-GitHub-Handle: newmember"
```

### Buscar sesiones por repo
```bash
curl -X GET "http://localhost:8000/fenix/sessions/by-repo?repo=org/project" \
  -H "X-MCP-API-Key: key" \
  -H "X-GitHub-Handle: user"
```

---

## 🚨 Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| 401 Unauthorized | API key inválida o headers faltantes | Verificar `X-MCP-API-Key` y `X-GitHub-Handle` |
| 403 Forbidden (teams) | No eres miembro | Necesitas ser añadido al equipo |
| 403 Forbidden (sessions) | No eres owner | Solo el owner puede modificar |
| 400 Already exists | Recurso duplicado | Usuario ya en equipo o sesión ya compartida |
| 404 Not Found | Recurso no existe | Verificar IDs |

---

## 📖 Documentación Completa

Ver `API_DOCUMENTATION.md` para documentación detallada con todos los schemas, ejemplos curl completos, y especificaciones técnicas.

---

**Última actualización:** 2026-02-15
**Versión:** 2.0.0
