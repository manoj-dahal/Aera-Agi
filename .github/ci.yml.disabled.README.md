# CI Workflow (disabled)

`ci.yml.disabled` is the ready-to-use GitHub Actions workflow.

The Arena GitHub App lacks `workflows` permission, so it cannot push files
into `.github/workflows/`. To enable CI, move it manually:

```bash
mkdir -p .github/workflows
git mv .github/ci.yml.disabled .github/workflows/ci.yml
git commit -m "ci: enable GitHub Actions workflow"
git push
```
