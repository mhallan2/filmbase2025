from django.core.exceptions import ValidationError

class SubtitleLineService:
    """
    Логика по сохранению lines formset.
    """

    def save_formset(self, formset):
        """
        Ожидается валидный formset (formset.is_valid() уже вызван).
        Мы вызываем full_clean() на каждом экземпляре (для модел-валидации), затем сохраняем.
        Возвращает tuple (ok: bool, errors: None or dict)
        """
        if not hasattr(formset, 'is_valid'):
            raise TypeError("Expected formset instance.")

        if not formset.is_valid():
            return False, formset.errors

        instances = formset.save(commit=False)

        for inst in instances:
            try:
                inst.full_clean()
            except ValidationError as e:
                return False, {'model_validation': e.messages}

        formset.save()
        return True, None