import os

class Config:
    SQLITE_DATABASE = "digital_trainer.db"
    UPLOAD_FOLDER = "uploads"
    GUIDE_FOLDER = "guide"
    ALLOWED_EXTENSIONS = {'pdf'}
    
    @classmethod
    def init_directories(cls):
        """Создание необходимых директорий"""
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.GUIDE_FOLDER, exist_ok=True)
        os.makedirs('data', exist_ok=True)