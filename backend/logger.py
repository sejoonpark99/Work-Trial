import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
import aiofiles

class EventLogger:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and os.getenv("LOGS_ENABLED", "false").lower() == "true"
        self.data_root = os.getenv("DATA_ROOT", "./data")
        self.log_file = os.path.join(self.data_root, "logs", "dev.log")
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Setup file logger
        self.file_logger = logging.getLogger("event_logger")
        self.file_logger.setLevel(logging.INFO)
        
        if not self.file_logger.handlers:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            self.file_logger.addHandler(handler)
    
    async def log_event(self, event_type: str, data: Dict[str, Any] = None):
        if not self.enabled:
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data or {}
        }
        
        # Log to file
        self.file_logger.info(json.dumps(event))
        
        # Could also store in memory for dashboard
        return event

# Global logger instance
event_logger = EventLogger()