from django.core.management.base import BaseCommand
import json
import os
from urllib.request import urlopen
from urllib.error import HTTPError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from films.models import Country, Genre, Person, Film
from .get_films import Command as GetCommand


class Command(BaseCommand):
    help = 'Import films from json file (only new films are created)'

    def handle(self, *args, **options):
        self.create_films()

    @staticmethod
    def get_image_by_url(url):
        img_tmp = NamedTemporaryFile(delete=True)
        try:
            with urlopen(url) as uo:
                assert uo.status == 200
                img_tmp.write(uo.read())
                img_tmp.flush()
        except HTTPError:
            return None
        return File(img_tmp)

    def create_person(self, data):
        print(f"Processing PERSON «{data['name']}»")
        attrs = {"name": data['name'], "origin_name": data['enName']}

        try:
            if not data['birthday'].startswith("0000-"):
                attrs['birthday'] = data['birthday'][:10]
        except KeyError:
            pass

        photo_url = data.get('photo')
        person, created = Person.objects.get_or_create(
            kinopoisk_id=data['id'],
            defaults=attrs
        )

        if created and photo_url:
            image_file = self.get_image_by_url(photo_url)
            if image_file:
                person.photo.save(os.path.basename(photo_url), image_file)

        return person

    def create_film(self, data):
        print(f"Processing FILM «{data['name']}»")

        # ✔ НЕ создаём фильм, если он уже есть
        if Film.objects.filter(kinopoisk_id=data['id']).exists():
            print(f"  -> Film already exists, skipping.")
            return Film.objects.get(kinopoisk_id=data['id'])

        # ------ С О З Д А Н И Е  Н О В О Г О  Ф И Л Ь М А ------
        country_name = data['countries'][0]['name']
        country = Country.objects.get_or_create(name=country_name)[0]

        genres = []
        for g in data['genres']:
            genres.append(Genre.objects.get_or_create(name=g['name'])[0])

        director = None
        people = []

        for person_data in data['persons']:
            if not person_data.get('name'):
                continue

            if person_data['profession'] == 'режиссеры' and director is None:
                director = self.create_person(person_data)
            elif person_data['profession'] == 'актеры':
                people.append(self.create_person(person_data))

        cover_url = data.get('poster', {}).get('url')

        attrs = {
            "name": data["name"],
            "origin_name": data["enName"],
            "slogan": data["slogan"],
            "length": data["movieLength"],
            "description": data["description"],
            "year": data["year"],
            "director": director,
            "country": country,
        }

        try:
            attrs["trailer_url"] = data['videos']['trailers'][0]['url']
        except (KeyError, IndexError):
            pass

        # ✔ Создаём фильм, только если он не существует
        film = Film.objects.create(kinopoisk_id=data['id'], **attrs)
        film.people.set(people)
        film.genres.set(genres)

        # Скачиваем обложку только для нового фильма
        if cover_url:
            image_file = self.get_image_by_url(cover_url)
            if image_file:

                # Если в БД cover пустой, но физический файл существует — удаляем его
                if not film.cover:
                    file_name = os.path.basename(cover_url)
                    media_path = os.path.join('media', 'films', 'covers', file_name)

                    if os.path.exists(media_path):
                        print(f"Удаление старого файла постера: {media_path}")
                        os.remove(media_path)

                # Теперь загружаем новый постер
                film.cover.save(os.path.basename(cover_url), image_file)

        return film

    def create_films(self):
        with open(GetCommand.filename(), 'r') as f:
            films_data = json.load(f)
            total = len(films_data['docs'])
            print(f"Found {total} films in JSON.\n")

            for film_data in films_data['docs']:
                self.create_film(film_data)
