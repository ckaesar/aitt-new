import os
import sys
import pymysql
from sqlalchemy.engine.url import make_url

# 将 backend 根目录加入模块路径，便于导入 app 包
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(CUR_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.config import settings
from app.utils.security import get_password_hash


def main(new_password: str = "password"):
    url = make_url(settings.DATABASE_URL)
    conn = pymysql.connect(
        host=url.host or "localhost",
        port=int(url.port or 3306),
        user=url.username,
        password=url.password or "",
        database=url.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        hashed = get_password_hash(new_password)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE aitt_users SET password_hash=%s WHERE username=%s",
                (hashed, "admin"),
            )
        conn.commit()
        print("admin 密码已重置为:", new_password)
    finally:
        conn.close()


if __name__ == "__main__":
    main()