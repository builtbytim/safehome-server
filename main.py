from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.main import router
from libs.huey_tasks.config import huey
from libs.config.settings import get_settings
from libs.huey_tasks.tasks import task_send_mail, task_test_huey,  task_initiate_kyc_verification, task_post_user_registration

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
    expose_headers=["X-ACTION", "X-AUTH-CODE", "WWW-Authenticate"],



)


# Root test route


app.include_router(router, prefix="/api/v1")
