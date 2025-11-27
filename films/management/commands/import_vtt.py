from django.core.management.base import BaseCommand, CommandError
from films.models import Film, SubtitleSet, SubtitleLine
import re
import os


class Command(BaseCommand):
    help = 'Imports subtitle lines from a standard WebVTT file and links them to a film.'

    def add_arguments(self, parser):
        # Обязательные аргументы для идентификации фильма
        parser.add_argument('kinopoisk_id', type=int, help='Kinopoisk ID of the film.')
        parser.add_argument('language_code', type=str, help='Language code (e.g., "ru", "en").')
        parser.add_argument('vtt_file', type=str, help='Path to the .vtt file.')

    def _vtt_time_to_seconds(self, time_str):
        """Конвертирует строку VTT-времени (00:00:00.000) в секунды (float)."""
        try:
            # VTT использует точку для миллисекунд: 00:00:00.000
            parts = time_str.split(':')
            if len(parts) == 3:
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2])
            elif len(parts) == 2:
                # Иногда часы опускаются (00:00.000)
                h = 0.0
                m = float(parts[0])
                s = float(parts[1])
            else:
                raise ValueError("Unexpected time format.")

            return h * 3600 + m * 60 + s
        except Exception as e:
            raise ValueError(f"Invalid time format in VTT: {time_str}") from e

    def parse_vtt(self, file_path):
        """Парсит VTT файл и возвращает список словарей с данными строк, извлекая стили."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.startswith("WEBVTT"):
            raise CommandError("File is not a valid WebVTT format (must start with WEBVTT).")

        # Регулярное выражение для поиска блоков VTT
        # Ищем тайминг 00:00:00.000 --> 00:00:00.000
        vtt_pattern = re.compile(
            r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})[^\n]*\n([\s\S]*?)(?=\n\n|\Z)',
            re.MULTILINE
        )

        subtitles = []
        for match in vtt_pattern.finditer(content):
            start_time_str = match.group(1)
            end_time_str = match.group(2)
            raw_text = match.group(3).strip()

            # --- ЛОГИКА ИЗВЛЕЧЕНИЯ ИМЕНИ И СТИЛЕЙ ---

            name = None
            style_classes = None
            text = raw_text

            # 1. Извлечение Имени (<c.speaker>Имя:</c>)
            # Ищем тег <c.speaker> в начале строки
            name_match = re.search(r'^<c\.speaker>(.*?):<\/c>\s*(.*)', raw_text)
            if name_match:
                name = name_match.group(1).strip()
                # Остальной текст после имени
                text = name_match.group(2).strip()

            # 2. Извлечение Классов Стилизации (например, <c.loud>текст</c>)
            # Ищем любые теги <c.класс> и извлекаем имя класса и очищаем текст.
            # Мы будем хранить только один класс, если их несколько

            # Внимание: Эта логика упрощена. Если в строке несколько тегов <c>,
            # будет выбран только первый.
            style_match = re.search(r'<c\.(\w+)>(.*?)<\/c>', text)
            if style_match:
                style_classes = style_match.group(1).strip() # loud
                # Очищаем текст от всех <c> тегов
                text = re.sub(r'<c\.\w+>(.*?)<\/c>', r'\1', text, flags=re.DOTALL).strip()

            # Финальная очистка текста от любых оставшихся тегов
            clean_text = re.sub(r'<[^>]+>', '', text).strip()

            subtitles.append({
                'start': self._vtt_time_to_seconds(start_time_str),
                'end': self._vtt_time_to_seconds(end_time_str),
                'text': clean_text,
                'name': name,
                'style_classes': style_classes
            })
        return subtitles


    def handle(self, *args, **options):
        # Код handle остается практически без изменений
        kp_id = options['kinopoisk_id']
        lang = options['language_code']
        vtt_path = options['vtt_file']

        if not os.path.exists(vtt_path):
            raise CommandError(f'File "{vtt_path}" does not exist.')

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
                name=line_data.get('name', None),
                # Используем полученный класс стиля
                style_classes=line_data.get('style_classes', None)
            ))

        if new_lines:
            SubtitleLine.objects.bulk_create(new_lines)
            self.stdout.write(self.style.SUCCESS(f"  -> Imported {len(new_lines)} lines successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"  -> Finished, but found no lines to import."))