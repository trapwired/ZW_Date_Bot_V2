"""The localization core: language resolution, t() fallbacks, and the
label-to-command reverse map that keeps localized reply keyboards routable."""
import pytest

import localization.CommandLabels as CommandLabels
import localization.Translator as Translator
from localization.LanguageContext import current_language, language_context
from localization.Languages import resolve_user_language
from localization.Translator import t


@pytest.fixture
def catalogs(monkeypatch):
    """A tiny controlled catalog so these tests don't depend on real translations;
    the CommandLabels reverse map is cached, so it is reset around each test."""
    monkeypatch.setattr(Translator, '_catalogs', {
        'de': {
            'Hello {name}!': 'Hallo {name}!',
            'Events': 'Termine',
            'broken placeholders': 'kaputt {oops}',
        },
        'gsw': {'Events': 'Termin'},
        'fr': {}, 'it': {},
    })
    monkeypatch.setattr(CommandLabels, '_reverse_map', None)
    yield
    CommandLabels._reverse_map = None


def test_resolution_explicit_choice_beats_client_language():
    assert resolve_user_language('it', 'de-CH') == 'it'


def test_resolution_falls_back_to_client_language_then_english():
    assert resolve_user_language(None, 'de-CH') == 'de'
    assert resolve_user_language(None, 'pt-BR') == 'en'
    assert resolve_user_language(None, None) == 'en'
    assert resolve_user_language('xx', 'fr') == 'fr'  # an invalid saved value self-heals


def test_default_language_is_english():
    assert current_language() == 'en'
    assert t('Hello {name}!', name='Zoe') == 'Hello Zoe!'


def test_translates_in_ambient_language(catalogs):
    with language_context('de'):
        assert t('Hello {name}!', name='Zoe') == 'Hallo Zoe!'


def test_missing_key_falls_back_to_english(catalogs):
    with language_context('fr'):
        assert t('Hello {name}!', name='Zoe') == 'Hello Zoe!'


def test_placeholder_drift_falls_back_to_english(catalogs):
    with language_context('de'):
        assert t('broken placeholders') == 'kaputt {oops}'  # no params: raw template
        # With params the drifted template raises internally and the English text wins.
        Translator._catalogs['de']['Hello {name}!'] = 'Hallo {typo}!'
        assert t('Hello {name}!', name='Zoe') == 'Hello Zoe!'


def test_reverse_map_folds_any_language_to_the_canonical_command(catalogs):
    assert CommandLabels.canonical_command('Termine') == 'events'   # de label
    assert CommandLabels.canonical_command('termin') == 'events'    # gsw label, stale keyboard
    assert CommandLabels.canonical_command('Events') == 'events'    # canonical always works
    assert CommandLabels.canonical_command('random text') == 'random text'
    assert CommandLabels.canonical_command('/start') == '/start'


def test_display_label_localizes_keyboard_buttons(catalogs):
    with language_context('de'):
        assert CommandLabels.display_label('events') == 'Termine'
        assert CommandLabels.display_label('/privacy') == '/privacy'
        assert CommandLabels.display_label('unmapped') == 'Unmapped'


def test_ambiguous_labels_across_commands_fail_loudly(catalogs):
    Translator._catalogs['de']['Admin'] = 'Termine'  # collides with Events
    with pytest.raises(ValueError):
        CommandLabels.canonical_command('anything')
