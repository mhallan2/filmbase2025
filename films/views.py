from dal import autocomplete
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import user_passes_test
from .models import Country, Film, Genre, Person, SubtitleSet
from .forms import CountryForm, GenreForm, FilmForm, PersonForm
from .helpers import paginate
from django.contrib import messages
from django.http import HttpResponse, Http404
import json


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


def film_detail(request, id):
    queryset = Film.objects.prefetch_related("country", "genres", "director",
                                             "people")
    film = get_object_or_404(queryset, id=id)
    speaker_color_map = {}
    target_set = None
    target_lang = 'fr' # Добавим, чтобы избежать ошибки Reverse, если не найдено

    try:
        # 1. Сначала, пробуем получить русский набор (приоритет)
        target_set = film.subtitle_sets.get(language__iexact='ru')
    except SubtitleSet.DoesNotExist:
        try:
            # 2. Если русского нет, пробуем получить любой первый попавшийся набор
            target_set = film.subtitle_sets.first()
        except Exception:
            pass

    if target_set:
        speaker_color_map = target_set.speaker_color_map
        target_lang = target_set.language # Сохраняем найденный язык

    # 🛑 УДАЛИТЬ: Не используем json.dumps()
    # speaker_color_map_json = json.dumps(speaker_color_map)

    return render(request, 'films/film/detail.html',
                  {'film': film,
                   'speaker_color_map': speaker_color_map, # ✅ Передаем Python-словарь
                   'target_lang': target_lang}) # ✅ Передаем язык для URL


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

def get_subtitles(request, film_id, language_code):
    """
    Отдает WebVTT файл по запросу клиента.
    """
    try:
        # Убедимся, что используем prefetch_related, как было ранее
        subtitle_set = SubtitleSet.objects.prefetch_related('lines').get(
            film_id=film_id,
            language__iexact=language_code
        )
    except SubtitleSet.DoesNotExist:
        from django.http import Http404
        raise Http404(f"Набор субтитров ({language_code}) не найден.")

    vtt_content = "WEBVTT\n\n"

    for line in subtitle_set.lines.all().order_by('start_time'):
        start_time_vtt = format_time(line.start_time)
        end_time_vtt = format_time(line.end_time)

        # Начало строки времени
        time_line = f"{start_time_vtt} --> {end_time_vtt}"

        # 1. КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Добавление тега спикера <v Имя> к СТРОКЕ ВРЕМЕНИ
        if line.name:
            speaker_name_cleaned = line.name.strip()
            # Добавляем VTT-тег спикера <v Name> к строке времени, через пробел
            time_line += f" <v {speaker_name_cleaned}>"

        # 2. Заголовок (время) с опциональным спикером и переносом строки
        vtt_content += f"{time_line}\n"

        # 3. Добавление текста субтитра
        # Мы берем чистый текст, так как имя спикера уже добавлено в time_line
        vtt_content += f"{line.text}\n\n"

    return HttpResponse(vtt_content, content_type="text/vtt; charset=utf-8")