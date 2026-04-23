from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from srs_engine.core.auth.deps import require_user
from srs_engine.core.config import get_settings
from srs_engine.core.db.mongo import get_db
from srs_engine.core.services.tracking_service import TrackingService

router = APIRouter()
templates = Jinja2Templates(directory="srs_engine/templates")

async def require_admin(request: Request, user: dict = Depends(require_user), db = Depends(get_db)):
    """Dependency to ensure the logged-in user is an admin via the dedicated admins collection."""
    from srs_engine.core.db.user_repo import UserRepo
    repo = UserRepo(db)
    if not await repo.is_admin(user.get("email")):
        # We raise 404 to hide the existence of the admin page
        raise HTTPException(status_code=404, detail="Page not found")
    return user

@router.get("/admin/pulse", response_class=HTMLResponse)
async def admin_pulse_dashboard(
    request: Request,
    admin_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Renders the secure Admin Pulse dashboard."""
    tracker = TrackingService(db)
    settings = get_settings()
    stats = await tracker.get_admin_stats(admin_email=settings.admin_email)
    
    return templates.TemplateResponse(
        "pages/admin_pulse.html",
        {
            "request": request,
            "user": admin_user,
            "stats": stats,
        }
    )

@router.post("/admin/user/{user_id}/action")
async def take_admin_action(
    user_id: str,
    request: Request,
    admin_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """
    General endpoint for admin actions (revoke, promote, message).
    Uses AI to reframe the reason into a polite email.
    """
    from srs_engine.core.db.user_repo import UserRepo
    from srs_engine.core.services.diplomat_service import DiplomatService
    from srs_engine.core.services.email_service import send_admin_action_email
    
    data = await request.json()
    action = data.get("action") # 'revoke', 'restore', 'promote', 'warn'
    raw_reason = data.get("reason", "Administrative update")
    
    repo = UserRepo(db)
    target_user = await repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    diplomat = DiplomatService()
    email_msg = await diplomat.reframe_comment(action, raw_reason)
    
    settings = get_settings()
    
    if action == "revoke":
        await repo.set_active_status(user_id, False)
        subject = "Account Status Update"
    elif action == "restore":
        await repo.set_active_status(user_id, True)
        subject = "Account Restored"
    elif action == "promote":
        new_srs_limit = int(data.get("quota", 5))
        new_chat_limit = int(data.get("chat_quota", 50))
        new_diag_limit = int(data.get("diag_quota", 10))
        new_upgrade_limit = int(data.get("upgrade_quota", 10))
        
        await repo.update_all_quotas(
            user_id, 
            srs_limit=new_srs_limit, 
            chat_limit=new_chat_limit,
            diag_limit=new_diag_limit,
            upgrade_limit=new_upgrade_limit
        )
        subject = "Your Account has been Promoted! 🌟"
    elif action == "message":
        subject = "Message from SpecForge Admin"
    else:
        subject = "Important Update Regarding Your Account"

    # Send the AI-reframed email
    try:
        await send_admin_action_email(
            settings=settings,
            to_email=target_user["email"],
            subject=subject,
            message=email_msg
        )
    except Exception as e:
        # We don't fail the whole action if email fails, but we log it
        print(f"Failed to send admin action email: {e}")

    return {"status": "success", "message": f"Action {action} taken and user notified."}

@router.get("/api/monitor/admin/all-stats")
async def get_all_stats_api(
    admin_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """JSON endpoint for raw admin statistics."""
    tracker = TrackingService(db)
    return await tracker.get_admin_stats()

@router.get("/api/monitor/my-progress")
async def get_my_progress(
    user: dict = Depends(require_user),
    db = Depends(get_db)
):
    """Allows a user to see their own workflow progress."""
    tracker = TrackingService(db)
    return await tracker.get_user_progress(str(user["_id"]))
