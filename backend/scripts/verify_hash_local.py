from passlib.context import CryptContext


def main():
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hash_str = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5W"
    candidates = [
        "password", "admin", "admin123", "123456", "12345678",
        "aitt123", "changeme", "root", "qwerty", "test123",
    ]
    matched = []
    for p in candidates:
        try:
            if ctx.verify(p, hash_str):
                matched.append(p)
        except Exception as e:
            print(f"error verifying '{p}': {e}")
    print("matched:", matched)


if __name__ == "__main__":
    main()