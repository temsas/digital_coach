// Глобальные переменные
let isProcessing = false;
let currentQuiz = null;
let currentFullTest = null;
let currentQuestionIndex = 0;
let userTestAnswers = [];

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    console.log("🎓 Интерактивный тренажер инициализирован");
    focusInput();
});

// Фокус на поле ввода
function focusInput() {
    const input = document.getElementById('messageInput');
    if (input) {
        input.focus();
    }
}

// Отправка сообщения (один урок)
async function sendMessage() {
    if (isProcessing) return;
    
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) {
        alert('Пожалуйста, введите тему для изучения');
        return;
    }

    isProcessing = true;
    updateUIForProcessing(true);
    
    try {
        // Добавляем сообщение пользователя в чат
        addMessageToChat('user', `Хочу изучить тему: "${message}"`);
        input.value = '';
        
        // Сбрасываем высоту textarea
        input.style.height = 'auto';
        
        // Отправляем запрос на сервер
        const response = await fetch('/api/learn-topic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic: message
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Добавляем объяснение помощника
            addMessageToChat('bot', data.explanation);
        } else {
            throw new Error(data.error || 'Неизвестная ошибка');
        }
        
    } catch (error) {
        console.error('❌ Ошибка отправки сообщения:', error);
        addMessageToChat('bot', '❌ ' + (error.message || 'Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.'));
    } finally {
        isProcessing = false;
        updateUIForProcessing(false);
        focusInput();
    }
}

// Обновите функцию updateUIForProcessing для нового дизайна
function updateUIForProcessing(processing, message = '') {
    const sendBtn = document.getElementById('sendBtn');
    const input = document.getElementById('messageInput');
    const statusSection = document.getElementById('statusSection');
    const statusMessage = document.getElementById('statusMessage');
    
    if (processing) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Анализирую...';
        input.disabled = true;
        
        statusMessage.textContent = message || '🔍 Анализирую руководство и готовлю объяснение...';
        statusSection.style.display = 'block';
    } else {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Изучить тему';
        input.disabled = false;
        statusSection.style.display = 'none';
    }
}

