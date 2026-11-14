from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.users.schemas import UserOut, validate_locale

PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]


class RegisterIn(BaseModel):
    email: EmailStr
    password: PasswordStr
    full_name: str = Field(min_length=1, max_length=120)
    locale: str = "en"
    country_code: str = Field(min_length=2, max_length=2)
    workshop_name: str = Field(min_length=1, max_length=120)
    accept_terms: bool

    _check_locale = field_validator("locale")(validate_locale)

    @field_validator("country_code")
    @classmethod
    def upper_country(cls, v: str) -> str:
        return v.upper()


class RegisterOut(BaseModel):
    user: UserOut
    email_verification_required: bool = True


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access_token expires


class RefreshIn(BaseModel):
    refresh_token: str


class EmailIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str


class ResetPasswordIn(BaseModel):
    token: str
    new_password: PasswordStr


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: PasswordStr
