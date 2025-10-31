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
        self.guide_files = Config.GUIDE_FILES
        self.guide_folder = Config.GUIDE_FOLDER
        
    def parse_all_guides(self):
        """Парсинг ВСЕХ учебников"""
        total_sections = 0
        
        # Очищаем старые данные
        self.db.clear_guide_data()
        
        for guide_file in self.guide_files:
            guide_path = os.path.join(self.guide_folder, guide_file)
            
            if not os.path.exists(guide_path):
                logger.warning(f"⚠️ Учебник не найден: {guide_path}")
                continue
                
            sections_count = self.parse_single_guide(guide_path, guide_file)
            total_sections += sections_count
            logger.info(f"✅ Учебник {guide_file} распарсен: {sections_count} страниц")
        
        logger.info(f"🎉 Всего распарсено учебников: {len(self.guide_files)}, разделов: {total_sections}")
        return total_sections

    def parse_single_guide(self, guide_path, guide_name):
        """Парсинг одного учебника"""
        try:
            with open(guide_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                sections_count = 0

                logger.info(f"📄 Парсинг учебника {guide_name}: {total_pages} страниц")

                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        # Очищаем текст
                        cleaned_text = self._clean_page_text(page_text, page_num + 1, guide_name)
                        
                        # Создаем раздел для каждой страницы
                        section_title = f"{guide_name} - Страница {page_num + 1}"
                        
                        # Сохраняем в БД с указанием учебника
                        self.db.save_guide_section(
                            title=section_title,
                            content=cleaned_text,
                            page=page_num + 1,
                            category=guide_name,  # Используем имя файла как категорию
                            guide_source=guide_name  # Добавляем источник
                        )
                        sections_count += 1
                        
                        if (page_num + 1) % 10 == 0:  # Логируем каждые 10 страниц
                            logger.info(f"📖 {guide_name}: обработано {page_num + 1}/{total_pages} страниц")

                logger.info(f"✅ {guide_name} полностью распарсен: {sections_count} страниц")
                return sections_count

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга учебника {guide_name}: {e}")
            return 0

    def _clean_page_text(self, text: str, page_num: int, guide_name: str) -> str:
        """Очистка текста страницы с учетом особенностей разных учебников"""
        if not text.strip():
            return ""
            
        # Удаляем лишние пробелы и переносы
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Убираем явный мусор (номера страниц, оглавления)
        lines = text.split('. ')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Убираем строки, которые являются только цифрами (номера страниц)
            if line.isdigit() and len(line) < 4:
                continue
            # Убираем очень короткие строки без смысла
            if len(line) > 15 and not self._is_garbage_line(line, page_num, guide_name):
                cleaned_lines.append(line)
        
        result = '. '.join(cleaned_lines)
        
        # Если после очистки слишком мало текста, возвращаем оригинал с ограничением длины
        if len(result) < 50:
            return text[:1500]
            
        return result[:2000]

    def _is_garbage_line(self, line: str, page_num: int, guide_name: str) -> bool:
        """Проверка на мусорные строки"""
        if not line or len(line) < 3:
            return True
            
        # Только явный мусор
        garbage_indicators = [
            'оглавление', 'содержание', 'contents', 'глава',
            'chapter', 'page', 'страница'
        ]
        
        line_lower = line.lower()
        if any(indicator in line_lower for indicator in garbage_indicators):
            return True
            
        if line.isdigit() and int(line) in [page_num, page_num - 1, page_num + 1]:
            return True
            
        return False

    def get_guide_content_for_training(self, max_sections: int = 20):
        """Получение содержимого ВСЕХ учебников для обучения"""
        sections = self.db.get_guide_sections(limit=max_sections)
        
        if not sections:
            return ""

        content = "СОДЕРЖАНИЕ ВСЕХ УЧЕБНИКОВ ПО ЦИФРОВОЙ ГРАМОТНОСТИ:\n\n"
        
        # Группируем по учебникам
        guides_content = {}
        for section in sections:
            guide_name = section.get('guide_source', 'unknown')
            if guide_name not in guides_content:
                guides_content[guide_name] = []
            guides_content[guide_name].append(section)

        # Формируем содержимое по учебникам
        for guide_name, guide_sections in guides_content.items():
            content += f"=== УЧЕБНИК: {guide_name.upper()} ===\n\n"
            
            for section in guide_sections[:5]:  # Берем по 5 разделов из каждого учебника
                title = section['section_title']
                section_content = section['section_content']
                
                content += f"--- {title} ---\n"
                content += f"{section_content}\n\n"
            
            content += "="*60 + "\n\n"

        logger.info(f"📚 Подготовлено содержимое {len(guides_content)} учебников: {len(content)} символов")
        return content

    def check_guides_exist(self):
        """Проверка существования всех учебников"""
        results = {}
        for guide_file in self.guide_files:
            guide_path = os.path.join(self.guide_folder, guide_file)
            exists = os.path.exists(guide_path)
            results[guide_file] = exists
            logger.info(f"🔍 Проверка учебника {guide_file}: {exists}")
        
        return results