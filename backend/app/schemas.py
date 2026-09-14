from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AgentOut(BaseModel):
    id: str
    email: str
    is_owner: bool
    tenant_id: str
    tenant_name: str
    tenant_plan: str


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SiteOut(BaseModel):
    id: str
    name: str
    key: str
