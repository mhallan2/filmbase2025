from dal import autocomplete
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError
from .models import Country, Film, Genre, Person, SubtitleSet, SubtitleLine # <-- Добавлен SubtitleLine
from .forms import CountryForm, GenreForm, FilmForm, PersonForm, SubtitleLineFormSet, SubtitleSetSelectForm, SpeakerColorFormSet
from .helpers import paginate
from django.contrib import messages
from django.http import HttpResponse, Http404
from collections import OrderedDict # <-- Для сохранения порядка в карте цветов


def check_admin(user):
    return user.is_superuser


def country_list(request):
    countries = Country.objects.all()
    return render(request, 'films/country/list.html', {'countries': countries})


def country_detail(request, id):
    country = get_object_or_404(Country, id=id)
    films = Film.objects.filter(country=country)

    films = paginate(request, films)
    return render(request, 'films/country/detail.html',
                  {'country': country, 'films': films})


@user_passes_test(check_admin)
def country_create(request):
    if request.method == 'POST':
        form = CountryForm(request.POST)
        if form.is_valid():
            country = form.save()
            messages.success(request, 'Страна добавлена')
            return redirect('films:country_detail', id=country.id)
    else:
        form = CountryForm()
    return render(request, 'films/country/create.html', {'form': form})


@user_passes_test(check_admin)
def country_update(request, id):
    country = get_object_or_404(Country, id=id)
    if request.method == 'POST':
        form = CountryForm(request.POST, instance=country)
        if form.is_valid():
            form.save()
            messages.success(request, 'Страна изменена')
            return redirect('films:country_detail', id=country.id)
    else:
        form = CountryForm(instance=country)
    return render(request, 'films/country/update.html',
                  {'form': form})


@user_passes_test(check_admin)
def country_delete(request, id):
    country = get_object_or_404(Country, id=id)
    if request.method == 'POST':
        country.delete()
        messages.success(request, 'Страна удалена')
        return redirect('films:country_list')
    return render(request, 'films/country/delete.html',
                  {'country': country})


def genre_list(request):
    genres = Genre.objects.all()
    return render(request, 'films/genre/list.html', {'genres': genres})


def genre_detail(request, id):
    genre = get_object_or_404(Genre, id=id)
    films = Film.objects.filter(genres=genre)

    films = paginate(request, films)
    return render(request, 'films/genre/detail.html',
                  {'genre': genre, 'films': films})


@user_passes_test(check_admin)
def genre_create(request):
    if request.method == 'POST':
        form = GenreForm(request.POST)
        if form.is_valid():
            genre = form.save()
            messages.success(request, 'Жанр добавлен')
            return redirect('films:genre_detail', id=genre.id)
    else:
        form = GenreForm()
    return render(request, 'films/genre/create.html', {'form': form})


@user_passes_test(check_admin)
def genre_update(request, id):
    genre = get_object_or_404(Genre, id=id)
    if request.method == 'POST':
        form = GenreForm(request.POST, instance=genre)
        if form.is_valid():
            form.save()
            messages.success(request, 'Жанр изменён')
            return redirect('films:genre_detail', id=genre.id)
    else:
        form = GenreForm(instance=genre)
    return render(request, 'films/genre/update.html',
                  {'form': form})


@user_passes_test(check_admin)
def genre_delete(request, id):
    genre = get_object_or_404(Genre, id=id)
    if request.method == 'POST':
        genre.delete()
        messages.success(request, 'Жанр удалён')
        return redirect('films:genre_list')
    return render(request, 'films/genre/delete.html',
                  {'genre': genre})


def film_list(request):
    films = Film.objects.all()
    query = request.GET.get('query', '')
    if query:
        films = films.filter(name__icontains=query)
    films = paginate(request, films)
    return render(request, 'films/film/list.html', {'films': films,
                                                    'query': query})

@user_passes_test(check_admin)
def film_create(request):
    if request.method == 'POST':
        form = FilmForm(request.POST, request.FILES)
        if form.is_valid():
            film = form.save()
            messages.success(request, 'Фильм добавлен')
            return redirect('films:film_detail', id=film.id)
    else:
        form = FilmForm()
    return render(request, 'films/film/create.html', {'form': form})


