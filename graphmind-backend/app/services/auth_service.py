from datetime import timedelta
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.schemas.user import UserCreate, Token, TokenData
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
)

settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_data: UserCreate) -> User:
        # Check if user exists
        existing = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create user
        user = User(
            email=user_data.email,
            name=user_data.name,
            github_id=user_data.github_id,
            password_hash=hashed_password,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, email: str, password: str) -> Optional[Token]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return await self.create_tokens(user)

    async def github_auth(self, code: str) -> Optional[Token]:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return None

            # Get user info from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            github_user = user_response.json()

            github_id = str(github_user["id"])
            email = github_user.get("email")
            name = github_user.get("name") or github_user.get("login")
            avatar_url = github_user.get("avatar_url")

            # Check if user exists by GitHub ID
            result = await self.db.execute(select(User).where(User.github_id == github_id))
            user = result.scalar_one_or_none()

            if user:
                # Update avatar if changed
                if avatar_url and user.avatar_url != avatar_url:
                    user.avatar_url = avatar_url
                    await self.db.commit()
            else:
                # Check if email exists
                if email:
                    result = await self.db.execute(select(User).where(User.email == email))
                    user = result.scalar_one_or_none()
                    if user:
                        user.github_id = github_id
                        if avatar_url:
                            user.avatar_url = avatar_url
                        await self.db.commit()
                    else:
                        # Create new user
                        user = User(
                            email=email or f"github_{github_id}@users.noreply.github.com",
                            name=name,
                            github_id=github_id,
                            avatar_url=avatar_url,
                            password_hash=None,  # OAuth only
                        )
                        self.db.add(user)
                        await self.db.commit()
                        await self.db.refresh(user)
                else:
                    # No email, create with GitHub ID
                    user = User(
                        email=f"github_{github_id}@users.noreply.github.com",
                        name=name,
                        github_id=github_id,
                        avatar_url=avatar_url,
                        password_hash=None,
                    )
                    self.db.add(user)
                    await self.db.commit()
                    await self.db.refresh(user)

            return await self.create_tokens(user)

    async def create_tokens(self, user: User) -> Token:
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> Optional[Token]:
        user_id = verify_token(refresh_token, "refresh")
        if not user_id:
            return None

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        return await self.create_tokens(user)

    async def get_current_user(self, token: str) -> Optional[User]:
        user_id = verify_token(token, "access")
        if not user_id:
            return None

        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()