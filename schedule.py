import pandas as pd
from datetime import datetime, time
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class ScheduleManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._schedule_cache: Dict[Tuple[str, str], List[Tuple[time, time, str]]] = {}
        self.days_mapping = {
            0: "Понедельник", 1: "Вторник", 2: "Среда",
            3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
        }

    def load_schedule(self) -> None:
        try:
            df = pd.read_excel(self.file_path)
            self._schedule_cache.clear()
            
            for _, row in df.iterrows():
                school_class = str(row['Класс']).strip().upper()
                day_of_week = str(row['День недели']).strip().capitalize()
                time_str = str(row['Время']).strip()
                subject = str(row['Предмет']).strip()
                
                try:
                    start_str, end_str = time_str.split('-')
                    t_start = datetime.strptime(start_str.strip(), "%H:%M").time()
                    t_end = datetime.strptime(end_str.strip(), "%H:%M").time()
                except Exception as e:
                    logger.error(f"Ошибка парсинга времени '{time_str}': {e}")
                    continue
                
                key = (school_class, day_of_week)
                if key not in self._schedule_cache:
                    self._schedule_cache[key] = []
                
                self._schedule_cache[key].append((t_start, t_end, subject))
            
            for key in self._schedule_cache:
                self._schedule_cache[key].sort(key=lambda x: x)
                
            logger.info(f"Расписание успешно загружено. Найдено классов/дней: {len(self._schedule_cache)}")
        except Exception as e:
            logger.error(f"Критическая ошибка при загрузке расписания: {e}")

    def get_all_classes(self) -> List[str]:
        classes = set(key[0] for key in self._schedule_cache.keys())
        return sorted(list(classes))

    def get_lessons_for_time(self, school_class: str, target_day: str, target_time: time) -> Tuple[Optional[str], Optional[str]]:
        key = (school_class.upper(), target_day.capitalize())
        lessons = self._schedule_cache.get(key, [])
        
        if not lessons:
            return None, None

        current_lesson = None
        next_lesson = None

        for i, (t_start, t_end, subject) in enumerate(lessons):
            if t_start <= target_time <= t_end:
                current_lesson = f"{subject} ({t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')})"
                if i + 1 < len(lessons):
                    n_start, n_end, n_subj = lessons[i+1]
                    next_lesson = f"{n_subj} ({n_start.strftime('%H:%M')}-{n_end.strftime('%H:%M')})"
                break
            elif target_time < t_start:
                next_lesson = f"{subject} ({t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')})"
                break
                
        return current_lesson, next_lesson

    def get_full_day_schedule(self, school_class: str, target_day: str) -> str:
        key = (school_class.upper(), target_day.capitalize())
        lessons = self._schedule_cache.get(key, [])
        if not lessons:
            return f"На {target_day} расписание для класса {school_class} не найдено."
        
        result = f"📅 Расписание на {target_day} ({school_class}):\n"
        for i, (t_start, t_end, subject) in enumerate(lessons, 1):
            result += f"{i}. {t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')} — {subject}\n"
        return result
