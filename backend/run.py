"""
Development server startup script.
Run with: python run.py
"""
import uvicorn
from config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"Starting {settings.app_name}")
    print(f"API will be available at: http://localhost:{settings.port}")
    print(f"API docs at: http://localhost:{settings.port}/docs")
    print(f"Auto-reload enabled (development mode)")
    print("\n" + "="*50 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
        log_level="debug"
    )
