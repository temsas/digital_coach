# debug_parser.py
import PyPDF2
import os

def parse_pages_11_to_21():
    """Парсинг страниц с 11 по 21 PDF прямо в терминал"""
    
    guide_path = "guide/digital_literacy_guide.pdf"
    
    if not os.path.exists(guide_path):
        print(f"❌ Файл не найден: {guide_path}")
        return
    
    print("=" * 80)
    print("🔍 ПАРСИНГ СТРАНИЦ С 11 ПО 21 PDF")
    print("=" * 80)
    
    try:
        with open(guide_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            print(f"📄 Всего страниц в PDF: {total_pages}")
            print()
            
            start_page = 10  # 11-я страница (индекс 10)
            end_page = min(20, total_pages - 1)  # 21-я страница (индекс 20) или последняя
            
            for page_num in range(start_page, end_page + 1):
                if page_num < total_pages:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    print(f"📖 СТРАНИЦА {page_num + 1} ({len(page_text)} символов):")
                    print("-" * 50)
                    print(page_text)
                    print("=" * 80)
                    print()
                else:
                    print(f"⚠️ Страница {page_num + 1} не существует (всего страниц: {total_pages})")
                
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")

if __name__ == "__main__":
    parse_pages_11_to_21()