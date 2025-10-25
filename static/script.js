// Глобальные переменные
let isProcessing = false;
let currentQuiz = null;

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

// Отправка сообщения
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
        
        // Скрываем блок с тестом
        hideQuizSection();
        
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
            
            // Если есть тест, показываем его
            if (data.quiz) {
                currentQuiz = data.quiz;
                showQuizSection(data.quiz);
            }
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

// Показать блок с тестом
function showQuizSection(quiz) {
    const quizSection = document.getElementById('quizSection');
    const quizOptions = document.getElementById('quizOptions');
    
    // Очищаем предыдущие варианты
    quizOptions.innerHTML = '';
    
    // Добавляем новые варианты ответов
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

// Выбор ответа в тесте
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

// Показать результат теста
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
function updateUIForProcessing(processing) {
    const sendBtn = document.getElementById('sendBtn');
    const input = document.getElementById('messageInput');
    const statusSection = document.getElementById('statusSection');
    const statusMessage = document.getElementById('statusMessage');
    
    if (processing) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Генерирую урок...';
        input.disabled = true;
        
        statusMessage.textContent = '📚 Ищу информацию в руководстве и создаю урок...';
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

// Показать блок с тестом
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