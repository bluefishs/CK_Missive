"""
統一的專案管理命令列工具 (CLI)
使用 Typer 建立，提供清晰、易用的指令來執行日常維護任務。

用法:
- 建立管理員: python manage.py create-admin ...
- 檢查資料庫: python manage.py check-db
"""
import asyncio
import typer
from typing_extensions import Annotated
from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.extended.models import User, Base
from app.core.auth_service import get_password_hash

app = typer.Typer()

@app.command()
def create_tables():
    """根據 models.py 中的定義，在資料庫中建立所有資料表。"""
    typer.echo("正在建立資料表...")
    try:
        Base.metadata.create_all(bind=engine.sync_engine)
        typer.secho("資料表成功建立！", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"建立資料表時發生錯誤: {e}", fg=typer.colors.RED)

@app.command()
def create_admin(
    email: Annotated[str, typer.Option(prompt=True)],
    username: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[str, typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)],
    full_name: Annotated[str, typer.Option(prompt=True)] = "Admin User"
):
    """建立一位新的管理員使用者。"""
    typer.echo(f"正在為 {email} 建立管理員帳號...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            typer.secho(f"錯誤：Email '{email}' 已被註冊。", fg=typer.colors.RED)
            return

        hashed_password = get_password_hash(password)
        admin_user = User(
            email=email,
            username=username,
            full_name=full_name,
            password_hash=hashed_password,
            is_admin=True,
            is_superuser=True,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        typer.secho(f"管理員 '{username}' ({email}) 成功建立！", fg=typer.colors.GREEN)
    except Exception as e:
        db.rollback()
        typer.secho(f"建立管理員時發生錯誤: {e}", fg=typer.colors.RED)
    finally:
        db.close()

@app.command()
def check_db():
    """檢查資料庫連線狀態。"""
    typer.echo("正在檢查資料庫連線...")
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            typer.secho("資料庫連線成功！", fg=typer.colors.GREEN)
        else:
            typer.secho("資料庫連線異常，但未拋出錯誤。", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"資料庫連線失敗: {e}", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
