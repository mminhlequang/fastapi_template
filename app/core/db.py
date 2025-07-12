from sqlmodel import Session, create_engine, select
from pathlib import Path
from sqlalchemy import text

from app.cruds import users
from app.core.config import settings
from app.models import User, SubscriptionPlan
from app.schemas.user import UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = users.create_user(session=session, user_create=user_in)

        # chạy sql từ file để tạo dữ liệu mẫu nếu chưa có dữ liệu

    # Seed base data from SQL file if necessary
    # Only run if no subscription plans exist to keep operation idempotent
    # plan_exists = session.exec(select(SubscriptionPlan)).first()
    # if not plan_exists:
    #     sql_file_path = Path(__file__).resolve().parents[2] / "sqls" / "base_data.sql"

    #     # Ensure the file exists before attempting execution
    #     if sql_file_path.exists():
    #         with open(sql_file_path, "r", encoding="utf-8") as file:
    #             sql_script = file.read()

    #         # Execute each statement individually to avoid driver limitations on multi-statements
    #         with engine.begin() as conn:
    #             for statement in sql_script.split(";"):
    #                 stmt = statement.strip()
    #                 if stmt:
    #                     conn.execute(text(stmt))

    #         # Refresh session to reflect newly inserted data
    #         session.commit()
    #     else:
    #         # Log or print warning if the file is missing (could integrate with logging framework)
    #         print(f"Warning: Base data SQL file not found at {sql_file_path}.")