// Функция добавления сообщения в чат (оставить без изменений)
function addMessageToChat(sender, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    
    messageDiv.className = `message ${sender}-message`;
    
    if (sender === 'bot') {
        // Форматируем текст помощника
        const formattedContent = formatBotMessage(content);
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <strong>Помощник:</strong>
                </div>
                <div class="message-text">${formattedContent}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <strong>Вы:</strong>
                </div>
                <div class="message-text">${escapeHtml(content)}</div>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatBotMessage(text) {
    let safeText = escapeHtml(text);
    let formatted = safeText
        .replace(/^(.*?:)$/gm, '<div class="message-subtitle">$1</div>')
        .replace(/^(\d+\.\s+.*)$/gm, '<div class="list-item numbered">$1</div>')
        .replace(/^([-•*]\s+.*)$/gm, '<div class="list-item bulleted">$1</div>')
        .replace(/\*\*(.*?)\*\*/g, '<span class="highlight">$1</span>');
    
    // Автоматическая нумерация
    formatted = autoNumberLists(formatted);
    
    // Разбиваем на параграфы
    return formatted.split('\n\n')
        .map(paragraph => paragraph.trim() ? 
            (paragraph.includes('class="') ? paragraph : `<p>${paragraph}</p>`) : '')
        .join('')
        .replace(/\n/g, '<br>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function focusInput() {
    const input = document.getElementById('messageInput');
    if (input) {
        input.focus();
    }
}

function autoNumberLists(formattedText) {
    let numberedText = formattedText;
    let listCounter = 0;
    
    // Нумеруем пронумерованные списки
    numberedText = numberedText.replace(/<div class="list-item numbered">(\d+\.\s+.*?)<\/div>/g, 
        function(match, content) {
            listCounter++;
            return `<div class="list-item numbered" data-number="${listCounter}">${content.replace(/^\d+\.\s+/, '')}</div>`;
        }
    );
    
    return numberedText;
}

// Запуск полного теста
async function startFullTest(topic) {
    if (isProcessing) return;

    isProcessing = true;
    updateUIForProcessing(true, `Генерирую тест из 5 вопросов по теме "${topic}"...`);

    try {
        const response = await fetch('/api/generate-full-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic: topic
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentFullTest = data.test_data;
            userTestAnswers = new Array(currentFullTest.questions.length).fill(null);
            currentQuestionIndex = 0;
            
            // Переходим на экран теста
            showFullTestScreen();
        } else {
            throw new Error(data.error || 'Неизвестная ошибка');
        }
        
    } catch (error) {
        console.error('❌ Ошибка генерации теста:', error);
        alert('❌ Произошла ошибка при создании теста. Пожалуйста, попробуйте еще раз.');
    } finally {
        isProcessing = false;
        updateUIForProcessing(false);
    }
}



// Показать экран полного теста
function showFullTestScreen() {
    document.getElementById('chatScreen').classList.remove('active');
    document.getElementById('fullTestScreen').classList.add('active');
    document.getElementById('fullTestScreen').style.display = 'block';
    
    // Показываем теорию
    document.getElementById('theoryContent').innerHTML = currentFullTest.theory;
    
    // Показываем первый вопрос
    showQuestion(0);
}

// Показать вопрос
function showQuestion(index) {
    const questionsContainer = document.getElementById('testQuestions');
    questionsContainer.innerHTML = '';
    
    const question = currentFullTest.questions[index];
    
    const questionElement = document.createElement('div');
    questionElement.className = 'full-test-question';
    questionElement.innerHTML = `
        <div class="question-header">
            <h4>Вопрос ${index + 1}</h4>
            <div class="question-text">${question.question}</div>
        </div>
        <div class="question-options">
            ${question.options.map((option, optIndex) => `
                <div class="question-option ${userTestAnswers[index] === optIndex ? 'selected' : ''}" 
                     onclick="selectTestAnswer(${index}, ${optIndex})">
                    <div class="option-number">${optIndex + 1}</div>
                    <div class="option-text">${option}</div>
                </div>
            `).join('')}
        </div>
    `;
    
    questionsContainer.appendChild(questionElement);
    
    // Обновляем прогресс
    updateProgress(index);
    
    // Обновляем кнопки навигации
    updateNavigationButtons(index);
}

// Выбор ответа в тесте
function selectTestAnswer(questionIndex, answerIndex) {
    userTestAnswers[questionIndex] = answerIndex;
    
    // Обновляем отображение
    const options = document.querySelectorAll('.question-option');
    options.forEach(option => option.classList.remove('selected'));
    
    event.currentTarget.classList.add('selected');
    
    // Активируем кнопку "Далее" если это не последний вопрос
    if (questionIndex === currentQuestionIndex) {
        document.getElementById('nextBtn').disabled = false;
    }
}

// Обновление прогресса
function updateProgress(index) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    const progress = ((index + 1) / currentFullTest.questions.length) * 100;
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `Вопрос ${index + 1} из ${currentFullTest.questions.length}`; // Будет показывать "из 5"
}

// Обновление кнопок навигации
function updateNavigationButtons(index) {
    document.getElementById('prevBtn').disabled = index === 0;
    
    if (index === currentFullTest.questions.length - 1) {
        document.getElementById('nextBtn').style.display = 'none';
        document.getElementById('submitBtn').style.display = 'block';
    } else {
        document.getElementById('nextBtn').style.display = 'block';
        document.getElementById('submitBtn').style.display = 'none';
    }
    
    // Проверяем, есть ли ответ на текущий вопрос
    document.getElementById('nextBtn').disabled = userTestAnswers[index] === null;
}

// Следующий вопрос
function nextQuestion() {
    if (currentQuestionIndex < currentFullTest.questions.length - 1) {
        currentQuestionIndex++;
        showQuestion(currentQuestionIndex);
    }
}

// Предыдущий вопрос
function prevQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        showQuestion(currentQuestionIndex);
    }
}

