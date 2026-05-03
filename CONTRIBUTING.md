# Contributing

Thanks for contributing.

## Ground rules

- Do not commit Telegram exports.
- Do not commit generated analysis artifacts.
- Do not commit local virtual environments.
- Keep the project local-first. New features should not require cloud APIs by default.
- If you add model-based behavior, it should work with a local `Ollama` runtime unless there is a strong reason not to.

## Local setup

```bash
./scripts/setup_local.sh
```

Run tests:

```bash
make test
```

## Development workflow

1. Create a branch.
2. Make the smallest reasonable change.
3. Add or update tests.
4. Run `make test`.
5. Open a pull request with a short description of:
   - what changed
   - why it changed
   - how you tested it

## Areas that are especially useful

- Telegram export compatibility improvements
- better relationship scoring
- better report UX
- better group-chat analysis
- stronger privacy/documentation polish
- packaging and installation ergonomics

## Code style

- Prefer simple Python over framework-heavy abstractions.
- Keep the CLI usable without extra infrastructure.
- Keep output files explicit and easy to inspect.
- Avoid hiding important scoring logic behind opaque wrappers.
