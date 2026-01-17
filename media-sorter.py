#!/usr/bin/env python3
"""
Smart Media Sorter - Automatically classify and organize photos/videos
Separates family/personal media from app icons, game assets, and cached files

Author: Created to solve the quarantine folder problem
License: MIT
Repository: https://github.com/alahyaoui/smart-media-sorter
"""

import os
import sys
import shutil
from pathlib import Path
import hashlib
import re
import imghdr
import mimetypes
import argparse
import json
from collections import defaultdict
from datetime import datetime

# Default configuration
DEFAULT_CONFIG = {
    "source_dir": "./quarantine",
    "output_dir": "./processed",
    "categories": {
        "personal": "personal_media",
        "app_icons": "app_icons",
        "game_assets": "game_assets",
        "thumbnails": "thumbnails",
        "system_cache": "system_cache",
        "review": "needs_review"
    },
    "patterns": {
        "app_icons": [
            "icon", "logo", "sprite", "badge", "button", "bg_", "background",
            "launcher", "drawable", "banner", "toolbar", "menu", "notification"
        ],
        "game_assets": [
            "game", "level", "character", "weapon", "enemy", "powerup", "coin",
            "_art", "texture", "tile", "monster", "zombie"
        ],
        "cache": [
            "cache", "thumb", "scaled", "temp", "tmp", r"\.png\.xmp$",
            r"r\d+_\d+_orig", r"r\d+_\d+_scaled", r"_\d+x\d+\.png$"
        ],
        "personal": [
            r"DSC_", r"IMG_\d{8}", r"VID_\d{8}", r"DCIM",
            r"photo.*\d{4}", r"video.*\d{4}", 
            r"\.(AVI|MP4|MOV|JPG|JPEG|PNG|HEIC)$"
        ]
    },
    "thresholds": {
        "icon_max_dimension": 256,
        "thumbnail_max_dimension": 200,
        "min_photo_dimension": 800,
        "min_video_size_mb": 5
    }
}


