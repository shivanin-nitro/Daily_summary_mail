#!/bin/bash

# Setup script to install a cron job that runs the Daily Summary Mail pipeline at 11 AM daily
# Usage: bash setup_cron.sh

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$PROJECT_DIR/run_pipeline.sh"

# Make the run_pipeline.sh script executable
chmod +x "$SCRIPT_PATH"

echo "📋 Setting up cron job for Daily Summary Mail Pipeline..."
echo "📁 Project directory: $PROJECT_DIR"
echo "🔧 Script path: $SCRIPT_PATH"

# Create a temporary cron file with the new job
TEMP_CRON=$(mktemp)

# Get current crontab (if it exists) and add it to temp file
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "" > "$TEMP_CRON"

# Check if the cron job already exists
if grep -q "run_pipeline.sh" "$TEMP_CRON"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    grep -v "run_pipeline.sh" "$TEMP_CRON" > "${TEMP_CRON}.tmp"
    mv "${TEMP_CRON}.tmp" "$TEMP_CRON"
fi

# Add the new cron job (11 AM daily)
# Format: minute hour day month day-of-week
# 0 11 * * * = every day at 11:00 AM
echo "0 11 * * * $SCRIPT_PATH >> $PROJECT_DIR/logs/cron.log 2>&1" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up temp file
rm "$TEMP_CRON"

echo "✅ Cron job installed successfully!"
echo "⏰ The pipeline will run every day at 11:00 AM"
echo "📊 Logs will be written to: $PROJECT_DIR/logs/cron.log"
echo ""
echo "📝 To view installed cron jobs, run: crontab -l"
echo "🗑️  To remove the cron job, run: crontab -e (and delete the line with run_pipeline.sh)"
