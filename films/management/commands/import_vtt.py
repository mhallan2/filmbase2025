from django.core.management.base import BaseCommand, CommandError
from films.models import Film, SubtitleSet, SubtitleLine
import re
import os
import json # Для работы с JSONField

# --- РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ ---

# Находит тег спикера в строке тайминга: <v Ivonn>
SPEAKER_TAG_REGEX = re.compile(r'<v\s*([^>]+)>')
# Находит тег открытия стилей: <c.loud.bold>
STYLE_OPEN_TAG_REGEX = re.compile(r'<c\.([^>]+)>')
# Находит тег закрытия стилей: </c>
STYLE_CLOSE_TAG_REGEX = re.compile(r'<\/c>')

# ⚡ TIME_FORMAT_REGEX: Находит строку времени, включая миллисекунды (00:00:00.000 или 00:00.000)
# Используется в format_time
TIME_FORMAT_REGEX = re.compile(r'(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})')

# ⚡ КОРРЕКТНЫЙ VTT_CUE_PATTERN: захватывает блоки с опциональными часами.
# Группа 1: Начальное время (ЧЧ:)?ММ:СС.ммм
# Группа 2: Остаток строки тайминга (Конечное время + теги спикера)
# Группа 3: Текст субтитра
VTT_CUE_PATTERN = re.compile(
    # Группа 1: Начальное время. (?:...)? делает ЧЧ: опциональным
    r'((?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})[^\n]*\s+-->\s+([^\n]+)\n([\s\S]*?)(?=\n\n|\Z)',
    re.MULTILINE
)


class Command(BaseCommand):
    help = 'Imports subtitle lines from a standard WebVTT file and links them to a film.'

    def add_arguments(self, parser):
        parser.add_argument('kinopoisk_id', type=int, help='Kinopoisk ID of the film.')
        parser.add_argument('language_code', type=str, help='Language code (e.g., "ru", "en").')
        parser.add_argument('vtt_file', type=str, help='Path to the .vtt file.')

    def format_time(self, time_str):
        """Конвертирует строку VTT-времени (00:00:00.000 или 00:00.000) в секунды (float)."""

        # 1. Извлекаем только чистое время, используя TIME_FORMAT_REGEX
        time_match = TIME_FORMAT_REGEX.search(time_str)
        if not time_match:
            raise ValueError(f"Time format not found: {time_str}")

        # Используем group(0) для полного совпадения (включая минуты и секунды)
        clean_time_str = time_match.group(0).replace(',', '.')

        try:
            parts = clean_time_str.split(':')

            if len(parts) == 3: # HH:MM:SS.mmm
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2])
            elif len(parts) == 2: # MM:SS.mmm
                h = 0.0
                m = float(parts[0])
                s = float(parts[1])
            else:
                raise ValueError("Unexpected number of time parts.")

            return h * 3600 + m * 60 + s
        except Exception as e:
            raise ValueError(f"Invalid time value in VTT: {time_str}") from e

    def parse_vtt(self, file_path):
        """Парсит VTT файл и возвращает список словарей с данными строк."""
        if not os.path.exists(file_path):
            raise CommandError(f'File "{file_path}" does not exist.')

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.startswith("WEBVTT"):
            raise CommandError("File is not a valid WebVTT format (must start with WEBVTT).")

        subtitles = []

        # ⚡ ИСПОЛЬЗУЕМ КОРРЕКТНЫЙ VTT_CUE_PATTERN
        for match in VTT_CUE_PATTERN.finditer(content):
            start_time_str = match.group(1).strip()
            end_line_part = match.group(2).strip() # Время конца + возможный <v Name>
            raw_text = match.group(3).strip()

            # --- 1. Извлечение Имени (<v Name>) ---
            name = None
            name_match = SPEAKER_TAG_REGEX.search(end_line_part)
            if name_match:
                name = name_match.group(1).strip()
                # Удаляем тег спикера, чтобы получить только чистое время окончания
                end_time_str = SPEAKER_TAG_REGEX.sub('', end_line_part).strip()
            else:
                end_time_str = end_line_part

            # --- 2. Извлечение Классов Стилизации (<c.loud>) ---
            text = raw_text
            style_classes = []

            # Ищем и извлекаем все классы из открывающего тега
            for match_style in STYLE_OPEN_TAG_REGEX.finditer(text):
                class_string = match_style.group(1) # loud.bold
                style_classes.extend([c.strip() for c in class_string.split('.') if c.strip()])

            # Очищаем текст от тегов стилей VTT (<c.класс> и </c>)
            text = STYLE_OPEN_TAG_REGEX.sub('', text)
            text = STYLE_CLOSE_TAG_REGEX.sub('', text)

            # Финальная очистка текста
            clean_text = re.sub(r'<[^>]+>', '', text).strip()

            # Формируем JSON-поле style (только классы)
            style_data = {'classes': list(set(style_classes))}

            try:
                subtitles.append({
                    'start': self.format_time(start_time_str),
                    'end': self.format_time(end_time_str),
                    'text': clean_text,
                    'name': name,
                    'style_data': style_data
                })
            except ValueError as e:
                # Если ошибка времени, пропускаем блок и логируем
                self.stderr.write(f"Skipping subtitle cue due to time error: {e}")
                continue

        return subtitles


    def handle(self, *args, **options):
        kp_id = options['kinopoisk_id']
        lang = options['language_code']
        vtt_path = options['vtt_file']

        self.stdout.write(f"Start parsing VTT file: {vtt_path}")

        # 1. Парсинг VTT
        try:
            subtitles_data = self.parse_vtt(vtt_path)
        except (ValueError, CommandError) as e:
            raise CommandError(f"Error during VTT parsing: {e}")

        if not subtitles_data:
            raise CommandError("No valid subtitle cues found in the file.")

        # 2. Поиск фильма
        try:
            film = Film.objects.get(kinopoisk_id=kp_id)
        except Film.DoesNotExist:
            raise CommandError(f"Film with kinopoisk_id={kp_id} not found.")

        # 3. Создаем/обновляем Набор Субтитров
        subtitle_set, created = SubtitleSet.objects.get_or_create(
            film=film,
            language=lang
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"Processing {film.name} ({lang}): {action} set.")

        # 4. Очищаем старые строки
        subtitle_set.lines.all().delete()

        # 5. Подготавливаем и сохраняем новые строки (Bulk Create)
        new_lines = []
        for line_data in subtitles_data:
            new_lines.append(SubtitleLine(
                subtitle_set=subtitle_set,
                start_time=line_data['start'],
                end_time=line_data['end'],
                text=line_data['text'],
                # Сохраняем имя в отдельном поле
                name=line_data['name'],
                # Сохраняем классы в JSONField
                style=line_data['style_data']
            ))

        if new_lines:
            SubtitleLine.objects.bulk_create(new_lines)
            self.stdout.write(self.style.SUCCESS(f"  -> Imported {len(new_lines)} lines successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"  -> Finished, but found no lines to import."))
