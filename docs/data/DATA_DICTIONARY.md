# Data Dictionary

This is a pointer, not a copy. The authoritative data dictionary stays at the
repo root, alongside the numbered case files it describes, because both are
part of the current runtime/input set:

**→ [`/15_data_dictionary.md`](../../15_data_dictionary.md)**

## Why this isn't moved

The numbered case files (`01`–`15`) are live inputs referenced by the
application, its tests, and its evidence pipeline — not just presentation
material. Relocating them (including the data dictionary itself) is treated
as a separate, explicitly gated engineering change, out of scope for this
documentation pass. See `docs/architecture/TARGET_STATE_ARCHITECTURE.md` for
where a future data-layer reorganization would be proposed.
