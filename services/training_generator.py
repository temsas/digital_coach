import json
import logging
from database.db_connection import Database
from services.pdf_parser import GuideParser
from services.gigachat_service import GigaChatService

logger = logging.getLogger(__name__)

class TrainingGenerator:
    def __init__(self):
        self.db = Database()
        self.guide_parser = GuideParser()
        self.gigachat_available = False
        self.gigachat = None
        
        try:
            self.gigachat = GigaChatService()
            self.gigachat_available = True
            logger.info("✅ GigaChat инициализирован")
        except Exception as e:
            logger.error(f"❌ GigaChat недоступен: {e}")
            # Создаем заглушку для gigachat
            self.gigachat = self._create_gigachat_stub()

    def _create_gigachat_stub(self):
        """Создает заглушку для GigaChat когда он недоступен"""
        class GigaChatStub:
            def generate_training_lessons(self, guide_content, num_lessons):
                return []
            
            def generate_simple_lesson(self, section_title, section_content):
                # Создаем простой урок на основе раздела
                theory = section_content[:200] + "..." if len(section_content) > 200 else section_content
                
                return {
                    "lesson_title": section_title,
                    "theory_content": theory,
                    "question": f"О чем говорится в разделе '{section_title}'?",
                    "options": [
                        "Об основах работы с компьютером",
                        "О безопасности в интернете", 
                        "О программах для обработки фото",
                        "Информация не указана в руководстве"
                    ],
                    "correct_answer": 0,
                    "explanation": f"Этот раздел содержит информацию из руководства по цифровой грамотности.",
                    "difficulty_level": "beginner"
                }
        
        return GigaChatStub()

    def initialize_system(self) -> bool:
        """Инициализация системы обучения"""
        logger.info("🔄 Инициализация системы обучения...")

        # Парсим руководство
        sections_count = self.guide_parser.parse_guide_pdf()
        
        if sections_count == 0:
            logger.error("❌ Не удалось распарсить руководство")
            return False

        # Генерируем уроки
        if not self.generate_training_lessons():
            logger.error("❌ Не удалось сгенерировать уроки")
            return False

        logger.info("✅ Система обучения инициализирована успешно")
        return True

    def generate_training_lessons(self, num_lessons: int = 10) -> bool:
        """Генерация уроков обучения"""
        try:
            # Получаем содержание руководства
            guide_content = self.guide_parser.get_guide_content_for_training()
            
            if not guide_content:
                logger.error("❌ Нет содержания руководства для генерации уроков")
                return False

            lessons_data = []

            if self.gigachat_available:
                # Пробуем сгенерировать через GigaChat
                logger.info("🔄 Генерация уроков через GigaChat...")
                lessons_data = self.gigachat.generate_training_lessons(guide_content, num_lessons)
                if lessons_data:
                    logger.info(f"✅ GigaChat сгенерировал {len(lessons_data)} уроков")
                else:
                    logger.warning("⚠️ GigaChat не вернул уроки")
            
            # Если GigaChat не сгенерировал, создаем простые уроки
            if not lessons_data:
                logger.info("🔄 Создание простых уроков на основе разделов...")
                lessons_data = self._generate_simple_lessons(num_lessons)

            # Сохраняем уроки в БД
            for lesson in lessons_data:
                lesson_data = {
                    'lesson_title': lesson['lesson_title'],
                    'theory_content': lesson['theory_content'],
                    'question': lesson['question'],
                    'options_json': json.dumps(lesson['options']),
                    'correct_answer': lesson['correct_answer'],
                    'explanation': lesson['explanation'],
                    'difficulty_level': lesson.get('difficulty_level', 'beginner')
                }
                self.db.save_training_lesson(lesson_data)

            logger.info(f"✅ Сгенерировано и сохранено {len(lessons_data)} уроков")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка генерации уроков: {e}")
            return False

    def _generate_simple_lessons(self, num_lessons: int) -> list:
        """Генерация простых уроков на основе разделов руководства"""
        sections = self.db.get_guide_sections(limit=num_lessons)
        lessons = []

        logger.info(f"📚 Создание уроков из {len(sections)} разделов...")
        
        for section in sections:
            lesson = self.gigachat.generate_simple_lesson(
                section['section_title'], 
                section['section_content']
            )
            lessons.append(lesson)

        return lessons

    def get_training_data(self) -> list:
        """Получение данных для обучения"""
        lessons = self.db.get_training_lessons(limit=10)
        
        if not lessons:
            logger.warning("❌ Нет уроков в БД, пытаемся сгенерировать...")
            if self.initialize_system():
                lessons = self.db.get_training_lessons(limit=10)

        training_data = []
        for lesson in lessons:
            training_data.append({
                'id': lesson['id'],
                'theory': lesson['theory_content'],
                'test': {
                    'question': lesson['question'],
                    'options': json.loads(lesson['options_json']),
                    'correct_answer': lesson['correct_answer'],
                    'explanation': lesson['explanation']
                }
            })

        logger.info(f"📊 Загружено {len(training_data)} уроков для обучения")
        return training_data

    def check_guide_available(self) -> bool:
        """Проверка доступности руководства"""
        return self.guide_parser.check_guide_exists()