// Отправка теста на проверку
async function submitFullTest() {
    if (isProcessing) return;
    
    // Проверяем, что на все вопросы есть ответы
    const unanswered = userTestAnswers.filter(answer => answer === null).length;
    if (unanswered > 0) {
        if (!confirm(`Вы ответили не на все вопросы. Осталось ${unanswered} без ответа. Все равно завершить тест?`)) {
            return;
        }
    }

    isProcessing = true;
    updateUIForProcessing(true, 'Проверяю ответы...');

    try {
        const response = await fetch('/api/check-full-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_answers: userTestAnswers,
                test_data: currentFullTest
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showResultsScreen(data);
        } else {
            throw new Error(data.error || 'Неизвестная ошибка');
        }
        
    } catch (error) {
        console.error('❌ Ошибка проверки теста:', error);
        alert('❌ Произошла ошибка при проверке теста.');
    } finally {
        isProcessing = false;
        updateUIForProcessing(false);
    }
}

// Показать результаты
function showResultsScreen(results) {
    document.getElementById('fullTestScreen').classList.remove('active');
    document.getElementById('resultsScreen').classList.add('active');
    document.getElementById('resultsScreen').style.display = 'block';
    
    const scoreDisplay = document.getElementById('scoreDisplay');
    const resultsDetails = document.getElementById('resultsDetails');
    
    // Отображаем оценку
    scoreDisplay.innerHTML = `
        <div class="score-circle ${results.score >= 70 ? 'good' : results.score >= 50 ? 'average' : 'poor'}">
            <div class="score-value">${results.score}%</div>
            <div class="score-label">Правильных ответов</div>
        </div>
        <div class="score-breakdown">
            <p>Правильных ответов: <strong>${results.correct_count}</strong> из ${results.total_questions}</p>
        </div>
    `;
    
    // Отображаем детали по вопросам
     resultsDetails.innerHTML = `
        <h4>Детали результатов:</h4>
        ${results.results.map((result, index) => `
            <div class="result-item ${result.is_correct ? 'correct' : 'incorrect'}">
                <div class="result-question">
                    <strong>Вопрос ${index + 1} из 5:</strong> ${result.question}
                </div>
                <!-- остальной код -->
            </div>
        `).join('')}
    `;
}


// Вернуться на главный экран
function goToMainScreen() {
    document.getElementById('resultsScreen').classList.remove('active');
    document.getElementById('resultsScreen').style.display = 'none';
    document.getElementById('chatScreen').classList.add('active');
    
    // Очищаем историю теста
    currentFullTest = null;
    userTestAnswers = [];
    currentQuestionIndex = 0;
}

// Пройти тест заново
function retryTest() {
    if (currentFullTest) {
        userTestAnswers = new Array(currentFullTest.questions.length).fill(null);
        currentQuestionIndex = 0;
        
        document.getElementById('resultsScreen').classList.remove('active');
        document.getElementById('resultsScreen').style.display = 'none';
        document.getElementById('fullTestScreen').classList.add('active');
        
        showQuestion(0);
    }
}

// Показать блок с тестом (для одного вопроса)
function showQuizSection(quiz) {
    const quizSection = document.getElementById('quizSection');
    const quizQuestion = document.getElementById('quizQuestion');
    const quizOptions = document.getElementById('quizOptions');
    
    console.log("🎯 Показываем тест:", quiz);
    
    // Очищаем предыдущие данные
    quizQuestion.innerHTML = '';
    quizOptions.innerHTML = '';
    
    // Добавляем вопрос
    const questionElement = document.createElement('div');
    questionElement.className = 'question-text';
    questionElement.textContent = quiz.question;
    quizQuestion.appendChild(questionElement);
    
    // Добавляем варианты ответов
    quiz.options.forEach((option, index) => {
        const optionElement = document.createElement('div');
        optionElement.className = 'quiz-option';
        optionElement.innerHTML = `
            <div class="option-number">${index + 1}</div>
            <div class="option-text">${option}</div>
        `;
        optionElement.onclick = () => selectQuizAnswer(index, optionElement);
        quizOptions.appendChild(optionElement);
    });
    
    // Показываем блок
    quizSection.style.display = 'block';
    
    // Прокручиваем к тесту
    quizSection.scrollIntoView({ behavior: 'smooth' });
}

