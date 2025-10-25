from flask import Flask, render_template, request, jsonify
import os
import json
import logging
import re
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

from config import Config
from services.gigachat_service import GigaChatService
from database.db_connection import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'digital-trainer-secret-2024'
app.config.from_object(Config)

# Инициализация сервисов
try:
    gigachat_service = GigaChatService()
    db = Database()
    GIGACHAT_AVAILABLE = True
    logger.info("✅ GigaChat инициализирован успешно")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
    GIGACHAT_AVAILABLE = False
    gigachat_service = None
    db = None

@app.route('/')
def index():
    """Главная страница тренажера"""
    return render_template('index.html', 
                         GIGACHAT_AVAILABLE=GIGACHAT_AVAILABLE)

@app.route('/api/learn-topic', methods=['POST'])
def learn_topic():
    """Генерация объяснения и теста по теме"""
    if not GIGACHAT_AVAILABLE:
        return jsonify({
            'status': 'error',
            'error': 'GigaChat недоступен'
        }), 503

    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        
        if not topic:
            return jsonify({
                'status': 'error',
                'error': 'Тема не может быть пустой'
            }), 400

        logger.info(f"🎓 Запрос на изучение темы: {topic}")

        # Получаем релевантные разделы из БД
        relevant_sections = get_relevant_sections(topic)
        logger.info(f"📚 Найдено релевантных разделов: {len(relevant_sections)}")
        
        if not relevant_sections:
            return jsonify({
                'status': 'success',
                'explanation': f"В руководстве по цифровой грамотности нет информации по теме '{topic}'. Попробуйте другую тему.",
                'quiz': None
            })

        # Создаем промпт для генерации объяснения и теста
        prompt = create_learning_prompt(topic, relevant_sections)
        
        # Отправляем запрос к GigaChat
        response = gigachat_service.client.chat(prompt)
        content = response.choices[0].message.content
        
        # Парсим ответ (объяснение + тест)
        explanation, quiz = parse_learning_response(content, topic, relevant_sections)
        
        # Детальное логирование теста
        if quiz:
            logger.info(f"✅ Тест создан:")
            logger.info(f"   Вопрос: {quiz['question']}")
            logger.info(f"   Варианты: {quiz['options']}")
            logger.info(f"   Правильный ответ: {quiz['correct_answer']}")
        else:
            logger.warning("⚠️ Тест не создан")
        
        logger.info(f"📚 Сгенерирован урок по теме '{topic}': quiz={quiz is not None}")

        return jsonify({
            'status': 'success',
            'explanation': explanation,
            'quiz': quiz
        })

    except Exception as e:
        logger.error(f"❌ Ошибка генерации урока: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Произошла ошибка при создании урока'
        }), 500

