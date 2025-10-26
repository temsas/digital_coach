from flask import Flask, render_template, request, jsonify
import os
import json
import logging
import re
import ast
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

# Популярные темы для быстрого выбора
POPULAR_TOPICS = [
    "компьютер", "интернет", "безопасность", "клавиатура", "мышь",
    "программы", "файлы", "папки", "электронная почта", "социальные сети",
    "поиск информации", "онлайн-покупки", "банковские карты", "пароли",
    "антивирус", "Wi-Fi", "браузер", "текстовый редактор", "таблицы"
]

@app.route('/')
def index():
    """Главная страница тренажера"""
    return render_template('index.html', 
                         GIGACHAT_AVAILABLE=GIGACHAT_AVAILABLE,
                         POPULAR_TOPICS=POPULAR_TOPICS)

@app.route('/api/generate-full-test', methods=['POST'])
def generate_full_test():
    """Генерация полноценного теста из 5 вопросов по теме"""
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

        logger.info(f"🎯 Запрос на генерацию полного теста по теме: {topic}")

        # Получаем релевантные разделы из БД
        relevant_sections = get_relevant_sections(topic)
        logger.info(f"📚 Найдено релевантных разделов: {len(relevant_sections)}")
        
        if not relevant_sections:
            return jsonify({
                'status': 'error',
                'error': f'В руководстве нет информации по теме "{topic}". Попробуйте другую тему.'
            })

        # Генерируем тест с улучшенным подходом
        test_data = generate_contextual_test(topic, relevant_sections)
        
        logger.info(f"✅ Полный тест создан: {len(test_data['questions'])} вопросов")
        
        return jsonify({
            'status': 'success',
            'test_data': test_data
        })

    except Exception as e:
        logger.error(f"❌ Ошибка генерации полного теста: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Произошла ошибка при создании теста'
        }), 500

def generate_contextual_test(topic, relevant_sections):
    """Генерация теста с контекстным анализом"""
    # Сначала создаем теорию на основе анализа контекста
    theory = generate_contextual_theory(topic, relevant_sections)
    
    # Затем генерируем вопросы с пониманием контекста
    questions = generate_contextual_questions(topic, relevant_sections, theory)
    
    return {
        'topic': topic,
        'theory': theory,
        'questions': questions
    }

def generate_contextual_questions(topic, relevant_sections, theory):
    """Генерация контекстных вопросов по теме - ТЕПЕРЬ 5 ВОПРОСОВ"""
    try:
        # Генерируем вопросы разных типов
        understanding_questions = generate_question_batch(topic, relevant_sections, theory, "understanding", 3)
        application_questions = generate_question_batch(topic, relevant_sections, theory, "application", 2)
        
        questions = understanding_questions + application_questions
        
        # Если вопросов недостаточно, добавляем резервные
        if len(questions) < 5:
            logger.warning(f"⚠️ Сгенерировано только {len(questions)} вопросов, добавляем резервные")
            for i in range(len(questions), 5):
                questions.append(create_meaningful_question(i, topic, relevant_sections))
        
        return questions[:5]  # Всегда возвращаем 5 вопросов
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации контекстных вопросов: {e}")
        # Возвращаем резервные вопросы
        return [create_meaningful_question(i, topic, relevant_sections) for i in range(5)]

