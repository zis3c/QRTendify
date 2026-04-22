from background_task import background
from .models import Session
import logging

logger = logging.getLogger(__name__)


@background
def open_session_task(session_id):
    """
    This task runs in the background to open a session.
    """
    try:
        session = Session.objects.get(pk=session_id)
        if session.status == "Scheduled":
            session.status = "Open"
            session.save()
            logger.info("Successfully opened session: %s", session.title)
    except Session.DoesNotExist:
        logger.warning("Session %s not found. Could not open.", session_id)
