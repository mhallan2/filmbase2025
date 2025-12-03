from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import JSONField
import datetime


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

    def format_time(self, milliseconds):
        hours, remainder = divmod(milliseconds, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, milliseconds = divmod(remainder, 1000)
        if hours > 0:
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{int(milliseconds):03}"
        return f"{int(minutes):02}:{int(seconds):02}.{int(milliseconds):03}"

    def generate_vtt(self):
        """
        Генерирует полный, ЧИСТЫЙ VTT-файл для видеоплеера.
        Использует только стандартный тег <v Name> для спикера.
        Использует тег <c.класс> только для стилизации текста.
        """
        vtt_lines = ["WEBVTT\n"]

        # Загружаем все строки, отсортированные по времени
        lines = self.lines.all().order_by('start_time')

        for line in lines:
            # Преобразование секунд в миллисекунды для format_time
            start_time = self.format_time(line.start_time * 1000)
            end_time = self.format_time(line.end_time * 1000)

            # 1. Формируем строку с таймингами
            vtt_cue_line = f"{start_time} --> {end_time}"

            # 🛑 ИСПРАВЛЕНИЕ: Удаляем добавление тега <v Name> из строки таймингов.
            # В этой строке остается только время.

            vtt_lines.append(vtt_cue_line) # <-- Заголовок метки

            # 2. Извлечение имени спикера
            speaker_name = line.name

            # Инициализируем контент текста
            text_content = line.text

            # ✅ КОРРЕКТИРОВКА: Добавляем тег спикера в НАЧАЛО ТЕКСТА
            if speaker_name:
                # Добавляем тег <v Имя> перед текстом субтитра
                text_content = f"<v {speaker_name}> {text_content.strip()}"

                # 3. Собираем классы для отображения (VTT-стилизация)
            custom_classes = line.style_classes.strip().split()

            # 4. Собираем финальный контент (обертывая текст и тег спикера в <c.класс>)
            if custom_classes:
                class_string = ".".join(custom_classes)
                # Оборачиваем текст (который теперь может содержать <v Name>) в тег <c.класс1.класс2>
                text_content = f"<c.{class_string}>{text_content}</c>"
            # else:
            # text_content уже содержит либо чистый текст, либо текст с <v Name>

            # 5. Добавляем чистый текст субтитра
            vtt_lines.append(text_content.strip())

            vtt_lines.append("\n") # Пустая строка для разделения блоков VTT

        return "\n".join(vtt_lines)


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
        validators=[MinValueValidator(0.0)] # Добавим валидатор
    )
    end_time = models.FloatField(
        verbose_name='Время окончания (с)',
        validators=[MinValueValidator(0.0)] # Добавим валидатор
    )
    text = models.TextField(
        verbose_name='Текст субтитра'
    )
    name = models.CharField( # Используем CharField, как согласовано
        max_length=100,
        verbose_name='Имя персонажа',
        null=True, blank=True
    )

    style_classes = models.CharField(
        max_length=255,
        default='',
        blank=True,
        verbose_name='Классы стилей CSS',
        help_text='Классы через пробел, например: bold shadow'
    )

    class Meta:
        verbose_name = 'Строка субтитра'
        verbose_name_plural = 'Строки субтитров'
        # Сортировка по времени начала. Если тайминги одинаковы, порядок не гарантирован,
        # что является компромиссом после удаления поля 'order'.
        ordering = ['start_time', 'end_time']

    def __str__(self):
        return f"[{self.start_time:.2f}] {self.text[:40]}..."

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)