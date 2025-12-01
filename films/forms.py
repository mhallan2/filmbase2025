from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from dal import autocomplete
from .models import Country, Genre, Film, Person, SubtitleSet, SubtitleLine


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

class SubtitleLineForm(forms.ModelForm):
    """Форма для редактирования одной строки субтитра с пользовательской валидацией."""

    # ⚡ КРИТИЧЕСКАЯ ПРАВКА: Установка начального значения для новых форм
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Проверяем, что это новая форма (instance.pk is None) и поле style не имеет значения.
        if self.instance.pk is None and not self.initial.get('style'):
            # Устанавливаем начальное значение в виде JSON-строки, как вы просили.
            self.initial['style'] = {"classes": []}

    class Meta:
        model = SubtitleLine
        fields = ['id', 'start_time', 'end_time', 'text', 'name', 'style']
        widgets = {
            'start_time': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'type': 'number', 'step': '0.00001', 'min': '0'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'type': 'number', 'step': '0.00001', 'min': '0'}),
            'text': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'style': forms.Textarea(attrs={'rows': 1, 'class': 'form-control form-control-sm', 'placeholder': '{"classes": ["loud"]}'}), 
        }

    def clean(self):
        """
        Пользовательская валидация для проверки времени начала/конца.
        """
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Если форма помечена как удаляемая, пропускаем валидацию
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

# Новая форма для выбора или создания набора субтитров
class SubtitleSetSelectForm(forms.Form):
    # Это поле не будет привязано к модели
    language_code = forms.CharField(
        max_length=2,
        required=True,
        label='Код языка (например, ru, en, fr)',
        widget=forms.TextInput(attrs={'placeholder': 'ru, en, fr'})
    )
    # Используется только для создания нового набора
    is_new = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

# Создаем фабрику формсетов
# Extra=3: Добавляем 3 пустые строки для новых субтитров.
SubtitleLineFormSet = inlineformset_factory(
    parent_model=SubtitleSet, 
    model=SubtitleLine, 
    form=SubtitleLineForm,
    fields=['id', 'start_time', 'end_time', 'text', 'name', 'style'],
    extra=0, # <-- ИЗМЕНЕНИЕ: Добавляем 3 пустые формы для добавления
    can_delete=True
)