import os


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "poomsae_saas")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Seguridad cookies (útil más adelante)
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "storage", "uploads")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB (ajusta)
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}

class Development(Config):
    DEBUG = True


class Production(Config):
    DEBUG = False