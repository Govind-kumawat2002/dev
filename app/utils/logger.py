"""
Structured Logging Module
Provides consistent logging across the application
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import structlog
from structlog.typing import EventDict

from app.config import settings


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """Add ISO timestamp to log events"""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def add_service_info(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict
) -> EventDict:
    """Add service metadata to log events"""
    event_dict["service"] = "dev-studio-face-api"
    event_dict["version"] = "1.0.0"
    return event_dict


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure structured logging for the application
    
    Args:
        log_level: Override log level from settings
    """
    level = log_level or settings.log_level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Ensure log directory exists
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_timestamp,
        add_service_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=shared_processors,
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with JSON output
    file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(numeric_level)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class RequestLogger:
    """Context manager for request-level logging"""
    
    def __init__(self, request_id: str, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.logger = get_logger("request")
        self._token = None
    
    def __enter__(self):
        self._token = structlog.contextvars.bind_contextvars(
            request_id=self.request_id,
            user_id=self.user_id
        )
        self.logger.info("request_started")
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(
                "request_failed",
                error_type=exc_type.__name__,
                error_message=str(exc_val)
            )
        else:
            self.logger.info("request_completed")
        structlog.contextvars.clear_contextvars()
        return False


# Initialize logging on module import
setup_logging()
logger = get_logger(__name__)
