from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from dal import autocomplete
from .models import Country, Genre, Film, Person, SubtitleSet, SubtitleLine
from collections import OrderedDict
from django.core.validators import MinLengthValidator


class CountryForm(forms.ModelForm):
    class Meta:
        model = Country
        fields = ['name']


class GenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = ['name']


class FilmForm(forms.ModelForm):
    class Meta:
        model = Film
        fields = ['name', 'origin_name', 'slogan', 'length', 'year',
                  'trailer_url', 'cover', 'description', 'country', 'genres',
                  "director", 'people']
        widgets = {
            'people': autocomplete.ModelSelect2Multiple(
                url='films:person_autocomplete'),
            'director': autocomplete.ModelSelect2(
                url='films:person_autocomplete'),
            'country': autocomplete.ModelSelect2(
                url='films:country_autocomplete'),
        }


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['name', 'origin_name', 'birthday', 'photo']
        widgets = {
            "birthday": forms.DateInput(attrs={'type': 'date'},
                                        format="%Y-%m-%d")
        }

STYLE_CHOICES = (
    ('bold', 'Жирный'),
    ('italic', 'Курсив'),
    ('loud', 'Крик'),
    # Добавьте другие классы
)

class SubtitleLineForm(forms.ModelForm):
    mapped_classes = forms.MultipleChoiceField(
        required=False,
        choices=STYLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Стили текста'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Заполняем чекбоксы данными из БД
        if self.instance.pk and self.instance.style_classes:
            initial_classes = self.instance.style_classes.split()
            self.fields['mapped_classes'].initial = initial_classes

        # 2. Скрываем модельное поле style_classes, так как его заполняет clean()
        self.fields['style_classes'].widget = forms.HiddenInput()

    """Форма для редактирования одной строки субтитра с пользовательской валидацией."""
    class Meta:
        model = SubtitleLine
        # ✅ ИЗМЕНЕНИЕ: Заменяем 'style' на 'style_classes'
        fields = ['id', 'start_time', 'end_time', 'text', 'name', 'style_classes']
        widgets = {
            'start_time': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'type': 'number', 'step': '0.001'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'type': 'number', 'step': '0.001'}),
            'text': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        # 1. ✅ НОВОЕ: Преобразуем список из чекбоксов в строку для БД
        selected_classes = cleaned_data.get('mapped_classes', [])
        cleaned_data['style_classes'] = " ".join(selected_classes)

        # 2. Удаляем временное поле, чтобы оно не попало в модель (хотя Django его игнорирует)
        del cleaned_data['mapped_classes']

        # 3. Валидация времени (остается без изменений)
        if cleaned_data.get('DELETE'):
            return cleaned_data

        # 1. Проверка на отрицательное время
        if start_time is not None and start_time < 0:
            self.add_error('start_time', 'Время начала не может быть отрицательным.')

        if end_time is not None and end_time < 0:
            self.add_error('end_time', 'Время окончания не может быть отрицательным.')

        # 2. Проверка, что start_time <= end_time
        if start_time is not None and end_time is not None:
            if start_time > end_time:
                # Ошибку можно добавить к любому из полей времени
                self.add_error('end_time', 'Время окончания должно быть больше или равно времени начала.')

        # 3. Дополнительная проверка на заполненность текста (если время указано)
        text = cleaned_data.get('text')
        if (start_time is not None or end_time is not None) and not text:
             # Если время есть, текст должен быть.
             self.add_error('text', 'Текст субтитра не может быть пустым, если указано время.')


        return cleaned_data

# Создаем фабрику формсетов для строк субтитров
SubtitleLineFormSet = inlineformset_factory(
    parent_model=SubtitleSet,
    model=SubtitleLine,
    form=SubtitleLineForm,
    fields=['id', 'start_time', 'end_time', 'text', 'name', 'style_classes'], # ✅ ИЗМЕНЕНИЕ
    extra=0,
    can_delete=True
)

# --- НОВЫЕ ФОРМЫ И ВИДЖЕТ ДЛЯ РЕДАКТИРОВАНИЯ СТИЛЕЙ ---

class ColorInput(forms.TextInput):
    """Виджет для выбора цвета (использует type="color" и TextInput)"""
    input_type = 'color'
    # ⚡ КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Указываем путь к нашему новому шаблону
    template_name = 'films/widgets/color_input.html'

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        # Используем form-control-color для Bootstrap 5
        attrs.update({'class': 'form-control form-control-color', 'style': 'height: 40px; width: 80px;'})
        super().__init__(attrs)


class SpeakerColorBaseForm(forms.Form):
    """Базовая форма для одной строки карты цветов."""

    speaker_name = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    color_hex = forms.CharField(
        label='Цвет',
        widget=ColorInput(),
        initial='#FFFFFF',
        max_length=7,
        required=True,
        help_text='HEX-код цвета.'
    )
    DELETE = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Динамически устанавливаем label для удобства пользователя
        speaker_name = self.initial.get('speaker_name') or (self.is_bound and self.data.get(f'{self.prefix}-speaker_name'))
        if speaker_name:
             self.fields['color_hex'].label = f'"{speaker_name}"'


# Фабрика формсетов для карты цветов
SpeakerColorFormSet = forms.formset_factory(
    SpeakerColorBaseForm,
    extra=0,
    can_delete=True
)

# --- ФОРМА ДЛЯ МОДАЛЬНОГО ОКНА (SubtitleSetSelectForm) ---
class SubtitleSetSelectForm(forms.Form):
    """Форма для выбора/создания языка субтитров в модальном окне."""
    language = forms.CharField(
        label='Код языка',
        max_length=2,
        required=True,
        validators=[MinLengthValidator(2)],
        widget=forms.TextInput(attrs={'placeholder': 'ru, en, fr', 'class': 'form-control'})
    )