@user_passes_test(check_admin)
def film_update(request, id):
    film = get_object_or_404(Film, id=id)
    if request.method == 'POST':
        form = FilmForm(request.POST, request.FILES, instance=film)
        if form.is_valid():
            form.save()
            messages.success(request, 'Фильм изменён')
            return redirect('films:film_detail', id=film.id)
    else:
        form = FilmForm(instance=film)
    return render(request, 'films/film/update.html',
                  {'form': form})


@user_passes_test(check_admin)
def film_delete(request, id):
    film = get_object_or_404(Film, id=id)
    if request.method == 'POST':
        film.delete()
        messages.success(request, 'Фильм удалён')
        return redirect('films:film_list')
    return render(request, 'films/film/delete.html',
                  {'film': film})


def person_list(request):
    people = Person.objects.all()
    query = request.GET.get('query', '')
    if query:
        people = people.filter(name__icontains=query)
    people = paginate(request, people)
    return render(request, 'films/person/list.html', {'people': people,
                                                      'query': query})


def person_detail(request, id):
    queryset = Person.objects.prefetch_related("film_set", "directed_films")
    person = get_object_or_404(queryset, id=id)
    return render(request, 'films/person/detail.html',
                  {'person': person})


@user_passes_test(check_admin)
def person_create(request):
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            person = form.save()
            messages.success(request, 'Персона добавлена')
            return redirect('films:person_detail', id=person.id)
    else:
        form = PersonForm()
    return render(request, 'films/person/create.html', {'form': form})


@user_passes_test(check_admin)
def person_update(request, id):
    person = get_object_or_404(Person, id=id)
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=person)
        if form.is_valid():
            form.save()
            messages.success(request, 'Персона изменена')
            return redirect('films:person_detail', id=person.id)
    else:
        form = PersonForm(instance=person)
    return render(request, 'films/person/update.html',
                  {'form': form})


@user_passes_test(check_admin)
def person_delete(request, id):
    person = get_object_or_404(Person, id=id)
    if request.method == 'POST':
        person.delete()
        messages.success(request, 'Персона удалена')
        return redirect('films:person_list')
    return render(request, 'films/person/delete.html',
                  {'person': person})


class PersonAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        people = Person.objects.all()
        if self.q:
            people = people.filter(name__istartswith=self.q)
        return people


class CountryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        countries = Country.objects.all()
        if self.q:
            countries = countries.filter(name__istartswith=self.q)
        return countries

def film_detail(request, id):
    queryset = Film.objects.prefetch_related("country", "genres", "director",
                                             "people", "subtitle_sets")
    film = get_object_or_404(queryset, id=id)
    subtitle_sets = film.subtitle_sets.all().order_by('language')

    available_languages = []
    # Словарь для хранения всех карт цветов: {'ru': {...}, 'fr': {...}}
    all_speaker_color_maps = {}
    default_lang = 'none'

    for sset in subtitle_sets:
        lang = sset.language.strip()
        available_languages.append(lang)
        all_speaker_color_maps[lang] = sset.speaker_color_map or {}

        # Логика выбора языка по умолчанию: русский, затем первый найденный
        if lang.lower() == 'ru':
            default_lang = lang
        elif default_lang == 'none' and lang:
            default_lang = lang

    return render(request, 'films/film/detail.html',
                  {'film': film,
                   'available_languages': available_languages,
                   'all_speaker_color_maps': all_speaker_color_maps,
                   'default_lang': default_lang,
                   })

def get_subtitles(request, film_id, language):
    """
    Отдает WebVTT файл по запросу клиента.
    Тег спикера <v Имя> добавляется в начало текста субтитра.
    Теги стилей <c.класс> добавляются, если указаны в поле style.
    """
    try:
        # Получаем набор субтитров с предварительной загрузкой строк
        subtitle_set = SubtitleSet.objects.prefetch_related('lines').get(
            film_id=film_id,
            language__iexact=language
        )
    except SubtitleSet.DoesNotExist:
        raise Http404(f"Набор субтитров ({language}) не найден.")

    vtt_content = subtitle_set.generate_vtt()

    return HttpResponse(vtt_content, content_type="text/vtt; charset=utf-8")

