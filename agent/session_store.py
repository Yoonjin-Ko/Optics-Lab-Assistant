"""Wave 12 — 프로세스 밖(SQLite 파일)에 두는 세션 저장소.

서버가 재시작돼도(새 프로세스, 새 인스턴스) 같은 session.db 파일을 다시 열므로
대화 이력이 유지된다. in-memory dict였다면 재시작 즉시 소실됐을 상태다.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "session.db"


class SqliteSessionStore:
    def __init__(self, db_path: Path = DB_PATH):
        """SQLite 연결과 대화 메시지 테이블을 준비한다.

        Args:
            db_path: SQLite 파일 경로.
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            " thread_id TEXT, role TEXT, content TEXT, created TEXT)"
        )
        self.conn.commit()

    def load(self, thread_id: str) -> list[dict]:
        """대화 ID로 메시지를 저장 순서대로 읽어 모델 입력 형식으로 변환한다.

        Args:
            thread_id: 대화를 구분하는 식별자.

        Returns:
            role/content 사전의 목록.
        """
        rows = self.conn.execute(
            "SELECT role, content FROM messages WHERE thread_id=? ORDER BY rowid",
            (thread_id,),
        ).fetchall()
        return [{"role": r, "content": c} for r, c in rows]

    def append(self, thread_id: str, role: str, content: str) -> None:
        """대화 ID·역할·본문·현재 시각을 SQLite에 저장하고 커밋한다.

        Args:
            thread_id: 대화를 구분하는 식별자.
            role: 메시지 역할(user/assistant 등).
            content: 저장할 메시지 또는 응답 문자열.
        """
        self.conn.execute(
            "INSERT INTO messages VALUES (?,?,?,?)",
            (thread_id, role, content, datetime.now().isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        """SQLite 데이터베이스 연결을 닫는다.
        """
        self.conn.close()
