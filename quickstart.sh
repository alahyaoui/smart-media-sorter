bash ./smart-media-sorter/quickstart.sh#!/bin/bash
# Quick start script for Smart Media Sorter

echo "=================================================="
echo "  Smart Media Sorter - Quick Start"
echo "=================================================="
echo ""

# Check if Python 3 is installed
if ! which python3 > /dev/null 2>&1; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Get source directory
read -p "Enter source directory path (e.g., ./photos): " SOURCE_DIR

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Directory '$SOURCE_DIR' does not exist"
    exit 1
fi

FILE_COUNT=$(find "$SOURCE_DIR" -type f | wc -l)
echo "✓ Found $FILE_COUNT files in $SOURCE_DIR"
echo ""

# Get output directory
read -p "Enter output directory path (e.g., ./sorted): " OUTPUT_DIR

# Confirm
echo ""
echo "Configuration:"
echo "  Source: $SOURCE_DIR ($FILE_COUNT files)"
echo "  Output: $OUTPUT_DIR"
echo ""
read -p "Run DRY RUN first? (recommended) [Y/n]: " DRY_RUN

if [[ $DRY_RUN =~ ^[Nn]$ ]]; then
    echo ""
    echo "⚠️  WARNING: This will MOVE files from source to output!"
    read -p "Are you sure? Type 'yes' to confirm: " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi
    
    echo ""
    echo "🚀 Running LIVE sort (moving files)..."
    python3 "$(dirname "$0")/media-sorter.py" --source "$SOURCE_DIR" --output "$OUTPUT_DIR" --execute
else
    echo ""
    echo "🔍 Running DRY RUN (preview only)..."
    python3 "$(dirname "$0")/media-sorter.py" --source "$SOURCE_DIR" --output "$OUTPUT_DIR"
    
    echo ""
    read -p "Execute the sort for real? [y/N]: " EXECUTE
    
    if [[ $EXECUTE =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Running LIVE sort (moving files)..."
        python3 "$(dirname "$0")/media-sorter.py" --source "$SOURCE_DIR" --output "$OUTPUT_DIR" --execute
        
        echo ""
        echo "✅ Done! Check $OUTPUT_DIR for sorted files"
        echo ""
        echo "📁 Folder structure:"
        echo "   $OUTPUT_DIR/personal_media/    - Your photos & videos"
        echo "   $OUTPUT_DIR/needs_review/      - Files needing manual review"
        echo "   $OUTPUT_DIR/app_icons/         - Application icons"
        echo "   $OUTPUT_DIR/game_assets/       - Game graphics"
        echo "   $OUTPUT_DIR/thumbnails/        - Small thumbnails"
        echo "   $OUTPUT_DIR/system_cache/      - Cache & duplicates"
    else
        echo ""
        echo "ℹ️  Dry run completed. No files were moved."
    fi
fi
