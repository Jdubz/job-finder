#!/bin/bash

# Git Wrapper Script to Prevent --no-verify Usage
# This script intercepts git commands and blocks --no-verify usage

# Function to show error message and exit
show_error() {
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
    exit 1
}

# Check if --no-verify is in the arguments
for arg in "$@"; do
    if [[ "$arg" == "--no-verify" ]]; then
        show_error
    fi
done

# If we get here, no --no-verify was found, proceed with normal git
exec git "$@"
