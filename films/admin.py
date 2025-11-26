from django.contrib import admin
from .models import Country, Film, Person, Genre, SubtitleSet, SubtitleLine


# 1. Inline для SubtitleLine (встроенное редактирование)
class SubtitleLineInline(admin.TabularInline):
    """
    Позволяет редактировать строки SubtitleLine прямо внутри страницы SubtitleSet.
    Используем TabularInline для компактного отображения таблицы.
    """
    model = SubtitleLine
    # Указываем, какие поля должны отображаться
    fields = ('start_time', 'end_time', 'text', 'name', 'style_classes')
    extra = 1 # Количество пустых строк для добавления по умолчанию


# 2. Регистрация SubtitleSet
@admin.register(SubtitleSet)
class SubtitleSetAdmin(admin.ModelAdmin):
    """Регистрация SubtitleSet в админ-панели."""
    # Поля, отображаемые в общем списке наборов
    list_display = ('film', 'language', 'line_count')
    list_filter = ('language',)
    search_fields = ('film__name', 'language')

    # Ключевой момент: добавляем Inline для редактирования строк
    inlines = [SubtitleLineInline]

    def line_count(self, obj):
        """Метод для подсчета количества строк в наборе."""
        return obj.lines.count()
    line_count.short_description = 'Кол-во строк'

# 3. Регистрация существующих моделей
admin.site.register(Film)
admin.site.register(Person)
admin.site.register(Country)
admin.site.register(Genre)
