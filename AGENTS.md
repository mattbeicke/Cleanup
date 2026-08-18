# Cleanup Assistant contributor notes

- Keep deletion safety-first: never permanently delete user content from the normal review flow.
- New classification rules belong in `src/cleanup_assistant/explainer.py` and should have tests.
- The scanner must not descend into protected directories such as `.git`, virtual environments, or OS-managed folders by default.
- Keep the core application dependency-light. `Send2Trash` is used only for recoverable deletion.
- Run `python -m pytest` before handing off a change.
- Always ask any questions before writing code, even if they seem minor.
- For each prompt update pyproject.toml the patch number of the SemVer. Increase the minor number if the change seems major enough. Don't touch the major number I will do it.
- Track all progress in a progress.md file. Ensure that it will be referencable and up to date if I must restart a session.