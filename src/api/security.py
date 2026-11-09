"""Auth en el borde: dependencias de rol y construcción de contextos de actor/auditoría."""

from __future__ import annotations

from src.api.commons import RequestContext
from src.core.auth import ADMIN_ONLY, ANY_USER, RequireRole, TokenPayload
from src.services.dto.commons import ActorContext, MutationAuditContext

require_user = RequireRole(ANY_USER)
require_admin = RequireRole(ADMIN_ONLY)


def actor(user: TokenPayload) -> ActorContext:
    return ActorContext(user_id=user.sub, role=user.role.value, persona_id=user.persona_id)


def mutation_audit(user: TokenPayload, ctx: RequestContext) -> MutationAuditContext:
    return MutationAuditContext(
        user_id=user.sub,
        role=user.role.value,
        persona_id=user.persona_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
