#!/usr/bin/env python
"""
Application Entry Point
Run with: python run.py
"""

import uvicorn
from app.config import settings


def main():
    """Start the application server"""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
