from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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
        max_length=10,
        verbose_name='Язык субтитров',
        help_text='Например, "en", "ru"'
    )

    class Meta:
        verbose_name = 'Набор субтитров'
        verbose_name_plural = 'Наборы субтитров'
        unique_together = ('film', 'language')

    def __str__(self):
        return f"{self.film.name} ({self.language})"

    def format_time(self, seconds):
        """Конвертирует секунды (float) в формат VTT (00:00:00.000)"""
        if seconds is None:
            return "00:00:00.000"

        ms = int(seconds * 1000)
        h = ms // 3600000
        ms %= 3600000
        m = ms // 60000
        ms %= 60000
        s = ms // 1000
        ms %= 1000

        return f"{h:02}:{m:02}:{s:02}.{ms:03}"

    def generate_vtt(self):
        """
        Генерирует полный VTT-файл из строк, хранящихся в базе.
        """
        vtt_lines = ["WEBVTT\n"]

        # Загружаем все строки, отсортированные по времени
        lines = self.lines.all().order_by('start_time')

        for line in lines:
            # 1. Тайминги: 00:00:00.000 --> 00:00:00.000
            start_time = self.format_time(line.start_time)
            end_time = self.format_time(line.end_time)
            vtt_lines.append(f"{start_time} --> {end_time}")

            # 2. Текст с VTT-тегами:
            text_parts = []

            # Добавляем имя говорящего, если есть (используем тег <c.speaker>)
            if line.name:
                text_parts.append(f"<c.speaker>{line.name}:</c>")

            # Добавляем текст, обернутый в стиль, если есть
            if line.style_classes:
                # В SubtitleLine.style_classes должно быть имя класса (например, 'loud')
                text_parts.append(f"<c.{line.style_classes}>{line.text}</c>")
            else:
                text_parts.append(line.text)

            vtt_lines.append(" ".join(text_parts))
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
        help_text='Время в секундах, с точностью до миллисекунд.'
    )
    end_time = models.FloatField(
        verbose_name='Время окончания (с)'
    )
    text = models.TextField(
        verbose_name='Текст субтитра'
    )
    name = models.CharField( # Используем CharField, как согласовано
        max_length=100,
        verbose_name='Имя персонажа',
        null=True, blank=True
    )
    style_classes = models.CharField( # Для всех стилей: bold italic loud-text
        max_length=255,
        verbose_name='Классы стилей',
        help_text='Например: "bold italic red-text"',
        null=True, blank=True
    )

    class Meta:
        verbose_name = 'Строка субтитра'
        verbose_name_plural = 'Строки субтитров'
        # Сортировка по времени начала. Если тайминги одинаковы, порядок не гарантирован,
        # что является компромиссом после удаления поля 'order'.
        ordering = ['start_time', 'end_time']

    def __str__(self):
        return f"[{self.start_time:.2f}] {self.text[:40]}..."