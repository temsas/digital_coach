import PyPDF2
import re
import os
import logging
from database.db_connection import Database
from config import Config

logger = logging.getLogger(__name__)

class GuideParser:
    def __init__(self):
        self.db = Database()
        self.guide_path = os.path.join(Config.GUIDE_FOLDER, "digital_literacy_guide.pdf")
        logger.info(f"🔍 Путь к руководству: {os.path.abspath(self.guide_path)}")

    def parse_guide_pdf(self):
        """Парсинг ВСЕГО руководства по цифровой грамотности"""
        
        if not os.path.exists(self.guide_path):
            logger.error(f"❌ Руководство не найдено: {self.guide_path}")
            return 0

        try:
            # Очищаем старые данные
            self.db.clear_guide_data()

            with open(self.guide_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                sections_count = 0

                logger.info(f"📄 Начало парсинга PDF: {total_pages} страниц")

                # Парсим ВСЕ страницы
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        # Очищаем текст
                        cleaned_text = self._clean_page_text(page_text, page_num + 1)
                        
                        # Создаем раздел для каждой страницы
                        section_title = f"Страница {page_num + 1}"
                        
                        # Сохраняем в БД
                        self.db.save_guide_section(
                            title=section_title,
                            content=cleaned_text,
                            page=page_num + 1,
                            category='page'
                        )
                        sections_count += 1
                        
                        logger.info(f"✅ Страница {page_num + 1} сохранена ({len(cleaned_text)} символов)")

                logger.info(f"🎉 PDF полностью распарсен: {sections_count} страниц")
                return sections_count

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга руководства: {e}")
            return 0

    def _clean_page_text(self, text: str, page_num: int) -> str:
        """Очистка текста страницы - упрощенная версия"""
        if not text.strip():
            return ""
            
        # Удаляем лишние пробелы и переносы
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Удаляем явный мусор (номера страниц в начале/конце)
        lines = text.split('. ')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Убираем строки, которые являются только цифрами (номера страниц)
            if line.isdigit() and len(line) < 4:
                continue
            # Убираем очень короткие строки без смысла
            if len(line) > 10:
                cleaned_lines.append(line)
        
        result = '. '.join(cleaned_lines)
        
        # Если после очистки слишком мало текста, возвращаем оригинал
        if len(result) < 50:
            return text[:1000]  # Ограничиваем длину
            
        return result[:2000]  # Ограничиваем максимальную длину

    def _is_garbage_line(self, line: str, page_num: int) -> bool:
        """Упрощенная проверка на мусор"""
        if not line or len(line) < 3:
            return True
            
        # Только явный мусор
        if line.isdigit() and int(line) in [page_num, page_num - 1, page_num + 1]:
            return True
            
        return False

    def get_guide_content_for_training(self, max_sections: int = 15):
        """Получение очищенного содержимого руководства для обучения"""
        sections = self.db.get_guide_sections(limit=max_sections)
        
        if not sections:
            return ""

        content = "ОЧИЩЕННОЕ РУКОВОДСТВО ПО ЦИФРОВОЙ ГРАМОТНОСТИ:\n\n"
        for section in sections:
            title = section['section_title']
            section_content = section['section_content']
            
            content += f"=== {title} ===\n"
            content += f"{section_content}\n"
            content += "="*50 + "\n\n"

        logger.info(f"📚 Подготовлено очищенное руководство: {len(content)} символов")
        return content

    def check_guide_exists(self):
        """Проверка существования руководства"""
        exists = os.path.exists(self.guide_path)
        logger.info(f"🔍 Проверка существования руководства: {self.guide_path} -> {exists}")
        return exists