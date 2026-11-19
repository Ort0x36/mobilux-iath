"""Translation catalogues and helpers.

Strings live in translations/<code>.json. Nested keys are addressed with dots,
e.g. t("home.hero.title"). Italian is the default and the fallback language.
To add a language, create its JSON file and add an entry to LANGUAGES.
"""
import json
import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "it"
LANGUAGE_COOKIE = "lang"

# Order matters: it is the order shown in the language selector.
LANGUAGES = {
    "it": {"name": "Italiano", "short": "IT", "hreflang": "it-IT", "og_locale": "it_IT"},
    "en": {"name": "English", "short": "EN", "hreflang": "en", "og_locale": "en_GB"},
}

_DIR = Path(__file__).with_name("translations")


def _flatten(data, prefix=""):
    flat = {}
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, path + "."))
        else:
            flat[path] = value
    return flat


CATALOGS = {
    code: _flatten(json.loads((_DIR / f"{code}.json").read_text(encoding="utf-8")))
    for code in LANGUAGES
}


def missing_keys():
    """Return {language: keys present in the default catalogue but missing here}."""
    reference = set(CATALOGS[DEFAULT_LANGUAGE])
    return {
        code: sorted(reference - set(catalog))
        for code, catalog in CATALOGS.items()
        if reference - set(catalog)
    }


for _code, _keys in missing_keys().items():
    log.warning("Missing %s translations: %s", _code, ", ".join(_keys))


def translate(lang, key, **params):
    value = CATALOGS.get(lang, {}).get(key)
    if value is None:
        log.warning("Missing translation for %r in %r", key, lang)
        value = CATALOGS[DEFAULT_LANGUAGE].get(key, key)
    if params and isinstance(value, str):
        value = value.format(**params)
    return value


def format_date(lang, iso_value):
    """Format a YYYY-MM-DD string as e.g. '17 dicembre 2026' / '17 December 2026'."""
    try:
        parsed = date.fromisoformat(iso_value)
    except (TypeError, ValueError):
        return iso_value
    month = translate(lang, "months")[parsed.month - 1]
    return f"{parsed.day} {month} {parsed.year}"
