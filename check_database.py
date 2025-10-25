import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    """Проверка содержимого базы данных"""
    conn = sqlite3.connect('digital_trainer.db')
    cursor = conn.cursor()
    
    # Проверяем таблицу guide_sections
    cursor.execute("SELECT COUNT(*) FROM guide_sections")
    count = cursor.fetchone()[0]
    logger.info(f"📊 Всего разделов в БД: {count}")
    
    # Показываем первые 5 разделов
    cursor.execute("SELECT section_title, page_number, LENGTH(section_content) as length FROM guide_sections LIMIT 5")
    sections = cursor.fetchall()
    
    logger.info("📋 Примеры разделов:")
    for title, page, length in sections:
        logger.info(f"   - Страница {page}: '{title}' ({length} символов)")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_database()