@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    """Проверка ответа на тест"""
    try:
        data = request.get_json()
        answer_index = data.get('answer_index')
        quiz_data = data.get('quiz_data')
        
        if answer_index is None or quiz_data is None:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        # Используем переданные данные теста для проверки
        is_correct = (answer_index == quiz_data['correct_answer'])
        
        result = {
            'is_correct': is_correct,
            'explanation': quiz_data['explanation'],
            'correct_answer': quiz_data['correct_answer']
        }
        
        return jsonify({
            'status': 'success', 
            'result': result
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки ответа: {e}")
        return jsonify({'error': str(e)}), 500

def get_relevant_sections(topic):
    """Получение релевантных разделов из БД по теме"""
    try:
        sections = db.get_guide_sections(limit=50)
        relevant = []
        
        topic_lower = topic.lower()
        topic_words = [word for word in topic_lower.split() if len(word) > 2]
        
        for section in sections:
            title = section['section_title'].lower()
            content = section['section_content'].lower()
            
            score = 0
            
            if topic_lower in title:
                score += 10
            if topic_lower in content:
                score += 5
                
            for word in topic_words:
                if word in title:
                    score += 3
                if word in content:
                    score += 1
            
            if score >= 2:
                relevant.append({
                    'title': section['section_title'],
                    'content': section['section_content'],
                    'score': score,
                    'page': section['page_number']
                })
        
        relevant.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"🔍 По теме '{topic}' найдено разделов: {len(relevant)}")
        for section in relevant[:3]:
            logger.info(f"   - '{section['title']}' (score: {section['score']})")
        
        return relevant[:3]
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска разделов: {e}")
        return []

def create_learning_prompt(topic, relevant_sections):
    """Создание УЛЬТРА-СТРОГОГО промпта"""
    
    concrete_texts = []
    for i, section in enumerate(relevant_sections[:2], 1):
        concrete_text = section['content'][:500]
        concrete_texts.append(f"РАЗДЕЛ {i} '{section['title']}':\n{concrete_text}")
    
    concrete_content = "\n\n".join(concrete_texts)
    
    prompt = f"""
    ИСПОЛЬЗУЙ ТОЛЬКО ЭТУ ИНФОРМАЦИЮ ИЗ РУКОВОДСТВА:

    {concrete_content}

    ЗАПРЕЩЕНО:
    - Придумывать информацию
    - Использовать свои знания
    - Давать общие фразы

    ЗАДАЧА 1: ОБЪЯСНЕНИЕ ТЕМЫ "{topic.upper()}"
    - Используй ТОЛЬКО факты из текста выше
    - Цитируй КОНКРЕТНЫЕ фразы из руководства
    - Объяснение: 3-4 предложения

    ЗАДАЧА 2: ТЕСТОВЫЙ ВОПРОС
    - Вопрос должен проверять КОНКРЕТНЫЙ факт из текста
    - Варианты ответов должны быть основаны на тексте
    - Только один вариант должен быть точной цитатой или прямым следствием из текста

    ПРИМЕР ПРАВИЛЬНОГО ОБЪЯСНЕНИЯ:
    "Компьютер готов к тому, что вы можете нажать 'не туда'. Он является вашим помощником и на качество его работы это не скажется. С помощью компьютера можно работать с текстом, создавать таблицы, искать информацию в интернете и общаться с родственниками."

    ПРИМЕР ПРАВИЛЬНОГО ВОПРОСА:
    "Для чего используется клавиша Enter согласно руководству?"

    ФОРМАТ ОТВЕТА (ТОЛЬКО JSON):
    {{
        "explanation": "Твое объяснение с ЦИТАТАМИ из текста...",
        "quiz": {{
            "question": "Конкретный вопрос по тексту выше...",
            "options": ["вариант1", "вариант2", "вариант3", "вариант4"],
            "correct_answer": 0,
            "explanation": "Правильный ответ - вариант X, потому что в тексте сказано: 'ЦИТАТА ИЗ РУКОВОДСТВА'."
        }}
    }}

    НАЧИНАЙ ОТВЕТ С {{"
    """
    
    return prompt

def parse_learning_response(response, topic, relevant_sections):
    """Принудительный парсинг ответа с проверкой на использование данных"""
    try:
        cleaned_response = response.strip()
        logger.info(f"🔧 Raw GigaChat response: {cleaned_response[:500]}...")
        
        start = cleaned_response.find('{')
        end = cleaned_response.rfind('}') + 1
        
        if start == -1 or end == 0:
            raise ValueError("JSON не найден в ответе")
            
        json_str = cleaned_response[start:end]
        data = json.loads(json_str)
        
        explanation = data.get('explanation', '')
        
        # ПРОВЕРКА: Объяснение должно содержать конкретные факты из руководства
        if not contains_concrete_info(explanation, relevant_sections):
            logger.warning("⚠️ GigaChat дал общее объяснение без конкретики!")
            explanation = create_forced_explanation(topic, relevant_sections)
        
        quiz_data = data.get('quiz')
        if not quiz_data:
            return explanation, None
            
        quiz = validate_and_fix_quiz(quiz_data, topic, relevant_sections)
        
        return explanation, quiz
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга ответа: {e}")
        return create_forced_explanation(topic, relevant_sections), create_forced_quiz(topic, relevant_sections)

def contains_concrete_info(explanation, relevant_sections):
    """Проверяет, содержит ли объяснение конкретную информацию из руководства"""
    if not explanation:
        return False
        
    guide_keywords = set()
    for section in relevant_sections:
        content_lower = section['content'].lower()
        words = set(re.findall(r'\b\w{4,}\b', content_lower))
        guide_keywords.update(words)
    
    explanation_lower = explanation.lower()
    matches = sum(1 for word in guide_keywords if word in explanation_lower)
    
    logger.info(f"🔍 Проверка конкретики: {matches} совпадений с руководством")
    return matches > 2

def create_forced_explanation(topic, relevant_sections):
    """Принудительно создаем объяснение на основе данных из БД"""
    first_section = relevant_sections[0]
    content = first_section['content']
    
    sentences = re.split(r'[.!?]+', content)
    meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
    
    if meaningful_sentences:
        explanation = " ".join(meaningful_sentences)
        if len(explanation) > 400:
            explanation = explanation[:400] + "..."
    else:
        explanation = content[:300] + "..."
    
    logger.info("🔧 Использовано принудительное объяснение из БД")
    return explanation

def validate_and_fix_quiz(quiz_data, topic, relevant_sections):
    """Валидация и исправление теста"""
    try:
        required_fields = ['question', 'options', 'correct_answer', 'explanation']
        for field in required_fields:
            if field not in quiz_data:
                raise ValueError(f"Отсутствует поле: {field}")
        
        if not isinstance(quiz_data['options'], list) or len(quiz_data['options']) != 4:
            quiz_data['options'] = ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"]
        
        if not isinstance(quiz_data['correct_answer'], int) or not 0 <= quiz_data['correct_answer'] <= 3:
            quiz_data['correct_answer'] = 0
            
        quiz = {
            'id': f'quiz_{hash(topic)}',
            'question': quiz_data['question'],
            'options': quiz_data['options'],
            'correct_answer': quiz_data['correct_answer'],
            'explanation': quiz_data['explanation']
        }
        
        return quiz
        
    except Exception as e:
        logger.error(f"❌ Ошибка валидации теста: {e}")
        return create_forced_quiz(topic, relevant_sections)

def create_forced_quiz(topic, relevant_sections):
    """Создаем тест принудительно на основе данных"""
    first_section = relevant_sections[0]
    content = first_section['content']
    
    # Создаем простой вопрос на основе содержания
    sentences = re.split(r'[.!?]+', content)
    first_meaningful = next((s.strip() for s in sentences if len(s.strip()) > 30), content[:100])
    
    quiz = {
        'id': 'forced_quiz',
        'question': f'Что говорится в руководстве о теме "{topic}"?',
        'options': [
            first_meaningful[:80] + "...",
            "Информация не указана в руководстве",
            "Это сложная тема для изучения", 
            "Нужно обратиться к другим источникам"
        ],
        'correct_answer': 0,
        'explanation': f'Правильный ответ основан на информации из раздела "{first_section["title"]}" руководства.'
    }
    
    logger.info("🔧 Использован принудительный тест из БД")
    return quiz

@app.route('/api/debug-sections')
def debug_sections():
    """Отладочный эндпоинт для просмотра распарсенных разделов"""
    if not db:
        return jsonify({'error': 'БД не инициализирована'}), 500
        
    sections = db.get_guide_sections(limit=10)
    result = []
    
    for section in sections:
        result.append({
            'id': section['id'],
            'title': section['section_title'],
            'content_preview': section['section_content'][:200] + '...',
            'page': section['page_number'],
            'category': section['category'],
            'content_length': len(section['section_content'])
        })
    
    return jsonify({
        'status': 'success',
        'sections_count': len(sections),
        'sections': result
    })

@app.route('/api/debug-topic-search')
def debug_topic_search():
    """Отладочный поиск по теме"""
    topic = request.args.get('topic', 'компьютер')
    
    sections = db.get_guide_sections(limit=20)
    relevant = get_relevant_sections(topic)
    
    result = {
        'topic': topic,
        'total_sections': len(sections),
        'relevant_sections': len(relevant),
        'relevant_details': []
    }
    
    for section in relevant:
        result['relevant_details'].append({
            'title': section['title'],
            'score': section['score'],
            'content_preview': section['content'][:300] + '...',
            'content_length': len(section['content'])
        })
    
    return jsonify(result)

@app.route('/api/status')
def status():
    """Статус системы"""
    sections_count = 0
    if db:
        try:
            sections = db.get_guide_sections(limit=1)
            sections_count = len(sections)
        except:
            sections_count = 0
    
    return jsonify({
        'status': 'running',
        'gigachat_available': GIGACHAT_AVAILABLE,
        'sections_loaded': sections_count
    })

def initialize_system():
    """Инициализация системы"""
    logger.info("🚀 Инициализация системы тренажера...")
    
    Config.init_directories()
    
    if db:
        db.init_db()
        
        from services.pdf_parser import GuideParser
        parser = GuideParser()
        if parser.check_guide_exists():
            db.clear_guide_data()
            logger.info("🗑️ Старые данные очищены")
            
            sections_count = parser.parse_guide_pdf()
            logger.info(f"📚 PDF распарсен: {sections_count} разделов")
            
            sections = db.get_guide_sections(limit=10)
            logger.info(f"📖 Проверка БД: загружено {len(sections)} разделов")
            for section in sections:
                logger.info(f"   - {section['section_title']} ({len(section['section_content'])} chars)")
                
            test_sections = get_relevant_sections("компьютер")
            logger.info(f"🔍 Тестовый поиск 'компьютер': найдено {len(test_sections)} разделов")
            
        else:
            logger.warning("⚠️ PDF руководство не найдено в guide/digital_literacy_guide.pdf")
    
    logger.info("✅ Система инициализирована")

if __name__ == '__main__':
    initialize_system()
    
    logger.info("🚀 Интерактивный тренажер запущен!")
    logger.info("🔍 Интерфейс: http://localhost:5000/")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)