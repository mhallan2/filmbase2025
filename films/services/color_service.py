from django.core.exceptions import ValidationError

class SubtitleColorService:
    """
    Управление картой цветов (initial и применение formset).
    Делегирует сохранение модели SubtitleSet.save_colors(formset).
    """

    def initial_from_set(self, subtitle_set):
        if not subtitle_set:
            return []
        return subtitle_set.get_speaker_colors()

    def apply_formset(self, subtitle_set, formset):
        """
        Применить formset с цветами к subtitle_set.
        Возвращает (ok: bool, message_or_errors)
        """
        if not hasattr(formset, 'is_valid'):
            raise TypeError("Expected a formset instance")

        # Проверяем валидность
        if not formset.is_valid():
            return False, formset.errors

        try:
            subtitle_set.save_colors(formset)
            return True, None
        except ValidationError as e:
            return False, e.messages
        except Exception as e:
            return False, str(e)