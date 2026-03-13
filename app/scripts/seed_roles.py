import uuid
from datetime import datetime

from app.db.database import SessionLocal
from app.models.role import Role


def seed_roles():
    session = SessionLocal()

    roles = [
        "director",
        "manager",
        "accountant"
    ]

    for role_name in roles:
        exists = session.query(Role).filter_by(name=role_name).first()

        if not exists:
            role = Role(
                id=uuid.uuid4(),
                name=role_name,
                created_at=datetime.utcnow()
            )

            session.add(role)

    session.commit()
    session.close()

    print("Roles seeded")


if __name__ == "__main__":
    seed_roles()