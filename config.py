import os

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLITE_DATABASE = os.path.join(BASE_DIR, "digital_trainer.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    GUIDE_FOLDER = os.path.join(BASE_DIR, "guide")
    ALLOWED_EXTENSIONS = {'pdf'}
    GUIDE_FILES = [
        "digital_literacy_guide.pdf",  # основной учебник
        "horizontsbook.pdf",           # первый дополнительный
        "guide_2.pdf"                  # второй дополнительный
    ]
    
    @classmethod
    def init_directories(cls):
        """Создание необходимых директорий"""
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.GUIDE_FOLDER, exist_ok=True)
        os.makedirs('data', exist_ok=True)