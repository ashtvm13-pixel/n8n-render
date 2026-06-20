#!/bin/bash
# Veda Katha — Oracle Cloud (Oracle Linux) VM setup
# Run once after SSH into fresh VM:
#   chmod +x setup_oracle.sh && ./setup_oracle.sh

set -e

echo "=== Veda Katha VM Setup ==="

# ── System packages ──────────────────────────
echo "[1/6] Installing system packages..."
sudo dnf update -y -q
sudo dnf install -y -q \
    curl git ImageMagick fontconfig \
    python3 python3-pip tmux unzip

# ── Node.js 20 ───────────────────────────────
echo "[2/6] Installing Node.js 20..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs

# ── Claude Code CLI ──────────────────────────
echo "[3/6] Installing Claude Code CLI..."
sudo npm install -g @anthropic-ai/claude-code

# ── Fonts ────────────────────────────────────
echo "[4/6] Installing fonts..."
sudo mkdir -p /usr/share/fonts/custom

sudo curl -sL -o /usr/share/fonts/custom/CormorantGaramond-Bold.ttf \
    "https://github.com/CatharsisFonts/Cormorant/raw/master/fonts/ttf/CormorantGaramond-Bold.ttf"

sudo curl -sL -o /usr/share/fonts/custom/DMSans-Regular.ttf \
    "https://github.com/google/fonts/raw/main/ofl/dmsans/static/DMSans-Regular.ttf"

sudo fc-cache -f
echo "Fonts installed."

# ── Claude config ────────────────────────────
echo "[5/6] Configuring Claude..."
echo ""
echo "  Enter your Anthropic API key (from console.anthropic.com):"
read -r -s ANTHROPIC_KEY
echo ""
mkdir -p ~/.config/claude
echo "{\"apiKey\": \"$ANTHROPIC_KEY\"}" > ~/.config/claude/config.json
echo "Claude config saved."

# ── Pipeline files ───────────────────────────
echo "[6/6] Copying pipeline..."
mkdir -p ~/veda_katha
cp pipeline.py ~/veda_katha/
chmod +x ~/veda_katha/pipeline.py

# ── Cron job (twice daily: 6AM + 6PM IST = 00:30 + 12:30 UTC) ──
echo ""
echo "Install cron job to auto-post twice daily? (y/n)"
read -r CRON_CHOICE
if [ "$CRON_CHOICE" = "y" ]; then
    CRON_CMD="30 0,12 * * * cd /home/opc/veda_katha && /usr/bin/python3 pipeline.py >> /home/opc/veda_katha/cron.log 2>&1"
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "Cron job installed: 6AM + 6PM IST daily."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Test run (dry run, no Instagram post):"
echo "  cd ~/veda_katha && python3 pipeline.py --dry-run"
echo ""
echo "Full run:"
echo "  cd ~/veda_katha && python3 pipeline.py"
echo ""
echo "Run in background with tmux:"
echo "  tmux new -s veda"
echo "  python3 pipeline.py"
echo "  # Ctrl+B then D to detach"
