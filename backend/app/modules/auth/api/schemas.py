from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshBodyRequest(BaseModel):
    """Optional body for one-time migration from legacy localStorage refresh tokens."""

    refresh_token: str | None = Field(default=None, min_length=1)


class LogoutBodyRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
