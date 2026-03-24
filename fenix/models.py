from django.db import models
from django.db.models import Q

import uuid


class User(models.Model):
    """Usuarios del sistema"""
    github_handle = models.CharField(max_length=255, primary_key=True)
    email = models.EmailField(null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fenix_users'
        ordering = ['-created_at']

    def __str__(self):
        return f"@{self.github_handle}"



class Team(models.Model):
    """Equipos de usuarios"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fenix_teams'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Session(models.Model):
    """Sesiones de asistentes de IA"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500, db_index=True)
    description = models.TextField(null=True, blank=True)
    session_data = models.TextField()
    assistant_type = models.CharField(max_length=50, default='claude-code')
    repo = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    is_public = models.BooleanField(default=False)

    # S3 Report URL (always .html files)
    report_url = models.URLField(max_length=1000, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fenix_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['assistant_type']),
        ]

    def __str__(self):
        return f"{self.title} by @{self.owner.github_handle}"


class SessionVersion(models.Model):
    """Snapshot del estado de una sesión antes de cada update."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    session_data = models.TextField()
    repo = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField()
    report_url = models.URLField(max_length=1000, null=True, blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fenix_session_versions'
        ordering = ['-version_number']
        unique_together = [['session', 'version_number']]
        indexes = [
            models.Index(fields=['session', '-version_number']),
        ]

    def __str__(self):
        return f"{self.session.title} v{self.version_number}"


class TeamUser(models.Model):
    """Relación entre equipos y usuarios"""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fenix_team_users'
        unique_together = [['team', 'user']]
        ordering = ['role', 'created_at']
        indexes = [
            models.Index(fields=['team']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"@{self.user.github_handle} in {self.team.name} ({self.role})"


class TeamInvitation(models.Model):
    """Invitaciones a equipos"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    role = models.CharField(max_length=20, choices=TeamUser.ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fenix_team_invitations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invited_user', 'status']),
            models.Index(fields=['team', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'invited_user'],
                condition=Q(status='pending'),
                name='unique_pending_invitation',
            ),
        ]

    def __str__(self):
        return f"Invitation for @{self.invited_user.github_handle} to {self.team.name} ({self.status})"


class TeamSession(models.Model):
    """Relación entre equipos y sesiones compartidas"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_sessions')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='shared_with_teams')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fenix_team_sessions'
        unique_together = [['team', 'session']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at']),
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"{self.session.title} shared with {self.team.name}"
