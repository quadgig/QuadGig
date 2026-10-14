from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.config import settings
from app.listings import router as listings_router
from app.orders import router as orders_router
from app.payments import router as payments_router
from app.reviews import router as reviews_router

app = FastAPI(title="Quadgig API")
app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(reviews_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.frontend_url.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}