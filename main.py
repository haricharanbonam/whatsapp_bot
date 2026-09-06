from fastapi import FastAPI
from app.controllers.whatsapp_controller import router as whatsapp_router
from app.services.scheduler_service import start_scheduler
from app.core.config import settings
import uvicorn

app = FastAPI()
app.include_router(whatsapp_router)

@app.on_event("startup")
def startup():
    start_scheduler()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
