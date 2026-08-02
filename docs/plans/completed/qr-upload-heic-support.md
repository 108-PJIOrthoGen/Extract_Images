# Execution Plan: HEIC Input Support for QR Upload

Date: 2026-07-30

## Status

Completed

## Outcome

The existing extraction upload boundary accepts `image/heic` and `image/heif`,
decodes those files deterministically, and supplies JPEG image parts to the
existing VLM extraction pipeline.

## Context

- Product authority: workspace `new_goal.txt`; the user explicitly approved the
  required HEIC decoder dependency on 2026-07-30.
- Existing boundary: `src/extractor/api/routes.py`.
- Existing loaders: `src/extractor/loaders/constants.py` and
  `src/extractor/loaders/image_loader.py`.

## Scope

In scope:

- `pillow-heif` dependency and HEIC/HEIF MIME/extension registration.
- Decode-to-JPEG data URL handling without changing downstream VLM contracts.
- Focused API and loader tests.

Out of scope:

- Preserving HEIC metadata after extraction.
- Supporting arbitrary RAW camera formats.

## Approach

1. Extend accepted MIME types/extensions.
2. Register the HEIF Pillow opener and encode decoded frames as JPEG data URLs.
3. Add tests and run the Python suite.

## Risks And Recovery

- Native wheel availability is validated through the repository lock/test flow.
- Rollback removes the dependency and HEIC/HEIF constants/loader branch.

## Progress

- [x] Product decision confirmed.
- [x] Existing upload boundary inspected.
- [x] Implement HEIC support.
- [x] Run focused and repository-wide validation.

## Decisions

- 2026-07-30: Convert HEIC/HEIF to high-quality JPEG in memory so downstream VLM
  providers receive a widely supported media type.

## Validation

- `uv run --extra dev --with-editable . pytest -q`: 75 passed.
- `ruff check .`: passed.
- `ruff format --check .`: 43 files already formatted.
- `mypy`: no issues in 30 source files.
- GitNexus change detection reported medium risk in the existing image-loading
  process; the complete Python validation suite passed.

## Result

HEIC and HEIF are accepted at the upload boundary and decoded through
`pillow-heif` into high-quality in-memory JPEG content for the existing VLM
pipeline. The dependency lock and product README are current.
