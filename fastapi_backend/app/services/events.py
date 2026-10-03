import json

from celery import Celery
from redis import Redis

from app.config import get_settings


def publish_user_event(user_id: int, payload: dict) -> None:
    try:
        Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        ).publish(
            f"notifications:{user_id}", json.dumps(payload, default=str)
        )
    except Exception:
        # A notification is already persisted in MySQL; Redis is only the live delivery path.
        return


def queue_email(template_name: str, recipient: str, context: dict) -> None:
    try:
        celery = Celery(broker=get_settings().celery_broker_url)
        celery.conf.update(
            broker_connection_timeout=0.5,
            broker_connection_retry_on_startup=False,
            task_publish_retry=False,
        )
        celery.send_task(
            "core.tasks.send_transactional_email",
            args=[template_name, recipient, context],
            retry=False,
        )
    except Exception:
        # The order transaction must not fail because the local worker is temporarily unavailable.
        return