@user_passes_test(check_admin)
def subtitle_editor_view(request, film_id):
    film = get_object_or_404(Film, id=film_id)
    available_sets = SubtitleSet.objects.filter(film=film).order_by('language')
    available_languages = [s.language for s in available_sets]

    # 1. Нормализация языка и флагов
    requested_lang = request.GET.get('lang') or request.GET.get('language')
    current_lang = requested_lang.upper() if requested_lang else (available_languages[0] if available_languages else None)
    is_new = request.GET.get('is_new') == 'True'

    subtitle_set = None

    # 2. Получение или создание набора
    if current_lang:
        subtitle_set = available_sets.filter(language__iexact=current_lang).first()

        if subtitle_set:
            if is_new:
                messages.info(request, f'Набор субтитров для "{current_lang}" уже существует и был открыт.')

        elif is_new: # Если набора НЕТ, но запрошено создание
            try:
                subtitle_set = SubtitleSet.objects.create(film=film, language=current_lang)
                messages.success(request, f'Набор субтитров для языка "{current_lang}" создан.')
                # Редирект для очистки GET-параметров и обновления списка
                return redirect(reverse('films:subtitle_editor_view', kwargs={"film_id": film_id}) + f'?lang={current_lang}')

            except IntegrityError:
                messages.error(request, f'Набор субтитров для "{current_lang}" уже существует.')
                current_lang = None
            except Exception as e:
                messages.error(request, f'Ошибка при создании набора субтитров: {e}')
                current_lang = None

        else: # Набора нет, и создание не запрошено
            messages.error(request, f'Набор субтитров для языка "{current_lang}" не найден.')
            current_lang = None

    # --- 3. Инициализация Forms/FormSets (без дублирования) ---

    # Конфигурация для SubtitleLineFormSet
    line_formset_instance = subtitle_set if subtitle_set else SubtitleSet(film=film)
    formset = SubtitleLineFormSet(instance=line_formset_instance, prefix='lines')

    # Конфигурация для SpeakerColorFormSet
    initial_styles = []
    if subtitle_set:
        # Сбор и фильтрация speaker colors (улучшенная и читаемая версия)
        names_qs = SubtitleLine.objects.filter(
            subtitle_set=subtitle_set
        ).exclude(name__in=[None, '']).values_list('name', flat=True).distinct()

        # Объединение существующих цветов с новыми (белыми)
        merged_colors = subtitle_set.speaker_color_map.copy() if subtitle_set.speaker_color_map else {}
        for name in names_qs:
            if name not in merged_colors:
                merged_colors[name] = '#ffffff'

        # Фильтрация и формирование initial данных (удаление пустых ключей)
        initial_styles = [
            {'speaker_name': n, 'color_hex': c}
            for n, c in merged_colors.items() if n and n.strip() # Фильтрация пустых/None
        ]

    style_formset = SpeakerColorFormSet(initial=initial_styles, prefix='styles')

    # Конфигурация для SelectForm
    default_lang = current_lang if current_lang else (requested_lang or 'RU')
    select_form = SubtitleSetSelectForm(initial={'language': default_lang})

    # 4. Рендеринг
    return render(request, 'films/subtitle/editor.html', {
        'film': film,
        'current_lang': current_lang,
        'available_languages': available_languages,
        'subtitle_set': subtitle_set,
        'formset': formset,
        'style_formset': style_formset,
        'select_form': select_form,
    })

@user_passes_test(check_admin)
def save_subtitle(request, film_id, language):
    if request.method != 'POST':
        return redirect('films:subtitle_editor_view', film_id=film_id, lang=language)

    subtitle_set = get_object_or_404(SubtitleSet, film_id=film_id, language__iexact=language)
    # Formset привязан к POST-данным
    formset = SubtitleLineFormSet(request.POST, instance=subtitle_set, prefix='lines')

    if formset.is_valid():
        try:
            # УСПЕХ: Сохраняем, выводим сообщение, делаем редирект (POST-Redirect-GET)
            formset.save()
            messages.success(request, f'Субтитры ({language}) успешно обновлены.')
            # Редирект обратно в редактор для обновления содержимого
            return redirect(f'{reverse("films:subtitle_editor_view", kwargs={"film_id": film_id})}?lang={language}')
        except Exception as e:
            # Ошибка сохранения (например, проблемы с БД)
            messages.error(request, f'Ошибка при сохранении субтитров: {e}')
            return redirect(f'{reverse("films:subtitle_editor_view", kwargs={"film_id": film_id})}?lang={language}')
    else:
        # 🛑 НЕУДАЧА: РЕНДЕРИНГ ШАБЛОНА С ОШИБКАМИ

        # 1. Собираем контекст, необходимый для editor.html
        film = get_object_or_404(Film, id=film_id)
        available_sets = SubtitleSet.objects.filter(film=film).order_by('language')
        available_languages = [s.language for s in available_sets]

        # 2. Инициализируем Style Formset (чистыми данными из БД, т.к. его не трогали)
        initial_styles_data = subtitle_set.get_speaker_colors()
        style_formset = SpeakerColorFormSet(initial=initial_styles_data, prefix='styles')

        # 3. Инициализируем форму выбора языка
        select_form = SubtitleSetSelectForm(initial={'language': language})

        # 4. Добавляем общее сообщение об ошибке (оно будет дополнено специфическими ошибками формсета)
        messages.error(request, 'Обнаружены ошибки в форме субтитров. Проверьте выделенные поля.')

        return render(request, 'films/subtitle/editor.html', {
            'film': film,
            'current_lang': language,
            'available_languages': available_languages,
            'subtitle_set': subtitle_set,
            # 💥 Передаем ошибочный formset, который содержит POST-данные пользователя
            'formset': formset,
            'style_formset': style_formset,
            'select_form': select_form,
        })

