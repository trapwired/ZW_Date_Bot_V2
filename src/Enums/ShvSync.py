from enum import IntEnum


class ShvDecisionKind(IntEnum):
    """Which question the SHV schedule sync asked the admins."""
    CREATE = 1         # SHV game with no bot counterpart: import it?
    ADOPT = 2          # bot game on the same date, different opponent: same game?
    DELETE_VANISHED = 3  # SHV-linked bot game gone from the feed: delete it?
    DELETE_MANUAL = 4    # manually entered game never on SHV: delete it?
    BULK_IMPORT = 5      # empty schedule: import the whole SHV feed at once?


class ShvDecisionStatus(IntEnum):
    PENDING = 1   # asked, no answer yet (answered-yes rows are deleted)
    DECLINED = 2  # answered no; kind decides if/when it is re-asked