class MediaSorter:
    """Main class for sorting media files"""
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.stats = defaultdict(int)
        self.duplicates = defaultdict(list)
        self.errors = []
        
    def get_file_hash(self, filepath, sample_size=8192):
        """Quick hash of file for duplicate detection"""
        try:
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                hasher.update(f.read(sample_size))
            return hasher.hexdigest()
        except Exception as e:
            self.errors.append(f"Hash error for {filepath}: {e}")
            return None
    
    def get_image_dimensions(self, filepath):
        """Get image dimensions without external dependencies"""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(24)
            
            # PNG
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                with open(filepath, 'rb') as f:
                    f.seek(16)
                    width = int.from_bytes(f.read(4), 'big')
                    height = int.from_bytes(f.read(4), 'big')
                return width, height
            
            # JPEG
            elif header.startswith(b'\xff\xd8'):
                with open(filepath, 'rb') as f:
                    f.seek(0)
                    while True:
                        marker = f.read(2)
                        if not marker or marker[0] != 0xFF:
                            break
                        
                        marker_type = marker[1]
                        if marker_type in [0xC0, 0xC1, 0xC2]:
                            f.read(3)
                            height = int.from_bytes(f.read(2), 'big')
                            width = int.from_bytes(f.read(2), 'big')
                            return width, height
                        
                        size = int.from_bytes(f.read(2), 'big')
                        f.seek(size - 2, 1)
            
            # GIF
            elif header.startswith(b'GIF'):
                width = int.from_bytes(header[6:8], 'little')
                height = int.from_bytes(header[8:10], 'little')
                return width, height
                
        except Exception:
            pass
        
        return None, None
    
    def classify_by_name(self, filename):
        """Classify based on filename patterns"""
        filename_lower = filename.lower()
        
        # Check cache patterns first (highest priority)
        for pattern in self.config['patterns']['cache']:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                return 'system_cache'
        
        # Check if it's likely personal media
        for pattern in self.config['patterns']['personal']:
            if re.search(pattern, filename, re.IGNORECASE):
                return 'personal'
        
        # Check app icons
        for pattern in self.config['patterns']['app_icons']:
            if re.search(pattern, filename_lower):
                return 'app_icons'
        
        # Check game assets
        for pattern in self.config['patterns']['game_assets']:
            if re.search(pattern, filename_lower):
                return 'game_assets'
        
        return None
    
    def classify_image(self, filepath):
        """Classify image based on dimensions"""
        try:
            width, height = self.get_image_dimensions(filepath)
            
            if width is None or height is None:
                return 'review'
            
            max_dim = max(width, height)
            min_dim = min(width, height)
            
            thresholds = self.config['thresholds']
            
            if max_dim <= thresholds['icon_max_dimension']:
                return 'app_icons'
            
            if max_dim <= thresholds['thumbnail_max_dimension']:
                return 'thumbnails'
            
            if min_dim >= thresholds['min_photo_dimension']:
                return 'personal'
            
            return 'review'
            
        except Exception as e:
            self.errors.append(f"Image analysis error for {filepath}: {e}")
            return 'review'
    
    def classify_file(self, filepath):
        """Main classification logic"""
        filename = os.path.basename(filepath)
        
        # Try filename classification first
        name_category = self.classify_by_name(filename)
        if name_category:
            return name_category
        
        # Get MIME type
        mime, _ = mimetypes.guess_type(filepath)
        if not mime:
            img_type = imghdr.what(filepath)
            if img_type:
                mime = f'image/{img_type}'
        
        if not mime:
            return 'review'
        
        # For images, use dimensional analysis
        if mime.startswith('image/'):
            return self.classify_image(filepath)
        
        # For videos
        if mime.startswith('video/'):
            for pattern in self.config['patterns']['personal']:
                if re.search(pattern, filename, re.IGNORECASE):
                    return 'personal'
            
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            min_video_size = self.config['thresholds']['min_video_size_mb']
            if size_mb > min_video_size:
                return 'personal'
            
            return 'review'
        
        return 'review'
    
    def create_output_dirs(self):
        """Create all output directories"""
        output_base = self.config['output_dir']
        for category_dir in self.config['categories'].values():
            os.makedirs(os.path.join(output_base, category_dir), exist_ok=True)
    
    def process_files(self, dry_run=True, verbose=False):
        """Process all files in source directory"""
        source_dir = self.config['source_dir']
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Starting classification...")
        print(f"Source: {source_dir}")
        print(f"Output: {self.config['output_dir']}\n")
        
        # Get all files
        files = list(Path(source_dir).rglob('*'))
        file_list = [f for f in files if f.is_file()]
        total_files = len(file_list)
        
        if total_files == 0:
            print(f"No files found in {source_dir}")
            return
        
        print(f"Found {total_files} files to process\n")
        
        processed = 0
        for filepath in file_list:
            processed += 1
            
            if processed % 100 == 0 or (verbose and processed % 10 == 0):
                print(f"Progress: {processed}/{total_files} ({processed*100//total_files}%)")
            
            # Check for duplicates
            file_hash = self.get_file_hash(str(filepath))
            if file_hash and file_hash in self.duplicates and len(self.duplicates[file_hash]) > 0:
                self.stats['duplicates'] += 1
                category = 'system_cache'
            else:
                if file_hash:
                    self.duplicates[file_hash].append(str(filepath))
                category = self.classify_file(str(filepath))
            
            self.stats[category] += 1
            
            # Move file
            if not dry_run:
                dest_dir = os.path.join(
                    self.config['output_dir'],
                    self.config['categories'].get(category, 'review')
                )
                dest_path = os.path.join(dest_dir, filepath.name)
                
                # Handle name conflicts
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(filepath.name)
                    dest_path = os.path.join(dest_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                try:
                    shutil.move(str(filepath), dest_path)
                except Exception as e:
                    self.errors.append(f"Move error for {filepath}: {e}")
        
        self.print_results(total_files, dry_run)
    
    def print_results(self, total_files, dry_run):
        """Print classification results"""
        print("\n" + "="*60)
        print("CLASSIFICATION RESULTS:")
        print("="*60)
        
        for category, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count * 100) / total_files if total_files > 0 else 0
            print(f"{category:20s}: {count:6d} files ({percentage:5.1f}%)")
        
        print("="*60)
        print(f"Total processed: {total_files} files")
        
        if self.errors:
            print(f"\n⚠️  {len(self.errors)} errors occurred")
            if len(self.errors) <= 10:
                for error in self.errors:
                    print(f"  - {error}")
        
        if dry_run:
            print("\n⚠️  This was a DRY RUN - no files were moved")
            print("Run with --execute to actually move files")


def load_config(config_file):
    """Load configuration from JSON file"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            user_config = json.load(f)
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    return DEFAULT_CONFIG


def save_default_config(output_file='config.json'):
    """Save default configuration to file"""
    with open(output_file, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Default configuration saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Smart Media Sorter - Organize photos/videos by separating personal media from system files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview only)
  python media-sorter.py --source ./photos --output ./sorted
  
  # Execute the sort
  python media-sorter.py --source ./photos --output ./sorted --execute
  
  # Use custom config
  python media-sorter.py --config my_config.json --execute
  
  # Generate default config
  python media-sorter.py --generate-config
        """
    )
    
    parser.add_argument('--source', '-s', 
                       help='Source directory containing files to sort')
    parser.add_argument('--output', '-o', 
                       help='Output directory for sorted files')
    parser.add_argument('--config', '-c', 
                       help='Path to JSON config file')
    parser.add_argument('--execute', action='store_true',
                       help='Actually move files (default is dry run)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--generate-config', action='store_true',
                       help='Generate default config.json file')
    
    args = parser.parse_args()
    
    if args.generate_config:
        save_default_config()
        return
    
    # Load configuration
    config = load_config(args.config) if args.config else DEFAULT_CONFIG.copy()
    
    # Override with command line args
    if args.source:
        config['source_dir'] = args.source
    if args.output:
        config['output_dir'] = args.output
    
    # Validate paths
    if not os.path.exists(config['source_dir']):
        print(f"Error: Source directory '{config['source_dir']}' does not exist")
        return 1
    
    # Create sorter and run
    sorter = MediaSorter(config)
    sorter.create_output_dirs()
    sorter.process_files(dry_run=not args.execute, verbose=args.verbose)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
