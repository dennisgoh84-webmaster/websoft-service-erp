"""
Seed Central Command's own database with a default admin user.

Run:  cd central-command/backend && uv run python seed.py
"""
from app.core.database import Base, engine, SessionLocal
from app.models.admin import AdminUser
from app.models.clients import Client  # noqa: F401 — register models
from app.models.advertisements import Advertisement, AdAssignment, VideoSetting, VideoAssignment  # noqa: F401
from app.models.config_updates import ConfigUpdate, ConfigPushLog  # noqa: F401
from app.models.push_logs import PushLog  # noqa: F401
from app.services.auth import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Default admin
    if not db.query(AdminUser).filter(AdminUser.username == "admin").first():
        db.add(AdminUser(
            username="admin",
            full_name="Dennis Goh",
            hashed_password=hash_password("Admin123"),
        ))
        print("Created admin user: admin / Admin123")
    else:
        print("Admin user already exists")

    db.commit()
    db.close()
    print("Central Command seed complete.")


if __name__ == "__main__":
    seed()
