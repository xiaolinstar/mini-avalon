import json
import logging
import sys
from datetime import UTC, datetime

from flask import g, has_app_context

from src.config.settings import settings


class TraceIdFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = "n/a"
        if has_app_context():
            record.trace_id = getattr(g, "trace_id", "n/a")
        return True

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "func": record.funcName,
            "trace_id": getattr(record, "trace_id", "n/a"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Add extra context if available
        if hasattr(record, "context"):
            log_record["context"] = record.context
            
        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        if settings.LOG_FORMAT.upper() == "JSON":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(trace_id)s] [%(name)s] [%(funcName)s] %(message)s'
            )
            
        handler.addFilter(TraceIdFilter())
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(settings.LOG_LEVEL.upper())
        
    return logger

def setup_logging():
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())
    
    # Add handler to root if not present
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if settings.LOG_FORMAT.upper() == "JSON":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(trace_id)s] [%(name)s] [%(funcName)s] %(message)s'
            )
        handler.addFilter(TraceIdFilter())
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
