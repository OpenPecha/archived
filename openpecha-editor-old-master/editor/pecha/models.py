from editor.database import Column, Model, db


class Pecha(Model):
    __tablename__ = "pecha"

    id = Column(db.String(7), primary_key=True)
    secret_key = Column(db.String(32))
