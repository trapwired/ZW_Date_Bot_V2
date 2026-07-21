"""Base for hand-written Repository stubs.

Implements every abstract method of the Repository seam with a loud failure, so a
test double can override just the two or three calls its scenario exercises while
still being a real Repository. Two things this buys over a bare class: a stub can
never satisfy a test by accident (unstubbed calls raise, they don't return None),
and a renamed interface method turns the double's now-dead override into a loud
miss instead of silently passing.
"""
from data.Repository import Repository


def _unstubbed(name):
    def fail(self, *args, **kwargs):
        raise AssertionError(f'{type(self).__name__} does not stub {name}()')
    return fail


# Built from the ABC itself, so the base tracks the interface without maintenance.
StubRepository = type('StubRepository', (Repository,),
                      {name: _unstubbed(name) for name in Repository.__abstractmethods__})
