#!/bin/bash
# Setup script for Apliqo Status Monitor
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"

echo "==> Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install via Homebrew: brew install python"
    exit 1
fi
echo "    $(python3 --version)"

echo "==> Creating virtual environment at $VENV ..."
python3 -m venv "$VENV"

echo "==> Installing dependencies into venv..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet rumps requests

# Create the launcher script pointing at the venv python
cat > "$DIR/run.sh" <<EOF
#!/bin/bash
exec "$VENV/bin/python" "$DIR/status_monitor.py" "\$@"
EOF
chmod +x "$DIR/run.sh"

echo ""
echo "✅  Done. Start the app with:"
echo ""
echo "    $DIR/run.sh"
echo ""
echo "To auto-launch at login:"
echo ""
echo "    $DIR/run.sh --install"
echo ""
echo "To stop auto-launch:"
echo ""
echo "    $DIR/run.sh --uninstall"
