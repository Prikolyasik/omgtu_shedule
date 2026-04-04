// ===== Глобальные переменные =====
let currentChangeType = 'transfer';
let selectedEntity = null;
let currentUser = null; // { role: 'student'|'teacher', user: {...} }

// ===== Проверка авторизации при загрузке =====
async function checkAuth() {
    try {
        const response = await fetch('/api/session');
        const session = await response.json();
        
        if (!session.logged_in) {
            window.location.href = '/login';
            return;
        }
        
        currentUser = {
            role: session.role,
            user: session.user
        };
        
        // Обновляем UI
        if (currentUser.user) {
            document.getElementById('userName').textContent = currentUser.user.name;
        } else {
            document.getElementById('userName').textContent = 'Студент';
        }
        
        document.getElementById('userRole').textContent = 
            currentUser.role === 'teacher' ? 'Преподаватель' : 'Студент';
        
        // Показываем вкладку "Консультации" всем
        document.getElementById('consultations-nav').style.display = 'block';
        
        // Показываем раздел "Изменения" только преподавателям
        if (currentUser.role === 'teacher') {
            document.getElementById('changes-nav').style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        window.location.href = '/login';
    }
}

// ===== Выход =====
async function doLogout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        showToast('Ошибка', 'Не удалось выйти', 'danger');
    }
}

// Запускаем проверку при загрузке
document.addEventListener('DOMContentLoaded', checkAuth);

// ===== Утилиты =====
function showToast(title, body, type = 'success') {
    document.getElementById('toastTitle').textContent = title;
    document.getElementById('toastBody').textContent = body;
    const toast = new bootstrap.Toast(document.getElementById('toast'));
    toast.show();
}

function formatDate(date) {
    return date.replace(/\./g, '-');
}

// ===== Навигация =====
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const sectionId = link.dataset.section;
        
        // Обновляем активную ссылку
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        // Показываем нужную секцию
        document.querySelectorAll('.content-section').forEach(s => s.style.display = 'none');
        document.getElementById(sectionId).style.display = 'block';
        
        // Загружаем изменения если нужно
        if (sectionId === 'changes-section') {
            loadChanges();
        }
    });
});

// ===== Поиск =====
document.getElementById('searchBtn').addEventListener('click', performSearch);
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

async function performSearch() {
    const type = document.getElementById('searchType').value;
    const term = document.getElementById('searchInput').value.trim();
    
    if (!term) {
        showToast('Ошибка', 'Введите поисковый запрос', 'danger');
        return;
    }
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, term })
        });
        
        const results = await response.json();
        
        if (results.error) {
            showToast('Ошибка', results.error, 'danger');
            return;
        }
        
        const resultsContainer = document.getElementById('searchResults');
        const resultsList = document.getElementById('searchResultsList');
        
        resultsList.innerHTML = '';
        
        if (results.length === 0) {
            resultsList.innerHTML = '<div class="list-group-item text-muted">Ничего не найдено</div>';
        } else {
            results.forEach(item => {
                const btn = document.createElement('button');
                btn.className = 'list-group-item list-group-item-action';
                btn.textContent = item.label;
                btn.onclick = () => selectSearchResult(item, type);
                resultsList.appendChild(btn);
            });
        }
        
        resultsContainer.style.display = 'block';
    } catch (error) {
        showToast('Ошибка', 'Ошибка при поиске: ' + error.message, 'danger');
    }
}

function selectSearchResult(item, type) {
    selectedEntity = { ...item, entityType: type };
    document.getElementById('dateRangeCard').style.display = 'block';
    document.getElementById('searchResults').style.display = 'none';
    
    // Устанавливаем даты по умолчанию
    const today = new Date();
    const monday = new Date(today);
    monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
    
    document.getElementById('dateFrom').value = monday.toISOString().split('T')[0];
    document.getElementById('dateTo').value = new Date(monday.getTime() + 6 * 86400000).toISOString().split('T')[0];
}

// ===== Показ расписания =====
document.getElementById('showScheduleBtn').addEventListener('click', showSchedule);

async function showSchedule() {
    if (!selectedEntity) {
        showToast('Ошибка', 'Сначала выберите группу/преподавателя/аудиторию', 'danger');
        return;
    }
    
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    if (!dateFrom || !dateTo) {
        showToast('Ошибка', 'Укажите даты', 'danger');
        return;
    }
    
    try {
        let url;
        if (selectedEntity.entityType === 'group') {
            url = `/api/schedule/group/${selectedEntity.id}?date_from=${dateFrom}&date_to=${dateTo}`;
        } else if (selectedEntity.entityType === 'lecturer') {
            url = `/api/schedule/teacher/${selectedEntity.id}?date_from=${dateFrom}&date_to=${dateTo}`;
        } else {
            url = `/api/schedule/auditory/${selectedEntity.id}?date_from=${dateFrom}&date_to=${dateTo}`;
        }
        
        const response = await fetch(url);
        const schedule = await response.json();
        
        if (schedule.error) {
            showToast('Ошибка', schedule.error, 'danger');
            return;
        }
        
        renderSchedule(schedule);
    } catch (error) {
        showToast('Ошибка', 'Ошибка при загрузке расписания: ' + error.message, 'danger');
    }
}

