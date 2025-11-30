from django.contrib import admin
from .models import Country, Film, Person, Genre, SubtitleSet, SubtitleLine


# 1. Inline для строк субтитров
class SubtitleLineInline(admin.TabularInline):
    model = SubtitleLine
    fields = ('start_time', 'end_time', 'text', 'name', 'style')
    ordering = ('start_time',)
    extra = 0 # Не добавлять пустые формы по умолчанию
    can_delete = True

# 2. Inline для набора субтитров (чтобы видеть их прямо в фильме)
class SubtitleSetInline(admin.StackedInline):
    model = SubtitleSet
    # inlines = [SubtitleLineInline] # Нельзя вкладывать Inline в StackedInline
    fields = ('language',)
    extra = 0
    # Поле 'language' должно быть уникальным,
    # а SubtitleLineInline позволит редактировать сами строки

@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'director', 'kinopoisk_id')
    inlines = [SubtitleSetInline] # Добавляем возможность видеть и редактировать наборы субтитров

# Отдельно регистрируем SubtitleSet (если нужно)
@admin.register(SubtitleSet)
class SubtitleSetAdmin(admin.ModelAdmin):
    list_display = ('film', 'language')
    list_filter = ('language',)
    search_fields = ('film__name',)
    # Добавляем SubtitleLineInline для редактирования строк
    inlines = [SubtitleLineInline]

# 3. Регистрация существующих моделей
admin.site.register(Person)
admin.site.register(Country)
admin.site.register(Genre)
