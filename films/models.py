from django.db import models
from films.validators import LanguageCodeValidator
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
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
        help_text='Например, "en", "ru"',
        validators=[LanguageCodeValidator]
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

    def get_speaker_colors(self):
        """
        Возвращает список словарей {"speaker_name":..., "color_hex":...}
        Теперь:
        — учитываются ВСЕ имена спикеров
        — новые имена получают #ffffff
        """
        # Все уникальные спикеры
        unique_names = (
            self.lines
            .exclude(name__isnull=True)
            .exclude(name__exact='')
            .values_list('name', flat=True)
            .distinct()
        )

        current_colors = self.speaker_color_map or {}
        combined = OrderedDict()

        # Сначала — существующие цвета
        for name, color in current_colors.items():
            combined[name] = color

        # Потом — новые имена с белым
        for name in unique_names:
            if name not in combined:
                combined[name] = '#FFFFFF'

        # Преобразуем в список
        initial_styles_data = [
            {"speaker_name": name, "color_hex": color}
            for name, color in combined.items()
        ]

        return initial_styles_data

    def save_colors(self, formset):
        """
        Сохраняет обновлённую карту цветов.
        Важно: теперь цвет #FFFFFF сохраняется, а не удаляется.
        """
        updated_colors = {}

        for form in formset:
            if not form.cleaned_data:
                continue

            delete = form.cleaned_data.get('DELETE')
            speaker = form.cleaned_data.get('speaker_name')
            color = form.cleaned_data.get('color_hex')

            if delete or not speaker:
                continue

            updated_colors[speaker.strip()] = color.upper()

        self.speaker_color_map = updated_colors
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

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("Время окончания должно быть больше времени начала.")
        self.text = self.text.strip()
        if self.name:
            self.name = self.name.strip()
        self.style_classes = " ".join(self.style_classes.split())

