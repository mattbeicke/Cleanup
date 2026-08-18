# Repository Instructions

## Protected files

- Never modify `todo.md`.
- Preserve unrelated user changes already present in the working tree.

## Log file preservation

- Never remove any log file.
- This applies to all log files, including tracked, ignored, and uncommitted
  files.

## Before changing code

- Ask clarifying questions before modifying code if the request is ambiguous,
  has multiple materially different implementations, or requires a product
  decision.
- If the requested change is clear and narrowly scoped, proceed without asking
  for confirmation.
- Do not make changes outside the scope of the user's request.

## Code comments

- Comment code as it is written or changed so a new maintainer can understand
  its purpose, important invariants, and non-obvious reasoning.
- Give new source and test files a file-level purpose comment or module
  docstring, and document new classes, functions, methods, fixtures, and tests.
- Add inline comments around tricky algorithms, state transitions, safety
  bounds, and behavior that would not be obvious from the code alone.
- Explain why the code works that way instead of merely restating individual
  statements.
- Update or remove comments when behavior changes so documentation never
  contradicts the implementation.

## Core premise

Cleanup Assistant is a local, safety-first Windows file-review tool. It helps a
person understand their files before acting, presents protected areas without
making them removable, and only ever moves user-selected items to the Recycle
Bin. The interface must make uncertainty explicit: recommendations are helpful
context, never authorization to delete something important. The server stays
on loopback, and its browser UI must remain responsive while inspecting large
folders.

## Progress tracking

- At the beginning of each new coding task, replace the contents of
  `progress.md` with:
    - the current objective;
    - relevant constraints;
    - completed work;
    - remaining work;
    - any blockers or decisions needed.
- Update `progress.md` after each meaningful implementation step.
- Do not create or update `progress.md` for read-only questions, reviews, or
  explanations.
- Before finishing a coding task, leave `progress.md` with an accurate final
  status so another agent can continue if necessary.
- Do not clear `progress.md` during an active task unless the user explicitly
  starts a different task.

## Verification

- Run the existing tests under `tests/` for code changes and verify that they still pass.
- Update existing tests when needed to keep them aligned with current behavior.
- Remove an existing test only when the functionality it covers has been removed.
- For code changes, verify that:
    1. the project compiles or passes its standard build check; and
    2. the existing test suite passes; and
    3. the application starts and reaches its normal initial state without an
       immediate error.
- If the correct build, test, or startup command cannot be determined from
  repository documentation or configuration, ask the user.
- Report exactly which verification commands were run and whether they passed.

## Running the application

- The application may be started briefly for verification.
- Stop every process started during verification before finishing.
- Do not leave a development server, watcher, or application process running.
- Do not open the application for the user; let the user run it themselves.
