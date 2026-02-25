from ninja import Schema
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# ============================================
# USER SCHEMAS
# ============================================

class UserOut(Schema):
    github_handle: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool
    created_at: datetime


# ============================================
# AUTH SCHEMAS
# ============================================

class ValidateOrCreateUserIn(Schema):
    email: Optional[str] = None
    display_name: Optional[str] = None


class ValidateOrCreateUserOut(Schema):
    github_handle: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    existed: bool

# ============================================
# TEAM SCHEMAS
# ============================================

class TeamOut(Schema):
    id: UUID
    name: str
    description: Optional[str] = None
    owner: UserOut
    created_at: datetime


class TeamCreateIn(Schema):
    name: str
    description: Optional[str] = None


class TeamMemberOut(Schema):
    id: UUID
    user: UserOut
    role: str
    created_at: datetime


class TeamDetailOut(Schema):
    id: UUID
    name: str
    description: Optional[str] = None
    owner: UserOut
    members: List[TeamMemberOut]
    created_at: datetime


class TeamAddMemberIn(Schema):
    github_handle: str
    role: str = 'member'


# ============================================
# SESSION SCHEMAS
# ============================================

class SessionOut(Schema):
    id: UUID
    title: str
    description: Optional[str] = None
    assistant_type: str
    repo: Optional[str] = None
    metadata: dict
    owner: UserOut
    is_public: bool
    report_url: Optional[str] = None
    created_at: datetime


class SessionCreateIn(Schema):
    title: str
    description: Optional[str] = None
    session_data: str
    assistant_type: str = 'claude-code'
    repo: Optional[str] = None
    metadata: Optional[dict] = None
    is_public: bool = False


class SessionDetailOut(Schema):
    id: UUID
    title: str
    description: Optional[str] = None
    session_data: str
    assistant_type: str
    repo: Optional[str] = None
    metadata: dict
    owner: UserOut
    is_public: bool
    report_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SessionUpdateIn(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    session_data: Optional[str] = None
    repo: Optional[str] = None
    metadata: Optional[dict] = None
    is_public: Optional[bool] = None


# ============================================
# TEAM SESSION SCHEMAS (sharing)
# ============================================

class ShareSessionWithTeamIn(Schema):
    session_id: UUID


class ShareSessionWithTeamOut(Schema):
    success: bool
    team_id: UUID
    session_id: UUID
    message: str


class TeamSessionOut(Schema):
    id: UUID
    session: SessionOut
    shared_at: datetime


# ============================================
# ERROR SCHEMAS
# ============================================

class ErrorOut(Schema):
    detail: str


class SuccessOut(Schema):
    success: bool
    message: str
