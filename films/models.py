from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime
from collections import OrderedDict


class MyModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Country(MyModel):
    name = models.CharField("Название", max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Страна"
        verbose_name_plural = "Страны"

    def __str__(self):
        return self.name


class Genre(MyModel):
    name = models.CharField("Название", max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"

    def __str__(self):
        return self.name


class Person(MyModel):
    name = models.CharField("Имя", max_length=400)
    origin_name = models.CharField("Имя в оригинале", max_length=400,
                                   blank=True, null=True)
    birthday = models.DateField("Дата рождения", blank=True, null=True,
                                validators=[
                                    MaxValueValidator(
                                        limit_value=datetime.date.today)
                                ])
    photo = models.ImageField(
        "Фото", upload_to='photos/', blank=True, null=True)
    kinopoisk_id = models.PositiveIntegerField(
        "Kinopoisk ID", blank=True, null=True)

    def age(self):
        if not self.birthday:
            return None
        today = datetime.date.today()
        return today.year - self.birthday.year \
            - ((today.month, today.day) < (self.birthday.month,
                                           self.birthday.day))

    class Meta:
        ordering = ["name"]
        verbose_name = "Персона"
        verbose_name_plural = "Персоны"

    def __str__(self):
        return self.name


class Film(MyModel):
    name = models.CharField("Имя", max_length=1024)
    origin_name = models.CharField(
        "Название (в оригинале)", max_length=1024, blank=True, null=True)
    slogan = models.CharField("Девиз", max_length=2048, blank=True, null=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, verbose_name="Страна")
    genres = models.ManyToManyField(Genre, verbose_name="Жанр")
    director = models.ForeignKey(
        Person, on_delete=models.CASCADE, verbose_name="Режиссер",
        related_name="directed_films")
    length = models.PositiveIntegerField(
        "Продолжительность", blank=True, null=True)
    year = models.PositiveIntegerField("Год выпуска", blank=True, null=True,
                                       validators=[MinValueValidator(
                                           limit_value=1885)])
    trailer_url = models.URLField("Трейлер", blank=True, null=True)
    cover = models.ImageField(
        "Постер", upload_to='covers/', blank=True, null=True)
    description = models.TextField("Описание", blank=True, null=True)
    people = models.ManyToManyField(Person, verbose_name="Актеры")
    kinopoisk_id = models.PositiveIntegerField(
        "Kinopoisk ID", blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"

    def __str__(self):
        return self.name

class SubtitleSet(MyModel):
    """Контейнер для набора субтитров определенного языка для фильма."""
    film = models.ForeignKey(
        'Film',
        on_delete=models.CASCADE,
        related_name='subtitle_sets',
        verbose_name='Фильм'
    )
    language = models.CharField(
        max_length=2,
        verbose_name='Язык субтитров',
        help_text='Например, "en", "ru"'
    )

    speaker_color_map = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Карта цветов персонажей',
        help_text='JSON: {"Имя Персонажа": "#HEX_ЦВЕТ", "Другое Имя": "#HEX_ЦВЕТ", ...}'
    )

    class Meta:
        verbose_name = 'Набор субтитров'
        verbose_name_plural = 'Наборы субтитров'
        unique_together = ('film', 'language')

    def __str__(self):
        return f"{self.film.name} ({self.language})"

    @staticmethod
    def format_time(milliseconds):
        hours, remainder = divmod(milliseconds, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, milliseconds = divmod(remainder, 1000)
        if hours > 0:
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{int(milliseconds):03}"
        return f"{int(minutes):02}:{int(seconds):02}.{int(milliseconds):03}"

    def generate_vtt(self):
        """
        Генерирует чистый VTT-файл для видеоплеера.
        Использует стандартный тег <v Name> для спикера.
        Использует тег <c.класс> для стилизации текста.
        """
        vtt_lines = ["WEBVTT\n"]

        # Загружаем все строки, отсортированные по времени
        lines = self.lines.all().order_by('start_time')

        for line in lines:
            # Преобразование секунд в миллисекунды для format_time
            start_time = SubtitleSet.format_time(line.start_time * 1000)
            end_time = SubtitleSet.format_time(line.end_time * 1000)

            # 1. Формируем строку с таймингами
            vtt_cue_line = f"{start_time} --> {end_time}"
            vtt_lines.append(vtt_cue_line)
            speaker_name = line.name
            text_content = line.text

            # Имя персонажа обрамляется в тег <v Speaker>
            if speaker_name:
                text_content = f"<v {speaker_name}> {text_content.strip()}"

            custom_classes = line.style_classes.strip().split()

            # Собираем финальный контент (обертывая текст и тег спикера в <c.класс>)
            if custom_classes:
                class_string = ".".join(custom_classes)
                text_content = f"<c.{class_string}>{text_content}</c>"

            # Добавляем чистый текст субтитра
            vtt_lines.append(text_content.strip())
            vtt_lines.append("\n")

        return "\n".join(vtt_lines)

    def get_speaker_colors(self):
        """
        Возвращает данные в формате initial=... для SpeakerColorFormSet,
        объединяя текущие стили с новыми именами спикеров из SubtitleLine.
        """
        # Сбор уникальных имен из существующих строк субтитров
        unique_names_qs = self.lines.filter(
            name__in=[None, '']
        ).values_list('name', flat=True).distinct()

        current_colors = self.speaker_color_map or {}
        combined_names = OrderedDict(current_colors)

        # Добавляем новые имена спикеров с белым цветом по умолчанию
        for name in unique_names_qs:
            if name not in combined_names:
                combined_names[name] = '#ffffff'

        colors_data = []
        for name, color in combined_names.items():
            colors_data.append({
                'speaker_name': name,
                'color_hex': color
            })

        return colors_data

    def save_colors(self, formset):
        """
        Обрабатывает SpeakerColorFormSet, обновляет JSONField и сохраняет модель.
        Возвращает True при успехе, или вызывает исключение при ошибке сохранения.
        """
        new_speaker_styles = {}

        for form in formset:
            # Использование .cleaned_data.get() гарантирует, что мы получим None, если поля нет
            should_delete = form.cleaned_data.get('DELETE')
            speaker = form.cleaned_data.get('speaker_name')
            color = form.cleaned_data.get('color_hex')

            if not should_delete and speaker and color and color.lower() != '#ffffff': # should_delete is not None?
                new_speaker_styles[speaker.strip()] = color.upper()

        self.speaker_color_map = new_speaker_styles
        self.save()
        return True

class SubtitleLine(MyModel):
    """Отдельная строка субтитров с таймингами и стилями."""

    subtitle_set = models.ForeignKey(
        'SubtitleSet',
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='Набор субтитров'
    )
    start_time = models.FloatField(
        verbose_name='Время начала (с)',
        help_text='Время в секундах, с точностью до миллисекунд.',
        validators=[MinValueValidator(0.0)]
    )
    end_time = models.FloatField(
        verbose_name='Время окончания (с)',
        validators=[MinValueValidator(0.0)]
    )
    text = models.TextField(
        verbose_name='Текст субтитра'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Имя персонажа',
        null=True, blank=True
    )

    style_classes = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name='Классы стилей CSS',
        help_text='Классы через пробел, например: bold loud'
    )

    class Meta:
        verbose_name = 'Строка субтитра'
        verbose_name_plural = 'Строки субтитров'
        ordering = ['start_time', 'end_time']

    def __str__(self):
        return f"[{self.start_time:.2f}] {self.text[:40]}..."
