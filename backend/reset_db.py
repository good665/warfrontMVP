"""개발용: 모든 테이블을 삭제하고 현재 모델 구조로 다시 만든다. (데이터 전부 삭제됨)

사용법 (backend 폴더에서):  python reset_db.py
"""
import sys

from app import models  # noqa: F401  (모델을 메타데이터에 등록)
from app.config import settings
from app.database import Base, engine

if settings.environment == "prod":
    sys.exit("ENVIRONMENT=prod 에서는 실행할 수 없습니다.")

print("DB:", settings.database_url)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("완료: 테이블을 새 구조로 다시 만들었습니다.")
