import httpx


BASE_URL = "http://localhost:8000/api/v1"


def login_get_token(username: str, password: str) -> str:
    r = httpx.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["data"]["access_token"]


def get_with_token(path: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    r = httpx.get(f"{BASE_URL}{path}", headers=headers, timeout=10)
    print(f"GET {path} -> status {r.status_code}")
    print(r.text)


def main():
    token = login_get_token("admin", "password")
    # 访问数据源列表（受保护，需 analyst/admin 权限；补齐尾斜杠避免 307 重定向）
    get_with_token("/data-sources/?limit=10", token)
    # 访问当前用户信息
    get_with_token("/auth/me", token)


if __name__ == "__main__":
    main()