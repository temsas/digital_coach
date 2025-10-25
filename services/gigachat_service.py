import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GigaChatService:
    def __init__(self):
        try:
            credentials = os.getenv("GIGACHAT_CREDENTIALS")

            if not credentials:
                raise ValueError("GIGACHAT_CREDENTIALS не установлен")

            from gigachat import GigaChat
            self.client = GigaChat(
                credentials=credentials,
                verify_ssl_certs=False,
                timeout=120
            )
            logger.info("✅ GigaChat initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize GigaChat: {e}")
            raise