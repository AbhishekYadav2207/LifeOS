from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenData
from app.schemas.responses import BaseResponse
from app.services import user_svc

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

@router.post("/register", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user and returns their basic info."""
    user = await user_svc.register_user(db, user_data)
    return BaseResponse(
        success=True,
        data=UserResponse.model_validate(user),
        message="User registered successfully"
    )

@router.post("/login", response_model=BaseResponse[TokenData])
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates a user and returns a JWT access token."""
    token = await user_svc.login_user(db, login_data)
    return BaseResponse(
        success=True,
        data=token,
        message="Login successful"
    )
