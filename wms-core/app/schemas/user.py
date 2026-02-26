from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    user_id: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
