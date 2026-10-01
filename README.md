# deep_merge

Merge nested mappings with explicit, predictable rules for lists and nulls. Zero dependencies, Python 3.8+.

## Usage

```python
from deep_merge import merge, MergeConfig

base = {"user": {"name": "Ada", "roles": ["admin"]}, "meta": {"created": "2024-01-01"}}
patch = {"user": {"roles": ["ops"], "email": "ada@example.org"}, "meta": {"created": None}}

result = merge(base, patch)
# {"user": {"name": "Ada", "roles": ["ops"], "email": "ada@example.org"}, "meta": {}}

# If you want None to overwrite instead of delete:
merge(base, patch, config=MergeConfig(null_deletes=False))
```

The package also exports `deep_merge` as an alias for `merge`.

## Why this exists

Most deep-merge libraries try to guess what you mean by "merge lists" — concatenate, union, index-zip, replace. All of them are wrong in some context. This library picks one answer and states it plainly: **lists are scalars**. A list in the source replaces the list in the destination, full stop. If you need list-aware merging, do it before you call `merge`.

The other deliberate choice is how `None` is handled. A `None` value in the source **deletes** the corresponding key from the result. This lets a patch express "remove this field" without knowing the target's shape. If you want `None` to overwrite instead, pass `MergeConfig(null_deletes=False)`.

## Edge cases you will hit

- **Non-dict mappings** (e.g. `OrderedDict`) are accepted on input but the output is always a plain `dict`. The input type is not preserved.
- **Mutable non-dict values** (lists, sets) in the source are stored in the result by reference. Mutating the result's list will mutate the source's list. This is intentional and documented; copy before merging if you need isolation.
- **`None` over a dict** deletes the whole dict, because deletion is checked before the recursive-mapping branch. This is the point of the rule — `None` means "remove", not "replace with null".
- The **destination is never mutated**. Nested dicts that survive into the result are shallow-copied so writes into the result do not leak back into the destination.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

