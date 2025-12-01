from dal import autocomplete
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import user_passes_test
from .models import Country, Film, Genre, Person, SubtitleSet
from .forms import CountryForm, GenreForm, FilmForm, PersonForm, SubtitleLineFormSet, SubtitleSetSelectForm
from .helpers import paginate
from django.contrib import messages
from django.http import HttpResponse, Http404


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

# -----------------------------------------------------------------
# ОБНОВЛЕННАЯ ФУНКЦИЯ FILM_DETAIL
# -----------------------------------------------------------------
def film_detail(request, id):
    # Добавляем prefetch для subtitle_sets для оптимизации
    queryset = Film.objects.prefetch_related("country", "genres", "director",
                                             "people", "subtitle_sets")
    film = get_object_or_404(queryset, id=id)

    # 1. Получаем ВСЕ наборы субтитров
    subtitle_sets = film.subtitle_sets.all().order_by('language')

    # 2. Инициализация структур данных
    available_languages = []
    # Словарь для хранения всех карт цветов: {'ru': {...}, 'fr': {...}}
    all_speaker_color_maps = {}
    default_lang = 'none' # Заглушка, если субтитров нет

    for sset in subtitle_sets:
        # Убедимся, что язык чистый
        lang = sset.language.strip()
        available_languages.append(lang)
        # Убедимся, что speaker_color_map не None, иначе используем пустой словарь
        all_speaker_color_maps[lang] = sset.speaker_color_map or {}

        # Логика выбора языка по умолчанию: русский, затем первый найденный
        if lang.lower() == 'ru':
            default_lang = lang
        elif default_lang == 'none' and lang:
            # Если русский еще не выбран, берем первый из списка
            default_lang = lang

    return render(request, 'films/film/detail.html',
                  {'film': film,
                   'available_languages': available_languages, # Список для выпадающего меню
                   'all_speaker_color_maps': all_speaker_color_maps, # Полная карта цветов (Lang -> Map)
                   'default_lang': default_lang, # Язык, выбранный по умолчанию
                   })


# Вспомогательная функция для форматирования времени в WebVTT
def format_time(seconds):
    """Конвертирует float-секунды в формат HH:MM:SS.mmm"""
    ms = round(seconds * 1000)
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"


# -----------------------------------------------------------------
# ОБНОВЛЕННАЯ ФУНКЦИЯ GET_SUBTITLES (С ТЕГОМ <V ИМЯ> В ТЕКСТЕ)
# -----------------------------------------------------------------
def get_subtitles(request, film_id, language_code):
    """
    Отдает WebVTT файл по запросу клиента.
    Тег спикера <v Имя> добавляется в начало текста субтитра.
    Теги стилей <c.класс> добавляются, если указаны в поле style.
    """
    try:
        # Получаем набор субтитров с предварительной загрузкой строк
        subtitle_set = SubtitleSet.objects.prefetch_related('lines').get(
            film_id=film_id,
            language__iexact=language_code
        )
    except SubtitleSet.DoesNotExist:
        raise Http404(f"Набор субтитров ({language_code}) не найден.")

    vtt_content = "WEBVTT\n\n"

    for line in subtitle_set.lines.all().order_by('start_time'):
        start_time_vtt = format_time(line.start_time)
        end_time_vtt = format_time(line.end_time)

        # 1. Заголовок (время)
        vtt_content += f"{start_time_vtt} --> {end_time_vtt}\n"

        text_to_write = line.text

        # --- 2. ЛОГИКА ОБРАБОТКИ СТИЛЕЙ (классов) ---
        open_style_tags = ""
        close_style_tags = ""

        # Проверяем, есть ли стили и классы в JSON-поле
        if (line.style and isinstance(line.style, dict) 
            and 'classes' in line.style and isinstance(line.style['classes'], list)):
            
            # Итерируемся по списку классов (например, ["loud", "bold"])
            for class_name in line.style['classes']:
                cleaned_class_name = class_name.strip()
                if cleaned_class_name:
                    # Создаем открывающий тег <c.className>
                    open_style_tags += f"<c.{cleaned_class_name}>"
                    # Создаем закрывающие теги в обратном порядке (LIFO)
                    close_style_tags = "</c>" + close_style_tags
        # ---------------------------------------------

        # 3. Добавление тега спикера (<v Имя>)
        if line.name:
            speaker_name_cleaned = line.name.strip()
            # Добавляем VTT-тег спикера <v Name> в начало строки текста
            text_to_write = f"<v {speaker_name_cleaned}>{text_to_write}"

        # 4. Оборачиваем весь текст (с или без спикера) тегами стилей.
        # Пример: <c.loud><v Ivonn>текст</c>
        text_to_write = f"{open_style_tags}{text_to_write}{close_style_tags}"

        # 5. Добавление текста субтитра и пустой строки для разделения
        vtt_content += f"{text_to_write}\n\n"

    return HttpResponse(vtt_content, content_type="text/vtt; charset=utf-8")

