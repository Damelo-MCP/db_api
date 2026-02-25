from ninja import NinjaAPI, Router
from ninja.security import APIKeyHeader
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from django.db.models import Q
from typing import List
from dotenv import load_dotenv

import os

from .models import User, Team, Session, TeamUser, TeamSession
from .schemas import (
    UserOut, ValidateOrCreateUserIn, ValidateOrCreateUserOut,
    TeamOut, TeamCreateIn, TeamDetailOut, TeamAddMemberIn, TeamMemberOut,
    SessionOut, SessionCreateIn, SessionDetailOut, SessionUpdateIn,
    ShareSessionWithTeamIn, ShareSessionWithTeamOut, TeamSessionOut,
    ErrorOut, SuccessOut
)
from .services.s3_service import s3_service

load_dotenv()

MCP_API_KEY = os.environ.get('MCP_API_KEY')

# ============================================
# AUTHENTICATION
# ============================================

class MCPAuth(APIKeyHeader):
    """
    Middleware de autenticación para MCP.
    Valida el API key compartido entre MCP y db_api.
    Extrae el github_handle del header X-GitHub-Handle.
    """
    param_name = "X-MCP-API-Key"

    def authenticate(self, request: HttpRequest, key: str):
        # Validar API key
        if key != MCP_API_KEY:
            return None

        # Extraer github_handle del header
        github_handle = request.headers.get('X-GitHub-Handle')
        if not github_handle:
            return None

        # Retornar github_handle para que esté disponible en request.auth
        return github_handle

# ============================================
# API INSTANCE
# ============================================

api = NinjaAPI(
    title="Dámelo API",
    version="2.0.0",
    description="API para compartir sesiones de asistentes de IA - Personal y Teams"
)

auth = MCPAuth()


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_user_from_request(request: HttpRequest) -> User:
    """
    Obtiene el objeto User a partir del github_handle en request.auth
    """
    github_handle = request.auth
    return get_object_or_404(User, github_handle=github_handle)


# ============================================
# AUTH ENDPOINTS
# ============================================

@api.post("/auth/validate-or-create", auth=auth, response={200: ValidateOrCreateUserOut, 201: ValidateOrCreateUserOut}, tags=["Auth"])
def validate_or_create_user(request, payload: ValidateOrCreateUserIn):
    """
    Valida si un usuario existe o lo crea si no existe.
    El MCP llama este endpoint después de autenticar al usuario vía OAuth.
    """
    # El github_handle viene en request.auth (extraído del header X-GitHub-Handle)
    github_handle = request.auth

    # Verificar si el usuario ya existe
    try:
        user = User.objects.get(github_handle=github_handle)
        # Usuario existe, actualizamos datos si vienen en el payload
        if payload.email:
            user.email = payload.email
        if payload.display_name:
            user.display_name = payload.display_name
        user.save()

        return 200, {
            "github_handle": user.github_handle,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "existed": True
        }
    except User.DoesNotExist:
        # Usuario no existe, crearlo
        user = User.objects.create(
            github_handle=github_handle,
            email=payload.email,
            display_name=payload.display_name
        )

        return 201, {
            "github_handle": user.github_handle,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "existed": False
        }


# ============================================
# USER ENDPOINTS
# ============================================

@api.get("/users/me", auth=auth, response=UserOut, tags=["Users"])
def get_current_user(request):
    """Obtener información del usuario autenticado"""
    user = get_user_from_request(request)
    return {
        "github_handle": user.github_handle,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "created_at": user.created_at
    }


# ============================================
# TEAM ENDPOINTS
# ============================================

@api.post("/teams", auth=auth, response={201: TeamOut, 400: ErrorOut}, tags=["Teams"])
def create_team(request, payload: TeamCreateIn):
    """Crear un nuevo equipo"""
    user = get_user_from_request(request)

    # Crear el equipo
    team = Team.objects.create(
        name=payload.name,
        description=payload.description,
        owner=user
    )

    # Añadir al creador como owner en la relación
    TeamUser.objects.create(
        team=team,
        user=user,
        role='owner'
    )

    return 201, {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner": {
            "github_handle": user.github_handle,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        "created_at": team.created_at
    }


@api.get("/teams", auth=auth, response=List[TeamOut], tags=["Teams"])
def list_teams(request):
    """Listar equipos del usuario"""
    user = get_user_from_request(request)

    # Obtener equipos donde el usuario es miembro
    teams = Team.objects.filter(
        team_users__user=user
    ).select_related('owner').distinct()

    return [
        {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "owner": {
                "github_handle": team.owner.github_handle,
                "email": team.owner.email,
                "display_name": team.owner.display_name,
                "is_active": team.owner.is_active,
                "created_at": team.owner.created_at
            },
            "created_at": team.created_at
        }
        for team in teams
    ]


