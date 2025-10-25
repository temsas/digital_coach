import sqlite3
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = Config.SQLITE_DATABASE

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Таблица для разделов руководства
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guide_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_title TEXT NOT NULL,
                    section_content TEXT NOT NULL,
                    page_number INTEGER,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица для сгенерированных уроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_title TEXT NOT NULL,
                    theory_content TEXT NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    correct_answer INTEGER NOT NULL,
                    explanation TEXT NOT NULL,
                    source_section_id INTEGER,
                    difficulty_level TEXT DEFAULT 'beginner',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_section_id) REFERENCES guide_sections (id)
                )
            ''')

            # Таблица для сессий обучения пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE,
                    training_data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info("✅ SQLite база данных тренажера инициализирована успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def save_guide_section(self, title: str, content: str, page: int = None, category: str = None):
        """Сохранение раздела руководства с логированием"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO guide_sections (section_title, section_content, page_number, category)
                VALUES (?, ?, ?, ?)
            ''', (title, content, page, category))
            
            conn.commit()
            logger.info(f"💾 Сохранен раздел: '{title}' (стр. {page}, {len(content)} символов)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения раздела: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_guide_sections(self, limit: int = 100):
        """Получение разделов руководства"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, section_title, section_content, page_number, category 
            FROM guide_sections 
            ORDER BY page_number, id
            LIMIT ?
        ''', (limit,))

        sections = cursor.fetchall()
        cursor.close()
        conn.close()

        return sections

    def save_training_lesson(self, lesson_data: dict):
        """Сохранение сгенерированного урока"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO training_lessons 
            (lesson_title, theory_content, question, options_json, correct_answer, explanation, source_section_id, difficulty_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            lesson_data['lesson_title'],
            lesson_data['theory_content'],
            lesson_data['question'],
            lesson_data['options_json'],
            lesson_data['correct_answer'],
            lesson_data['explanation'],
            lesson_data.get('source_section_id'),
            lesson_data.get('difficulty_level', 'beginner')
        ))

        conn.commit()
        cursor.close()
        conn.close()

    def get_training_lessons(self, limit: int = 10):
        """Получение сгенерированных уроков"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, lesson_title, theory_content, question, options_json, correct_answer, explanation
            FROM training_lessons 
            ORDER BY id
            LIMIT ?
        ''', (limit,))

        lessons = cursor.fetchall()
        cursor.close()
        conn.close()

        return lessons

    def clear_guide_data(self):
        """Очистка данных руководства"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM guide_sections")
        cursor.execute("DELETE FROM training_lessons")
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("🗑️ Данные руководства очищены")


if __name__ == "__main__":
    db = Database()
    db.init_db()