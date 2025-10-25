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
