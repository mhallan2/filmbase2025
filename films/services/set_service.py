from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from films.models import SubtitleSet, Film


class SubtitleSetService:
    """
    Сервис для работы с объектом SubtitleSet — получение, создание, подготовка начальных данных.
    """

    def get(self, film_id, language):
        """
        Возвращает набор субтитров.
        """
        try:
            return SubtitleSet.objects.prefetch_related("lines").get(
                film_id=film_id, language__iexact=language
            )
        except SubtitleSet.DoesNotExist:
            return None

    def get_or_create(self, film, language):
        """
        Возвращает (subtitle_set, created_bool).
        """
        lang_norm = (language or "").strip()
        if not lang_norm:
            raise ValueError("Предъявите, пожалуйста, язык субтитров.")

        try:
            sset, created = SubtitleSet.objects.get_or_create(
                film=film, language=lang_norm
            )
            return sset, created
        except IntegrityError:
            sset = SubtitleSet.objects.filter(film=film, language__iexact=lang_norm).first()
            if sset:
                return sset, False
            raise

    def get_available_languages(self, film):
        """
        Список языков для указанного фильма.
        """
        available_langs = list(film.subtitle_sets.all().order_by('language').values_list('language', flat=True))
        return available_langs

    def build_style_initial(self, subtitle_set):
        if not subtitle_set:
            return []
        return subtitle_set.get_speaker_colors()

    def resolve_from_request(self, request, film_id):
        """
        Возвращает словарь с ключами: film, subtitle_set, current_lang, available_languages, is_new
        """
        film = get_object_or_404(Film, id=film_id)
        available_sets_qs = SubtitleSet.objects.filter(film=film).order_by('language')
        available_languages = [s.language for s in available_sets_qs]

        requested_lang = request.GET.get('lang') or request.GET.get('language')
        current_lang = requested_lang.upper() if requested_lang else (
            available_languages[0] if available_languages else None
        )
        is_new = request.GET.get('is_new') == 'True'

        subtitle_set = None
        if current_lang:
            subtitle_set = available_sets_qs.filter(language__iexact=current_lang).first()
            if subtitle_set is None and is_new:
                # try creating — caller will handle redirect or errors
                try:
                    subtitle_set = SubtitleSet.objects.create(film=film, language=current_lang)
                except IntegrityError:
                    subtitle_set = SubtitleSet.objects.filter(film=film, language__iexact=current_lang).first()
                except Exception:
                    subtitle_set = None

        return {
            'film': film,
            'subtitle_set': subtitle_set,
            'current_lang': current_lang,
            'available_languages': available_languages,
            'is_new': is_new,
        }