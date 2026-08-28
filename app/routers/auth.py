from fastapi import APIRouter, Depends, HTTPException, status

from app import store
from app.auth import get_current_user, hash_password, issue_token, verify_password
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    email = payload.email.lower()

    if email in store.users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = {
        "name": payload.name,
        "email": email,
        "password": hash_password(payload.password),
        "role": payload.role,
    }
    store.users[email] = user
    return UserResponse(**user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = store.users.get(payload.email.lower())

    if user is None or not verify_password(payload.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=issue_token(user["email"]),
        role=user["role"],
        name=user["name"],
    )


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)):
    return UserResponse(**user)
