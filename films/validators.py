import re
from django.core.exceptions import ValidationError

def LanguageCodeValidator(value):
    """
    Разрешает только латинские буквы (a-z, A-Z), длина 2–5 символов.
    Например: en, fr, ru, zh, pt-br и т.п.
    """
    regex = r"^[A-Za-z]{2}$"

    if not re.fullmatch(regex, value):
        raise ValidationError("Код языка должен состоять ровно из двух латинских букв.")
