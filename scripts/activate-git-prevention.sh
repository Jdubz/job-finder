#!/bin/bash

# Script to activate git --no-verify prevention
# Source this script in your shell: source scripts/activate-git-prevention.sh

# Function to show comprehensive error message
show_no_verify_error() {
    echo "🚫 ERROR: --no-verify flag is STRICTLY FORBIDDEN in this repository!"
    echo ""
    echo "❌ Why --no-verify is banned:"
    echo "   • It bypasses essential quality checks (linting, type checking, tests)"
    echo "   • It allows broken code into the repository"
    echo "   • It breaks CI/CD pipelines and wastes team time"
    echo "   • It violates our code quality standards"
    echo ""
    echo "✅ What to do instead:"
    echo "   • Fix the underlying issues (linting errors, type errors, failing tests)"
    echo "   • Read the error messages - they tell you exactly what's wrong"
    echo "   • Use 'npm run lint:fix' to auto-fix linting issues"
    echo "   • Use 'npm run test' to run tests locally"
    echo "   • Commit/push again after fixing the issues"
    echo ""
    echo "🔧 Common fixes:"
    echo "   • Linting errors: npm run lint:fix"
    echo "   • Type errors: Fix TypeScript issues"
    echo "   • Test failures: Fix failing tests"
    echo "   • Formatting: npm run format"
    echo ""
    echo "💡 Remember: The hooks are there to help maintain code quality!"
    echo ""
    echo "🆘 If you're in a true emergency:"
    echo "   1. Temporarily rename .husky: mv .husky .husky.disabled"
    echo "   2. Make your commit/push"
    echo "   3. Immediately restore: mv .husky.disabled .husky"
    echo "   4. Fix the issues and recommit properly"
    return 1
}

# Override git function to prevent --no-verify
git() {
    # Check all arguments for --no-verify
    for arg in "$@"; do
        if [[ "$arg" == "--no-verify" ]]; then
            show_no_verify_error
            return 1
        fi
    done
    
    # If no --no-verify found, proceed with normal git
    command git "$@"
}

# Safe commit function that runs checks first
safe_commit() {
    echo "🔍 Running pre-commit checks..."
    npm run lint && npm run type-check && git commit "$@"
}

# Safe push function that runs checks first
safe_push() {
    echo "🧪 Running pre-push checks..."
    npm run test && git push "$@"
}

echo "🛡️  Git --no-verify prevention activated!"
echo "   • git() function now prevents --no-verify usage"
echo "   • Use safe_commit() and safe_push() for safe operations"
echo "   • Emergency override available if needed"
echo ""
echo "💡 To make this permanent, add this to your .bashrc or .zshrc:"
echo "   source $(pwd)/scripts/activate-git-prevention.sh"
