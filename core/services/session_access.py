from __future__ import annotations

from django.db.models import Q, QuerySet

from ..models import Session, User


def active_orgs_for_user(user: User):
    return user.organizations.filter(organizationmember__status="active")


def sessions_user_can_access(user: User) -> QuerySet[Session]:
    user_orgs = active_orgs_for_user(user)
    return (
        Session.objects.filter(
            Q(organization__in=user_orgs) | Q(creator=user, organization=None)
        )
        .select_related("organization")
        .distinct()
    )


def user_can_access_session(user: User, session: Session) -> bool:
    if not user.is_authenticated:
        return False

    if session.organization_id is None:
        return session.creator_id == user.id

    return user.organizations.filter(
        pk=session.organization_id, organizationmember__status="active"
    ).exists()
