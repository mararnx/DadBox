# DadBox

Hardware + software maker project. See `docs/BRIEF.md` for what it actually is
— if that file is still a template, ask before assuming a platform or stack.

## Conventions

- Firmware in `firmware/`, host-side code in `software/`. Keep the wire protocol
  between them documented in `docs/` rather than only in code.
- Hardware choices that were not obvious get an ADR in `docs/decisions/`.
- Every bench session gets an entry at the top of `docs/BUILD-LOG.md`.
- Part numbers and prices live in `hardware/bom/bom.csv`, not scattered in prose.
- Never commit secrets — Wi-Fi credentials and API keys go in `.env` (gitignored)
  or a gitignored `secrets.h`.
