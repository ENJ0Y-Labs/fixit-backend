from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=12, max_length=128)
    role: str
    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        if value not in {"customer", "provider"}:
            raise ValueError("Public registration is limited to customer and provider accounts.")
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class EmailRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=128)

class VerificationConfirmRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
