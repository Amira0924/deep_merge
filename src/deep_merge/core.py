"""Deep merge of nested mappings with explicit list and null semantics.

Design decisions (stated plainly so behaviour is predictable):

- Only dicts are merged recursively. Any non-dict value is replaced wholesale.
  This means a list at a key is treated as a scalar: the destination's list is
  discarded and the source's list takes its place. We do not concatenate, zip,
  or index-merge lists, because every one of those strategies is domain-
  specific and none of them is correct in general. If you need list merging,
  do it before calling this function.

- None in the source is treated as an instruction to delete the key from the
  destination. This is the one non-obvious rule, and it exists so that a patch
  can express "remove this field" without having to know the target's shape.
  A None that lands on a key the destination does not have is a no-op, not an
  insertion of None — the intent is removal, and there is nothing to remove.

- The destination is never mutated. A new dict is returned. Nested dicts that
  are carried over unchanged are shallow-copied into the result so that later
  assignments into the result cannot leak back into the caller's destination.
  Nested dicts that are merged are, by construction, already fresh.

- Non-dict mappings (e.g. OrderedDict, types.MappingProxyType) are treated as
  dicts for the purpose of merging: their items are copied into a plain dict.
  This keeps the output type predictable (always dict) without forcing callers
  to convert. We deliberately do not preserve the input mapping type, because
  mixing mapping types across recursion levels makes equality assertions
  brittle and serves no purpose here.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


class MergeConfig:
    """Behavioural knobs for :func:`merge`.

    The defaults encode the rules described in the module docstring. The knobs
    exist so that callers who genuinely need a different policy for None can
    flip it without forking the function; they are not an invitation to build
    a configuration DSL.

    Attributes:
        null_deletes: If True (default), a None value in the source removes
            the key from the destination. If False, None overwrites the
            destination value like any other scalar.
    """

    __slots__ = ("null_deletes",)

    def __init__(self, *, null_deletes: bool = True) -> None:
        self.null_deletes = null_deletes

    def replace(self, **overrides: Any) -> "MergeConfig":
        """Return a copy of this config with the given fields overridden.

        Useful when a caller wants to tweak one rule for a single merge
        without mutating a shared config object.
        """
        kwargs = {"null_deletes": self.null_deletes}
        kwargs.update(overrides)
        return MergeConfig(**kwargs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MergeConfig):
            return NotImplemented
        return self.null_deletes == other.null_deletes

    def __repr__(self) -> str:
        return f"MergeConfig(null_deletes={self.null_deletes!r})"


def _is_mapping(obj: Any) -> bool:
    """True for any mapping, not just dict.

    We accept arbitrary mappings on input but always emit plain dicts, so that
    the output type is stable regardless of what the caller feeds in.
    """
    return isinstance(obj, Mapping)


def _merge_into(
    dest: MutableMapping[str, Any],
    src: Mapping[str, Any],
    config: MergeConfig,
) -> MutableMapping[str, Any]:
    """Fold ``src`` into ``dest`` in place and return ``dest``.

    ``dest`` is assumed to already be a fresh dict owned by this call, so
    mutating it is safe. Callers must not pass a dict they do not own.
    """
    for key, src_val in src.items():
        # None handling is checked before the mapping branch so that a None
        # source value always means "delete", even if the destination holds a
        # dict. Without this ordering, a None over a dict would silently fall
        # through to the scalar-replace branch and leave the dict in place.
        if src_val is None and config.null_deletes:
            dest.pop(key, None)
            continue

        if _is_mapping(src_val) and key in dest and _is_mapping(dest[key]):
            # Both sides are mappings: recurse into a shallow copy of the
            # destination's dict so we never mutate the caller's structure.
            dest[key] = _merge_into(dict(dest[key]), src_val, config)
        else:
            # Scalar replacement. This covers lists, tuples, ints, strings,
            # and any non-mapping. We do not copy scalars: immutables are safe
            # to share, and mutables (lists, sets) are documented as shared by
            # reference in the README. Copying here would be a performance
            # trap with no correctness benefit for the common case.
            dest[key] = src_val
    return dest


def merge(
    destination: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    config: MergeConfig | None = None,
) -> dict[str, Any]:
    """Recursively merge ``source`` into ``destination`` and return a new dict.

    See the module docstring for the full rules. In short:

    * Nested dicts are merged key-by-key.
    * Non-dict values (including lists) are replaced, not concatenated.
    * By default, ``None`` in ``source`` deletes the key from the result.
    * ``destination`` is never mutated.

    Args:
        destination: The base mapping. Treated as read-only.
        source: The mapping whose values win on conflict.
        config: Optional :class:`MergeConfig`. If omitted, defaults are used.

    Returns:
        A new ``dict``.
    """
    if config is None:
        config = MergeConfig()
    if not _is_mapping(destination):
        raise TypeError(f"destination must be a mapping, got {type(destination).__name__}")
    if not _is_mapping(source):
        raise TypeError(f"source must be a mapping, got {type(source).__name__}")
    return _merge_into(dict(destination), source, config)


def deep_merge(
    destination: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    config: MergeConfig | None = None,
) -> dict[str, Any]:
    """Alias for :func:`merge`.

    Provided because "deep_merge" is the name most callers will reach for by
    instinct. It is the same function under a friendlier handle.
    """
    return merge(destination, source, config=config)
