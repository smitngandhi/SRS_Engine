import json
import asyncio
from srs_engine.core.logging import get_logger
from srs_engine.core.services.email_service import send_srs_complete_email
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
            # The [0] is the key, [1] is the value
            result = await app.state.redis.blpop("notification_queue", timeout=30)
            
            if result:
                payload = json.loads(result[1])
                logger.info(f"NotificationWorker | Processing {payload['type']} for {payload['user_email']}")
                
                if payload["type"] == "srs_complete":
                    await send_srs_complete_email(
                        settings=settings,
                        to_email=payload["user_email"],
                        project_name=payload["project_name"]
                    )
                    logger.info(f"NotificationWorker | Email sent successfully")
                
        except Exception as e:
            logger.error(f"NotificationWorker | Error: {e}")
            await asyncio.sleep(5)
