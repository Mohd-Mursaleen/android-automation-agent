#!/bin/bash
# android-ai-agent setup script
# Works on Termux (Android arm64) and Linux/macOS

set -e

echo ""
echo "android-ai-agent setup"
echo ""

# Check Python
python3 --version || { echo "Python 3 not found. Run: pkg install python"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env — add your OpenRouter API key:"
    echo "  nano .env"
    echo "  Get your free key at: https://openrouter.ai/keys"
else
    echo ".env file already exists"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add your API key:  nano .env"
echo "  2. Activate venv:     source .venv/bin/activate"
echo "  3. Check setup:       python check.py"
echo "  4. Run a task:        python run.py \"Open Settings\""
echo ""
