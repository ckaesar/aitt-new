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
from app.utils.security import verify_password


def main():
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, password_hash FROM aitt_users WHERE username=%s",
                ("admin",),
            )
            row = cur.fetchone()
        if not row:
            print("admin 用户不存在")
            return
        print("username:", row["username"]) 
        print("hash_prefix:", row["password_hash"][:20])
        print("verify 'password':", verify_password("password", row["password_hash"]))
        print("verify 'admin123':", verify_password("admin123", row["password_hash"]))
    finally:
        conn.close()


if __name__ == "__main__":
    main()