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

    def parse_guide_pdf(self):
        """Парсинг руководства по цифровой грамотности с очисткой текста"""
        
        if not os.path.exists(self.guide_path):
            logger.error(f"❌ Руководство не найдено: {self.guide_path}")
            return 0

        try:
            # Очищаем старые данные
            self.db.clear_guide_data()

            with open(self.guide_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                sections_count = 0

                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    # Очищаем текст страницы перед добавлением
                    cleaned_text = self._clean_page_text(page_text, page_num + 1)
                    full_text += cleaned_text + "\n"

                # Разбиваем на чистые разделы
                sections = self._extract_clean_sections(full_text)
                
                # Сохраняем только качественные разделы
                for section in sections:
                    if self._is_quality_section(section):
                        self.db.save_guide_section(
                            title=section['title'],
                            content=section['content'],
                            page=section.get('page'),
                            category=section.get('category')
                        )
                        sections_count += 1

                logger.info(f"✅ Руководство распарсено: {sections_count} качественных разделов")
                return sections_count

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга руководства: {e}")
            return 0

    def _clean_page_text(self, text: str, page_num: int) -> str:
        """Очистка текста страницы от мусора"""
        if not text.strip():
            return ""
            
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Удаляем мусор
            if self._is_garbage_line(line, page_num):
                continue
                
            # Очищаем оставшиеся строки
            cleaned_line = self._clean_line(line)
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)

    def _is_garbage_line(self, line: str, page_num: int) -> bool:
        """Определяет, является ли строка мусором"""
        # Пустые строки
        if not line:
            return True
            
        # Номера страниц (только цифры)
        if line.isdigit() and int(line) in [page_num, page_num - 1, page_num + 1]:
            return True
            
        # Подписи к картинкам (1.1, 2.2, 1.15 и т.д.)
        if re.match(r'^\d+\.\d+$', line):
            return True
            
        # Одиночные цифры или очень короткие строки без смысла
        if len(line) < 3 and not line.isalpha():
            return True
            
        # Строки только с цифрами и точками
        if re.match(r'^[\d\.\s]+$', line):
            return True
            
        return False

    def _clean_line(self, line: str) -> str:
        """Очистка отдельной строки"""
        # Удаляем лишние пробелы
        line = re.sub(r'\s+', ' ', line)
        
        # Удаляем изолированные цифры в середине текста (но сохраняем даты, номера)
        line = re.sub(r'(?<!\d)\s\d{1,2}\s(?!\d)', ' ', line)
        
        return line.strip()

    def _extract_clean_sections(self, text):
        """Извлечение чистых разделов из текста"""
        sections = []
        
        # Ищем заголовки глав
        chapter_patterns = [
            r'ГЛАВА [А-Я]+\s*[А-Я]*(?:\s*/\s*[А-Я\s]+)?\n(.*?)(?=ГЛАВА|$)',
            r'[А-Я][А-Я\s]{10,}\n(.*?)(?=[А-Я][А-Я\s]{10,}|$)',
        ]
        
        for pattern in chapter_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                title = match.group(0).split('\n')[0].strip()
                content = match.group(1).strip()
                
                if len(content) > 200:  # Только значимые разделы
                    # Очищаем контент раздела
                    cleaned_content = self._clean_section_content(content)
                    
                    section = {
                        'title': title,
                        'content': cleaned_content,
                        'category': 'chapter'
                    }
                    sections.append(section)
        
        # Если не нашли по паттернам, разбиваем на осмысленные абзацы
        if not sections:
            paragraphs = re.split(r'\n\s*\n', text)
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if self._is_meaningful_paragraph(paragraph):
                    # Создаем заголовок из первых слов
                    first_line = paragraph.split('\n')[0]
                    title = first_line[:100] + '...' if len(first_line) > 100 else first_line
                    
                    section = {
                        'title': title,
                        'content': self._clean_section_content(paragraph),
                        'category': 'paragraph'
                    }
                    sections.append(section)
        
        return sections

    def _clean_section_content(self, content: str) -> str:
        """Очистка контента раздела"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not self._is_garbage_line(line, 0) and len(line) > 10:
                cleaned_line = self._clean_line(line)
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)

    def _is_meaningful_paragraph(self, paragraph: str) -> bool:
        """Проверяет, является ли абзац осмысленным"""
        if len(paragraph) < 100:
            return False
            
        # Должен содержать нормальные слова
        words = paragraph.split()
        if len(words) < 15:
            return False
            
        # Не должен состоять в основном из цифр
        digit_ratio = sum(1 for char in paragraph if char.isdigit()) / len(paragraph)
        if digit_ratio > 0.3:
            return False
            
        return True

    def _is_quality_section(self, section: dict) -> bool:
        """Проверяет качество раздела перед сохранением"""
        content = section['content']
        
        # Минимальная длина
        if len(content) < 150:
            return False
            
        # Должен содержать нормальный текст
        words = content.split()
        if len(words) < 20:
            return False
            
        # Не должен быть набором цифр
        if re.match(r'^[\d\s\.]+$', content):
            return False
            
        return True

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
        return os.path.exists(self.guide_path)