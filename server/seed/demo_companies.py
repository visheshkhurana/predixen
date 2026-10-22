"""Which company rows under the demo account may be written to, and which deleted.

HAG-646 made the demo seed run for the demo account on every login instead of
only outside production, which is what lets production heal a renamed company or
a wiped financials row. The cost is that the duplicate-company cleanup in
``seed_demo.py`` also runs on every login -- and the demo password is public, so
"every login" means "any visitor's login". A visitor who created a second
company under the shared demo account had it deleted when the next visitor
arrived, and the rename that follows could rewrite whichever row
``.first()`` happened to return.

So the seed marks the rows it created, and only marked rows are ever deleted or
renamed::

    companies.metadata_json["seed_created"] is True

That key lives in an existing JSON column, so there is no migration. It is
written through ``save_metadata_value``, which merges one key rather than
replacing the blob, so a concurrent writer cannot drop it on the path the seed
takes.

What the mark is not:

- **Not ``is_sample``.** That flag is visitor-triggerable -- the sample-data and
  sample-company routes set it on the caller's own company -- so keying a delete
  on it would delete the very row it looks like it protects. A row carrying
  ``{"is_sample": True}`` is *not* seed-created.
- **Not a shape test** (name, website, stage, a company_state row). Every
  company the API creates has those; content is not provenance.

Everything here is pure and takes plain ``id`` / ``metadata_json`` attributes,
so it can be tested without a database. The single write is injectable.
"""

import logging
from typing import Any, Optional, Sequence

from server.core.company_metadata import save_metadata_value

SEED_MARKER = "seed_created"
# Beside the marker, not inside it: a row the bootstrap GUESSED was the
# seed's is marked, and only this key says the provenance was inferred.
# The guess has to survive the run that made it, because the rename it
# authorises happens later. Both keys are written in ONE commit (see
# ``ensure_seed_marked``): committing them separately leaves a window where the
# row reads as provenance with the guess absent, and a death in that window is
# how the next run comes to rename a visitor's company while saying nothing.
SEED_GUESSED = "seed_guessed"

logger = logging.getLogger(__name__)


def _metadata(row: Any) -> Any:
    return getattr(row, "metadata_json", None)


def is_seed_created(metadata: Any) -> bool:
    """True only for a dict that carries the marker set to a literal ``True``.

    A missing key, a non-dict blob, ``False`` and the string ``"true"`` are all
    not provenance. The strict test matters in the direction that loses data:
    anything uncertain must read as "not the seed's", because the only thing
    this predicate authorises is deletion.
    """
    if not isinstance(metadata, dict):
        return False
    return metadata.get(SEED_MARKER) is True


def is_seed_guess(metadata: Any) -> bool:
    """True only when the marker on this row came from the bootstrap's guess.

    Strict for the same reason as ``is_seed_created``: this only ever adds a
    warning, but a mark that read as a guess when it was not would make the
    seed cry wolf on every rename.
    """
    if not isinstance(metadata, dict):
        return False
    return metadata.get(SEED_GUESSED) is True


def pick_primary_id(rows: Sequence[Any]) -> Optional[int]:
    """The id of the first marked row, or ``None`` when nothing is marked.

    The caller queries ordered by id, so this is the lowest-id marked row. It is
    deliberately not the lowest-id row: a visitor's company can hold that id.
    """
    for row in rows:
        if is_seed_created(_metadata(row)):
            return row.id
    return None


def needs_bootstrap(rows: Sequence[Any]) -> bool:
    """True when no row under the demo account carries the marker.

    That is the state of every account before this marker first ships -- and,
    because a whole-blob writer elsewhere can drop the key, it is also a state
    that can come back. Either way the bootstrap below is a guess, so it warns.
    """
    return pick_primary_id(rows) is None


def rows_to_purge(rows: Sequence[Any], primary_id: Optional[int]) -> list:
    """Marked rows other than the primary, in the order they were given.

    Unmarked rows are never returned, so a visitor's company is never deleted.
    With no primary (nothing marked) nothing is returned: the delete fails
    closed, at the price of leaving an unmarked duplicate seed row in place. That
    row is stranded, not pending -- nothing re-marks an old duplicate, so no later
    run collects it -- and the bootstrap WARNING that explains the state fires
    once, on the run that re-marked.
    """
    return [
        row
        for row in rows
        if row.id != primary_id and is_seed_created(_metadata(row))
    ]


def ensure_seed_marked(
    db: Any,
    rows: Sequence[Any],
    save=save_metadata_value,
) -> Optional[int]:
    """Return the primary company id, marking the seed's row first if needed.

    Everything already marked is trusted and nothing is written. When nothing is
    marked this makes the one-time bet the marker needs to exist at all: the
    lowest-id company under the demo account is taken to be the seed's. That bet
    is allowed because the seed creates its company in the same run as the demo
    user, so it holds the lowest id. It is still a guess, and it is worth saying
    how it goes wrong: if a **visitor** created the lowest-id company, that is
    the row marked here, and the seed's own row stays unmarked and is never
    healed. The pick is loud once -- the WARNING below names the id it chose and
    how many rows it chose from -- so the guess is also recorded under
    ``seed_guessed``, which is what lets every later run recognise the row
    instead of trusting it. A later run refuses to rename a row carrying that
    key (``seed_demo_data``) and warns again on every run it refuses: prevention
    rather than detection, because a rename that already happened cannot be
    undone by an alarm.

    Returns ``None`` when the account has no companies; the caller then creates
    (and marks) a fresh one.
    """
    primary_id = pick_primary_id(rows)
    if primary_id is not None:
        return primary_id
    if not rows:
        return None

    primary = rows[0]
    logger.warning(
        "Demo seed: no company under the demo account has metadata_json[%r]; "
        "treating the lowest id (%s) as the seed's own, chosen from %d row(s). "
        "If that row was not created by the seed, it will be renamed and any "
        "marked duplicates removed.",
        SEED_MARKER,
        primary.id,
        len(rows),
    )
    # One transaction for both keys, and it is the caller's ``db`` that commits.
    # ``save_metadata_value``'s default is ``commit=True``, so the obvious form
    # of this is two commits - and a death between them leaves the marker on the
    # row with the guess missing. That state is indistinguishable from
    # provenance, so the next run skips the bootstrap and renames a visitor's
    # company with nothing at WARNING from ``seed_demo``: this card's original
    # harm, on a one-statement window. Measured before this fix, with a death
    # injected between the two writes and an ordinary second run:
    #   run1 raised: process died between the two marker writes
    #   run1 state: name="A Visitor's Co" meta={'is_sample': True, 'seed_created': True}
    #   run2 state: name='TechFlow Analytics' meta={'seed_created': True}
    # With both writes uncommitted and this commit after the second, the same
    # injected death leaves ``meta={'is_sample': True}`` and run 2 emits both the
    # bootstrap and the rename-refusal warnings.
    save(db, primary, SEED_MARKER, True, commit=False)
    save(db, primary, SEED_GUESSED, True, commit=False)
    db.commit()
    return primary.id
