#!/bin/bash
# Setup git hooks for the job-finder project
# This script copies git hooks to the .git/hooks directory

set -e

echo "Setting up git hooks..."

# Check if .githooks directory exists
if [ ! -d ".githooks" ]; then
    echo "❌ Error: .githooks directory not found. Are you in the project root?"
    exit 1
fi

# Copy pre-commit hook
if [ -f ".githooks/pre-commit" ]; then
    cp .githooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hook installed successfully!"
else
    echo "❌ Error: .githooks/pre-commit not found"
    exit 1
fi

# Copy pre-push hook
if [ -f ".githooks/pre-push" ]; then
    cp .githooks/pre-push .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
    echo "✅ Pre-push hook installed successfully!"
else
    echo "❌ Error: .githooks/pre-push not found"
    exit 1
fi

echo ""
echo "Git hooks are now configured:"
echo ""
echo "Pre-commit (fast checks):"
echo "  - Black code formatting check"
echo ""
echo "Pre-push (slower checks):"
echo "  - Mypy type checking"
echo "  - Pytest test suite"
echo ""
echo "These checks will run automatically at the appropriate times."
