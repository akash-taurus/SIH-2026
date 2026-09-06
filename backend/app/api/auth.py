from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "citizen"

@router.post("/auth/login")
async def login(credentials: LoginRequest):
    return {
        "access_token": "ner-lews-demo-jwt-token",
        "token_type": "bearer",
        "user": {
            "username": credentials.username,
            "role": "official" if "admin" in credentials.username else "citizen"
        }
    }

@router.post("/auth/register")
async def register(payload: RegisterRequest):
    return {
        "success": True,
        "user": {
            "username": payload.username,
            "email": payload.email,
            "role": payload.role
        }
    }

@router.get("/auth/me")
async def get_me():
    return {
        "username": "command_officer_1",
        "role": "official",
        "jurisdiction": "Meghalaya Disaster Management Authority"
    }
