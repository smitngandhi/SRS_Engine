import json
import asyncio
from srs_engine.core.logging import get_logger
from srs_engine.core.services.email_service import (
    send_srs_complete_email,
    send_welcome_email,
    send_verification_email,
    send_login_notification,
    send_admin_security_alert
)
from srs_engine.core.config import get_settings

logger = get_logger(__name__)

async def run_notification_worker(app):
    """
    Background task for the Render web server to send emails 
    that the Hugging Face worker cannot send due to port blocks.
    """
    logger.info("NotificationWorker | Starting")
    settings = get_settings()
    
    while True:
        try:
            if not hasattr(app.state, "redis") or app.state.redis is None:
                await asyncio.sleep(5)
                continue

            # Blpop (Blocking left pop) waits for a message
            result = await app.state.redis.client.blpop("notification_queue", timeout=30)
            
            if result:
                payload = json.loads(result[1])
                p_type = payload.get("type")
                email = payload.get("user_email")
                
                logger.info(f"NotificationWorker | Processing {p_type} for {email}")
                
                if p_type == "srs_complete":
                    await send_srs_complete_email(
                        settings=settings,
                        to_email=email,
                        project_name=payload["project_name"]
                    )
                
                elif p_type == "welcome_email":
                    await send_welcome_email(
                        settings=settings,
                        to_email=email,
                        display_name=payload.get("display_name", "User")
                    )

                elif p_type == "verification_email":
                    await send_verification_email(
                        settings=settings,
                        to_email=email,
                        otp=payload.get("otp")
                    )

                elif p_type == "admin_login":
                    await send_login_notification(
                        settings=settings,
                        username=payload.get("username", "Unknown"),
                        user_email=email,
                        ip_address=payload.get("ip_address", "Unknown")
                    )

                elif p_type == "security_alert":
                    await send_admin_security_alert(
                        settings=settings,
                        ip_address=payload.get("ip_address", "Unknown"),
                        user_agent=payload.get("user_agent", "Unknown")
                    )
                
                logger.info(f"NotificationWorker | {p_type} sent successfully")
                
        except Exception as e:
            logger.error(f"NotificationWorker | Error: {e}")
            await asyncio.sleep(5)