function renderSchedule(schedule) {
    // Группируем занятия по датам
    const days = {};
    schedule.forEach(lesson => {
        const date = lesson.date || 'unknown';
        if (!days[date]) days[date] = [];
        days[date].push(lesson);
    });
    
    const container = document.getElementById('scheduleBody');
    container.innerHTML = '';
    
    // Сортируем даты
    const sortedDates = Object.keys(days).sort();
    
    if (sortedDates.length === 0) {
        container.innerHTML = '<tr><td colspan="7" class="text-center text-muted-custom">Нет занятий</td></tr>';
    } else {
        sortedDates.forEach(date => {
            const lessons = days[date];
            
            // Создаём строку-разделитель дня
            const dayRow = document.createElement('tr');
            dayRow.innerHTML = `
                <td colspan="7" style="padding: 0;">
                    <div class="schedule-day">
                        <div class="schedule-day-header">
                            <span>
                                <span class="day-badge">${lessons.length} занятий</span>
                            </span>
                            <span class="day-date">${formatDateToDayName(date)}</span>
                        </div>
                        <div class="schedule-day-body">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th style="width: 50px;">№</th>
                                        <th>Время</th>
                                        <th>Дисциплина</th>
                                        <th>Вид работы</th>
                                        <th>Преподаватель</th>
                                        <th>Аудитория</th>
                                        <th>Подгруппа</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${lessons.map((lesson, idx) => {
                                        const changedType = lesson._changed || '';
                                        const changedBadge = changedType ? 
                                            `<span class="changed-badge ${changedType === 'отмена' ? 'cancel' : changedType === 'перенос' ? 'transfer' : changedType === 'замена пары' ? 'substitution' : changedType === 'консультация' ? 'consultation' : changedType}">${changedType}</span>` : '';
                                        
                                        const reasonText = lesson._cancel_reason ? 
                                            `<br><small style="color: var(--text-tertiary);">Причина: ${lesson._cancel_reason}</small>` : '';
                                        
                                        const roomStr = lesson.auditorium ? 
                                            `${lesson.auditorium} ${lesson.building ? `(${lesson.building})` : ''}` : '';
                                        
                                        return `
                                            <tr class="${changedType ? 'changed changed-' + (changedType === 'отмена' ? 'cancel' : changedType === 'перенос' ? 'transfer' : changedType === 'замена пары' ? 'substitution' : changedType === 'консультация' ? 'consultation' : '') : ''}">
                                                <td><span class="lesson-number">${idx + 1}</span></td>
                                                <td style="font-weight: 500; color: var(--text-primary); white-space: nowrap;">${lesson.beginLesson || ''} — ${lesson.endLesson || ''}</td>
                                                <td>${lesson.discipline || ''}${changedBadge}${reasonText}</td>
                                                <td>${lesson.kindOfWork || ''}</td>
                                                <td>${lesson.lecturer || ''}</td>
                                                <td>${roomStr}</td>
                                                <td>${lesson.subGroup || ''}</td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </td>
            `;
            container.appendChild(dayRow);
        });
    }
    
    document.getElementById('scheduleTitle').innerHTML = `<i class="bi bi-calendar-week me-2"></i>Расписание: ${selectedEntity.label}`;
    document.getElementById('scheduleCard').style.display = 'block';
}

function formatDateToDayName(dateStr) {
    // Преобразуем 2026.03.31 в "Понедельник, 31 марта 2026"
    const date = new Date(dateStr.replace(/\./g, '-'));
    const days = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
    const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    
    const dayName = days[date.getDay()];
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    
    return `${dayName}, ${day} ${month} ${year}`;
}

// ===== Отмена пары =====
setupEntitySearch('cancelGroup', 'cancelGroupResults', 'cancelGroupId', 'group');

document.getElementById('cancelDateTo').addEventListener('change', loadCancelLessons);
document.getElementById('cancelDateFrom').addEventListener('change', loadCancelLessons);

function watchCancelFields() {
    let lastGroupId = '';
    let lastDateFrom = '';
    let lastDateTo = '';
    setInterval(() => {
        const groupId = document.getElementById('cancelGroupId')?.value || '';
        const dateFrom = document.getElementById('cancelDateFrom')?.value || '';
        const dateTo = document.getElementById('cancelDateTo')?.value || '';
        if ((groupId !== lastGroupId || dateFrom !== lastDateFrom || dateTo !== lastDateTo) &&
            groupId && dateFrom && dateTo) {
            lastGroupId = groupId; lastDateFrom = dateFrom; lastDateTo = dateTo;
            loadCancelLessons();
        }
    }, 500);
}
watchCancelFields();

async function loadCancelLessons() {
    const groupId = document.getElementById('cancelGroupId').value;
    const dateFrom = document.getElementById('cancelDateFrom').value;
    const dateTo = document.getElementById('cancelDateTo').value;
    if (!groupId || !dateFrom || !dateTo) return;
    try {
        const response = await fetch(`/api/schedule/group/${groupId}?date_from=${dateFrom}&date_to=${dateTo}`);
        const schedule = await response.json();
        const select = document.getElementById('cancelLesson');
        select.innerHTML = '';
        if (schedule.length === 0) { select.innerHTML = '<option value="">Нет занятий</option>'; return; }
        schedule.forEach((lesson, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.dataset.lesson = JSON.stringify(lesson);
            option.textContent = `${lesson.date} ${lesson.beginLesson} - ${lesson.discipline} ${lesson.subGroup ? '[' + lesson.subGroup + ']' : ''}`;
            select.appendChild(option);
        });
    } catch (e) { console.error(e); }
}

document.getElementById('saveCancelBtn').addEventListener('click', async () => {
    const groupId = document.getElementById('cancelGroupId').value;
    const lessonSelect = document.getElementById('cancelLesson');
    const selectedLesson = lessonSelect.options[lessonSelect.selectedIndex]?.dataset.lesson;
    if (!groupId || !selectedLesson) { showToast('Ошибка', 'Выберите пару', 'danger'); return; }
    const lesson = JSON.parse(selectedLesson);
    const cancel = {
        type: 'cancel',
        group: document.getElementById('cancelGroup').value,
        group_id: parseInt(groupId),
        subgroup: lesson.subGroup || '',
        original_date: lesson.date,
        original_time: `${lesson.beginLesson} - ${lesson.endLesson}`,
        discipline: lesson.discipline,
        teacher: lesson.lecturer,
        auditory: lesson.auditorium,
        reason: document.getElementById('cancelReason').value.trim(),
        created_at: new Date().toISOString()
    };
    try {
        const response = await fetch('/api/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cancel)
        });
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            showToast('Ошибка сервера', text.substring(0, 200), 'danger');
            return;
        }
        const result = await response.json();
        if (result.status === 'ok') {
            showToast('Успех', result.message);
            bootstrap.Modal.getInstance(document.getElementById('cancelModal')).hide();
            document.getElementById('cancelForm').reset();
        } else {
            showToast('Ошибка', result.error || 'Не удалось сохранить', 'danger');
        }
    } catch (error) {
        showToast('Ошибка', 'Ошибка при сохранении: ' + error.message, 'danger');
    }
});

// ===== Консультации =====

// Поиск преподавателя для фильтра
setupEntitySearch('consultFilterTeacher', 'consultFilterTeacherResults', 'consultFilterTeacherId', 'lecturer');

document.getElementById('loadConsultationsBtn').addEventListener('click', loadConsultations);

async function loadConsultations() {
    try {
        const response = await fetch('/api/changes');
        const changes = await response.json();
        
        const teacherId = document.getElementById('consultFilterTeacherId')?.value || '';
        const dateFrom = document.getElementById('consultDateFrom')?.value || '';
        const dateTo = document.getElementById('consultDateTo')?.value || '';
        
        let consultations = changes.consultations || [];
        
        // Фильтруем по преподавателю
        if (teacherId) {
            consultations = consultations.filter(c => String(c.teacher_id) === teacherId);
        }
        
        // Фильтруем по датам — приводим к ISO формату для корректного сравнения
        if (dateFrom) {
            consultations = consultations.filter(c => {
                const d = (c.date || '').replace(/\./g, '-');
                return d >= dateFrom;
            });
        }
        if (dateTo) {
            consultations = consultations.filter(c => {
                const d = (c.date || '').replace(/\./g, '-');
                return d <= dateTo;
            });
        }
        
        renderConsultations(consultations);
    } catch (error) {
        showToast('Ошибка', 'Не удалось загрузить консультации', 'danger');
    }
}

function renderConsultations(consultations) {
    const container = document.getElementById('consultationsContainer');
    container.innerHTML = '';
    
    if (consultations.length === 0) {
        container.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-body text-center text-muted-custom">
                    <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                    <p class="mt-2 mb-0">Консультаций не найдено</p>
                </div>
            </div>
        `;
        return;
    }
    
    consultations.forEach(consult => {
        const card = document.createElement('div');
        card.className = 'card shadow-sm mb-3';
        
        const dateFormatted = formatDateToDayName(consult.date);
        
        card.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h6 class="mb-1" style="font-weight: 600;">
                            <i class="bi bi-person-badge me-1" style="color: var(--accent);"></i>${consult.teacher}
                        </h6>
                        <p class="text-muted-custom mb-0" style="font-size: 0.85rem;">${dateFormatted}</p>
                    </div>
                    <span style="font-size: 1.1rem; font-weight: 600; color: var(--accent);">${consult.time}</span>
                </div>
                <div class="d-flex flex-wrap gap-3 mt-2">
                    ${consult.auditory ? `
                        <div class="d-flex align-items-center">
                            <i class="bi bi-geo-alt me-1" style="color: var(--text-tertiary);"></i>
                            <span style="color: var(--text-secondary); font-size: 0.875rem;">ауд. ${consult.auditory}</span>
                        </div>
                    ` : ''}
                    ${consult.group ? `
                        <div class="d-flex align-items-center">
                            <i class="bi bi-people me-1" style="color: var(--text-tertiary);"></i>
                            <span style="color: var(--text-secondary); font-size: 0.875rem;">гр. ${consult.group}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        container.appendChild(card);
    });
}

// ===== Управление изменениями =====
document.querySelectorAll('[data-change]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-change]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentChangeType = btn.dataset.change;
    });
});

document.getElementById('addChangeBtn').addEventListener('click', () => {
    const modalMap = {
        'transfer': 'transferModal',
        'substitution': 'substitutionModal',
        'cancel': 'cancelModal',
        'consultation': 'consultationModal',
        'retake': 'retakeModal'
    };
    
    const modal = new bootstrap.Modal(document.getElementById(modalMap[currentChangeType]));
    modal.show();
});

// ===== Поиск внутри модалок =====
function setupEntitySearch(inputId, resultsId, hiddenId, type) {
    const input = document.getElementById(inputId);
    const resultsDiv = document.getElementById(resultsId);
    const hiddenInput = document.getElementById(hiddenId);
    
    if (!input) return;
    
    let debounceTimer;
    
    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const term = input.value.trim();
        
        if (term.length < 2) {
            resultsDiv.classList.remove('show');
            return;
        }
        
        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type, term })
                });
                
                const results = await response.json();
                
                if (results.length === 0) {
                    resultsDiv.innerHTML = '<div class="list-group-item text-muted">Ничего не найдено</div>';
                } else {
                    resultsDiv.innerHTML = '';
                    results.slice(0, 5).forEach(item => {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'list-group-item list-group-item-action';
                        btn.textContent = item.label;
                        btn.onclick = () => {
                            input.value = item.label;
                            hiddenInput.value = item.id;
                            resultsDiv.classList.remove('show');
                        };
                        resultsDiv.appendChild(btn);
                    });
                }
                
                resultsDiv.classList.add('show');
            } catch (error) {
                console.error('Ошибка поиска:', error);
            }
        }, 300);
    });
    
    // Закрываем результаты при клике вне
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.classList.remove('show');
        }
    });
}

// Настраиваем все поиски в модалках
setupEntitySearch('transferTeacher', 'transferTeacherResults', 'transferTeacherId', 'lecturer');
setupEntitySearch('transferGroup', 'transferGroupResults', 'transferGroupId', 'group');
setupEntitySearch('transferAuditory', 'transferAuditoryResults', 'transferAuditoryId', 'auditory');
setupEntitySearch('substitutionGroup', 'substitutionGroupResults', 'substitutionGroupId', 'group');
setupEntitySearch('substitutionNewTeacher', 'substitutionTeacherResults', 'substitutionNewTeacherId', 'lecturer');
setupEntitySearch('substitutionNewAuditory', 'substitutionAuditoryResults', 'substitutionNewAuditoryId', 'auditory');
setupEntitySearch('consultationTeacher', 'consultationTeacherResults', 'consultationTeacherId', 'lecturer');
setupEntitySearch('consultationGroup', 'consultationGroupResults', 'consultationGroupId', 'group');
setupEntitySearch('consultationAuditory', 'consultationAuditoryResults', 'consultationAuditoryId', 'auditory');
setupEntitySearch('retakeGroup', 'retakeGroupResults', 'retakeGroupId', 'group');
setupEntitySearch('retakeAuditory', 'retakeAuditoryResults', 'retakeAuditoryId', 'auditory');

// ===== Перенос пары =====
document.getElementById('transferDateTo').addEventListener('change', loadTransferLessons);
document.getElementById('transferDateFrom').addEventListener('change', loadTransferLessons);

// Перезагружаем уроки при изменении любого ключевого поля
function watchTransferFields() {
    let lastGroupId = '';
    let lastTeacherId = '';
    let lastDateFrom = '';
    let lastDateTo = '';
    
    setInterval(() => {
        const groupId = document.getElementById('transferGroupId')?.value || '';
        const teacherId = document.getElementById('transferTeacherId')?.value || '';
        const dateFrom = document.getElementById('transferDateFrom')?.value || '';
        const dateTo = document.getElementById('transferDateTo')?.value || '';
        
        if ((groupId !== lastGroupId || teacherId !== lastTeacherId || 
             dateFrom !== lastDateFrom || dateTo !== lastDateTo) &&
            groupId && teacherId && dateFrom && dateTo) {
            lastGroupId = groupId;
            lastTeacherId = teacherId;
            lastDateFrom = dateFrom;
            lastDateTo = dateTo;
            loadTransferLessons();
        }
    }, 500);
}

watchTransferFields();

async function loadTransferLessons() {
    const teacherId = document.getElementById('transferTeacherId').value;
    const groupId = document.getElementById('transferGroupId').value;
    const dateFrom = document.getElementById('transferDateFrom').value;
    const dateTo = document.getElementById('transferDateTo').value;
    
    if (!groupId || !teacherId || !dateFrom || !dateTo) return;
    
    try {
        const response = await fetch(`/api/schedule/group/${groupId}?date_from=${dateFrom}&date_to=${dateTo}`);
        const schedule = await response.json();
        
        const select = document.getElementById('transferLesson');
        select.innerHTML = '';
        
        if (schedule.length === 0) {
            select.innerHTML = '<option value="">Нет занятий</option>';
            return;
        }
        
        schedule.forEach((lesson, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.dataset.lesson = JSON.stringify(lesson);
            option.textContent = `${lesson.date} ${lesson.beginLesson} - ${lesson.discipline} ${lesson.subGroup ? '[' + lesson.subGroup + ']' : ''}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки уроков:', error);
    }
}

document.getElementById('transferNewDate').addEventListener('change', loadFreeSlots);

async function loadFreeSlots() {
    const teacherId = document.getElementById('transferTeacherId').value;
    const groupId = document.getElementById('transferGroupId').value;
    const date = document.getElementById('transferNewDate').value;
    const lessonSelect = document.getElementById('transferLesson');
    const selectedLesson = lessonSelect.options[lessonSelect.selectedIndex]?.dataset.lesson;
    
    let subgroup = '';
    if (selectedLesson) {
        try {
            subgroup = JSON.parse(selectedLesson).subGroup || '';
        } catch (e) {}
    }
    
    if (!teacherId || !groupId || !date) return;
    
    try {
        const response = await fetch(`/api/free-slots?teacher_id=${teacherId}&group_id=${groupId}&date=${date}&subgroup=${subgroup}`);
        const slots = await response.json();
        
        const select = document.getElementById('transferNewTime');
        select.innerHTML = '';
        
        if (slots.length === 0) {
            select.innerHTML = '<option value="">Нет свободных слотов</option>';
            return;
        }
        
        slots.forEach(slot => {
            const option = document.createElement('option');
            option.value = `${slot.start} - ${slot.end}`;
            option.textContent = `${slot.start} - ${slot.end} (рекомендуется)`;
            select.appendChild(option);
        });
        
        // Добавляем опцию ручного ввода
        const manualOption = document.createElement('option');
        manualOption.value = 'manual';
        manualOption.textContent = 'Ввести время вручную';
        select.appendChild(manualOption);
    } catch (error) {
        console.error('Ошибка загрузки слотов:', error);
    }
}

document.getElementById('saveTransferBtn').addEventListener('click', async () => {
    const teacherId = document.getElementById('transferTeacherId').value;
    const groupId = document.getElementById('transferGroupId').value;
    const lessonSelect = document.getElementById('transferLesson');
    const selectedLesson = lessonSelect.options[lessonSelect.selectedIndex]?.dataset.lesson;
    
    if (!teacherId || !groupId || !selectedLesson) {
        showToast('Ошибка', 'Заполните все обязательные поля', 'danger');
        return;
    }
    
    const lesson = JSON.parse(selectedLesson);
    const newTime = document.getElementById('transferNewTime').value;
    
    if (newTime === 'manual') {
        showToast('Ошибка', 'Ручной ввод времени пока не поддерживается', 'warning');
        return;
    }
    
    const transfer = {
        type: 'transfer',
        group: document.getElementById('transferGroup').value,
        group_id: parseInt(groupId),
        teacher: document.getElementById('transferTeacher').value,
        teacher_id: parseInt(teacherId),
        subgroup: lesson.subGroup || '',
        original_date: lesson.date,
        original_time: `${lesson.beginLesson} - ${lesson.endLesson}`,
        subject: lesson.discipline,
        new_date: document.getElementById('transferNewDate').value,
        new_time: newTime,
        auditory: document.getElementById('transferAuditory').value,
        created_at: new Date().toISOString()
    };
    
    try {
        const response = await fetch('/api/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(transfer)
        });

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            showToast('Ошибка сервера', text.substring(0, 200), 'danger');
            return;
        }

        const result = await response.json();

        if (result.status === 'ok') {
            showToast('Успех', result.message);
            bootstrap.Modal.getInstance(document.getElementById('transferModal')).hide();
            document.getElementById('transferForm').reset();
        } else {
            showToast('Ошибка', result.error || 'Не удалось сохранить', 'danger');
        }
    } catch (error) {
        showToast('Ошибка', 'Ошибка при сохранении: ' + error.message, 'danger');
    }
});

// ===== Замена преподавателя =====
document.getElementById('substitutionDateTo').addEventListener('change', loadSubstitutionLessons);
document.getElementById('substitutionDateFrom').addEventListener('change', loadSubstitutionLessons);

// Polling для substitution
function watchSubstitutionFields() {
    let lastGroupId = '';
    let lastDateFrom = '';
    let lastDateTo = '';
    
    setInterval(() => {
        const groupId = document.getElementById('substitutionGroupId')?.value || '';
        const dateFrom = document.getElementById('substitutionDateFrom')?.value || '';
        const dateTo = document.getElementById('substitutionDateTo')?.value || '';
        
        if ((groupId !== lastGroupId || dateFrom !== lastDateFrom || dateTo !== lastDateTo) &&
            groupId && dateFrom && dateTo) {
            lastGroupId = groupId;
            lastDateFrom = dateFrom;
            lastDateTo = dateTo;
            loadSubstitutionLessons();
        }
    }, 500);
}

watchSubstitutionFields();

async function loadSubstitutionLessons() {
    const groupId = document.getElementById('substitutionGroupId').value;
    const dateFrom = document.getElementById('substitutionDateFrom').value;
    const dateTo = document.getElementById('substitutionDateTo').value;
    
    if (!groupId || !dateFrom || !dateTo) return;
    
    try {
        const response = await fetch(`/api/schedule/group/${groupId}?date_from=${dateFrom}&date_to=${dateTo}`);
        const schedule = await response.json();
        
        const select = document.getElementById('substitutionLesson');
        select.innerHTML = '';
        
        if (schedule.length === 0) {
            select.innerHTML = '<option value="">Нет занятий</option>';
            return;
        }
        
        schedule.forEach((lesson, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.dataset.lesson = JSON.stringify(lesson);
            option.textContent = `${lesson.date} ${lesson.beginLesson} - ${lesson.discipline} | ${lesson.lecturer}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки уроков:', error);
    }
}

document.getElementById('saveSubstitutionBtn').addEventListener('click', async () => {
    const groupId = document.getElementById('substitutionGroupId').value;
    const lessonSelect = document.getElementById('substitutionLesson');
    const selectedLesson = lessonSelect.options[lessonSelect.selectedIndex]?.dataset.lesson;
    const newTeacherId = document.getElementById('substitutionNewTeacherId').value;
    
    if (!groupId || !selectedLesson || !newTeacherId) {
        showToast('Ошибка', 'Заполните все обязательные поля', 'danger');
        return;
    }
    
    const lesson = JSON.parse(selectedLesson);
    const newDate = document.getElementById('substitutionNewDate').value;
    const newTimeStart = document.getElementById('substitutionNewTimeStart').value;
    const newTimeEnd = document.getElementById('substitutionNewTimeEnd').value;
    const newDiscipline = document.getElementById('substitutionNewDiscipline').value.trim();
    
    if (!newDate || !newTimeStart || !newTimeEnd || !newDiscipline) {
        showToast('Ошибка', 'Заполните параметры заменяющей пары', 'danger');
        return;
    }
    
    const substitution = {
        type: 'substitution',
        group: document.getElementById('substitutionGroup').value,
        group_id: parseInt(groupId),
        subgroup: lesson.subGroup || '',
        original_date: lesson.date,
        original_time: `${lesson.beginLesson} - ${lesson.endLesson}`,
        original_discipline: lesson.discipline,
        original_teacher: lesson.lecturer,
        new_date: newDate,
        new_time: `${newTimeStart} - ${newTimeEnd}`,
        new_discipline: newDiscipline,
        new_teacher: document.getElementById('substitutionNewTeacher').value,
        new_teacher_id: parseInt(newTeacherId),
        new_auditory: document.getElementById('substitutionNewAuditory').value,
        created_at: new Date().toISOString()
    };
    
    try {
        const response = await fetch('/api/substitution', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(substitution)
        });
        
        const result = await response.json();
        
        if (result.status === 'ok') {
            showToast('Успех', result.message);
            bootstrap.Modal.getInstance(document.getElementById('substitutionModal')).hide();
            document.getElementById('substitutionForm').reset();
        } else {
            showToast('Ошибка', result.error || 'Не удалось сохранить', 'danger');
        }
    } catch (error) {
        showToast('Ошибка', 'Ошибка при сохранении: ' + error.message, 'danger');
    }
});

// ===== Консультация =====
document.getElementById('saveConsultationBtn').addEventListener('click', async () => {
    const teacherId = document.getElementById('consultationTeacherId').value;
    const date = document.getElementById('consultationDate').value;
    const timeStart = document.getElementById('consultationTimeStart').value;
    const timeEnd = document.getElementById('consultationTimeEnd').value;
    
    if (!teacherId || !date || !timeStart || !timeEnd) {
        showToast('Ошибка', 'Заполните все обязательные поля', 'danger');
        return;
    }
    
    const consultation = {
        type: 'consultation',
        teacher: document.getElementById('consultationTeacher').value,
        teacher_id: parseInt(teacherId),
        date,
        time: `${timeStart} - ${timeEnd}`,
        auditory: document.getElementById('consultationAuditory').value,
        group: document.getElementById('consultationGroup').value,
        group_id: document.getElementById('consultationGroupId').value ? parseInt(document.getElementById('consultationGroupId').value) : null,
        created_at: new Date().toISOString()
    };
    
    try {
        const response = await fetch('/api/consultation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(consultation)
        });
        
        const result = await response.json();
        
        if (result.status === 'ok') {
            showToast('Успех', result.message);
            bootstrap.Modal.getInstance(document.getElementById('consultationModal')).hide();
            document.getElementById('consultationForm').reset();
        } else {
            showToast('Ошибка', result.error || 'Не удалось сохранить', 'danger');
        }
    } catch (error) {
        showToast('Ошибка', 'Ошибка при сохранении: ' + error.message, 'danger');
    }
});

// ===== Пересдача =====
document.getElementById('retakeType').addEventListener('change', (e) => {
    const container = document.getElementById('retakeTeachersContainer');
    if (e.target.value === 'commission') {
        container.innerHTML = `
            <label class="form-label">Преподаватели комиссии</label>
            <div class="mb-2">
                <input type="text" class="form-control mb-2 retakeTeacherInput" placeholder="ФИО преподавателя #1" required>
                <input type="hidden" class="retakeTeacherIdInput">
                <div class="search-results-dropdown retakeTeacherResults"></div>
            </div>
            <div class="mb-2">
                <input type="text" class="form-control mb-2 retakeTeacherInput" placeholder="ФИО преподавателя #2">
                <input type="hidden" class="retakeTeacherIdInput">
                <div class="search-results-dropdown retakeTeacherResults"></div>
            </div>
            <div class="mb-2">
                <input type="text" class="form-control mb-2 retakeTeacherInput" placeholder="ФИО преподавателя #3">
                <input type="hidden" class="retakeTeacherIdInput">
                <div class="search-results-dropdown retakeTeacherResults"></div>
            </div>
        `;
        
        // Настраиваем поиск для новых полей
        container.querySelectorAll('.retakeTeacherInput').forEach((input, index) => {
            const resultsDiv = input.parentElement.querySelector('.retakeTeacherResults');
            const hiddenInput = input.parentElement.querySelector('.retakeTeacherIdInput');
            setupEntitySearchForElement(input, resultsDiv, hiddenInput, 'lecturer');
        });
    } else {
        container.innerHTML = `
            <label class="form-label">Преподаватель</label>
            <input type="text" class="form-control mb-2 retakeTeacherInput" placeholder="ФИО преподавателя" required>
            <input type="hidden" class="retakeTeacherIdInput">
            <div class="search-results-dropdown retakeTeacherResults"></div>
        `;
        
        const input = container.querySelector('.retakeTeacherInput');
        const resultsDiv = container.querySelector('.retakeTeacherResults');
        const hiddenInput = container.querySelector('.retakeTeacherIdInput');
        setupEntitySearchForElement(input, resultsDiv, hiddenInput, 'lecturer');
    }
});

function setupEntitySearchForElement(input, resultsDiv, hiddenInput, type) {
    let debounceTimer;
    
    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const term = input.value.trim();
        
        if (term.length < 2) {
            resultsDiv.classList.remove('show');
            return;
        }
        
        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type, term })
                });
                
                const results = await response.json();
                
                if (results.length === 0) {
                    resultsDiv.innerHTML = '<div class="list-group-item text-muted">Ничего не найдено</div>';
                } else {
                    resultsDiv.innerHTML = '';
                    results.slice(0, 5).forEach(item => {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'list-group-item list-group-item-action';
                        btn.textContent = item.label;
                        btn.onclick = () => {
                            input.value = item.label;
                            hiddenInput.value = item.id;
                            resultsDiv.classList.remove('show');
                        };
                        resultsDiv.appendChild(btn);
                    });
                }
                
                resultsDiv.classList.add('show');
            } catch (error) {
                console.error('Ошибка поиска:', error);
            }
        }, 300);
    });
    
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.classList.remove('show');
        }
    });
}

document.getElementById('saveRetakeBtn').addEventListener('click', async () => {
    const teacherInputs = document.querySelectorAll('.retakeTeacherInput');
    const teacherIdInputs = document.querySelectorAll('.retakeTeacherIdInput');
    const discipline = document.getElementById('retakeDiscipline').value.trim();
    
    if (!discipline) {
        showToast('Ошибка', 'Укажите дисциплину', 'danger');
        return;
    }
    
    const teachers = [];
    teacherInputs.forEach((input, index) => {
        if (input.value.trim()) {
            teachers.push({
                name: input.value.trim(),
                id: parseInt(teacherIdInputs[index].value) || null
            });
        }
    });
    
    if (teachers.length === 0) {
        showToast('Ошибка', 'Укажите хотя бы одного преподавателя', 'danger');
        return;
    }
    
    const retake = {
        type: 'retake',
        subtype: document.getElementById('retakeType').value,
        teachers,
        date: document.getElementById('retakeDate').value,
        time: `${document.getElementById('retakeTimeStart').value} - ${document.getElementById('retakeTimeEnd').value}`,
        auditory: document.getElementById('retakeAuditory').value,
        discipline,
        group: document.getElementById('retakeGroup').value,
        group_id: document.getElementById('retakeGroupId').value ? parseInt(document.getElementById('retakeGroupId').value) : null,
        created_at: new Date().toISOString()
    };
    
    try {
        const response = await fetch('/api/retake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(retake)
        });
        
        const result = await response.json();
        
        if (result.status === 'ok') {
            showToast('Успех', result.message);
            bootstrap.Modal.getInstance(document.getElementById('retakeModal')).hide();
            document.getElementById('retakeForm').reset();
        } else {
            showToast('Ошибка', result.error || 'Не удалось сохранить', 'danger');
        }
    } catch (error) {
        showToast('Ошибка', 'Ошибка при сохранении: ' + error.message, 'danger');
    }
});

// ===== Загрузка изменений =====
async function loadChanges() {
    try {
        const response = await fetch('/api/changes');
        const changes = await response.json();
        
        const container = document.getElementById('changesList');
        container.innerHTML = '';
        
        const allChanges = [
            ...changes.transfers.map(c => ({ ...c, changeType: 'transfer', label: 'Перенос' })),
            ...changes.substitutions.map(c => ({ ...c, changeType: 'substitution', label: 'Замена' })),
            ...changes.cancellations.map(c => ({ ...c, changeType: 'cancel', label: 'Отмена' })),
            ...changes.consultations.map(c => ({ ...c, changeType: 'consultation', label: 'Консультация' })),
            ...changes.retakes.map(c => ({ ...c, changeType: 'retake', label: 'Пересдача' }))
        ];
        
        if (allChanges.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">Нет сохранённых изменений</p>';
            return;
        }
        
        allChanges.forEach(change => {
            const item = document.createElement('div');
            item.className = 'change-item';
            
            let details = '';
            if (change.changeType === 'transfer') {
                details = `<strong>${change.group}</strong>: ${change.original_date} ${change.original_time} → ${change.new_date} ${change.new_time}`;
            } else if (change.changeType === 'substitution') {
                const origDisc = change.original_discipline ? change.original_discipline : '';
                const newDisc = change.new_discipline ? change.new_discipline : '';
                const origStr = `${change.original_date} ${change.original_time}${origDisc ? ' | ' + origDisc : ''}`;
                const newStr = `${change.new_date} ${change.new_time}${newDisc ? ' | ' + newDisc : ''}`;
                details = `<strong>${change.group}</strong>: ${origStr} → ${newStr}`;
            } else if (change.changeType === 'cancel') {
                const reason = change.reason ? ` | Причина: ${change.reason}` : '';
                details = `<strong>${change.group_name || change.group}</strong>: ${change.original_date} ${change.original_time} — ${change.discipline}${reason}`;
            } else if (change.changeType === 'consultation') {
                details = `<strong>${change.teacher}</strong>: ${change.date} ${change.time} (${change.auditory || 'без аудитории'})`;
            } else if (change.changeType === 'retake') {
                const tNames = change.teachers.map(t => t.name).join(', ');
                const disc = change.discipline ? ` | ${change.discipline}` : '';
                details = `<strong>[${change.subtype === 'commission' ? 'Комиссионная' : 'Обычная'}]</strong> ${change.date} ${change.time}: ${tNames}${disc}`;
            }
            
            item.innerHTML = `
                <span class="change-type ${change.changeType}">${change.label}</span>
                <div class="change-details">${details}</div>
            `;
            
            container.appendChild(item);
        });
    } catch (error) {
        container.innerHTML = '<p class="text-danger text-center">Ошибка загрузки</p>';
    }
}

// ===== Инициализация =====
(function init() {
    // Устанавливаем сегодняшнюю дату как начальную, кроме полей фильтра консультаций
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        // Не ставим дефолтные даты для фильтра консультаций
        if (input.id === 'consultDateFrom' || input.id === 'consultDateTo') return;
        if (!input.value) {
            input.value = today;
        }
    });
})();
