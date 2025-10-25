#!/bin/bash

# Setup script to prevent --no-verify usage in git commands
# This script configures multiple layers of protection

set -e

echo "🛡️  Setting up --no-verify prevention system..."

# Make all prevention scripts executable
chmod +x scripts/prevent-no-verify.sh
chmod +x scripts/git-no-verify-prevention.sh
chmod +x scripts/activate-git-prevention.sh

# Create a git wrapper that can be used as an alias
cat > scripts/git-wrapper.sh << 'EOF'
#!/bin/bash
# Git wrapper that prevents --no-verify usage

# Check for --no-verify in arguments
for arg in "$@"; do
    if [[ "$arg" == "--no-verify" ]]; then
        echo "🚫 ERROR: --no-verify flag is STRICTLY FORBIDDEN!"
        echo ""
        echo "❌ Why --no-verify is banned:"
        echo "   • It bypasses essential quality checks"
        echo "   • It allows broken code into the repository"
        echo "   • It breaks CI/CD pipelines"
        echo "   • It violates our code quality standards"
        echo ""
        echo "✅ What to do instead:"
        echo "   • Fix the underlying issues (linting, type errors, tests)"
        echo "   • Use 'npm run lint:fix' to auto-fix linting issues"
        echo "   • Use 'npm run test' to run tests locally"
        echo "   • Commit/push again after fixing the issues"
        echo ""
        echo "💡 The hooks are there to help maintain code quality!"
        exit 1
    fi
done

# If no --no-verify found, proceed with normal git
exec git "$@"
EOF

chmod +x scripts/git-wrapper.sh

# Create git aliases that prevent --no-verify
echo "📝 Configuring git aliases..."

# Remove existing aliases first
git config --unset alias.commit 2>/dev/null || true
git config --unset alias.push 2>/dev/null || true

# Add aliases to local git config using the wrapper script
git config alias.commit '!./scripts/git-no-verify-prevention.sh commit'
git config alias.push '!./scripts/git-no-verify-prevention.sh push'

# Add safe aliases that run checks first
git config alias.safe-commit '!f() { echo "🔍 Running pre-commit checks..."; npm run lint && npm run type-check && git commit "$@"; }; f'
git config alias.safe-push '!f() { echo "🧪 Running pre-push checks..."; npm run test && git push "$@"; }; f'

# Create a .gitignore entry to prevent accidental commits of bypass scripts
echo "📝 Updating .gitignore..."
if ! grep -q "# Prevent --no-verify bypass scripts" .gitignore 2>/dev/null; then
    cat >> .gitignore << 'EOF'

# Prevent --no-verify bypass scripts
git-bypass-*
no-verify-*
EOF
fi

# Create a README for the prevention system
cat > NO_VERIFY_PREVENTION.md << 'EOF'
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
EOF

echo "✅ --no-verify prevention system configured!"
echo ""
echo "🛡️  Protection mechanisms active:"
echo "   • Git aliases override commit/push commands"
echo "   • Enhanced husky hooks detect bypass attempts"
echo "   • Wrapper scripts provide helpful error messages"
echo "   • Safe aliases available: git safe-commit, git safe-push"
echo ""
echo "📚 Documentation created: NO_VERIFY_PREVENTION.md"
echo ""
echo "💡 Remember: Always fix the underlying issues instead of bypassing hooks!"
