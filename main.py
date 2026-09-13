from fastapi import FastAPI
from app.controllers.whatsapp_controller import router as whatsapp_router
from app.controllers.leetcode_controller import router as leetcode_router
from app.services.scheduler_service import start_scheduler
from app.services.startup_runner import run_once_updates
from app.core.config import settings
import uvicorn

app = FastAPI()
app.include_router(whatsapp_router)
app.include_router(leetcode_router)

@app.on_event("startup")
async def startup():
    start_scheduler()
    await run_once_updates()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
