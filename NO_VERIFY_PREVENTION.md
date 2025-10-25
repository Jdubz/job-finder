# --no-verify Prevention System

This repository has multiple layers of protection to prevent the use of `--no-verify` flags in git commands.

## Why --no-verify is Forbidden

The `--no-verify` flag bypasses essential quality checks including:
- Linting (code quality and style)
- Type checking (TypeScript errors)
- Unit tests (functionality verification)
- Pre-commit and pre-push hooks

Using `--no-verify` can lead to:
- Broken code in the repository
- CI/CD pipeline failures
- Wasted debugging time
- Violation of code quality standards

## Prevention Mechanisms

### 1. Git Aliases
- `git commit` and `git push` are overridden to detect and block `--no-verify`
- Safe alternatives: `git safe-commit` and `git safe-push`

### 2. Enhanced Husky Hooks
- Pre-commit and pre-push hooks detect bypass attempts
- Provide helpful error messages and fix suggestions

### 3. Wrapper Scripts
- `scripts/prevent-no-verify.sh` - Main prevention script
- `scripts/git-wrapper.sh` - Git command wrapper

## How to Use

### Normal Workflow
```bash
# Make your changes
git add .
git commit -m "Your commit message"
git push origin branch-name
```

### If Hooks Fail
1. **Read the error message** - it tells you exactly what's wrong
2. **Fix the issues**:
   - Linting errors: `npm run lint:fix`
   - Type errors: Fix TypeScript issues
   - Test failures: Fix failing tests
   - Formatting: `npm run format`
3. **Commit/push again** after fixing

### Safe Alternatives
```bash
# Run checks first, then commit
git safe-commit -m "Your commit message"

# Run tests first, then push
git safe-push origin branch-name
```

## Emergency Override (Not Recommended)

If you absolutely must bypass hooks (emergency only):
1. Temporarily rename `.husky` directory: `mv .husky .husky.disabled`
2. Make your commit/push
3. Immediately restore: `mv .husky.disabled .husky`
4. Fix the issues and recommit properly

**Note**: This should only be used in true emergencies and the issues must be fixed immediately after.

## Team Guidelines

- **Never use `--no-verify`** - it's strictly forbidden
- **Always fix the underlying issues** instead of bypassing
- **Help teammates** who are struggling with hook failures
- **Report persistent hook issues** to the team lead

## Troubleshooting

### Common Issues and Solutions

1. **Linting Errors**
   ```bash
   npm run lint:fix  # Auto-fix many issues
   npm run lint      # See remaining issues
   ```

2. **Type Errors**
   ```bash
   npm run type-check  # See TypeScript errors
   # Fix the errors in your code
   ```

3. **Test Failures**
   ```bash
   npm run test  # Run tests locally
   # Fix failing tests
   ```

4. **Formatting Issues**
   ```bash
   npm run format  # Auto-format code
   ```

Remember: The hooks are there to help maintain code quality and prevent issues from reaching the repository!
