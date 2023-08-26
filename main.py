from fastapi import FastAPI
from config.settings import Settings
from fastapi.middleware.cors import CORSMiddleware

settings = Settings()


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

)


# Root test route
@app.get("/", status_code=200)
async def root():
    return {"message": "Hello World"}