@api.get("/teams/{team_id}", auth=auth, response={200: TeamDetailOut, 403: ErrorOut, 404: ErrorOut}, tags=["Teams"])
def get_team(request, team_id: str):
    """Obtener detalles de un equipo"""
    user = get_user_from_request(request)

    team = get_object_or_404(Team, id=team_id)

    # Verificar que el usuario es miembro del equipo
    if not TeamUser.objects.filter(team=team, user=user).exists():
        return 403, {"detail": "You are not a member of this team"}

    # Obtener miembros del equipo
    members = TeamUser.objects.filter(team=team).select_related('user')

    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "owner": {
            "github_handle": team.owner.github_handle,
            "email": team.owner.email,
            "display_name": team.owner.display_name,
            "is_active": team.owner.is_active,
            "created_at": team.owner.created_at
        },
        "members": [
            {
                "id": member.id,
                "user": {
                    "github_handle": member.user.github_handle,
                    "email": member.user.email,
                    "display_name": member.user.display_name,
                    "is_active": member.user.is_active,
                    "created_at": member.user.created_at
                },
                "role": member.role,
                "created_at": member.created_at
            }
            for member in members
        ],
        "created_at": team.created_at
    }


@api.post("/teams/{team_id}/members", auth=auth, response={201: SuccessOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut}, tags=["Teams"])
def add_team_member(request, team_id: str, payload: TeamAddMemberIn):
    """Añadir miembro a un equipo"""
    user = get_user_from_request(request)

    team = get_object_or_404(Team, id=team_id)

    # Verificar que el usuario es owner o admin del equipo
    membership = TeamUser.objects.filter(team=team, user=user).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return 403, {"detail": "Only owners and admins can add members"}

    # Buscar usuario a añadir
    try:
        new_member = User.objects.get(github_handle=payload.github_handle)
    except User.DoesNotExist:
        return 400, {"detail": f"User @{payload.github_handle} not found"}

    # Verificar que no sea ya miembro
    if TeamUser.objects.filter(team=team, user=new_member).exists():
        return 400, {"detail": f"@{payload.github_handle} is already a member"}

    # Añadir miembro
    TeamUser.objects.create(
        team=team,
        user=new_member,
        role=payload.role
    )

    return 201, {
        "success": True,
        "message": f"@{payload.github_handle} added to team as {payload.role}"
    }


@api.delete("/teams/{team_id}/members/{github_handle}", auth=auth, response={200: SuccessOut, 403: ErrorOut, 404: ErrorOut}, tags=["Teams"])
def remove_team_member(request, team_id: str, github_handle: str):
    """Remover miembro de un equipo"""
    user = get_user_from_request(request)

    team = get_object_or_404(Team, id=team_id)

    # Verificar que el usuario es owner o admin del equipo
    membership = TeamUser.objects.filter(team=team, user=user).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return 403, {"detail": "Only owners and admins can remove members"}

    # Buscar miembro a remover
    member_to_remove = get_object_or_404(TeamUser, team=team, user__github_handle=github_handle)

    # No permitir remover al owner
    if member_to_remove.role == 'owner':
        return 403, {"detail": "Cannot remove team owner"}

    member_to_remove.delete()

    return {
        "success": True,
        "message": "Member removed from team"
    }


# ============================================
# SESSION ENDPOINTS
# ============================================

@api.post("/sessions", auth=auth, response={201: SessionOut, 400: ErrorOut}, tags=["Sessions"])
def create_session(request, payload: SessionCreateIn):
    """Crear una nueva sesión y subir session_data a S3"""
    user = get_user_from_request(request)

    # Crear sesión primero para obtener el ID real
    session = Session.objects.create(
        title=payload.title,
        description=payload.description,
        session_data=payload.session_data,
        assistant_type=payload.assistant_type,
        repo=payload.repo,
        metadata=payload.metadata or {},
        owner=user,
        is_public=payload.is_public
    )

    # Subir session_data a S3 como archivo .md
    report_url = s3_service.upload_session_report(
        session_id=str(session.id),
        content=payload.session_data,
        github_handle=user.github_handle
    )

    # Actualizar sesión con la URL del reporte
    if report_url:
        session.report_url = report_url
        session.save()

    return 201, {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "assistant_type": session.assistant_type,
        "repo": session.repo,
        "metadata": session.metadata,
        "owner": {
            "github_handle": user.github_handle,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        "is_public": session.is_public,
        "report_url": session.report_url,
        "created_at": session.created_at
    }


@api.get("/sessions", auth=auth, response=List[SessionOut], tags=["Sessions"])
def list_sessions(request, assistant_type: str = None):
    """Listar sesiones del usuario"""
    user = get_user_from_request(request)

    # Sesiones propias del usuario
    sessions = Session.objects.filter(owner=user)

    if assistant_type:
        sessions = sessions.filter(assistant_type=assistant_type)

    sessions = sessions.select_related('owner').order_by('-created_at')

    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "assistant_type": s.assistant_type,
            "repo": s.repo,
            "metadata": s.metadata,
            "owner": {
                "github_handle": s.owner.github_handle,
                "email": s.owner.email,
                "display_name": s.owner.display_name,
                "is_active": s.owner.is_active,
                "created_at": s.owner.created_at
            },
            "is_public": s.is_public,
            "report_url": s.report_url,
            "created_at": s.created_at
        }
        for s in sessions
    ]


