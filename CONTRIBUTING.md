# Making and sharing changes

Start with [the development guide](docs/development.md) for setup and a map of the code. Use a branch for each feature or issue so changes are easy to review and undo.

## Start a change

From the repository root, check for unfinished work before switching branches. Commit or otherwise preserve that work first.

```powershell
git status
git switch main
git pull --ff-only
git switch -c feature/short-description
```

For an issue, use a descriptive branch such as `fix/12-history-order`. Make the change locally and exercise the affected screen or API. Keep unrelated changes in separate commits.

## Check your work

From `backend`, run the API tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

From `frontend`, run the tests, TypeScript/production build, and lint:

```powershell
npm test
npm run build
npm run lint
```

Run checks for the parts you changed; for a change spanning the app, run both sets. Documentation-only edits need a review of their instructions and links rather than application tests. When changing behavior, add a test that would catch the bug or protect the new behavior. For database changes, verify migrations separately as described in the development guide.

Before sharing a UI change, check its loading, empty, success, and error states where relevant, and try a phone-sized viewport. For privacy or group changes, try two different development users.

## Commit and push

From the repository root:

```powershell
git diff --check
git diff
git status --short
```

Stage the specific files you intended to change. For example, for a UI edit:

```powershell
git add frontend/src/App.tsx frontend/src/styles.css
git diff --cached
git commit -m "Improve log form layout"
git push -u origin HEAD
```

Substitute your actual paths and commit message. Keep credentials, `.env` files, local databases, and generated dependency/build folders out of commits. The repository's `.gitignore` covers the standard local artifacts.

Open a pull request on GitHub from your branch into `main`. Explain what changed, how you checked it, and include a screenshot for visible changes. Add `Closes #12` to the description when the PR fully resolves issue 12. After merging, switch to `main` and run `git pull --ff-only` before starting the next branch.

## Writing useful issues

For a bug, include what you expected, what happened, steps to reproduce, the screen involved, and whether it happened locally or in production. A screenshot and relevant error text help; remove personal data and secrets.

For a feature, describe who needs it, what they should be able to do, and a few concrete conditions that would make it complete. You can hand an issue number to Codex or implement it yourself using the same workflow.