@user_passes_test(check_admin)
def save_speaker_colors(request, film_id, language):
    """
    Обрабатывает POST-запрос на сохранение карты цветов персонажей (SpeakerColorFormSet).
    Функция является 'тонкой', делегируя всю логику данных методам модели SubtitleSet.
    """
    # 1. Защита от GET-запросов и проверка прав
    if request.method != 'POST':
        # Перенаправляет обратно в редактор с сохранением контекста
        return redirect('films:subtitle_editor_view', film_id=film_id, lang=language)

    # 2. Получение объекта
    subtitle_set = get_object_or_404(SubtitleSet, film_id=film_id, language__iexact=language)

    # 3. Получение начальных данных (через метод модели)
    # Эта логика (сбор уникальных имен, объединение цветов) теперь находится в models.py
    try:
        initial_styles_data = subtitle_set.get_speaker_colors()
    except Exception as e:
        messages.error(request, f'Ошибка при подготовке данных для стилей: {e}')
        return redirect(f'{reverse("films:subtitle_editor_view", kwargs={"film_id": film_id})}?lang={language}')

    # 4. Инициализация и валидация Formset
    style_formset = SpeakerColorFormSet(
        request.POST,
        initial=initial_styles_data,
        prefix='styles'
    )

    if style_formset.is_valid():
        try:
            # 5. Сохранение данных (через метод модели)
            # Вся сложная логика обработки и сохранения JSONField находится здесь
            subtitle_set.save_colors(style_formset)
            messages.success(request, f'Карта цветов ({language}) успешно обновлена.')
        except Exception as e:
            # Обработка ошибок, которые могут возникнуть при сохранении в базе данных
            messages.error(request, f'Ошибка при сохранении карты цветов: {e}')
    else:
        # Если валидация не прошла (например, некорректный HEX-код)
        messages.error(request, 'Ошибка при сохранении карты цветов. Пожалуйста, проверьте выделенные поля.')

    # 6. Редирект обратно в редактор (для сохранения контекста или отображения ошибок)
    return redirect(f'{reverse("films:subtitle_editor_view", kwargs={"film_id": film_id})}?lang={language}')

@user_passes_test(check_admin)
def delete_subtitles(request, film_id, language):
    film = get_object_or_404(Film, pk=film_id)

    try:
        subtitle_set = SubtitleSet.objects.get(film=film, language=language)
    except SubtitleSet.DoesNotExist:
        messages.error(request, f'Субтитры для языка "{language}" не найдены.')
        return redirect('films:film_detail', id=film.id)

    if request.method == 'POST':
        deleted_count, _ = SubtitleLine.objects.filter(
            subtitle_set=subtitle_set
        ).delete()
        SubtitleSet.objects.filter(pk=subtitle_set.pk).delete()
        messages.success(request, f'Удалено {deleted_count} строк субтитров для языка "{language}".')

        return redirect('films:film_detail', id=film.id)

    # Если метод GET, показываем страницу подтверждения
    return render(request, 'films/subtitle/delete_confirm.html',
                  {
                      'film': film,
                      'language': language,
                      'subtitle_set': subtitle_set,
                  })