import enum

from sqlalchemy import Enum

from editor.database import Column, PkModel, db


class RoleType(enum.Enum):
    admin = "Admin"
    owner = "Owner"
    contributor = "Contributor"


class User(PkModel):
    __tablename__ = "users"

    username = Column(db.String(255))
    pecha_id = Column(db.String(7))
    role = Column(Enum(RoleType))
