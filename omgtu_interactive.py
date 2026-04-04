"""
Интерактивный парсер расписания ОмГТУ.

Позволяет:
1. Выбрать роль (студент/преподаватель)
2. Просмотреть расписание
3. Сформировать переносы/замены пар
4. Выбрать время для консультаций и пересдач
5. Проверить доступность аудиторий, групп и преподавателей
"""

import requests
from datetime import datetime, timedelta
from typing import Optional
import json
import os


class OmgtuParser:
    """Парсер расписания ОмГТУ."""

    BASE_URL = "https://rasp.omgtu.ru/api"

    # Стандартное расписание пар ОмГТУ
    STANDARD_SLOTS = [
        ("08:00", "09:30"),
        ("09:40", "11:10"),
        ("11:35", "13:05"),
        ("13:15", "14:45"),
        ("15:10", "16:40"),
        ("16:50", "18:20"),
        ("18:30", "20:00"),
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        self.changes_file = "schedule_changes.json"
        self.changes = self.load_changes()

    def load_changes(self) -> dict:
        """Загрузить сохранённые изменения из файла."""
        if os.path.exists(self.changes_file):
            try:
                with open(self.changes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"transfers": [], "substitutions": [], "consultations": [], "retakes": []}

    def save_changes(self):
        """Сохранить изменения в файл."""
        with open(self.changes_file, 'w', encoding='utf-8') as f:
            json.dump(self.changes, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] Изменения сохранены в {self.changes_file}")

    def find_group(self, name: str) -> Optional[dict]:
        """Найти группу через API поиска."""
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search",
                params={"term": name, "type": "group"},
                timeout=10
            )
            results = resp.json()
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return None

        if not results:
            print(f"❌ Группа '{name}' не найдена")
            return None
        elif len(results) == 1:
            return results[0]
        else:
            print(f"\nНайдено групп: {len(results)}")
            for i, g in enumerate(results, 1):
                print(f"  {i}. {g['label']} (ID={g['id']})")
            choice = input("\nВведи номер группы: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                return results[int(choice) - 1]
            else:
                print("Неверный номер")
                return None

    def find_teacher(self, name: str) -> Optional[dict]:
        """Найти преподавателя через API поиска."""
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search",
                params={"term": name, "type": "teacher"},
                timeout=10
            )
            results = resp.json()
            # Оставляем только тип lecturer — у них рабочий ID для расписания
            results = [r for r in results if r.get("type") == "lecturer"]
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return None

        if not results:
            print(f"❌ Преподаватель '{name}' не найден")
            return None
        elif len(results) == 1:
            return results[0]
        else:
            print(f"\nНайдено преподавателей: {len(results)}")
            for i, t in enumerate(results, 1):
                print(f"  {i}. {t['label']} (ID={t['id']})")
            choice = input("\nВведи номер: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                return results[int(choice) - 1]
            else:
                print("Неверный номер")
                return None

    def find_auditory(self, name: str) -> Optional[dict]:
        """Найти аудиторию через API поиска."""
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/search",
                params={"term": name, "type": "auditory"},
                timeout=10
            )
            results = resp.json()
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return None

        if not results:
            print(f"❌ Аудитория '{name}' не найдена")
            return None
        elif len(results) == 1:
            return results[0]
        else:
            print(f"\nНайдено аудиторий: {len(results)}")
            for i, a in enumerate(results, 1):
                print(f"  {i}. {a['label']} (ID={a['id']})")
            choice = input("\nВведи номер: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                return results[int(choice) - 1]
            else:
                print("Неверный номер")
                return None

    def get_group_schedule(
        self,
        group_id: int,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> list[dict]:
        """Получить расписание группы."""
        if not date_from:
            today = datetime.now()
            start = today - timedelta(days=today.weekday())
            date_from = start.strftime("%Y.%m.%d")
        else:
            date_from = date_from.replace("-", ".")
        if not date_to:
            date_to = (datetime.now() + timedelta(days=7)).strftime("%Y.%m.%d")
        else:
            date_to = date_to.replace("-", ".")
        params = {"start": date_from, "finish": date_to, "lng": 1}
        try:
            url = f"{self.BASE_URL}/schedule/group/{group_id}"
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Ошибка: {e}")
        return []

    def get_teacher_schedule(
        self,
        teacher_id: int,
        date_from: str,
        date_to: str
    ) -> list[dict]:
        """Получить расписание преподавателя."""
        params = {"start": date_from, "finish": date_to, "lng": 1}
        try:
            # Правильный эндпоинт — lecturer, не teacher
            url = f"{self.BASE_URL}/schedule/lecturer/{teacher_id}"
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Ошибка: {e}")
        return []

    def get_auditory_schedule(
        self,
        auditory_id: int,
        date_from: str,
        date_to: str
    ) -> list[dict]:
        """Получить расписание аудитории."""
        params = {"start": date_from, "finish": date_to, "lng": 1}
        try:
            url = f"{self.BASE_URL}/schedule/auditory/{auditory_id}"
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Ошибка: {e}")
        return []

    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Проверить пересечение двух временных интервалов."""
        return not (end1 <= start2 or start1 >= end2)

    def _subgroups_conflict(self, sub1: str, sub2: str) -> bool:
        """
        Конфликт подгрупп есть если:
        - хотя бы одна пара общая (нет подгруппы)
        - обе пары одной подгруппы
        Нет конфликта если разные подгруппы (БИТ-241/1 и БИТ-241/2).
        """
        if not sub1 or not sub2:
            return True
        return sub1 == sub2

    def apply_changes(
        self,
        schedule: list[dict],
        group_id: int = None,
        teacher_id: int = None
    ) -> list[dict]:
        """Наложить локальные изменения на расписание."""
        # Нормализуем даты — все к формату с точками (2026.03.31)
        result = []
        for lesson in schedule:
            l = dict(lesson)
            l["date"] = l.get("date", "").replace("-", ".")
            result.append(l)

        # Применяем переносы
        for change in self.changes.get("transfers", []):
            if group_id and change.get("group_id") != group_id:
                continue
            orig_date = change.get("original_date", "").replace("-", ".")
            orig_time_start = change.get("original_time", "").split(" - ")[0].strip()
            new_date = change.get("new_date", "").replace("-", ".")
            new_times = change.get("new_time", " - ").split(" - ")
            for lesson in result:
                if (lesson.get("date", "") == orig_date and
                        lesson.get("beginLesson", "") == orig_time_start):
                    lesson["date"] = new_date
                    lesson["beginLesson"] = new_times[0].strip() if len(new_times) > 0 else lesson["beginLesson"]
                    lesson["endLesson"] = new_times[1].strip() if len(new_times) > 1 else lesson["endLesson"]
                    if change.get("auditory"):
                        lesson["auditorium"] = change["auditory"]
                    lesson["_changed"] = "перенос"

        # Применяем замены пар
        for change in self.changes.get("substitutions", []):
            if group_id and change.get("group_id") != group_id:
                continue
            orig_date = change.get("original_date", "").replace("-", ".")
            orig_time_start = change.get("original_time", "").split(" - ")[0].strip()
            
            # Проверяем, это новый формат (полная замена) или старый (только преподаватель)
            if change.get("new_date") and change.get("new_time"):
                # Новый формат: полная замена пары
                new_date = change.get("new_date", "").replace("-", ".")
                new_times = change.get("new_time", " - ").split(" - ")
                new_discipline = change.get("new_discipline", "")
                new_auditory = change.get("new_auditory", "")
                
                for lesson in result:
                    if (lesson.get("date", "") == orig_date and
                            lesson.get("beginLesson", "") == orig_time_start):
                        lesson["date"] = new_date
                        lesson["beginLesson"] = new_times[0].strip() if len(new_times) > 0 else lesson["beginLesson"]
                        lesson["endLesson"] = new_times[1].strip() if len(new_times) > 1 else lesson["endLesson"]
                        if new_discipline:
                            lesson["discipline"] = new_discipline
                        if change.get("new_teacher"):
                            lesson["lecturer"] = change["new_teacher"]
                        if new_auditory:
                            lesson["auditorium"] = new_auditory
                        lesson["_changed"] = "замена пары"
            else:
                # Старый формат: только замена преподавателя
                change_time_start = change.get("time", "").split(" - ")[0].strip()
                change_date = change.get("date", "").replace("-", ".")
                for lesson in result:
                    if (lesson.get("date", "") == change_date and
                            lesson.get("beginLesson", "") == change_time_start):
                        lesson["lecturer"] = change.get("new_teacher", lesson["lecturer"])
                        lesson["_changed"] = "замена преподавателя"

        # Добавляем консультации
        for change in self.changes.get("consultations", []):
            if teacher_id and change.get("teacher_id") != teacher_id:
                continue
            if group_id and change.get("group_id") != group_id:
                continue
            times = change.get("time", " - ").split(" - ")
            result.append({
                "date": change.get("date", "").replace("-", "."),
                "beginLesson": times[0].strip() if len(times) > 0 else "",
                "endLesson": times[1].strip() if len(times) > 1 else "",
                "discipline": "Консультация",
                "kindOfWork": "Консультация",
                "lecturer": change.get("teacher", ""),
                "auditorium": change.get("auditory", ""),
                "building": "",
                "subGroup": change.get("group", ""),
                "_changed": "консультация"
            })

        # Добавляем пересдачи
        for change in self.changes.get("retakes", []):
            if group_id and change.get("group_id") != group_id:
                continue
            teacher_names = [t["name"] for t in change.get("teachers", [])]
            if teacher_id:
                teacher_ids = [t["id"] for t in change.get("teachers", [])]
                if teacher_id not in teacher_ids:
                    continue
            times = change.get("time", " - ").split(" - ")
            subtype = "Комиссионная пересдача" if change.get("subtype") == "commission" else "Пересдача"
            result.append({
                "date": change.get("date", "").replace("-", "."),
                "beginLesson": times[0].strip() if len(times) > 0 else "",
                "endLesson": times[1].strip() if len(times) > 1 else "",
                "discipline": subtype,
                "kindOfWork": subtype,
                "lecturer": ", ".join(teacher_names),
                "auditorium": change.get("auditory", ""),
                "building": "",
                "subGroup": change.get("group", ""),
                "_changed": "пересдача"
            })

        # Сортируем по дате и времени
        result.sort(key=lambda x: (x.get("date", ""), x.get("beginLesson", "")))
        return result

    def check_auditory_availability(
        self,
        auditory_id: int,
        date: str,
        time_start: str,
        time_end: str
    ) -> bool:
        """Проверить доступность аудитории в указанное время."""
        date_fmt = date.replace("-", ".")
        schedule = self.get_auditory_schedule(auditory_id, date_fmt, date_fmt)
        for lesson in schedule:
            if self._times_overlap(
                time_start, time_end,
                lesson.get("beginLesson", ""),
                lesson.get("endLesson", "")
            ):
                return False
        return True

    def check_group_availability(
        self,
        group_id: int,
        date: str,
        time_start: str,
        time_end: str,
        subgroup: str = ""
    ) -> bool:
        """Проверить доступность группы с учётом подгрупп."""
        date_fmt = date.replace("-", ".")
        schedule = self.get_group_schedule(group_id, date_fmt, date_fmt)
        for lesson in schedule:
            lesson_sub = lesson.get("subGroup", "")
            if not self._subgroups_conflict(subgroup, lesson_sub):
                continue
            if self._times_overlap(
                time_start, time_end,
                lesson.get("beginLesson", ""),
                lesson.get("endLesson", "")
            ):
                return False
        return True

    def check_teacher_availability(
        self,
        teacher_id: int,
        date: str,
        time_start: str,
        time_end: str
    ) -> bool:
        """Проверить доступность преподавателя в указанное время."""
        date_fmt = date.replace("-", ".")
        schedule = self.get_teacher_schedule(teacher_id, date_fmt, date_fmt)
        for lesson in schedule:
            if self._times_overlap(
                time_start, time_end,
                lesson.get("beginLesson", ""),
                lesson.get("endLesson", "")
            ):
                return False
        return True

    def get_free_slots(
        self,
        teacher_id: int,
        group_id: int,
        date: str,
        subgroup: str = ""
    ) -> list[tuple]:
        """
        Найти свободные стандартные слоты ОмГТУ для переноса.
        Проверяет занятость преподавателя и группы (с учётом подгрупп).
        Возвращает список (time_start, time_end).
        """
        date_fmt = date.replace("-", ".")
        teacher_schedule = self.get_teacher_schedule(teacher_id, date_fmt, date_fmt)
        group_schedule = self.get_group_schedule(group_id, date_fmt, date_fmt)

        # Занятые интервалы преподавателя
        teacher_busy = [
            (l.get("beginLesson", ""), l.get("endLesson", ""))
            for l in teacher_schedule
            if l.get("beginLesson") and l.get("endLesson")
        ]

        # Занятые интервалы группы с учётом подгрупп
        group_busy = [
            (l.get("beginLesson", ""), l.get("endLesson", ""))
            for l in group_schedule
            if l.get("beginLesson") and l.get("endLesson")
            and self._subgroups_conflict(subgroup, l.get("subGroup", ""))
        ]

        free_slots = []
        for t_start, t_end in self.STANDARD_SLOTS:
            teacher_free = not any(self._times_overlap(t_start, t_end, s, e) for s, e in teacher_busy)
            group_free = not any(self._times_overlap(t_start, t_end, s, e) for s, e in group_busy)
            if teacher_free and group_free:
                free_slots.append((t_start, t_end))

        return free_slots

    def add_transfer(self, transfer: dict):
        self.changes["transfers"].append(transfer)
        self.save_changes()

    def add_substitution(self, substitution: dict):
        self.changes["substitutions"].append(substitution)
        self.save_changes()

    def add_consultation(self, consultation: dict):
        self.changes["consultations"].append(consultation)
        self.save_changes()

    def add_retake(self, retake: dict):
        self.changes["retakes"].append(retake)
        self.save_changes()


def print_schedule(schedule: list[dict], name: str, entity_type: str = "group"):
    """Вывести расписание."""
    if not schedule:
        print("Расписание не найдено")
        return

    print(f"\n{'='*60}")
    print(f"  Расписание: {name}")
    print(f"{'='*60}")

    current_date = None
    for lesson in schedule:
        date = lesson.get("date", "")
        if date != current_date:
            current_date = date
            print(f"\n📅 {date}")
            print("-" * 60)

        time_str = f"{lesson.get('beginLesson', '')} - {lesson.get('endLesson', '')}"
        subject = lesson.get("discipline", lesson.get("lessonName", "N/A"))
        kind = lesson.get("kindOfWork", "")
        teacher = lesson.get("lecturer", "")
        auditorium = lesson.get("auditorium", "")
        building = lesson.get("building", "")
        room_str = f"{auditorium} ({building})" if auditorium else ""

        # Подгруппа для студента, группа для преподавателя
        sub = lesson.get("subGroup", "")
        if entity_type == "teacher":
            extra_str = f" | гр. {sub}" if sub else ""
        else:
            extra_str = f" | подгр. {sub}" if sub else ""

        changed = lesson.get("_changed", "")
        changed_str = f" ⚠️  [{changed}]" if changed else ""

        print(f"  {time_str:15} | {subject}{changed_str}")
        parts = [p for p in [kind, teacher, f"ауд. {room_str}" if room_str else ""] if p]
        if parts:
            print(f"                  {' | '.join(parts)}{extra_str}")


def show_transfers_menu(parser: OmgtuParser):
    """Меню переноса пары с рекомендацией свободных слотов."""
    print("\n" + "=" * 60)
    print("  ПЕРЕНОС ПАРЫ")
    print("=" * 60)

    teacher_name = input("Введите фамилию преподавателя: ").strip()
    teacher = parser.find_teacher(teacher_name)
    if not teacher:
        return

    group_name = input("Введите название группы: ").strip()
    group = parser.find_group(group_name)
    if not group:
        return

    date_from = input("Дата начала периода (ГГГГ-ММ-ДД): ").strip()
    date_to = input("Дата конца периода (ГГГГ-ММ-ДД): ").strip()

    schedule = parser.get_group_schedule(group["id"], date_from, date_to)
    print_schedule(schedule, group["label"])

    if not schedule:
        print("Нет занятий в указанном периоде")
        return

    print("\nНомера пар:")
    for i, lesson in enumerate(schedule, 1):
        sub = lesson.get("subGroup", "")
        sub_str = f" [{sub}]" if sub else ""
        print(f"  {i}. {lesson.get('date')} {lesson.get('beginLesson')} - {lesson.get('discipline', '')}{sub_str}")

    lesson_idx = input("\nВведите номер пары для переноса: ").strip()
    if not lesson_idx.isdigit() or int(lesson_idx) < 1 or int(lesson_idx) > len(schedule):
        print("Неверный номер")
        return

    lesson = schedule[int(lesson_idx) - 1]
    subgroup = lesson.get("subGroup", "")

    new_date = input("\nНа какой день перенести? (ГГГГ-ММ-ДД): ").strip()

    # Ищем свободные стандартные слоты
    print(f"\nИщу свободные окошки на {new_date}...")
    free_slots = parser.get_free_slots(teacher["id"], group["id"], new_date, subgroup)

    new_time_start = ""
    new_time_end = ""

    if free_slots:
        print(f"\n✅ Свободные слоты ({len(free_slots)} из {len(parser.STANDARD_SLOTS)}):")
        for i, (t_start, t_end) in enumerate(free_slots, 1):
            print(f"  {i}. {t_start} - {t_end}")
        print(f"  0. Ввести время вручную")

        slot_choice = input("\nВыберите номер слота (или 0 для ручного ввода): ").strip()

        if slot_choice == "0":
            new_time_start = input("Время начала (ЧЧ:ММ): ").strip()
            new_time_end = input("Время конца (ЧЧ:ММ): ").strip()
            # Проверяем конфликты для вручную введённого времени
            if not parser.check_teacher_availability(teacher["id"], new_date, new_time_start, new_time_end):
                print(f"❌ Преподаватель {teacher['label']} занят в это время!")
                if input("Продолжить? (д/н): ").strip().lower() != 'д':
                    return
            if not parser.check_group_availability(group["id"], new_date, new_time_start, new_time_end, subgroup):
                print(f"❌ Группа {group['label']} занята в это время!")
                if input("Продолжить? (д/н): ").strip().lower() != 'д':
                    return
        elif slot_choice.isdigit() and 1 <= int(slot_choice) <= len(free_slots):
            new_time_start, new_time_end = free_slots[int(slot_choice) - 1]
            print(f"[OK] Выбрано: {new_time_start} - {new_time_end}")
        else:
            print("Неверный выбор")
            return
    else:
        print(f"\n❌ Свободных стандартных слотов на {new_date} нет")
        print("Можно ввести время вручную:")
        new_time_start = input("Время начала (ЧЧ:ММ): ").strip()
        new_time_end = input("Время конца (ЧЧ:ММ): ").strip()
        if not parser.check_teacher_availability(teacher["id"], new_date, new_time_start, new_time_end):
            print(f"⚠️  Преподаватель занят в это время!")
        if not parser.check_group_availability(group["id"], new_date, new_time_start, new_time_end, subgroup):
            print(f"⚠️  Группа занята в это время!")
        if input("Всё равно сохранить? (д/н): ").strip().lower() != 'д':
            return

    # Аудитория (опционально)
    auditory_name = input("\nВведите название аудитории (Enter чтобы пропустить): ").strip()
    auditory = None
    if auditory_name:
        auditory = parser.find_auditory(auditory_name)
        if auditory:
            if not parser.check_auditory_availability(auditory["id"], new_date, new_time_start, new_time_end):
                print(f"❌ Аудитория {auditory['label']} занята в это время!")
                if input("Продолжить? (д/н): ").strip().lower() != 'д':
                    return

    transfer = {
        "type": "transfer",
        "group": group["label"],
        "group_id": group["id"],
        "teacher": teacher["label"],
        "teacher_id": teacher["id"],
        "subgroup": subgroup,
        "original_date": lesson.get("date", ""),
        "original_time": f"{lesson.get('beginLesson', '')} - {lesson.get('endLesson', '')}",
        "subject": lesson.get("discipline", ""),
        "new_date": new_date.replace("-", "."),
        "new_time": f"{new_time_start} - {new_time_end}",
        "auditory": auditory["label"] if auditory else "",
        "created_at": datetime.now().isoformat()
    }

    parser.add_transfer(transfer)
    print("\n[OK] Перенос добавлен")


def show_substitutions_menu(parser: OmgtuParser):
    """Меню замены преподавателя с проверкой занятости."""
    print("\n" + "=" * 60)
    print("  ЗАМЕНА ПАРЫ")
    print("=" * 60)

    group_name = input("Введите название группы: ").strip()
    group = parser.find_group(group_name)
    if not group:
        return

    date_from = input("Дата начала периода (ГГГГ-ММ-ДД): ").strip()
    date_to = input("Дата конца периода (ГГГГ-ММ-ДД): ").strip()

    schedule = parser.get_group_schedule(group["id"], date_from, date_to)
    print_schedule(schedule, group["label"])

    if not schedule:
        print("Нет занятий в указанном периоде")
        return

    print("\nНомера пар:")
    for i, lesson in enumerate(schedule, 1):
        sub = lesson.get("subGroup", "")
        sub_str = f" [{sub}]" if sub else ""
        print(f"  {i}. {lesson.get('date')} {lesson.get('beginLesson')} - {lesson.get('discipline', '')} | {lesson.get('lecturer', '')}{sub_str}")

    lesson_idx = input("\nВведите номер пары для замены: ").strip()
    if not lesson_idx.isdigit() or int(lesson_idx) < 1 or int(lesson_idx) > len(schedule):
        print("Неверный номер")
        return

    lesson = schedule[int(lesson_idx) - 1]
    subgroup = lesson.get("subGroup", "")
    lesson_date = lesson.get("date", "")
    lesson_start = lesson.get("beginLesson", "")
    lesson_end = lesson.get("endLesson", "")

    print(f"\nТекущий преподаватель: {lesson.get('lecturer', '')}")
    new_teacher_name = input("Новый преподаватель (ФИО): ").strip()
    new_teacher = parser.find_teacher(new_teacher_name)
    if not new_teacher:
        return

    # Проверяем доступность нового преподавателя
    if not parser.check_teacher_availability(new_teacher["id"], lesson_date, lesson_start, lesson_end):
        print(f"❌ Преподаватель {new_teacher['label']} занят в это время!")
        # Показываем его расписание на этот день
        day_sched = parser.get_teacher_schedule(
            new_teacher["id"],
            lesson_date.replace("-", "."),
            lesson_date.replace("-", ".")
        )
        if day_sched:
            print(f"\nРасписание {new_teacher['label']} на {lesson_date}:")
            for l in day_sched:
                print(f"  {l.get('beginLesson')} - {l.get('endLesson')} | {l.get('discipline', '')}")

        # Предлагаем рекомендуемую замену — ищем свободных преподавателей той же кафедры
        print(f"\nПопробуйте найти другого преподавателя.")
        if input("Продолжить с этим преподавателем? (д/н): ").strip().lower() != 'д':
            return

    substitution = {
        "type": "substitution",
        "group": group["label"],
        "group_id": group["id"],
        "subgroup": subgroup,
        "date": lesson_date,
        "time": f"{lesson_start} - {lesson_end}",
        "subject": lesson.get("discipline", ""),
        "original_teacher": lesson.get("lecturer", ""),
        "new_teacher": new_teacher["label"],
        "new_teacher_id": new_teacher["id"],
        "created_at": datetime.now().isoformat()
    }

    parser.add_substitution(substitution)
    print("\n[OK] Замена добавлена")


def show_consultations_menu(parser: OmgtuParser):
    """Меню консультаций."""
    print("\n" + "=" * 60)
    print("  КОНСУЛЬТАЦИИ")
    print("=" * 60)

    teacher_name = input("Введите ФИО преподавателя: ").strip()
    teacher = parser.find_teacher(teacher_name)
    if not teacher:
        return

    group_name = input("Введите название группы: ").strip()
    group = parser.find_group(group_name)

    date = input("\nДата консультации (ГГГГ-ММ-ДД): ").strip()

    # Ищем свободные слоты для консультации
    if group:
        print(f"\nИщу свободные слоты на {date}...")
        free_slots = parser.get_free_slots(teacher["id"], group["id"], date)
        if free_slots:
            print(f"\n✅ Свободные слоты:")
            for i, (t_start, t_end) in enumerate(free_slots, 1):
                print(f"  {i}. {t_start} - {t_end}")
            print(f"  0. Ввести время вручную")
            slot_choice = input("\nВыберите номер слота (или 0): ").strip()
            if slot_choice.isdigit() and 1 <= int(slot_choice) <= len(free_slots):
                time_start, time_end = free_slots[int(slot_choice) - 1]
            else:
                time_start = input("Время начала (ЧЧ:ММ): ").strip()
                time_end = input("Время конца (ЧЧ:ММ): ").strip()
        else:
            print("Свободных слотов нет, введите время вручную:")
            time_start = input("Время начала (ЧЧ:ММ): ").strip()
            time_end = input("Время конца (ЧЧ:ММ): ").strip()
    else:
        time_start = input("Время начала (ЧЧ:ММ): ").strip()
        time_end = input("Время конца (ЧЧ:ММ): ").strip()

    # Проверяем преподавателя
    if not parser.check_teacher_availability(teacher["id"], date, time_start, time_end):
        print(f"❌ Преподаватель {teacher['label']} занят в это время!")
        if input("Продолжить? (д/н): ").strip().lower() != 'д':
            return

    auditory_name = input("\nВведите название аудитории: ").strip()
    auditory = parser.find_auditory(auditory_name)
    if auditory:
        if not parser.check_auditory_availability(auditory["id"], date, time_start, time_end):
            print(f"❌ Аудитория {auditory['label']} занята в это время!")
            if input("Продолжить? (д/н): ").strip().lower() != 'д':
                return

    consultation = {
        "type": "consultation",
        "teacher": teacher["label"],
        "teacher_id": teacher["id"],
        "date": date,
        "time": f"{time_start} - {time_end}",
        "auditory": auditory["label"] if auditory else "",
        "group": group["label"] if group else "",
        "group_id": group["id"] if group else None,
        "created_at": datetime.now().isoformat()
    }

    parser.add_consultation(consultation)
    print("\n[OK] Консультация добавлена")


def show_retakes_menu(parser: OmgtuParser):
    """Меню пересдач."""
    print("\n" + "=" * 60)
    print("  ПЕРЕСДАЧИ")
    print("=" * 60)

    print("\nТип пересдачи:")
    print("  1. Обычная (один преподаватель)")
    print("  2. Комиссионная (несколько преподавателей)")
    retake_type = input("\nВаш выбор: ").strip()

    if retake_type == "1":
        teacher_name = input("Введите ФИО преподавателя: ").strip()
        teacher = parser.find_teacher(teacher_name)
        if not teacher:
            return
        teachers = [teacher]
    elif retake_type == "2":
        teachers = []
        print("\nВведите преподавателей комиссии (до 3 человек)")
        for i in range(3):
            teacher_name = input(f"Преподаватель #{i+1} (ФИО, пустая строка для завершения): ").strip()
            if not teacher_name:
                break
            teacher = parser.find_teacher(teacher_name)
            if teacher:
                teachers.append(teacher)
        if not teachers:
            print("Не указано ни одного преподавателя")
            return
    else:
        print("Неверный выбор")
        return

    group_name = input("\nВведите название группы: ").strip()
    group = parser.find_group(group_name)

    date = input("\nДата пересдачи (ГГГГ-ММ-ДД): ").strip()

    # Ищем свободные слоты для всех преподавателей сразу
    if group and teachers:
        print(f"\nИщу слоты когда свободны все преподаватели и группа...")
        # Начинаем с полного списка слотов и пересекаем
        free_slots = set(parser.STANDARD_SLOTS)
        for t in teachers:
            teacher_slots = set(parser.get_free_slots(t["id"], group["id"], date))
            free_slots &= teacher_slots
        free_slots = sorted(free_slots)

        if free_slots:
            print(f"\n✅ Общие свободные слоты ({len(free_slots)}):")
            for i, (t_start, t_end) in enumerate(free_slots, 1):
                print(f"  {i}. {t_start} - {t_end}")
            print(f"  0. Ввести время вручную")
            slot_choice = input("\nВыберите номер слота (или 0): ").strip()
            if slot_choice.isdigit() and 1 <= int(slot_choice) <= len(free_slots):
                time_start, time_end = free_slots[int(slot_choice) - 1]
                print(f"[OK] Выбрано: {time_start} - {time_end}")
            else:
                time_start = input("Время начала (ЧЧ:ММ): ").strip()
                time_end = input("Время конца (ЧЧ:ММ): ").strip()
        else:
            print("Общих свободных слотов нет, введите время вручную:")
            time_start = input("Время начала (ЧЧ:ММ): ").strip()
            time_end = input("Время конца (ЧЧ:ММ): ").strip()
    else:
        time_start = input("Время начала (ЧЧ:ММ): ").strip()
        time_end = input("Время конца (ЧЧ:ММ): ").strip()

    # Предупреждаем о занятых преподавателях
    for t in teachers:
        if not parser.check_teacher_availability(t["id"], date, time_start, time_end):
            print(f"⚠️  Преподаватель {t['label']} занят в это время!")

    auditory_name = input("\nВведите название аудитории: ").strip()
    auditory = parser.find_auditory(auditory_name)
    if auditory:
        if not parser.check_auditory_availability(auditory["id"], date, time_start, time_end):
            print(f"⚠️  Аудитория {auditory['label']} занята в это время!")

    students = []
    print("\nВведите студентов (минимум 2)")
    for i in range(10):
        student_name = input(f"Студент #{i+1} (ФИО, пустая строка для завершения): ").strip()
        if not student_name:
            break
        students.append(student_name)

    if len(students) < 2:
        print("❌ Нужно минимум 2 студента")
        return

    retake = {
        "type": "retake",
        "subtype": "normal" if retake_type == "1" else "commission",
        "teachers": [{"name": t["label"], "id": t["id"]} for t in teachers],
        "date": date,
        "time": f"{time_start} - {time_end}",
        "auditory": auditory["label"] if auditory else "",
        "students": students,
        "group": group["label"] if group else "",
        "group_id": group["id"] if group else None,
        "created_at": datetime.now().isoformat()
    }

    parser.add_retake(retake)
    print("\n[OK] Пересдача добавлена")


def show_changes_menu(parser: OmgtuParser):
    """Показать все сохранённые изменения."""
    print("\n" + "=" * 60)
    print("  СОХРАНЁННЫЕ ИЗМЕНЕНИЯ")
    print("=" * 60)

    changes = parser.changes

    print(f"\n📋 Переносы пар: {len(changes['transfers'])}")
    for i, t in enumerate(changes["transfers"], 1):
        print(f"  {i}. {t['group']}: {t['original_date']} {t['original_time']} → {t['new_date']} {t['new_time']}")

    print(f"\n🔄 Замены преподавателей: {len(changes['substitutions'])}")
    for i, s in enumerate(changes["substitutions"], 1):
        print(f"  {i}. {s['group']}: {s['original_teacher']} → {s['new_teacher']} ({s['date']})")

    print(f"\n💬 Консультации: {len(changes['consultations'])}")
    for i, c in enumerate(changes["consultations"], 1):
        print(f"  {i}. {c['teacher']}: {c['date']} {c['time']} ({c.get('auditory', '')})")

    print(f"\n📝 Пересдачи: {len(changes['retakes'])}")
    for i, r in enumerate(changes["retakes"], 1):
        t_names = ", ".join([t["name"] for t in r["teachers"]])
        students = ", ".join(r["students"])
        print(f"  {i}. [{r['subtype']}] {r['date']} {r['time']}: {t_names} | Студенты: {students}")


def student_menu(parser: OmgtuParser):
    """Меню для студента."""
    print("\n" + "=" * 60)
    print("  МЕНЮ СТУДЕНТА")
    print("=" * 60)

    while True:
        print("\n1. Найти группу и показать расписание")
        print("2. Показать сохранённые изменения")
        print("0. Назад")

        choice = input("\nВаш выбор: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            search = input("Введите название группы: ").strip()
            found = parser.find_group(search)
            if not found:
                continue
            today = datetime.now()
            start = today - timedelta(days=today.weekday())
            finish = start + timedelta(days=6)
            schedule = parser.get_group_schedule(
                found["id"],
                start.strftime("%Y.%m.%d"),
                finish.strftime("%Y.%m.%d")
            )
            schedule = parser.apply_changes(schedule, group_id=found["id"])
            print_schedule(schedule, found["label"])
        elif choice == "2":
            show_changes_menu(parser)
        else:
            print("Неверный выбор")


def teacher_menu(parser: OmgtuParser):
    """Меню для преподавателя."""
    print("\n" + "=" * 60)
    print("  МЕНЮ ПРЕПОДАВАТЕЛЯ")
    print("=" * 60)

    while True:
        print("\n1. Показать моё расписание")
        print("2. Найти преподавателя и показать расписание")
        print("3. Перенос пары")
        print("4. Замена пары")
        print("5. Консультации")
        print("6. Пересдачи")
        print("7. Показать сохранённые изменения")
        print("0. Назад")

        choice = input("\nВаш выбор: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            search = input("Введите вашу фамилию: ").strip()
            found = parser.find_teacher(search)
            if not found:
                continue
            today = datetime.now()
            start = today - timedelta(days=today.weekday())
            finish = start + timedelta(days=30)
            schedule = parser.get_teacher_schedule(
                found["id"],
                start.strftime("%Y.%m.%d"),
                finish.strftime("%Y.%m.%d")
            )
            schedule = parser.apply_changes(schedule, teacher_id=found["id"])
            print_schedule(schedule, found["label"], "teacher")
        elif choice == "2":
            search = input("Введите фамилию преподавателя: ").strip()
            found = parser.find_teacher(search)
            if not found:
                continue
            today = datetime.now()
            start = today - timedelta(days=today.weekday())
            finish = start + timedelta(days=30)
            schedule = parser.get_teacher_schedule(
                found["id"],
                start.strftime("%Y.%m.%d"),
                finish.strftime("%Y.%m.%d")
            )
            schedule = parser.apply_changes(schedule, teacher_id=found["id"])
            print_schedule(schedule, found["label"], "teacher")
        elif choice == "3":
            show_transfers_menu(parser)
        elif choice == "4":
            show_substitutions_menu(parser)
        elif choice == "5":
            show_consultations_menu(parser)
        elif choice == "6":
            show_retakes_menu(parser)
        elif choice == "7":
            show_changes_menu(parser)
        else:
            print("Неверный выбор")


def main():
    parser = OmgtuParser()

    print("=" * 60)
    print("  ПАРСЕР РАСПИСАНИЯ ОМГТУ")
    print("=" * 60)

    while True:
        print("\nВыберите вашу роль:")
        print("  1. Студент")
        print("  2. Преподаватель")
        print("  0. Выход")

        role_choice = input("\nВаш выбор: ").strip()

        if role_choice == "0":
            print("Выход...")
            break
        elif role_choice == "1":
            student_menu(parser)
        elif role_choice == "2":
            teacher_menu(parser)
        else:
            print("Неверный выбор")


if __name__ == "__main__":
    main()