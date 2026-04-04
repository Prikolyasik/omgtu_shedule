"""
SQLite менеджер для хранения изменений расписания.
"""

import sqlite3
import json
import os
from datetime import datetime


class DatabaseManager:
    """Управление базой данных SQLite."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schedule.db')
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Создать таблицы если их нет."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                teacher TEXT NOT NULL,
                teacher_id INTEGER NOT NULL,
                subgroup TEXT DEFAULT '',
                original_date TEXT NOT NULL,
                original_time TEXT NOT NULL,
                subject TEXT DEFAULT '',
                new_date TEXT NOT NULL,
                new_time TEXT NOT NULL,
                auditory TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS substitutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                subgroup TEXT DEFAULT '',
                original_date TEXT NOT NULL,
                original_time TEXT NOT NULL,
                original_discipline TEXT DEFAULT '',
                original_teacher TEXT DEFAULT '',
                new_date TEXT NOT NULL,
                new_time TEXT NOT NULL,
                new_discipline TEXT DEFAULT '',
                new_teacher TEXT NOT NULL,
                new_teacher_id INTEGER NOT NULL,
                new_auditory TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher TEXT NOT NULL,
                teacher_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                auditory TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                group_id INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS retakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subtype TEXT NOT NULL DEFAULT 'normal',
                teachers TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                auditory TEXT DEFAULT '',
                discipline TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                group_id INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS cancellations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                subgroup TEXT DEFAULT '',
                original_date TEXT NOT NULL,
                original_time TEXT NOT NULL,
                discipline TEXT DEFAULT '',
                teacher TEXT DEFAULT '',
                auditory TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_transfers_group ON transfers(group_id);
            CREATE INDEX IF NOT EXISTS idx_transfers_date ON transfers(new_date);
            CREATE INDEX IF NOT EXISTS idx_substitutions_group ON substitutions(group_id);
            CREATE INDEX IF NOT EXISTS idx_consultations_teacher ON consultations(teacher_id);
            CREATE INDEX IF NOT EXISTS idx_consultations_date ON consultations(date);
            CREATE INDEX IF NOT EXISTS idx_retakes_date ON retakes(date);
        """)

        conn.commit()
        conn.close()

    def migrate_from_json(self, json_path=None):
        """Мигрировать данные из JSON файла в БД."""
        if json_path is None:
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schedule_changes.json')
        
        if not os.path.exists(json_path):
            return False

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conn = self._get_conn()
        cursor = conn.cursor()

        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM transfers")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return False  # Уже есть данные, не мигрируем

        # Мигрируем переносы
        for item in data.get('transfers', []):
            cursor.execute("""
                INSERT INTO transfers (group_name, group_id, teacher, teacher_id, subgroup,
                    original_date, original_time, subject, new_date, new_time, auditory, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get('group', ''), item.get('group_id', 0),
                item.get('teacher', ''), item.get('teacher_id', 0),
                item.get('subgroup', ''), item.get('original_date', ''),
                item.get('original_time', ''), item.get('subject', ''),
                item.get('new_date', ''), item.get('new_time', ''),
                item.get('auditory', ''), item.get('created_at', '')
            ))

        # Мигрируем замены
        for item in data.get('substitutions', []):
            cursor.execute("""
                INSERT INTO substitutions (group_name, group_id, subgroup,
                    original_date, original_time, original_discipline, original_teacher,
                    new_date, new_time, new_discipline, new_teacher, new_teacher_id,
                    new_auditory, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get('group', ''), item.get('group_id', 0),
                item.get('subgroup', ''), item.get('original_date', ''),
                item.get('original_time', ''), item.get('subject', ''),
                item.get('original_teacher', ''), item.get('new_date', ''),
                item.get('new_time', ''), item.get('new_discipline', ''),
                item.get('new_teacher', ''), item.get('new_teacher_id', 0),
                item.get('new_auditory', ''), item.get('created_at', '')
            ))

        # Мигрируем консультации
        for item in data.get('consultations', []):
            cursor.execute("""
                INSERT INTO consultations (teacher, teacher_id, date, time,
                    auditory, group_name, group_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get('teacher', ''), item.get('teacher_id', 0),
                item.get('date', ''), item.get('time', ''),
                item.get('auditory', ''), item.get('group', ''),
                item.get('group_id'), item.get('created_at', '')
            ))

        # Мигрируем пересдачи
        for item in data.get('retakes', []):
            cursor.execute("""
                INSERT INTO retakes (subtype, teachers, date, time, auditory,
                    discipline, group_name, group_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get('subtype', 'normal'),
                json.dumps(item.get('teachers', [])),
                item.get('date', ''), item.get('time', ''),
                item.get('auditory', ''), item.get('discipline', ''),
                item.get('group', ''), item.get('group_id'),
                item.get('created_at', '')
            ))

        conn.commit()
        conn.close()
        return True

    # === CRUD операции ===

    def get_transfers(self, group_id=None):
        conn = self._get_conn()
        if group_id:
            rows = conn.execute(
                "SELECT * FROM transfers WHERE group_id = ? ORDER BY new_date, new_time",
                (group_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transfers ORDER BY new_date, new_time"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_substitutions(self, group_id=None):
        conn = self._get_conn()
        if group_id:
            rows = conn.execute(
                "SELECT * FROM substitutions WHERE group_id = ? ORDER BY new_date, new_time",
                (group_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM substitutions ORDER BY new_date, new_time"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_consultations(self, teacher_id=None, date_from=None, date_to=None):
        conn = self._get_conn()
        query = "SELECT * FROM consultations WHERE 1=1"
        params = []

        if teacher_id:
            query += " AND teacher_id = ?"
            params.append(teacher_id)
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " ORDER BY date, time"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_retakes(self, group_id=None):
        conn = self._get_conn()
        if group_id:
            rows = conn.execute(
                "SELECT * FROM retakes WHERE group_id = ? ORDER BY date, time",
                (group_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM retakes ORDER BY date, time"
            ).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            d['teachers'] = json.loads(d['teachers']) if d['teachers'] else []
            results.append(d)
        return results

    def get_all_changes(self, group_id=None, teacher_id=None):
        """Получить все изменения (для API /api/changes)."""
        return {
            'transfers': self.get_transfers(group_id),
            'substitutions': self.get_substitutions(group_id),
            'consultations': self.get_consultations(teacher_id),
            'retakes': self.get_retakes(group_id),
            'cancellations': self.get_cancellations(group_id)
        }

    def get_cancellations(self, group_id=None):
        conn = self._get_conn()
        if group_id:
            rows = conn.execute(
                "SELECT * FROM cancellations WHERE group_id = ? ORDER BY original_date, original_time",
                (group_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cancellations ORDER BY original_date, original_time"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_cancel(self, data):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO cancellations (group_name, group_id, subgroup,
                original_date, original_time, discipline, teacher, auditory, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('group', ''), data.get('group_id', 0),
            data.get('subgroup', ''), data.get('original_date', ''),
            data.get('original_time', ''), data.get('discipline', ''),
            data.get('teacher', ''), data.get('auditory', ''),
            data.get('reason', ''), data.get('created_at', datetime.now().isoformat())
        ))
        conn.commit()
        conn.close()

    def add_transfer(self, data):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO transfers (group_name, group_id, teacher, teacher_id, subgroup,
                original_date, original_time, subject, new_date, new_time, auditory, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('group', ''), data.get('group_id', 0),
            data.get('teacher', ''), data.get('teacher_id', 0),
            data.get('subgroup', ''), data.get('original_date', ''),
            data.get('original_time', ''), data.get('subject', ''),
            data.get('new_date', ''), data.get('new_time', ''),
            data.get('auditory', ''), data.get('created_at', datetime.now().isoformat())
        ))
        conn.commit()
        conn.close()

    def add_substitution(self, data):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO substitutions (group_name, group_id, subgroup,
                original_date, original_time, original_discipline, original_teacher,
                new_date, new_time, new_discipline, new_teacher, new_teacher_id,
                new_auditory, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('group', ''), data.get('group_id', 0),
            data.get('subgroup', ''), data.get('original_date', ''),
            data.get('original_time', ''), data.get('original_discipline', ''),
            data.get('original_teacher', ''), data.get('new_date', ''),
            data.get('new_time', ''), data.get('new_discipline', ''),
            data.get('new_teacher', ''), data.get('new_teacher_id', 0),
            data.get('new_auditory', ''), data.get('created_at', datetime.now().isoformat())
        ))
        conn.commit()
        conn.close()

    def add_consultation(self, data):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO consultations (teacher, teacher_id, date, time,
                auditory, group_name, group_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('teacher', ''), data.get('teacher_id', 0),
            data.get('date', ''), data.get('time', ''),
            data.get('auditory', ''), data.get('group', ''),
            data.get('group_id'), data.get('created_at', datetime.now().isoformat())
        ))
        conn.commit()
        conn.close()

    def add_retake(self, data):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO retakes (subtype, teachers, date, time, auditory,
                discipline, group_name, group_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('subtype', 'normal'),
            json.dumps(data.get('teachers', []), ensure_ascii=False),
            data.get('date', ''), data.get('time', ''),
            data.get('auditory', ''), data.get('discipline', ''),
            data.get('group', ''), data.get('group_id'),
            data.get('created_at', datetime.now().isoformat())
        ))
        conn.commit()
        conn.close()
