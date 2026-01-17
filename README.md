# Smart Media Sorter

An intelligent Python tool that automatically classifies and organizes photos and videos by separating personal/family media from app icons, game assets, system cache, and other non-essential files.

## 🎯 The Problem

Have you ever found yourself with thousands of images and videos scattered in a folder, mixed with:
- App icons and logos from your phone
- Game graphics and assets
- Cached thumbnails and temporary files
- Social media cache images
- System-generated files

Manually sorting through 10,000+ files to find your actual family photos and videos is time-consuming and frustrating. That's exactly the problem this tool solves.

## 🚀 Why I Created This

I had over 13,000 files in a "quarantine" folder after recovering data from multiple sources - phones, backups, and various apps. The folder contained:
- **Actual family photos and videos** I wanted to preserve
- **Thousands of app icons** from Android/iOS applications
- **Game assets** from installed games
- **Cached thumbnails** and temporary files
- **Social media cache** from apps like Instagram, Facebook, etc.

Sorting through this manually would have taken days. This tool classified all 13,343 files in under 2 minutes, correctly identifying:
- ✅ 20.4% as personal/family media
- 📱 53.2% as app icons
- 🎮 1.6% as game assets
- 🗑️ 20.1% as cache/thumbnails/duplicates
- ❓ 12.4% needing manual review

## 🎯 How It Works

The tool uses multiple intelligent heuristics:

1. **Filename Pattern Recognition**: Identifies files based on naming conventions
   - Personal: `DSC_`, `IMG_`, `VID_`, camera patterns
   - App Icons: `icon`, `logo`, `launcher`, `drawable`
   - Game Assets: `game`, `character`, `texture`, `level`
   - Cache: `thumb`, `scaled`, `cache`, `temp`

2. **Image Dimension Analysis**: 
   - Icons are typically small (≤256px)
   - Thumbnails are small (≤200px)
   - Real photos are larger (≥800px in smallest dimension)

3. **File Size Analysis**:
   - Large videos (>5MB) are likely personal content
   - Small images are likely icons or cache

4. **Duplicate Detection**: 
   - Identifies duplicate files using MD5 hashing
   - Automatically categorizes duplicates as cache

## 📋 Requirements

- **Python 3.7+** (uses only standard library - no external dependencies!)
- Works on Linux, macOS, and Windows

## 🔧 Installation

```bash
# Clone or download the repository
git clone https://github.com/alahyaoui/smart-media-sorter.git
cd smart-media-sorter

# Make executable (optional)
chmod +x media-sorter.py
```

## 📖 Usage

### Basic Usage (Dry Run)

Preview classification without moving files:

```bash
python3 media-sorter.py --source ./my_photos --output ./sorted
```

### Execute the Sort

Actually move files to organized folders:

```bash
python3 media-sorter.py --source ./my_photos --output ./sorted --execute
```

### Using Custom Configuration

Generate a config file:

```bash
python3 media-sorter.py --generate-config
```

Edit `config.json` to customize patterns and thresholds, then:

```bash
python3 media-sorter.py --config config.json --execute
```

### Command Line Options

```
--source, -s       Source directory containing files to sort
--output, -o       Output directory for sorted files
--config, -c       Path to JSON config file
--execute          Actually move files (default is dry run)
--verbose, -v      Show detailed progress
--generate-config  Create a default config.json file
```

## 📁 Output Structure

Files are organized into these categories:

```
processed/
├── personal_media/     # Your family photos and videos
├── app_icons/          # Application icons and logos
├── game_assets/        # Game graphics and textures
├── thumbnails/         # Small cached thumbnails
├── system_cache/       # Cache files and duplicates
└── needs_review/       # Uncertain files for manual review
```

## ⚙️ Configuration

Create a `config.json` file to customize:

```json
{
  "source_dir": "./quarantine",
  "output_dir": "./processed",
  "patterns": {
    "personal": [
      "DSC_", 
      "IMG_\\d{8}", 
      "photo.*\\d{4}",
      "\\.(AVI|MP4|MOV|JPG)$"
    ],
    "app_icons": ["icon", "logo", "sprite", "launcher"],
    "game_assets": ["game", "level", "character", "weapon"],
    "cache": ["cache", "thumb", "scaled", "temp"]
  },
  "thresholds": {
    "icon_max_dimension": 256,
    "thumbnail_max_dimension": 200,
    "min_photo_dimension": 800,
    "min_video_size_mb": 5
  }
}
```

### Customizing Patterns

Add your own filename patterns to match your specific needs:

- **Personal photos**: Add your camera's naming pattern (e.g., Canon uses `_MG_`, Nikon uses `DSC_`)
- **Family names**: Add specific names that appear in your photos
- **Custom app patterns**: Add patterns for specific apps you want to filter

## 🎯 Use Cases

- **Data Recovery**: Sort recovered files from backup software
- **Phone Backups**: Organize files from phone backup/sync apps
- **Cloud Storage Cleanup**: Clean up mixed folders from cloud storage
- **Digital Hoarding**: Finally organize that "unsorted" folder from 2018
- **Migration**: Prepare files for migration to photo management software

## 📊 Performance

- Processes **~6,500 files per minute** on average hardware
- Memory efficient (uses file streaming for large files)
- No external dependencies required

## 🤝 Contributing

Contributions are welcome! Here are ways you can help:

- Add patterns for more camera brands
- Improve classification accuracy
- Add support for more file types
- Optimize performance
- Improve documentation

## 📝 License

MIT License - feel free to use, modify, and distribute.

## ⚠️ Important Notes

1. **Always run a dry run first** to preview the classification
2. **Backup your files** before running with `--execute`
3. **Review the "needs_review" folder** manually for edge cases
4. The tool is conservative - when uncertain, it marks files for review
5. Duplicate detection uses a quick hash - not 100% accurate but very fast

## 🐛 Troubleshooting

### Files not classified correctly?

1. Check if the filename matches expected patterns
2. Add custom patterns to `config.json`
3. Adjust dimension thresholds for your camera

### Tool too slow?

- The tool is already optimized for speed
- Consider processing folders in batches
- Use SSD storage for better I/O performance

### Getting errors?

- Check file permissions
- Ensure sufficient disk space in output directory
- Verify Python version (3.7+ required)

## 💡 Tips

- Review the **personal_media** folder first - these are your priority files
- The **needs_review** folder contains uncertain files - worth checking manually
- Use the **--verbose** flag to see detailed progress
- Run multiple iterations with refined patterns for better accuracy

## 📧 Support

Found a bug? Have a feature request? Open an issue on GitHub!

---

**Made with ❤️ to solve a real-world problem of sorting 13,000+ mixed media files**