@user_passes_test(check_admin)
def subtitle_edit(request, film_id):
    film = get_object_or_404(Film, id=film_id)

    # 1. Загружаем все доступные языки для этого фильма
    available_sets = SubtitleSet.objects.filter(film=film).order_by('language')
    available_languages = [s.language for s in available_sets]

    # Определяем текущий язык для редактирования
    current_lang = request.GET.get('lang', available_languages[0] if available_languages else None)

    subtitle_set = None
    formset = None

    if current_lang:
        try:
            subtitle_set = available_sets.get(language__iexact=current_lang)
            # Инициализируем Formset для существующего набора
            formset = SubtitleLineFormSet(request.POST or None, instance=subtitle_set)
        except SubtitleSet.DoesNotExist:
            # Если текущий язык не найден (например, был передан некорректно), игнорируем
            pass

    # --- Логика обработки POST-запроса ---
    if request.method == 'POST':
        # A. Обработка переключения/создания (Форма SubtitleSetSelectForm)
        if 'language_code' in request.POST:
            select_form = SubtitleSetSelectForm(request.POST)
            if select_form.is_valid():
                new_lang = select_form.cleaned_data['language_code'].strip().lower()
                is_new_request = select_form.cleaned_data.get('is_new', False)

                # Попытка найти существующий набор
                try:
                    found_set = SubtitleSet.objects.get(film=film, language__iexact=new_lang)
                    # Если нашли, просто переключаемся на него
                    messages.info(request, f'Переключено на язык: {new_lang.upper()}')
                    return redirect(f'{request.path}?lang={new_lang}')
                except SubtitleSet.DoesNotExist:
                    # Если не нашли и это запрос на создание
                    if is_new_request:
                        new_set = SubtitleSet.objects.create(film=film, language=new_lang)
                        messages.success(request, f'Создан новый набор субтитров для языка: {new_lang.upper()}')
                        return redirect(f'{request.path}?lang={new_lang}')

        # B. Обработка сохранения Formset
        elif formset and formset.is_valid():
            try:
                formset.save()
                messages.success(request, f'Субтитры ({current_lang}) успешно обновлены.')
                return redirect('films:film_detail', id=film.id)
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {e}')
        elif formset:
            messages.error(request, 'Обнаружены ошибки в форме. Пожалуйста, проверьте выделенные поля.')

    # 4. Рендеринг шаблона
    # Если набора еще нет (т.е. фильм без субтитров), formset будет пуст.
    # Создаем пустой Formset для рендеринга
    if not subtitle_set:
        SubtitleLineFormSet.extra = 1 # Добавим 1 пустую строку, чтобы было куда вводить
        formset = SubtitleLineFormSet(instance=SubtitleSet(film=film))
    else:
        # Убедимся, что empty_form доступна
        if not formset:
            formset = SubtitleLineFormSet(instance=subtitle_set)

    # Форма для переключения/добавления (не привязана к POST-данным)
    select_form = SubtitleSetSelectForm(initial={'language_code': current_lang})

    return render(request, 'films/subtitle_edit.html', {
        'film': film,
        'formset': formset,
        'current_lang': current_lang,
        'available_languages': available_languages,
        'select_form': select_form,
    })