// Скрыть блок с тестом
function hideQuizSection() {
    const quizSection = document.getElementById('quizSection');
    quizSection.style.display = 'none';
    currentQuiz = null;
}

// Выбор ответа в тесте (один вопрос)
async function selectQuizAnswer(answerIndex, element) {
    if (!currentQuiz) return;
    
    // Снимаем выделение со всех вариантов
    document.querySelectorAll('.quiz-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Выделяем выбранный вариант
    element.classList.add('selected');
    
    // Блокируем дальнейший выбор
    document.querySelectorAll('.quiz-option').forEach(opt => {
        opt.style.pointerEvents = 'none';
    });
    
    // Отправляем ответ на сервер
    try {
        const response = await fetch('/api/check-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                answer_index: answerIndex,
                quiz_data: currentQuiz
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Показываем результат
            showQuizResult(data.result, answerIndex);
        } else {
            throw new Error(data.error || 'Ошибка проверки ответа');
        }
        
    } catch (error) {
        console.error('❌ Ошибка проверки ответа:', error);
        addMessageToChat('bot', '❌ Произошла ошибка при проверке ответа.');
    }
}

// Показать результат теста (один вопрос)
function showQuizResult(result, selectedIndex) {
    const quizOptions = document.getElementById('quizOptions');
    const options = quizOptions.querySelectorAll('.quiz-option');
    
    // Помечаем правильные/неправильные ответы
    options.forEach((option, index) => {
        if (index === result.correct_answer) {
            option.classList.add('correct');
        } else if (index === selectedIndex && index !== result.correct_answer) {
            option.classList.add('incorrect');
        }
    });
    
    // Добавляем объяснение в чат
    addMessageToChat('bot', `
        <strong>Результат:</strong> ${result.is_correct ? '✅ Правильно!' : '❌ Неправильно'}<br><br>
        <strong>Объяснение:</strong> ${result.explanation}
    `);
    
    // Показываем кнопку для продолжения
    const continueButton = document.createElement('button');
    continueButton.className = 'continue-btn';
    continueButton.textContent = 'Изучить следующую тему →';
    continueButton.onclick = () => {
        hideQuizSection();
        focusInput();
    };
    
    quizOptions.appendChild(continueButton);
}

// Добавление сообщения в чат
function addMessageToChat(sender, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    
    messageDiv.className = `message ${sender}-message`;
    messageDiv.innerHTML = `
        <div class="message-content">
            <strong>${sender === 'user' ? 'Вы' : 'Помощник'}:</strong> ${content}
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Обновление UI во время обработки
function updateUIForProcessing(processing, message = '') {
    const sendBtn = document.getElementById('sendBtn');
    const input = document.getElementById('messageInput');
    const statusSection = document.getElementById('statusSection');
    const statusMessage = document.getElementById('statusMessage');
    
    if (processing) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Анализирую...';
        input.disabled = true;
        
        statusMessage.textContent = message || '🔍 Анализирую руководство и готовлю объяснение...';
        statusSection.style.display = 'block';
    } else {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Изучить тему';
        input.disabled = false;
        statusSection.style.display = 'none';
    }
}

// Отправка по Enter (без Shift)
document.getElementById('messageInput').addEventListener('keypress', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// Автоматическое увеличение высоты textarea
document.getElementById('messageInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

async function sendMessage() {
    if (isProcessing) return;
    
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) {
        alert('Пожалуйста, введите тему для изучения');
        return;
    }

    isProcessing = true;
    updateUIForProcessing(true);
    
    try {
        // Добавляем сообщение пользователя в чат
        addMessageToChat('user', `Хочу изучить тему: "${message}"`);
        input.value = '';
        
        // Отправляем запрос на сервер
        const response = await fetch('/api/learn-topic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic: message
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Добавляем объяснение помощника
            addMessageToChat('bot', data.explanation);
        } else {
            throw new Error(data.error || 'Неизвестная ошибка');
        }
        
    } catch (error) {
        console.error('❌ Ошибка отправки сообщения:', error);
        addMessageToChat('bot', '❌ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.');
    } finally {
        isProcessing = false;
        updateUIForProcessing(false);
        focusInput();
    }
}