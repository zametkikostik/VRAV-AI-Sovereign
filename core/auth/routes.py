from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.auth.store import auth_store
from core.auth.middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class CreateUserBody(BaseModel):
    username: str
    role: str = "user"

class CreateKeyBody(BaseModel):
    user_id: str
    name: str = "default"

@router.get("/me")
async def me(user=Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}

@router.get("/users")
async def list_users(user=Depends(get_current_user)):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "admin only")
    return {"users": auth_store.list_users()}

@router.post("/users")
async def create_user(body: CreateUserBody, user=Depends(get_current_user)):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "admin only")
    uid = auth_store.create_user(body.username, body.role)
    return {"user_id": uid, "username": body.username}

@router.post("/keys")
async def create_key(body: CreateKeyBody, user=Depends(get_current_user)):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "admin only")
    raw = auth_store.create_key(body.user_id, body.name)
    return {"api_key": raw, "note": "store this key; it will not be shown again"}

@router.get("/keys")
async def list_keys(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "auth required")
    if user.get("role") == "admin":
        return {"keys": auth_store.list_keys()}
    return {"keys": auth_store.list_keys(user["user_id"])}

@router.post("/keys/{key_id}/revoke")
async def revoke_key(key_id: str, user=Depends(get_current_user)):
    if not user or user.get("role") != "admin":
        raise HTTPException(403, "admin only")
    auth_store.revoke_key(key_id)
    return {"revoked": key_id}
