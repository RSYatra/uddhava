#!/bin/bash
# Auto-format and fix all Python code
# Run this to automatically fix formatting issues before committing

set -e

echo "🔧 Auto-formatting Python code with Ruff..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Ruff formatter (like black)
echo "📝 Running Ruff format..."
ruff format .

# Run Ruff linter with auto-fix
echo "🔍 Running Ruff linter with auto-fix..."
ruff check . --fix

echo "✅ Done! All formatting issues fixed."
echo "💡 Tip: You can now commit your changes."
