from sqlmodel import Field, SQLModel
from typing import Optional


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    last_name: str
    email: str
    number_phone: int
    password: str
    
    