def generate_test_step_by_step(topic, relevant_sections):
    """Поэтапная генерация теста - резервный метод - ТЕПЕРЬ 5 ВОПРОСОВ"""
    logger.info(f"🔄 Поэтапная генерация теста по теме: {topic}")
    
    try:
        # Генерируем теорию
        theory = generate_contextual_theory(topic, relevant_sections)
        
        # Генерируем вопросы поэтапно
        questions = []
        
        # Первая партия вопросов
        try:
            batch1 = generate_question_batch(topic, relevant_sections, theory, "understanding", 3)
            questions.extend(batch1)
        except Exception as e:
            logger.error(f"❌ Ошибка первой партии вопросов: {e}")
            for i in range(len(questions), len(questions) + 3):
                questions.append(create_meaningful_question(i, topic, relevant_sections))
        
        # Вторая партия вопросов
        try:
            batch2 = generate_question_batch(topic, relevant_sections, theory, "application", 2)
            questions.extend(batch2)
        except Exception as e:
            logger.error(f"❌ Ошибка второй партии вопросов: {e}")
            for i in range(len(questions), len(questions) + 2):
                questions.append(create_meaningful_question(i, topic, relevant_sections))
        
        # Обеспечиваем ровно 5 вопросов
        if len(questions) > 5:
            questions = questions[:5]
        elif len(questions) < 5:
            for i in range(len(questions), 5):
                questions.append(create_meaningful_question(i, topic, relevant_sections))
        
        return {
            'topic': topic,
            'theory': theory,
            'questions': questions
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка поэтапной генерации: {e}")
        # Полностью резервный метод
        return create_quality_full_test(topic, relevant_sections)

def generate_contextual_theory(topic, relevant_sections):
    """Генерация теоретической справки с анализом контекста"""
    prompt = f"""
ПРОАНАЛИЗИРУЙ СОДЕРЖАНИЕ РУКОВОДСТВА И СОСТАВЬ КРАТКУЮ ТЕОРЕТИЧЕСКУЮ СПРАВКУ ПО ТЕМЕ: "{topic}"

ИСХОДНЫЙ ТЕКСТ ИЗ РУКОВОДСТВА:
{format_sections_for_analysis(relevant_sections)}

ЗАДАЧА:
1. ПРОЧИТАЙ и ПОНЯТЬ контекст каждого раздела
2. ВЫДЕЛИ основные идеи и концепции по теме "{topic}"
3. СОСТАВЬ связное объяснение (5-7 предложений), которое:
   - Объясняет СУТЬ темы, а не перечисляет факты
   - Связывает разные аспекты темы между собой
   - Использует ЕСТЕСТВЕННЫЙ язык объяснения
   - Помогает понять, КАК применять знания на практике

ПРИМЕР ПЛОХОГО ОБЪЯСНЕНИЯ (НЕ ДЕЛАЙ ТАК):
"Компьютер состоит из процессора, монитора, клавиатуры. Процессор обрабатывает информацию. Монитор показывает информацию."

ПРИМЕР ХОРОШЕГО ОБЪЯСНЕНИЯ (ДЕЛАЙ ТАК):
"Компьютер - это универсальное устройство, которое помогает автоматизировать различные задачи. С его помощью можно работать с документами, искать информацию в интернете и общаться с людьми. Основные компоненты компьютера работают вместе: процессор обрабатывает данные, монитор отображает результат, а клавиатура и мышь позволяют управлять процессами. Понимание этих основ помогает эффективно использовать компьютер в повседневной жизни."

ФОРМАТ: Просто текст объяснения, без JSON и дополнительных форматов.
"""
    
    try:
        response = gigachat_service.client.chat(prompt)
        theory = response.choices[0].message.content.strip()
        
        # Проверяем качество теории
        if len(theory) < 100 or is_low_quality_theory(theory):
            theory = create_meaningful_theory(topic, relevant_sections)
            
        return theory
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации теории: {e}")
        return create_meaningful_theory(topic, relevant_sections)

def generate_contextual_test(topic, relevant_sections):
    """Генерация теста с контекстным анализом - улучшенная версия"""
    logger.info(f"🔄 Генерация теста по теме '{topic}'...")
    
    try:
        # Пытаемся основной метод
        theory = generate_contextual_theory(topic, relevant_sections)
        questions = generate_contextual_questions(topic, relevant_sections, theory)
        
        # Проверяем качество вопросов
        quality_questions = [q for q in questions if validate_question_quality(q)]
        
        if len(quality_questions) < 5:  # Если мало качественных вопросов
            logger.warning("⚠️ Мало качественных вопросов, использую поэтапную генерацию")
            return generate_test_step_by_step(topic, relevant_sections)
        
        return {
            'topic': topic,
            'theory': theory,
            'questions': quality_questions[:10]
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка в основном методе генерации: {e}")
        # Используем резервный метод
        return generate_test_step_by_step(topic, relevant_sections)

def generate_question_batch(topic, relevant_sections, theory, question_type, count):
    """Генерация партии вопросов определенного типа - С УЛУЧШЕННЫМИ ПОЯСНЕНИЯМИ"""
    prompt = f"""
СОЗДАЙ {count} КАЧЕСТВЕННЫХ ВОПРОСОВ ДЛЯ ПРОВЕРКИ ПОНИМАНИЯ ТЕМЫ: "{topic}"

ТЕОРЕТИЧЕСКАЯ СПРАВКА:
{theory}

ТИП ВОПРОСОВ: {question_type.upper()}
{"- Вопросы на понимание сути и концепций" if question_type == "understanding" else "- Вопросы на применение знаний в практических ситуациях"}

ВАЖНЫЕ ПРАВИЛА:
1. ВОЗВРАЩАЙ ТОЛЬКО ВАЛИДНЫЙ JSON БЕЗ ЛЮБЫХ ДОПОЛНИТЕЛЬНЫХ ТЕКСТОВ
2. correct_answer ДОЛЖЕН БЫТЬ ЧИСЛОМ от 0 до 3
3. options ДОЛЖЕН СОДЕРЖАТЬ РОВНО 4 ВАРИАНТА
4. Объяснение (explanation) должно быть подробным и полезным для обучения

ТРЕБОВАНИЯ К ОБЪЯСНЕНИЯМ:
- Объяснение должно помочь понять, ПОЧЕМУ ответ правильный
- Укажите, КАКИЕ конкретно знания из руководства подтверждают ответ
- Дайте дополнительную ценную информацию по теме
- Объяснение должно быть понятным и обучающим

ФОРМАТ ОТВЕТА (ТОЛЬКО JSON):
{{
    "questions": [
        {{
            "question": "Текст вопроса...",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correct_answer": 0,
            "explanation": "Детальное объяснение, которое поможет понять материал. Укажите, почему этот ответ правильный и какие знания из руководства его подтверждают."
        }}
    ]
}}

НЕ ДОБАВЛЯЙ КОММЕНТАРИИ, ОБЪЯСНЕНИЯ ИЛИ ДРУГОЙ ТЕКСТ ВНЕ JSON СТРУКТУРЫ!
"""
    
    try:
        response = gigachat_service.client.chat(prompt)
        content = response.choices[0].message.content
        
        # Удаляем возможные markdown-обертки
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        return parse_questions_json(content)
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации вопросов типа {question_type}: {e}")
        return []

def format_sections_for_analysis(relevant_sections):
    """Форматирование разделов для контекстного анализа"""
    formatted = []
    for i, section in enumerate(relevant_sections[:3], 1):
        # Очищаем текст для лучшего понимания контекста
        clean_content = clean_text_for_context(section['content'])
        formatted.append(f"РАЗДЕЛ {i}: {section['title']}\n{clean_content}")
    
    return "\n\n".join(formatted)

def clean_text_for_context(text):
    """Очистка текста для лучшего понимания контекста"""
    # Убираем технические артефакты, оставляем смысловое содержание
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        # Убираем слишком короткие строки (возможно, артефакты)
        if len(line) < 10:
            continue
        # Убираем строки, состоящие в основном из цифр и символов
        if re.match(r'^[\d\s\.\-]+$', line):
            continue
        # Убираем повторяющиеся фразы
        if line in clean_lines:
            continue
            
        clean_lines.append(line)
    
    return ' '.join(clean_lines[:500])  # Ограничиваем длину

def parse_questions_json(content):
    """Парсинг JSON с вопросами - УЛУЧШЕННАЯ ВЕРСИЯ"""
    try:
        # Очищаем JSON более тщательно
        cleaned = clean_json_string(content)
        
        # Удаляем возможные markdown-блоки кода
        cleaned = re.sub(r'```json\s*', '', cleaned)
        cleaned = re.sub(r'```\s*', '', cleaned)
        
        # Ищем JSON структуру - более надежный метод
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        matches = re.findall(json_pattern, cleaned, re.DOTALL)
        
        if not matches:
            logger.warning("❌ JSON структура не найдена в ответе")
            return []
            
        # Пробуем каждый найденный JSON
        for json_str in matches:
            try:
                # Дополнительная очистка
                json_str = json_str.strip()
                if not json_str.startswith('{'):
                    continue
                    
                data = json.loads(json_str)
                
                # Проверяем структуру
                if 'questions' in data and isinstance(data['questions'], list):
                    questions = data['questions']
                    validated_questions = []
                    
                    for i, q in enumerate(questions):
                        if validate_question_quality(q):
                            validated_questions.append({
                                'id': i,
                                'question': q['question'],
                                'options': q['options'][:4],  # Обеспечиваем 4 варианта
                                'correct_answer': min(q.get('correct_answer', 0), 3),  # Обеспечиваем корректный индекс
                                'explanation': q.get('explanation', 'Объяснение основано на материалах руководства.')
                            })
                    
                    logger.info(f"✅ Успешно распарсено {len(validated_questions)} вопросов")
                    return validated_questions
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Ошибка декодирования JSON: {e}")
                continue
            except Exception as e:
                logger.warning(f"⚠️ Ошибка обработки JSON: {e}")
                continue
        
        logger.error("❌ Ни один JSON не прошел валидацию")
        return []
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга вопросов: {e}")
        return []

def validate_question_quality(question):
    """Валидация качества вопроса"""
    if not isinstance(question, dict):
        return False
        
    required = ['question', 'options']
    if not all(field in question for field in required):
        return False
    
    # Проверяем, что вопрос не слишком короткий
    if len(question['question']) < 10:
        return False
    
    # Проверяем, что есть варианты ответов
    options = question['options']
    if not isinstance(options, list) or len(options) != 4:
        return False
    
    # Проверяем, что варианты разные
    if len(set(options)) < 3:
        return False
    
    # Проверяем, что вопрос осмысленный (не содержит только технические термины без контекста)
    if is_meaningless_question(question['question']):
        return False
        
    return True

def is_meaningless_question(question):
    """Проверка, является ли вопрос бессмысленным"""
    meaningless_patterns = [
        r'сколько.*кнопок',
        r'какого.*цвета',
        r'что такое.*\?$',
        r'как называется.*\?$',
        r'упоминается ли.*\?$'
    ]
    
    question_lower = question.lower()
    for pattern in meaningless_patterns:
        if re.search(pattern, question_lower):
            return True
    
    return False

def is_low_quality_theory(theory):
    """Проверка качества теоретической справки"""
    # Проверяем длину
    if len(theory) < 150:
        return True
    
    # Проверяем наличие списков и перечислений (признак низкого качества)
    if theory.count('-') > 3 or theory.count('•') > 3:
        return True
    
    # Проверяем, что это не просто набор фактов
    sentences = re.split(r'[.!?]+', theory)
    if len(sentences) < 4:
        return True
    
    return False

def create_robust_question_batch(topic, relevant_sections, theory, question_type, count):
    """Создание надежной партии вопросов с обработкой ошибок"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            questions = generate_question_batch(topic, relevant_sections, theory, question_type, count)
            if questions and len(questions) >= count:
                return questions
        except Exception as e:
            logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
            if attempt == max_retries - 1:
                logger.error(f"❌ Все попытки создания вопросов типа {question_type} провалились")
    
    # Резервные вопросы
    return [create_meaningful_question(i, topic, relevant_sections) for i in range(count)]

def create_meaningful_theory(topic, relevant_sections):
    """Создание осмысленной теоретической справки вручную"""
    if not relevant_sections:
        return f"Тема '{topic}' рассматривается в руководстве по цифровой грамотности. Рекомендуется изучить соответствующие разделы для получения практических навыков."
    
    # Анализируем содержание разделов для создания осмысленного объяснения
    key_concepts = extract_key_concepts(relevant_sections, topic)
    
    if key_concepts:
        theory = f"В руководстве рассматривается тема '{topic}' в контексте {key_concepts[0]}. "
        if len(key_concepts) > 1:
            theory += f"Основное внимание уделяется {', '.join(key_concepts[1:3])}. "
        theory += "Эти знания помогут вам уверенно использовать компьютер в повседневных задачах."
    else:
        theory = f"Тема '{topic}' важна для освоения цифровой грамотности. В руководстве представлены практические рекомендации по использованию соответствующих технологий в бытовых ситуациях."
    
    return theory

def extract_key_concepts(relevant_sections, topic):
    """Извлечение ключевых концепций из разделов"""
    concepts = set()
    
    for section in relevant_sections[:2]:
        content = section['content'].lower()
        
        # Ищем смысловые конструкции
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30 and topic.lower() in sentence:
                # Извлекаем ключевые фразы
                words = re.findall(r'\b[\w]{5,}\b', sentence)
                if len(words) > 3:
                    concept = ' '.join(words[:3])
                    concepts.add(concept)
    
    return list(concepts)[:5]

def create_meaningful_question(question_id, topic, relevant_sections):
    """Создание осмысленного вопроса вручную"""
    question_types = [
        f"Как правильно использовать {topic} согласно руководству?",
        f"Что рекомендуется делать при работе с {topic}?",
        f"Какой способ работы с {topic} считается наиболее эффективным?",
        f"Что важно учитывать при использовании {topic}?",
        f"Как избежать типичных ошибок при работе с {topic}?",
        f"Для чего преимущественно используется {topic}?",
        f"Что нужно сделать перед началом работы с {topic}?",
        f"Как проверить, что {topic} работает правильно?",
        f"Что делать, если возникли проблемы с {topic}?",
        f"Какие меры безопасности важны при работе с {topic}?"
    ]
    
    question_text = question_types[question_id % len(question_types)]
    
    return {
        'id': question_id,
        'question': question_text,
        'options': [
            "Следовать рекомендациям из руководства",
            "Экспериментировать без ограничений", 
            "Обратиться к случайным источникам",
            "Прекратить использование"
        ],
        'correct_answer': 0,
        'explanation': f"Правильный ответ основан на рекомендациях из руководства по цифровой грамотности."
    }

def clean_json_string(json_string):
    """Очистка JSON строки"""
    replacements = {
        '“': '"', '”': '"', '„': '"', '«': '"', '»': '"',
        '‘': "'", '’': "'", '`': "'", '´': "'",
        '“': '"', '”': '"', '«': '"', '»': '"',
        '‘': "'", '’': "'", '`': "'",
        ' ': ' ', '\\"': '"', "\\'": "'"
    }
    
    cleaned = json_string
    for wrong, correct in replacements.items():
        cleaned = cleaned.replace(wrong, correct)
    
    return cleaned

def get_relevant_sections(topic):
    """Получение релевантных разделов из БД по теме"""
    try:
        sections = db.get_guide_sections(limit=100)
        relevant = []
        
        topic_lower = topic.lower()
        topic_words = [word for word in topic_lower.split() if len(word) > 2]
        
        logger.info(f"🔍 Поиск по теме '{topic}': проверяем {len(sections)} разделов")
        
        for section in sections:
            title = section['section_title'].lower()
            content = section['section_content'].lower()
            
            score = 0
            
            # Повышаем вес заголовков
            if topic_lower in title:
                score += 20
            if topic_lower in content:
                score += 8
                
            # Учитываем отдельные слова
            for word in topic_words:
                if word in title:
                    score += 5
                if word in content:
                    score += 2
            
            # Снижаем порог релевантности
            if score >= 1:
                relevant.append({
                    'title': section['section_title'],
                    'content': section['section_content'],
                    'score': score,
                    'page': section['page_number']
                })
        
        relevant.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"📚 По теме '{topic}' найдено разделов: {len(relevant)}")
        for section in relevant[:3]:
            logger.info(f"   - '{section['title']}' (score: {section['score']})")
        
        return relevant[:3]
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска разделов: {e}")
        return []

@app.route('/api/check-full-test', methods=['POST'])
def check_full_test():
    """Проверка всего теста из 5 вопросов"""
    try:
        data = request.get_json()
        user_answers = data.get('user_answers', [])
        test_data = data.get('test_data', {})
        
        if not user_answers or not test_data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
        
        # Проверяем каждый ответ
        results = []
        correct_count = 0
        
        for i, user_answer in enumerate(user_answers):
            question = test_data['questions'][i]
            is_correct = (user_answer == question['correct_answer'])
            
            if is_correct:
                correct_count += 1
                
            results.append({
                'question_index': i,
                'question': question['question'],
                'options': question['options'],  # Добавляем варианты ответов
                'user_answer': user_answer,
                'correct_answer': question['correct_answer'],
                'is_correct': is_correct,
                'explanation': question.get('explanation', 'Объяснение отсутствует')
            })
        
        # Считаем оценку
        total_questions = len(test_data['questions'])
        score = int((correct_count / total_questions) * 100)
        
        return jsonify({
            'status': 'success',
            'results': results,
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_questions
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки полного теста: {e}")
        return jsonify({'error': str(e)}), 500

def get_relevant_sections(topic):
    """Получение релевантных разделов из БД по теме - РАСШИРЕННАЯ ВЕРСИЯ"""
    try:
        sections = db.get_guide_sections(limit=200)  # Увеличиваем лимит
        relevant = []
        
        topic_lower = topic.lower()
        topic_words = [word for word in topic_lower.split() if len(word) > 2]
        
        logger.info(f"🔍 Расширенный поиск по теме '{topic}': проверяем {len(sections)} разделов")
        
        # Добавляем синонимы для популярных тем
        topic_synonyms = get_topic_synonyms(topic)
        all_search_terms = [topic_lower] + topic_synonyms
        
        for section in sections:
            title = section['section_title'].lower()
            content = section['section_content'].lower()
            
            score = 0
            
            # Поиск по всем терминам (основной теме и синонимам)
            for search_term in all_search_terms:
                # Повышаем вес заголовков
                if search_term in title:
                    score += 25
                if search_term in content:
                    score += 10
                    
            # Учитываем отдельные слова
            for word in topic_words:
                if word in title:
                    score += 8
                if word in content:
                    score += 3
            
            # Снижаем порог релевантности еще больше
            if score >= 1:
                relevant.append({
                    'title': section['section_title'],
                    'content': section['section_content'],
                    'score': score,
                    'page': section['page_number']
                })
        
        relevant.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"📚 По теме '{topic}' найдено разделов: {len(relevant)}")
        for section in relevant[:5]:
            logger.info(f"   - '{section['title']}' (score: {section['score']}, {len(section['content'])} chars)")
        
        return relevant[:5]  # Возвращаем топ-5 результатов
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска разделов: {e}")
        return []

def get_topic_synonyms(topic):
    """Получение синонимов и связанных терминов для темы"""
    synonyms_map = {
        'интернет': ['интернет', 'сеть', 'online', 'браузер', 'веб', 'сайт', 'проводник'],
        'компьютер': ['компьютер', 'пк', 'ноутбук', 'системный блок', 'монитор'],
        'мышь': ['мышь', 'мышка', 'курсор', 'манипулятор'],
        'клавиатура': ['клавиатура', 'клавиши', 'ввод текста'],
        'безопасность': ['безопасность', 'защита', 'антивирус', 'пароль', 'вирус'],
        'файлы': ['файлы', 'документы', 'папки', 'сохранение'],
        'программы': ['программы', 'приложения', 'софт', 'установка']
    }
    
    topic_lower = topic.lower()
    return synonyms_map.get(topic_lower, [])

def create_learning_prompt(topic, relevant_sections):
    """Создание промпта для одного урока"""
    
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
        
        # Исправляем "умные" кавычки перед парсингом JSON
        cleaned_response = clean_json_string(cleaned_response)
        
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
            explanation = create_quality_explanation(topic, relevant_sections)
        
        quiz_data = data.get('quiz')
        if not quiz_data:
            return explanation, None
            
        quiz = validate_and_fix_quiz(quiz_data, topic, relevant_sections)
        
        return explanation, quiz
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга ответа: {e}")
        return create_quality_explanation(topic, relevant_sections), create_quality_quiz(topic, relevant_sections)

def create_full_test_prompt(topic, relevant_sections):
    """Создание промпта для полного теста из 10 вопросов"""
    
    concrete_texts = []
    for i, section in enumerate(relevant_sections[:3], 1):
        concrete_text = section['content'][:800]  # Увеличиваем объем для большего контекста
        concrete_texts.append(f"РАЗДЕЛ {i} '{section['title']}':\n{concrete_text}")
    
    concrete_content = "\n\n".join(concrete_texts)
    
    prompt = f"""
    ТЫ - ЭКСПЕРТ ПО СОЗДАНИЮ ТЕСТОВ. СОЗДАЙ ТЕСТ ИЗ 5 ВОПРОСОВ ПО ТЕМЕ "{topic.upper()}".

    ИСПОЛЬЗУЙ ТОЛЬКО ЭТУ ИНФОРМАЦИЮ ИЗ РУКОВОДСТВА:

    {concrete_content}

    КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:
    1. НЕ придумывай информацию - используй ТОЛЬКО текст выше
    2. Каждый вопрос должен проверять КОНКРЕТНЫЙ факт из руководства
    3. Все 4 варианта ответа должны быть РАЗНЫМИ и ОСМЫСЛЕННЫМИ
    4. Только один вариант должен быть ПРАВИЛЬНЫМ
    5. НЕ используй общие фразы или свои знания

    СТРУКТУРА ТЕСТА:

    1. ТЕОРЕТИЧЕСКАЯ СПРАВКА (5-7 предложений):
       - Краткое объяснение темы на основе руководства
       - Используй КОНКРЕТНЫЕ факты из текста
       - Цитируй ключевые моменты

    2. 10 ВОПРОСОВ:
       - Каждый вопрос = 4 разных варианта ответа
       - Правильный ответ = точная цитата или прямое следствие из текста
       - Неправильные ответы = правдоподобные, но неверные утверждения
       - Вопросы должны охватывать РАЗНЫЕ аспекты темы

    ПРИМЕР ПРАВИЛЬНОГО ВОПРОСА:
    Вопрос: "Для чего используется клавиша Enter согласно руководству?"
    Варианты: [
        "Для подтверждения ввода команд",
        "Для удаления текста", 
        "Для включения caps lock",
        "Для вызова диспетчера задач"
    ]
    Правильный ответ: 0

    ФОРМАТ ОТВЕТА (СТРОГО СОБЛЮДАЙ):

    {{
        "theory": "Теоретическая справка с конкретными фактами из руководства...",
        "questions": [
            {{
                "question": "Вопрос 1...",
                "options": ["вариант1", "вариант2", "вариант3", "вариант4"],
                "correct_answer": 0,
                "explanation": "Объяснение с цитатой из руководства"
            }},
            {{
                "question": "Вопрос 2...",
                "options": ["вариант1", "вариант2", "вариант3", "вариант4"],
                "correct_answer": 1,
                "explanation": "Объяснение с цитатой из руководства"
            }}
            // ... еще 8 вопросов
        ]
    }}

    ВАЖНО: Должно быть РОВНО 10 вопросов с РАЗНЫМИ вариантами ответов!
    """
    
    return prompt

def parse_learning_response(response, topic, relevant_sections):
    """Принудительный парсинг ответа с проверкой на использование данных"""
    try:
        cleaned_response = response.strip()
        logger.info(f"🔧 Raw GigaChat response: {cleaned_response[:500]}...")
        
        # Исправляем "умные" кавычки перед парсингом JSON
        cleaned_response = clean_json_string(cleaned_response)
        
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
            explanation = create_quality_explanation(topic, relevant_sections)
        
        quiz_data = data.get('quiz')
        if not quiz_data:
            return explanation, None
            
        quiz = validate_and_fix_quiz(quiz_data, topic, relevant_sections)
        
        return explanation, quiz
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга ответа: {e}")
        return create_quality_explanation(topic, relevant_sections), create_quality_quiz(topic, relevant_sections)

def parse_full_test_response(response, topic, relevant_sections):
    """Парсинг ответа для полного теста - УЛУЧШЕННАЯ ВЕРСИЯ - ТЕПЕРЬ 5 ВОПРОСОВ"""
    try:
        cleaned_response = response.strip()
        cleaned_response = clean_json_string(cleaned_response)
        
        json_data = extract_json_from_text(cleaned_response)
        
        if not json_data:
            logger.error("❌ Не удалось извлечь JSON из ответа")
            return create_quality_full_test(topic, relevant_sections)
        
        theory = json_data.get('theory', '')
        questions = json_data.get('questions', [])
        
        # Проверяем качество теории
        if not theory or len(theory) < 50:
            theory = create_quality_explanation(topic, relevant_sections)
        
        # Проверяем и исправляем вопросы
        validated_questions = []
        for i, question in enumerate(questions[:5]):  # Берем максимум 5 вопросов
            try:
                validated_question = validate_question(question, i, topic, relevant_sections)
                if validated_question:
                    validated_questions.append(validated_question)
            except Exception as e:
                logger.error(f"❌ Ошибка валидации вопроса {i}: {e}")
                continue
        
        # Если вопросов меньше 5, добавляем качественные вопросы
        while len(validated_questions) < 5:  # Изменили с 10 на 5
            i = len(validated_questions)
            quality_question = create_quality_question(i, topic, relevant_sections)
            validated_questions.append(quality_question)
        
        test_data = {
            'topic': topic,
            'theory': theory,
            'questions': validated_questions[:5]  # Точно 5 вопросов
        }
        
        logger.info(f"✅ Успешно создано {len(validated_questions)} вопросов")
        return test_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга полного теста: {e}")
        return create_quality_full_test(topic, relevant_sections)
    
def extract_json_from_text(text):
    """Извлечение JSON из текста разными методами"""
    methods = [
        extract_json_direct,
        extract_json_with_regex,
        extract_json_with_ast
    ]
    
    for method in methods:
        try:
            result = method(text)
            if result:
                logger.info(f"✅ JSON извлечен методом: {method.__name__}")
                return result
        except Exception as e:
            logger.warning(f"⚠️ Метод {method.__name__} не сработал: {e}")
            continue
    
    return None

def extract_json_direct(text):
    """Прямое извлечение JSON"""
    start = text.find('{')
    end = text.rfind('}') + 1
    
    if start == -1 or end == 0:
        return None
        
    json_str = text[start:end]
    return json.loads(json_str)

def extract_json_with_regex(text):
    """Извлечение JSON с помощью регулярных выражений"""
    import re
    # Ищем структуру JSON
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match)
        except:
            continue
    
    return None

def extract_json_with_ast(text):
    """Извлечение JSON с помощью ast (для Python-подобных структур)"""
    try:
        # Пытаемся интерпретировать как Python dict
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except:
        pass
    
    return None

def clean_json_string(json_string):
    """Очистка JSON строки от 'умных' кавычек и других проблемных символов"""
    replacements = {
        '“': '"', '”': '"', '„': '"', '«': '"', '»': '"',
        '‘': "'", '’': "'", '`': "'", '´': "'",
        '“': '"', '”': '"', '«': '"', '»': '"',
        '‘': "'", '’': "'", '`': "'",
        ' ': ' ', '\\"': '"', "\\'": "'"
    }
    
    cleaned = json_string
    for wrong, correct in replacements.items():
        cleaned = cleaned.replace(wrong, correct)
    
    return cleaned

def validate_question(question, question_id, topic, relevant_sections):
    """Валидация и исправление вопроса"""
    if not isinstance(question, dict):
        return create_quality_question(question_id, topic, relevant_sections)
    
    # Проверяем обязательные поля
    required_fields = ['question', 'options', 'correct_answer']
    for field in required_fields:
        if field not in question:
            return create_quality_question(question_id, topic, relevant_sections)
    
    # Проверяем options
    options = question.get('options', [])
    if not isinstance(options, list) or len(options) != 4:
        options = create_quality_options(question_id, topic, relevant_sections)
    
    # Проверяем, что все варианты разные
    if len(set(options)) < 3:  # Минимум 3 разных варианта
        options = create_quality_options(question_id, topic, relevant_sections)
    
    # Проверяем correct_answer
    correct_answer = question.get('correct_answer', 0)
    if not isinstance(correct_answer, int) or not 0 <= correct_answer <= 3:
        correct_answer = 0
    
    return {
        'id': question_id,
        'question': question.get('question', f'Вопрос {question_id + 1} по теме "{topic}"'),
        'options': options,
        'correct_answer': correct_answer,
        'explanation': question.get('explanation', 'Объяснение основано на информации из руководства.')
    }

def create_quality_full_test(topic, relevant_sections):
    """Создание качественного теста при ошибках парсинга - ТЕПЕРЬ 5 ВОПРОСОВ"""
    questions = []
    for i in range(5):  # Изменили с 10 на 5
        questions.append(create_quality_question(i, topic, relevant_sections))
    
    return {
        'topic': topic,
        'theory': create_quality_explanation(topic, relevant_sections),
        'questions': questions
    }

def create_quality_explanation(topic, relevant_sections):
    """Создание качественного объяснения на основе данных из БД"""
    if not relevant_sections:
        return f"В руководстве есть информация по теме '{topic}', но она требует изучения."
    
    # Объединяем содержимое нескольких разделов
    explanations = []
    for section in relevant_sections[:2]:
        content = section['content']
        # Извлекаем осмысленные предложения
        sentences = re.split(r'[.!?]+', content)
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 30][:2]
        if meaningful_sentences:
            explanations.extend(meaningful_sentences)
    
    if explanations:
        explanation = " ".join(explanations[:3])
        if len(explanation) > 500:
            explanation = explanation[:500] + "..."
    else:
        # Используем первые абзацы из разделов
        explanation_parts = []
        for section in relevant_sections[:2]:
            content = section['content']
            if len(content) > 100:
                explanation_parts.append(content[:200] + "...")
        
        explanation = " ".join(explanation_parts) if explanation_parts else f"Тема '{topic}' рассматривается в руководстве по цифровой грамотности."
    
    return explanation

def create_detailed_explanation(topic, section, correct_idx):
    """Создание детального пояснения для ответа"""
    section_preview = section['content'][:150] + "..." if len(section['content']) > 150 else section['content']
    
    explanations = [
        f"✅ Этот ответ правильный, потому что он соответствует информации из раздела '{section['title']}' (страница {section['page']}). В руководстве указано: '{section_preview}'",
        
        f"📚 Правильный ответ основан на материалах руководства. В разделе '{section['title']}' на странице {section['page']} объясняется: '{section_preview}'",
        
        f"🎯 Этот вариант верный, так как он точно отражает содержание руководства. Согласно разделу '{section['title']}': '{section_preview}'",
        
        f"💡 Да, это правильный ответ! В руководстве по цифровой грамотности в разделе '{section['title']}' (стр. {section['page']}) говорится: '{section_preview}'",
        
        f"🌟 Верно! Этот ответ соответствует информации из руководства. В разделе '{section['title']}' на странице {section['page']} указано: '{section_preview}'"
    ]
    
    import random
    return random.choice(explanations)

def create_quality_question(question_id, topic, relevant_sections):
    """Создание качественного вопроса с разными вариантами ответов и пояснениями"""
    if not relevant_sections:
        return create_fallback_question(question_id, topic)
    
    # Используем разные разделы для разных вопросов
    section_index = question_id % len(relevant_sections)
    section = relevant_sections[section_index]
    content = section['content']
    
    # Извлекаем осмысленные фрагменты для вопросов и ответов
    sentences = re.split(r'[.!?]+', content)
    meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if meaningful_sentences:
        # Создаем более осмысленные варианты ответов
        correct_answer = f"Правильный вариант, основанный на информации из руководства"
        wrong_answers = [
            "Неверное утверждение, которое противоречит руководству",
            "Распространенное заблуждение, не соответствующее материалам", 
            "Неточная информация, требующая уточнения в руководстве"
        ]
        
        # Перемешиваем варианты
        import random
        options = [correct_answer] + wrong_answers
        correct_idx = 0
        
        # Создаем детальное пояснение
        explanation = create_detailed_explanation(topic, section, correct_idx)
        
    else:
        # Fallback если не нашли хороших предложений
        return create_fallback_question(question_id, topic)
    
    return {
        'id': question_id,
        'question': f'Вопрос {question_id + 1}: Что говорится в руководстве о теме "{topic}"?',
        'options': options,
        'correct_answer': correct_idx,
        'explanation': explanation
    }

def create_quality_options(question_id, topic, relevant_sections):
    """Создание качественных вариантов ответов"""
    return [
        "Правильный ответ, основанный на руководстве",
        "Неправильный вариант, не соответствующий руководству", 
        "Ошибочное утверждение, которого нет в руководстве",
        "Неверная информация, противоречащая руководству"
    ]

def create_fallback_question(question_id, topic):
    """Создание вопроса-заглушки"""
    return {
        'id': question_id,
        'question': f'Вопрос {question_id + 1} по теме "{topic}":',
        'options': [
            "Правильный вариант, соответствующий руководству",
            "Неправильный вариант",
            "Ошибочное утверждение",
            "Неверная информация"
        ],
        'correct_answer': 0,
        'explanation': 'Этот вопрос проверяет знания по указанной теме.'
    }

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
        return create_quality_quiz(topic, relevant_sections)

def create_quality_quiz(topic, relevant_sections):
    """Создаем качественный тест на основе данных"""
    first_section = relevant_sections[0] if relevant_sections else None
    
    if first_section:
        content = first_section['content']
        sentences = re.split(r'[.!?]+', content)
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        if meaningful_sentences:
            correct_answer = meaningful_sentences[0]
        else:
            correct_answer = content[:100]
        
        quiz = {
            'id': 'quality_quiz',
            'question': f'Что говорится в руководстве о теме "{topic}"?',
            'options': [
                correct_answer[:80] + "...",
                "Информация не соответствует руководству",
                "Это распространенное заблуждение", 
                "Данные отсутствуют в руководстве"
            ],
            'correct_answer': 0,
            'explanation': f'Правильный ответ основан на информации из раздела "{first_section["title"]}" руководства.'
        }
    else:
        quiz = {
            'id': 'fallback_quiz',
            'question': f'Вопрос по теме "{topic}":',
            'options': [
                "Правильный вариант",
                "Неправильный вариант",
                "Ошибочное утверждение",
                "Неверная информация"
            ],
            'correct_answer': 0,
            'explanation': 'Этот вопрос проверяет знания по указанной теме.'
        }
    
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

@app.route('/api/learn-topic', methods=['POST'])
def learn_topic():
    """Генерация только теоретического объяснения по теме - УЛУЧШЕННАЯ ВЕРСИЯ"""
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

        logger.info(f"🎯 Запрос на изучение темы: {topic}")

        # Получаем релевантные разделы из БД
        relevant_sections = get_relevant_sections(topic)
        logger.info(f"📚 Найдено релевантных разделов: {len(relevant_sections)}")
        
        if not relevant_sections:
            return jsonify({
                'status': 'error',
                'error': f'В руководстве нет информации по теме "{topic}". Попробуйте другую тему.'
            })

        # Генерируем качественное объяснение с глубоким контекстом
        logger.info("🔄 Генерация объяснения...")
        explanation = generate_deep_context_explanation(topic, relevant_sections)
        
        logger.info(f"✅ Объяснение создано: {len(explanation)} символов")
        
        return jsonify({
            'status': 'success',
            'explanation': explanation
        })

    except Exception as e:
        logger.error(f"❌ Ошибка генерации объяснения: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Произошла ошибка при создании объяснения'
        }), 500

def generate_deep_context_explanation(topic, relevant_sections):
    """Генерация глубокого контекстного объяснения - С ФОРМАТИРОВАНИЕМ"""
    
    prompt = f"""
ТЫ - ЭКСПЕРТ-ПРЕПОДАВАТЕЛЬ ПО ЦИФРОВОЙ ГРАМОТНОСТИ. ДАЙ КАЧЕСТВЕННОЕ ОБЪЯСНЕНИЕ ПО ТЕМЕ: "{topic.upper()}"

КОНКРЕТНЫЙ МАТЕРИАЛ ИЗ РУКОВОДСТВА:
{format_concrete_sections(relevant_sections)}
ТВОЯ ЗАДАЧА:
СОСТАВЬ СТРУКТУРИРОВАННОЕ ОБЪЯСНЕНИЕ С ЧЕТКОЙ СТРУКТУРОЙ:

Основная концепция:
- Кратко объясни суть темы

Как это работает:
- Опиши механизм работы
- Используй конкретные примеры из руководства

Практическое применение:
- Как именно использовать на практике
- Пошаговые рекомендации

Важные моменты:
- Ключевые аспекты для запоминания
- Частые ошибки и как их избежать

ТРЕБОВАНИЯ К ФОРМАТУ:
- Используй заголовки с двоеточием в конце
- Используй маркированные списки через дефис
- Выделяй **важные термины** двойными звездочками
- Разделяй блоки пустыми строками
- Давай конкретные примеры из руководства

ОТВЕЧАЙ ТОЛЬКО ТЕКСТОМ ОБЪЯСНЕНИЯ, без вступлений и заключений.
"""
    
    try:
        # УБЕРИТЕ max_tokens - этот параметр не поддерживается
        response = gigachat_service.client.chat(prompt)
        explanation = response.choices[0].message.content.strip()
        
        # Проверяем и улучшаем качество
        explanation = enhance_explanation_quality(explanation, topic, relevant_sections)
        
        return explanation
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации объяснения: {e}")
        return create_specific_explanation(topic, relevant_sections)

def format_concrete_sections(relevant_sections):
    """Форматирование КОНКРЕТНЫХ разделов с извлечением смысла"""
    concrete_parts = []
    
    for i, section in enumerate(relevant_sections[:4], 1):
        # Извлекаем конкретные предложения по теме
        specific_content = extract_specific_content(section['content'])
        if specific_content:
            concrete_parts.append(f"--- РАЗДЕЛ {i}: {section['title']} ---\n{specific_content}")
    
    return "\n\n".join(concrete_parts) if concrete_parts else "В разделах есть общая информация по теме."

def extract_specific_content(text):
    """Извлечение конкретного содержательного контента"""
    sentences = re.split(r'[.!?]+', text)
    relevant_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        # Отбираем только содержательные предложения
        if (len(sentence) > 25 and 
            not re.match(r'^[\\d\\s\\-\\.]+$', sentence) and
            'оглавление' not in sentence.lower() and
            'страница' not in sentence.lower()):
            relevant_sentences.append(sentence)
    
    # Ограничиваем количество, но обеспечиваем качество
    return '. '.join(relevant_sentences[:8]) + '.'

def analyze_topic_specifics(topic, relevant_sections):
    """Анализ специфики темы для лучшего контекста"""
    all_content = " ".join([section['content'] for section in relevant_sections[:3]])
    
    # Анализируем, о чем конкретно говорится в контексте темы
    analysis_parts = []
    
    # Ищем конкретные применения
    usage_patterns = [
        r'для чего (используется|применяется)[^.!?]*' + re.escape(topic),
        r'как (работает|использовать)[^.!?]*' + re.escape(topic),
        r'функции[^.!?]*' + re.escape(topic),
        topic + r' (позволяет|нужен|помогает)[^.!?]*'
    ]
    
    for pattern in usage_patterns:
        matches = re.findall(pattern, all_content.lower())
        if matches:
            analysis_parts.append(f"Найдено применение: {matches[0][:100]}...")
    
    # Ищем конкретные инструкции
    instruction_patterns = [
        r'как (настроить|установить|подключить)[^.!?]*' + re.escape(topic),
        r'правила?[^.!?]*' + re.escape(topic),
        r'советы?[^.!?]*' + re.escape(topic)
    ]
    
    for pattern in instruction_patterns:
        if re.search(pattern, all_content.lower()):
            analysis_parts.append("Есть конкретные инструкции по использованию")
            break
    
    return "; ".join(analysis_parts) if analysis_parts else "Общая информация о теме"

def enhance_explanation_quality(explanation, topic, relevant_sections):
    """Улучшение качества объяснения"""
    # Проверяем длину
    if len(explanation) < 150:
        logger.warning("⚠️ Объяснение слишком короткое, добавляем детали")
        explanation = add_specific_details(explanation, topic, relevant_sections)
    
    # Проверяем конкретику
    if not has_specific_details(explanation):
        logger.warning("⚠️ Объяснение слишком общее, добавляем конкретику")
        explanation = create_specific_explanation(topic, relevant_sections)
    
    # Очищаем текст
    explanation = clean_text_response(explanation)
    
    return explanation

def has_specific_details(text):
    """Проверка наличия конкретных деталей"""
    # Ищем конкретные глаголы и инструкции
    specific_indicators = [
        'нажать', 'выбрать', 'перетащить', 'щелкнуть', 'открыть',
        'закрыть', 'настроить', 'использовать', 'подключить',
        'левая кнопка', 'правая кнопка', 'колесико', 'курсор'
    ]
    
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in specific_indicators)

def add_specific_details(explanation, topic, relevant_sections):
    """Добавление конкретных деталей к объяснению"""
    # Извлекаем конкретные факты из разделов
    specific_facts = extract_specific_facts(topic, relevant_sections)
    
    if specific_facts:
        return explanation + " " + " ".join(specific_facts[:2])
    else:
        return create_specific_explanation(topic, relevant_sections)

def extract_specific_facts(topic, relevant_sections):
    """Извлечение конкретных фактов по теме"""
    facts = []
    
    for section in relevant_sections[:2]:
        content = section['content']
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 30 and 
                topic.lower() in sentence.lower() and
                any(keyword in sentence.lower() for keyword in ['кнопка', 'меню', 'файл', 'папка', 'окно', 'экран'])):
                facts.append(sentence)
    
    return facts[:3]  # Возвращаем не более 3 фактов

def create_specific_explanation(topic, relevant_sections):
    """Создание конкретного объяснения на основе данных"""
    if not relevant_sections:
        return f"В руководстве рассматривается тема '{topic}'. Рекомендуется изучить соответствующие разделы для получения подробной информации."
    
    # Собираем конкретные детали из разделов
    specific_details = []
    
    for section in relevant_sections[:2]:
        # Ищем предложения с конкретными действиями
        sentences = re.split(r'[.!?]+', section['content'])
        for sentence in sentences:
            if (topic.lower() in sentence.lower() and 
                len(sentence) > 40 and
                any(verb in sentence.lower() for verb in ['нажать', 'выбрать', 'открыть', 'закрыть', 'перейти'])):
                specific_details.append(sentence.strip())
    
    if specific_details:
        base = f"Согласно руководству, {topic} используется следующим образом: "
        return base + " ".join(specific_details[:2])
    else:
        # Используем заголовки разделов для контекста
        sections_context = ", ".join([section['title'] for section in relevant_sections[:2]])
        return f"Тема '{topic}' рассматривается в разделах {sections_context}. В руководстве представлены практические рекомендации по работе с этим инструментом."

def clean_text_response(text):
    """Очистка текстового ответа"""
    # Убираем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    # Убираем проблемы с кодировкой (заменяем странные символы)
    text = re.sub(r'[^\w\sа-яА-ЯёЁ.,!?;:()-]', '', text)
    return text.strip()

def format_sections_for_deep_analysis(relevant_sections):
    """Форматирование разделов для глубокого контекстного анализа"""
    formatted = []
    for i, section in enumerate(relevant_sections[:3], 1):
        # Берем больше контекста для глубокого анализа
        meaningful_content = extract_meaningful_content(section['content'])
        formatted.append(f"РАЗДЕЛ {i}: {section['title']}\n{meaningful_content}")
    
    return "\n\n" + "="*50 + "\n\n".join(formatted) + "\n" + "="*50

def extract_meaningful_content(text, max_length=800):
    """Извлечение осмысленного контента с сохранением контекста"""
    # Разбиваем на предложения
    sentences = re.split(r'[.!?]+', text)
    meaningful_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        # Отбираем содержательные предложения (не слишком короткие и не технический мусор)
        if (len(sentence) > 20 and 
            not re.match(r'^[\d\s\-\.]+$', sentence) and
            not any(word in sentence.lower() for word in ['оглавление', 'страница', 'глава'])):
            meaningful_sentences.append(sentence)
    
    # Объединяем, ограничивая длину
    result = '. '.join(meaningful_sentences[:15]) + '.'
    if len(result) > max_length:
        result = result[:max_length] + "..."
    
    return result

def clean_explanation_text(text):
    """Очистка текста объяснения от HTML и лишнего форматирования"""
    # Убираем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    # Убираем маркеры JSON
    text = re.sub(r'[{}[\]"]', '', text)
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    # Убираем фразы про JSON
    text = re.sub(r'json\s*:', '', text, flags=re.IGNORECASE)
    
    return text.strip()

def is_low_quality_explanation(explanation):
    """Проверка качества объяснения"""
    if len(explanation) < 200:
        return True
    
    # Проверяем на перечисление фактов без объяснения
    sentences = re.split(r'[.!?]+', explanation)
    if len(sentences) < 5:
        return True
    
    # Проверяем на наличие глубоких объяснительных конструкций
    deep_patterns = [
        r'помогает', r'позволяет', r'нужно чтобы', r'важно потому что',
        r'как если бы', r'представьте что', r'это похоже на'
    ]
    
    explanation_lower = explanation.lower()
    deep_matches = sum(1 for pattern in deep_patterns if re.search(pattern, explanation_lower))
    
    return deep_matches < 2

def create_quality_context_explanation(topic, relevant_sections):
    """Создание качественного контекстного объяснения на основе данных"""
    if not relevant_sections:
        return f"Тема '{topic}' рассматривается в руководстве по цифровой грамотности. Это важный аспект, который поможет вам лучше понимать работу с компьютерными технологиями."
    
    # Анализируем содержание для создания осмысленного объяснения
    context_keywords = analyze_context_keywords(relevant_sections, topic)
    
    if context_keywords:
        explanation = f"В руководстве тема '{topic}' рассматривается в контексте {context_keywords['primary_context']}. "
        explanation += f"Основное внимание уделяется {context_keywords['key_aspects']}. "
        explanation += f"Это помогает пользователям {context_keywords['practical_benefit']}. "
        explanation += "Понимание этой темы сделает работу с компьютером более комфортной и эффективной."
    else:
        explanation = f"Тема '{topic}' - важный элемент цифровой грамотности. В руководстве представлены практические рекомендации по использованию этого инструмента в повседневных задачах, что поможет вам стать более уверенным пользователем."
    
    return explanation

def analyze_context_keywords(relevant_sections, topic):
    """Анализ ключевых слов контекста"""
    all_content = " ".join([section['content'] for section in relevant_sections[:2]])
    content_lower = all_content.lower()
    
    # Ищем контекстные паттерны
    patterns = {
        'primary_context': find_primary_context(content_lower, topic),
        'key_aspects': find_key_aspects(content_lower, topic),
        'practical_benefit': find_practical_benefit(content_lower, topic)
    }
    
    return patterns

def find_primary_context(content, topic):
    """Поиск основного контекста"""
    context_indicators = [
        r'для\s+\w+\s+нужно', r'используется\s+для', r'позволяет',
        r'с\s+помощью', r'при\s+работе'
    ]
    
    for indicator in context_indicators:
        matches = re.findall(f"{indicator}[^.!?]*{topic}[^.!?]*[.!?]", content)
        if matches:
            # Берем первое совпадение и очищаем
            match = matches[0]
            return clean_context_phrase(match)
    
    return "работы с компьютером"

def find_key_aspects(content, topic):
    """Поиск ключевых аспектов"""
    # Ищем перечисления и списки
    list_indicators = [r'во-первых[^.!?]*', r'также[^.!?]*', r'кроме того[^.!?]*']
    
    aspects = []
    for indicator in list_indicators:
        pattern = f"{indicator}[^.!?]*{topic}[^.!?]*[.!?]"
        matches = re.findall(pattern, content)
        for match in matches:
            aspect = clean_context_phrase(match)
            if aspect and aspect not in aspects:
                aspects.append(aspect)
    
    if aspects:
        return ", ".join(aspects[:2])
    
    return "основным принципам и практическому применению"

def find_practical_benefit(content, topic):
    """Поиск практической пользы"""
    benefit_indicators = [
        r'помогает[^.!?]*', r'упрощает[^.!?]*', r'ускоряет[^.!?]*',
        r'позволяет[^.!?]*', r'дает возможность[^.!?]*'
    ]
    
    for indicator in benefit_indicators:
        pattern = f"{indicator}[^.!?]*{topic}[^.!?]*[.!?]"
        matches = re.findall(pattern, content)
        if matches:
            benefit = clean_context_phrase(matches[0])
            return benefit.replace(topic, "этого")
    
    return "эффективно решать повседневные задачи"

def clean_context_phrase(phrase):
    """Очистка контекстной фразы"""
    phrase = re.sub(r'\s+', ' ', phrase)
    phrase = phrase.strip()
    # Убираем слишком длинные фразы
    if len(phrase) > 100:
        words = phrase.split()
        return ' '.join(words[:15]) + '...'
    return phrase



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
    """Инициализация системы - ПРИНУДИТЕЛЬНЫЙ ПАРСИНГ"""
    logger.info("🚀 Инициализация системы тренажера...")
    
    Config.init_directories()
    
    # ПРЯМАЯ ПРОВЕРКА ФАЙЛА
    guide_path = "guide/digital_literacy_guide.pdf"
    logger.info(f"🔍 Проверка файла: {os.path.abspath(guide_path)}")
    logger.info(f"📄 Файл существует: {os.path.exists(guide_path)}")
    
    if db:
        db.init_db()
        
        from services.pdf_parser import GuideParser
        parser = GuideParser()
        
        # ПРИНУДИТЕЛЬНЫЙ ПАРСИНГ ВСЕГО PDF
        logger.info("🔄 Принудительный парсинг всего PDF...")
        db.clear_guide_data()  # Очищаем старые данные
        
        sections_count = parser.parse_guide_pdf()
        
        if sections_count > 0:
            logger.info(f"✅ PDF распарсен: {sections_count} страниц")
            
            # Проверяем сохраненные данные
            sections = db.get_guide_sections(limit=5)
            total_sections = len(db.get_guide_sections(limit=1000))
            logger.info(f"📖 Проверка БД: загружено разделов всего: {total_sections}")
            for section in sections:
                logger.info(f"   - '{section['section_title']}' ({len(section['section_content'])} chars)")
                
            # Тестовый поиск
            test_sections = get_relevant_sections("компьютер")
            logger.info(f"🔍 Тестовый поиск 'компьютер': найдено {len(test_sections)} разделов")
        else:
            logger.error("❌ Не удалось распарсить PDF")
    
    logger.info("✅ Система инициализирована")

if __name__ == '__main__':
    initialize_system()
    
    logger.info("🚀 Интерактивный тренажер запущен!")
    logger.info("🔍 Интерфейс: http://localhost:5000/")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)