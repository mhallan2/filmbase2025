from django import forms
from django.forms import inlineformset_factory
from dal import autocomplete
from django.core.validators import MinLengthValidator
from .models import (
    Country, Genre, Film, Person, SubtitleSet, SubtitleLine
)


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
        fields = [
            'name', 'origin_name', 'slogan', 'length', 'year',
            'trailer_url', 'cover', 'description',
            'country', 'genres', "director", 'people'
        ]
        widgets = {
            'people': autocomplete.ModelSelect2Multiple(url='films:person_autocomplete'),
            'director': autocomplete.ModelSelect2(url='films:person_autocomplete'),
            'country': autocomplete.ModelSelect2(url='films:country_autocomplete'),
        }


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['name', 'origin_name', 'birthday', 'photo']
        widgets = {
            "birthday": forms.DateInput(attrs={'type': 'date'}, format="%Y-%m-%d")
        }


# =========================================================
#  SUBTITLE LINE FORM
# =========================================================

STYLE_CHOICES = (
    ('bold', 'Жирный'),
    ('italic', 'Курсив'),
    ('loud', 'Крик'),
)

class SubtitleLineForm(forms.ModelForm):
    """
    Улучшения:
    - Уменьшено дублирование.
    - Валидация времени — оставлена, но слегка упрощена логически.
    - mapped_classes остаётся только как удобный UX-слой.
    """

    mapped_classes = forms.MultipleChoiceField(
        required=False,
        choices=STYLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Стили текста'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Скрываем реальное поле
        self.fields['style_classes'].widget = forms.HiddenInput()

        # Инициализация чекбоксов
        if self.instance.pk and self.instance.style_classes:
            self.fields['mapped_classes'].initial = self.instance.style_classes.split()

    class Meta:
        model = SubtitleLine
        fields = ['id', 'start_time', 'end_time', 'text', 'name', 'style_classes']
        widgets = {
            'start_time': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'end_time': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'text': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean(self):
        cleaned = super().clean()

        # Маппинг классов → строка
        classes = cleaned.get('mapped_classes') or []
        cleaned['style_classes'] = " ".join(classes)

        # Валидацию выполняем только если форма не помечена на удаление
        if cleaned.get('DELETE'):
            return cleaned

        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        text = cleaned.get('text')

        # Отрицательное время
        if start is not None and start < 0:
            self.add_error('start_time', 'Время начала не может быть отрицательным.')

        if end is not None and end < 0:
            self.add_error('end_time', 'Время окончания не может быть отрицательным.')

        # Неверный диапазон
        if start is not None and end is not None and start > end:
            self.add_error('end_time', 'Время окончания должно быть >= времени начала.')

        # Пустой текст при указанных таймингах
        if (start is not None or end is not None) and not text:
            self.add_error('text', 'Текст субтитра обязателен, если указано время.')

        return cleaned


SubtitleLineFormSet = inlineformset_factory(
    SubtitleSet,
    SubtitleLine,
    form=SubtitleLineForm,
    extra=0,
    can_delete=True
)


# =========================================================
#  COLOR PICKER WIDGET
# =========================================================

class ColorInput(forms.TextInput):
    input_type = 'color'
    template_name = 'films/widgets/color_input.html'

    def __init__(self, attrs=None):
        base_attrs = {
            'class': 'form-control form-control-color',
        }
        if attrs:
            base_attrs.update(attrs)
        super().__init__(base_attrs)


# =========================================================
#  SPEAKER COLOR FORMSET
# =========================================================

class SpeakerColorBaseForm(forms.Form):
    speaker_name = forms.CharField(widget=forms.HiddenInput())
    color_hex = forms.CharField(
        label='Цвет',
        widget=ColorInput(),
        max_length=7,
        required=True,
    )
    DELETE = forms.BooleanField(required=False)

    # Улучшение: автоматическая установка label
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        speaker = (
            self.initial.get('speaker_name') or
            self.data.get(f"{self.prefix}-speaker_name")
        )
        if speaker:
            self.fields['color_hex'].label = f'"{speaker}"'

    def clean_color_hex(self):
        """Небольшая встроенная очистка HEX."""
        val = self.cleaned_data['color_hex'].strip().upper()

        if len(val) != 7 or not val.startswith('#'):
            raise forms.ValidationError('Цвет должен быть в формате #RRGGBB.')

        # Допустим только 0–9 A–F
        if any(c not in '0123456789ABCDEF#' for c in val):
            raise forms.ValidationError('HEX содержит недопустимые символы.')

        return val


SpeakerColorFormSet = forms.formset_factory(
    SpeakerColorBaseForm,
    extra=0,
    can_delete=True
)


# =========================================================
#  MODAL FORM — выбор языка
# =========================================================

class SubtitleSetSelectForm(forms.Form):
    language = forms.CharField(
        label='Код языка',
        max_length=2,
        validators=[MinLengthValidator(2)],
        widget=forms.TextInput(attrs={'placeholder': 'ru, en, fr', 'class': 'form-control'})
    )

    def clean_language(self):
        """Маленькое, но полезное улучшение UX."""
        lang = self.cleaned_data['language'].lower().strip()
        if not lang.isalpha():
            raise forms.ValidationError('Код языка должен состоять только из букв.')
        return lang
