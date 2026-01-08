import gettext
import os

LOCALE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "locales", "translations"
)
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "translations")


def set_language(lang="ENGLISH"):
    """Language set up"""
    try:
        lang_translation = gettext.translation(
            "messages", localedir=LOCALE_DIR, languages=[lang], fallback=True
        )
        lang_translation.install()
        return lang_translation
    except FileNotFoundError:
        print(f"Warning: Translation for language '{lang}' not found. Using English.")
        en_translation = gettext.translation(
            "messages", localedir=LOCALE_DIR, languages=["en"], fallback=True
        )
        en_translation.install()
        return en_translation


def get_text(language_code: str = "ENGLISH"):
    # language_code = "TGL"
    translation = set_language(language_code)
    T_ = translation.gettext
    return T_
