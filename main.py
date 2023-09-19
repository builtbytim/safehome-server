from fastapi import FastAPI
from lib.config.settings import get_settings
from fastapi.middleware.cors import CORSMiddleware
from routers.main import router
from lib.huey_tasks.config import huey

settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    servers=[

        {
            "url": "http://localhost:7000",
            "description": "Development server"
        },

    ]
)

# CSRF config


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
    expose_headers=["X-ACTION", "WWW-Authenticate"],



)


# Root test route


app.include_router(router, prefix="/api/v1")
