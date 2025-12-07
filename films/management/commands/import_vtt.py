from django.core.management.base import BaseCommand, CommandError
from films.models import Film, SubtitleSet, SubtitleLine
from django.db import transaction
import re
import os

# Регулярки
# Извлечение временных диапазонов в WebVTT (поддерживает HH:MM:SS.mmm и MM:SS.mmm)
VTT_CUE_PATTERN = re.compile(
    r'((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})\s*\n(.*?)(?=\n{2,}|\Z)',
    re.DOTALL | re.IGNORECASE
)

# <v Speaker>
SPEAKER_TAG_REGEX = re.compile(r'<v\s+([^>]+)>', re.IGNORECASE)

# <c.class1.class2>...<\/c>
C_TAG_REGEX = re.compile(r'<c\.([^>]+)>', re.IGNORECASE)

# Удаление всех HTML-тегов (после того, как мы убрали <c> и <v>)
HTML_TAG_REGEX = re.compile(r'</?[^>]+>', re.DOTALL)

# Поддержка BOM
BOM = '\ufeff'


def vtt_time_to_seconds(time_str: str) -> float:
    """
    Преобразует VTT время (HH:MM:SS.mmm или MM:SS.mmm) в секунды float.
    Принимает и запятые, и точки в дробной части.
    """
    t = time_str.strip().replace(',', '.')
    parts = t.split(':')
    try:
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            raise ValueError("Unexpected time format")
    except Exception as e:
        raise ValueError(f"Invalid time value: '{time_str}' ({e})") from e


class Command(BaseCommand):
    help = 'Import subtitles from a WebVTT file and attach to a film (by kinopoisk_id).'

    def add_arguments(self, parser):
        parser.add_argument('kinopoisk_id', type=int, help='Kinopoisk ID of the film.')
        parser.add_argument('language_code', type=str, help='Language code (e.g. "ru", "en").')
        parser.add_argument('vtt_file', type=str, help='Path to the .vtt file.')

    def parse_vtt(self, content: str):
        """
        Возвращает список dict: {start, end, text, name, style_classes}
        """
        # Убираем BOM, ведущие пробелы
        if content.startswith(BOM):
            content = content.lstrip(BOM)

        # Нормализуем переводы строки
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Простейшая проверка
        if not content.strip().upper().startswith("WEBVTT"):
            raise ValueError("File does not start with WEBVTT header.")

        # Обрезаем заголовок до первого двойного переноса строки (если есть)
        # Это пригодно, если в начале есть мета/комментарии
        # Но не обрезаем все — мы парсим cues в любом случае
        subtitles = []

        for match in VTT_CUE_PATTERN.finditer(content):
            start_raw = match.group(1).strip()
            end_raw = match.group(2).strip()
            block_text = match.group(3).strip() if match.group(3) else ""

            # Извлекаем спикера <v Name> (если есть) — берем первое вхождение
            name = None
            speaker_search = SPEAKER_TAG_REGEX.search(block_text)
            if speaker_search:
                name = speaker_search.group(1).strip()
                # удаляем только первый тег <v ...>
                block_text = SPEAKER_TAG_REGEX.sub('', block_text, count=1)

            # Извлекаем все <c.xxx> теги: они дают список классов, разделённых точкой
            classes = []
            for c_match in C_TAG_REGEX.finditer(block_text):
                cls_list = c_match.group(1).strip()
                if cls_list:
                    # <c.bold.italic> -> ['bold','italic']
                    parts = [p.strip() for p in cls_list.split('.') if p.strip()]
                    classes.extend(parts)

            # Удаляем теги <c.xxx> и любые остальные теги
            block_text = C_TAG_REGEX.sub('', block_text)
            # Удаляем закрывающие </c> и закрывающие </v> и др.
            block_text = HTML_TAG_REGEX.sub('', block_text)

            # Очищаем пробелы и лишние пустые строки внутри cue
            clean_text = '\n'.join([line.strip() for line in block_text.splitlines() if line.strip()])

            try:
                start_sec = vtt_time_to_seconds(start_raw)
                end_sec = vtt_time_to_seconds(end_raw)
            except ValueError as e:
                # Пропускаем некорректный cue, но логируем в stderr
                self.stderr.write(f"Skipping cue due to time parse error: {e}")
                continue

            # Пропускаем пустые тексты
            if not clean_text:
                # иногда cue может быть только NOTE или пустым — пропускаем
                continue

            # Собираем и добавляем подсказку
            subtitles.append({
                'start': start_sec,
                'end': end_sec,
                'text': clean_text,
                'name': name or None,
                # сохраняем уникальные классы в строке через пробел
                'style_classes': ' '.join(sorted(set(classes))) if classes else ''
            })

        return subtitles

    def handle(self, *args, **options):
        kinopoisk_id = options['kinopoisk_id']
        language_code = (options['language_code'] or '').strip().lower()
        vtt_file = options['vtt_file']

        if not language_code:
            raise CommandError("Language code is required.")

        if not os.path.exists(vtt_file):
            raise CommandError(f"File not found: {vtt_file}")

        # Найдём фильм
        try:
            film = Film.objects.get(kinopoisk_id=kinopoisk_id)
        except Film.DoesNotExist:
            raise CommandError(f"Film with kinopoisk_id={kinopoisk_id} not found.")

        self.stdout.write(f"Importing VTT for film {film.name} (lang={language_code}) from {vtt_file}...")

        with open(vtt_file, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            parsed = self.parse_vtt(content)
        except ValueError as e:
            raise CommandError(f"VTT parse error: {e}")

        if not parsed:
            raise CommandError("No cues found in the VTT file.")

        # Создаём или получаем SubtitleSet (language в lowercase)
        with transaction.atomic():
            subtitle_set, created = SubtitleSet.objects.get_or_create(
                film=film,
                language=language_code
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created subtitle set for {language_code}."))
            else:
                self.stdout.write(f"Using existing subtitle set for {language_code} (will overwrite lines).")

            # Удаляем старые строки
            deleted_count, _ = subtitle_set.lines.all().delete()
            if deleted_count:
                self.stdout.write(f"Deleted {deleted_count} existing lines.")

            # Подготавливаем bulk_create
            new_objs = []
            for item in parsed:
                new_objs.append(SubtitleLine(
                    subtitle_set=subtitle_set,
                    start_time=item['start'],
                    end_time=item['end'],
                    text=item['text'],
                    name=item['name'],
                    style_classes=item.get('style_classes', '') or ''
                ))

            if new_objs:
                SubtitleLine.objects.bulk_create(new_objs)
                self.stdout.write(self.style.SUCCESS(f"Imported {len(new_objs)} subtitle lines."))
            else:
                self.stdout.write(self.style.WARNING("No subtitle lines to import after parsing."))

        self.stdout.write(self.style.SUCCESS("Import finished."))