@api.get("/sessions/by-repo", auth=auth, response={200: List[SessionOut], 400: ErrorOut}, tags=["Sessions"])
def list_sessions_by_repo(request, repo: str):
    """Listar sesiones de un repo compartidas en equipos del usuario"""
    user = get_user_from_request(request)

    if not repo:
        return 400, {"detail": "repo parameter is required"}

    # Obtener equipos del usuario
    user_teams = Team.objects.filter(team_users__user=user)

    # Buscar sesiones:
    # 1. Que tengan el repo especificado
    # 2. Que estén compartidas con algún equipo del usuario
    sessions = Session.objects.filter(
        repo=repo,
        shared_with_teams__team__in=user_teams
    ).select_related('owner').distinct().order_by('-created_at')

    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "assistant_type": s.assistant_type,
            "repo": s.repo,
            "metadata": s.metadata,
            "owner": {
                "github_handle": s.owner.github_handle,
                "email": s.owner.email,
                "display_name": s.owner.display_name,
                "is_active": s.owner.is_active,
                "created_at": s.owner.created_at
            },
            "is_public": s.is_public,
            "report_url": s.report_url,
            "created_at": s.created_at
        }
        for s in sessions
    ]


@api.get("/sessions/{session_id}", auth=auth, response={200: SessionDetailOut, 403: ErrorOut, 404: ErrorOut}, tags=["Sessions"])
def get_session(request, session_id: str):
    """Obtener detalles completos de una sesión"""
    user = get_user_from_request(request)

    session = get_object_or_404(Session, id=session_id)

    # Verificar acceso: owner, sesión pública, o miembro de equipo con acceso
    has_access = (
        session.owner == user or
        session.is_public or
        TeamSession.objects.filter(
            session=session,
            team__team_users__user=user
        ).exists()
    )

    if not has_access:
        return 403, {"detail": "You don't have access to this session"}

    return {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "session_data": session.session_data,
        "assistant_type": session.assistant_type,
        "repo": session.repo,
        "metadata": session.metadata,
        "owner": {
            "github_handle": session.owner.github_handle,
            "email": session.owner.email,
            "display_name": session.owner.display_name,
            "is_active": session.owner.is_active,
            "created_at": session.owner.created_at
        },
        "is_public": session.is_public,
        "report_url": session.report_url,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@api.patch("/sessions/{session_id}", auth=auth, response={200: SessionOut, 403: ErrorOut, 404: ErrorOut}, tags=["Sessions"])
def update_session(request, session_id: str, payload: SessionUpdateIn):
    """Actualizar una sesión"""
    user = get_user_from_request(request)

    session = get_object_or_404(Session, id=session_id)

    # El owner o cualquier miembro de un team con acceso puede actualizar
    if session.owner != user:
        is_team_member = TeamSession.objects.filter(
            session=session,
            team__team_users__user=user
        ).exists()
        if not is_team_member:
            return 403, {"detail": "Only the owner or a team member can update this session"}

    # Actualizar campos si están presentes
    if payload.title is not None:
        session.title = payload.title
    if payload.description is not None:
        session.description = payload.description
    if payload.session_data is not None:
        session.session_data = payload.session_data
        # Subir session_data actualizado a S3 (sobreescribir el archivo existente)
        report_url = s3_service.update_session_report(
            report_url=session.report_url,
            content=payload.session_data,
        )
        if report_url: session.report_url = report_url
    if payload.repo is not None:
        session.repo = payload.repo
    if payload.metadata is not None:
        session.metadata = payload.metadata
    if payload.is_public is not None:
        session.is_public = payload.is_public

    session.save()

    return {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "assistant_type": session.assistant_type,
        "repo": session.repo,
        "metadata": session.metadata,
        "owner": {
            "github_handle": session.owner.github_handle,
            "email": session.owner.email,
            "display_name": session.owner.display_name,
            "is_active": session.owner.is_active,
            "created_at": session.owner.created_at
        },
        "is_public": session.is_public,
        "report_url": session.report_url,
        "created_at": session.created_at
    }


@api.delete("/sessions/{session_id}", auth=auth, response={200: SuccessOut, 403: ErrorOut, 404: ErrorOut}, tags=["Sessions"])
def delete_session(request, session_id: str):
    """Eliminar una sesión"""
    user = get_user_from_request(request)

    session = get_object_or_404(Session, id=session_id)

    # Solo el owner puede eliminar
    if session.owner != user:
        return 403, {"detail": "Only the owner can delete this session"}

    session.delete()

    return {
        "success": True,
        "message": "Session deleted successfully"
    }


# ============================================
# TEAM SESSION ENDPOINTS (sharing)
# ============================================

@api.post("/teams/{team_id}/sessions", auth=auth, response={201: ShareSessionWithTeamOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut}, tags=["Team Sessions"])
def share_session_with_team(request, team_id: str, payload: ShareSessionWithTeamIn):
    """Compartir una sesión con un equipo"""
    user = get_user_from_request(request)

    team = get_object_or_404(Team, id=team_id)
    session = get_object_or_404(Session, id=payload.session_id)

    # Verificar que el usuario es miembro del equipo
    if not TeamUser.objects.filter(team=team, user=user).exists():
        return 403, {"detail": "You are not a member of this team"}

    # Verificar que el usuario es el dueño de la sesión
    if session.owner != user:
        return 403, {"detail": "You can only share your own sessions"}

    # Verificar que no esté ya compartida
    if TeamSession.objects.filter(team=team, session=session).exists():
        return 400, {"detail": "Session already shared with this team"}

    # Compartir sesión
    TeamSession.objects.create(
        team=team,
        session=session
    )

    return 201, {
        "success": True,
        "team_id": team.id,
        "session_id": session.id,
        "message": f"Session shared with team {team.name}"
    }


@api.get("/teams/{team_id}/sessions", auth=auth, response={200: List[TeamSessionOut], 403: ErrorOut, 404: ErrorOut}, tags=["Team Sessions"])
def list_team_sessions(request, team_id: str):
    """Listar sesiones compartidas con un equipo"""
    user = get_user_from_request(request)

    team = get_object_or_404(Team, id=team_id)

    # Verificar que el usuario es miembro del equipo
    if not TeamUser.objects.filter(team=team, user=user).exists():
        return 403, {"detail": "You are not a member of this team"}

    # Obtener sesiones compartidas con el equipo
    team_sessions = TeamSession.objects.filter(team=team).select_related('session', 'session__owner')

    return [
        {
            "id": ts.id,
            "session": {
                "id": ts.session.id,
                "title": ts.session.title,
                "description": ts.session.description,
                "assistant_type": ts.session.assistant_type,
                "repo": ts.session.repo,
                "metadata": ts.session.metadata,
                "owner": {
                    "github_handle": ts.session.owner.github_handle,
                    "email": ts.session.owner.email,
                    "display_name": ts.session.owner.display_name,
                    "is_active": ts.session.owner.is_active,
                    "created_at": ts.session.owner.created_at
                },
                "is_public": ts.session.is_public,
                "created_at": ts.session.created_at
            },
            "shared_at": ts.created_at
        }
        for ts in team_sessions
    ]


@api.delete("/teams/{team_id}/sessions/{session_id}", auth=auth, response={200: SuccessOut, 403: ErrorOut, 404: ErrorOut}, tags=["Team Sessions"])
def unshare_session_from_team(request, team_id: str, session_id: str):
    """Dejar de compartir una sesión con un equipo"""
    user = get_user_from_request(request)

    team = get_object_or_404(Team, id=team_id)
    session = get_object_or_404(Session, id=session_id)

    # Verificar que el usuario es owner/admin del equipo o dueño de la sesión
    membership = TeamUser.objects.filter(team=team, user=user).first()
    is_team_admin = membership and membership.role in ['owner', 'admin']
    is_session_owner = session.owner == user

    if not (is_team_admin or is_session_owner):
        return 403, {"detail": "Only team admins or session owner can unshare"}

    # Remover compartición
    team_session = get_object_or_404(TeamSession, team=team, session=session)
    team_session.delete()

    return {
        "success": True,
        "message": "Session unshared from team"
    }


# ============================================
# HEALTH CHECK
# ============================================

@api.get("/health", tags=["Health"])
def health_check(request):
    """Health check endpoint"""
    return {"status": "ok", "version": "2.0.0"}
