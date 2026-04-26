from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.stat import UserStat
from app.models.plan import UserPlan
from app.schemas.user import UserCreate, UserLogin, TokenData
from app.core.security import get_password_hash, verify_password, create_access_token
import logging

logger = logging.getLogger(__name__)

async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        timezone=user_data.timezone
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    # Initialize basic stats for user
    initial_stat = UserStat(user_id=new_user.id)
    db.add(initial_stat)
    
    await db.commit()
    await db.refresh(new_user)
    logger.info(f"Registered user {user_data.email}")
    return new_user

async def login_user(db: AsyncSession, login_data: UserLogin) -> TokenData:
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": str(user.id)})

    # Check for active plan
    active_result = await db.execute(
        select(UserPlan).where(UserPlan.user_id == user.id, UserPlan.active == True)
    )
    active_plan = active_result.scalars().first()

    return TokenData(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        has_active_plan=active_plan is not None,
        active_plan_id=active_plan.plan_id if active_plan else None,
    )
