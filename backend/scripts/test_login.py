import httpx


def main():
    url = "http://localhost:8000/api/v1/auth/login"
    # 该接口使用 OAuth2PasswordRequestForm，需提交表单数据
    payload = {"username": "admin", "password": "password"}
    r = httpx.post(url, data=payload, timeout=10)
    print("status:", r.status_code)
    print("body:", r.text)


if __name__ == "__main__":
    main()