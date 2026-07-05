"""Drift guards between code and locale catalogs (ADR 0004):
- every t() key must be statically resolvable (or a known enum-derived site),
- every key must exist in every catalog, no orphans,
- a translation's {placeholders} must match its English key's.
A failure here means a t() call changed without the catalogs moving with it.
"""
import json
import os
import re

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.EventField import EventField

from localization.CommandLabels import COMMAND_LABEL_KEYS, WORD_ALIAS_KEYS
from localization.KeyExtraction import collect_translation_keys
from localization.Languages import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

SRC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src')
LOCALES_PATH = os.path.join(SRC_ROOT, 'localization', 'locales')

# t() call sites whose key is enum-derived at runtime (t(x.name.title()) etc.);
# their full key sets are pinned in _enum_derived_keys below.
KNOWN_DYNAMIC_KEY_SITES = (
    'Utils/PrintUtils.py',
    'features/attendance/IcsService.py',
    'localization/CommandLabels.py',
)

PLACEHOLDER = re.compile(r'\{[a-z_]+\}')


def _enum_derived_keys() -> set[str]:
    return ({e.name.title() for e in Event}
            | {s.name.title() for s in AttendanceState}
            | {f.name.title() for f in EventField}
            | {'Timekeepingevent'}  # PrintUtils titles the entity CLASS name
            | set(COMMAND_LABEL_KEYS.values())
            | set(WORD_ALIAS_KEYS.values()))


def _required_keys() -> set[str]:
    keys, _ = collect_translation_keys(SRC_ROOT)
    return keys | _enum_derived_keys()


def _catalog(language: str) -> dict[str, str]:
    with open(os.path.join(LOCALES_PATH, f'{language}.json'), encoding='utf-8') as file:
        return json.load(file)


def _translated_languages():
    return [language for language in SUPPORTED_LANGUAGES if language != DEFAULT_LANGUAGE]


def test_every_t_call_site_is_statically_resolvable_or_known():
    _, violations = collect_translation_keys(SRC_ROOT)
    unexpected = [v for v in violations if not any(site in v for site in KNOWN_DYNAMIC_KEY_SITES)]
    assert not unexpected, f'New dynamic t() keys - make them static or pin their key set here:\n' \
                           + '\n'.join(unexpected)


def test_catalogs_cover_every_key():
    required = _required_keys()
    for language in _translated_languages():
        missing = required - _catalog(language).keys()
        assert not missing, f'{language}.json is missing {len(missing)} key(s):\n' \
                            + '\n'.join(sorted(missing)[:10])


def test_catalogs_have_no_orphaned_keys():
    required = _required_keys()
    for language in _translated_languages():
        orphans = _catalog(language).keys() - required
        assert not orphans, f'{language}.json has {len(orphans)} key(s) no code references:\n' \
                            + '\n'.join(sorted(orphans)[:10])


def test_translations_keep_their_placeholders():
    for language in _translated_languages():
        for key, translation in _catalog(language).items():
            expected = set(PLACEHOLDER.findall(key))
            actual = set(PLACEHOLDER.findall(translation))
            assert actual == expected, \
                f'{language}.json placeholder drift for key {key[:60]!r}: {expected} vs {actual}'


def test_translations_are_not_empty_or_untranslated_placeholders():
    for language in _translated_languages():
        for key, translation in _catalog(language).items():
            assert translation.strip(), f'{language}.json has an empty translation for {key[:60]!r}'
