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

# ANSI Color codes for terminal output
class Colors:
    """ANSI color codes for prettier terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

    @staticmethod
    def disable():
        """Disable colors (for piping or non-terminal output)"""
        Colors.HEADER = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''
        Colors.DIM = ''

# Check if we should use colors
# Enable for VSCode terminal (TERM_PROGRAM=vscode) or regular terminals
if os.environ.get('TERM_PROGRAM') == 'vscode' or sys.stdout.isatty():
    pass  # Colors enabled
else:
    Colors.disable()

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
            r"\d{8}_\d{6}\.(mp4|avi|mov|MP4|AVI|MOV)$"
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
        
    def get_file_hash(self, filepath):
        """Calculate hash of entire file for accurate duplicate detection"""
        try:
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
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
    
    def check_output_dirs(self):
        """Check if output directories exist and have files"""
        output_base = self.config['output_dir']
        if not os.path.exists(output_base):
            return False, 0
        
        total_existing = 0
        for category_dir in self.config['categories'].values():
            cat_path = os.path.join(output_base, category_dir)
            if os.path.exists(cat_path):
                total_existing += len([f for f in os.listdir(cat_path) if os.path.isfile(os.path.join(cat_path, f))])
        
        return True, total_existing
    
    def create_output_dirs(self):
        """Create all output directories"""
        output_base = self.config['output_dir']
        for category_dir in self.config['categories'].values():
            os.makedirs(os.path.join(output_base, category_dir), exist_ok=True)
    
    def process_files(self, dry_run=True, verbose=False):
        """Process all files in source directory"""
        source_dir = self.config['source_dir']
        
        # Print header
        print(f"\n{Colors.BOLD}{'═' * 70}{Colors.ENDC}")
        if dry_run:
            print(f"{Colors.YELLOW}{Colors.BOLD}🔍 DRY RUN MODE{Colors.ENDC} {Colors.DIM}(preview only - no files will be moved){Colors.ENDC}")
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}🚀 LIVE MODE{Colors.ENDC} {Colors.DIM}(files will be moved){Colors.ENDC}")
        print(f"{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")
        
        # Check for existing output
        exists, existing_count = self.check_output_dirs()
        if exists and existing_count > 0:
            print(f"{Colors.YELLOW}⚠️  Warning:{Colors.ENDC} Output directory already contains {Colors.BOLD}{existing_count}{Colors.ENDC} files")
            print(f"{Colors.DIM}   Files will be added to existing categories{Colors.ENDC}\n")
        
        print(f"{Colors.CYAN}📂 Source:{Colors.ENDC}  {Colors.BOLD}{source_dir}{Colors.ENDC}")
        print(f"{Colors.CYAN}📁 Output:{Colors.ENDC}  {Colors.BOLD}{self.config['output_dir']}{Colors.ENDC}\n")
        
        # Get all files
        print(f"{Colors.DIM}Scanning directory...{Colors.ENDC}")
        files = list(Path(source_dir).rglob('*'))
        file_list = [f for f in files if f.is_file()]
        total_files = len(file_list)
        
        if total_files == 0:
            print(f"{Colors.RED}❌ No files found in {source_dir}{Colors.ENDC}")
            return
        
        print(f"{Colors.GREEN}✓{Colors.ENDC} Found {Colors.BOLD}{total_files}{Colors.ENDC} files to process\n")
        print(f"{Colors.DIM}{'─' * 70}{Colors.ENDC}")
        
        processed = 0
        for filepath in file_list:
            processed += 1
            
            if processed % 100 == 0 or (verbose and processed % 10 == 0):
                percentage = processed * 100 // total_files
                bar_length = 30
                filled = int(bar_length * processed / total_files)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"\r{Colors.CYAN}Progress:{Colors.ENDC} [{bar}] {Colors.BOLD}{percentage}%{Colors.ENDC} ({processed}/{total_files})", end='', flush=True)
            
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
        print(f"\n\n{Colors.BOLD}{'═' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}📊 CLASSIFICATION RESULTS{Colors.ENDC}")
        print(f"{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")
        
        # Category icons
        icons = {
            'personal': '📸',
            'app_icons': '📱',
            'game_assets': '🎮',
            'thumbnails': '🖼️',
            'system_cache': '🗑️',
            'duplicates': '🔄',
            'review': '❓'
        }
        
        for category, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count * 100) / total_files if total_files > 0 else 0
            icon = icons.get(category, '📄')
            
            # Color based on category
            if category == 'personal':
                color = Colors.GREEN
            elif category in ['duplicates', 'system_cache']:
                color = Colors.DIM
            elif category == 'review':
                color = Colors.YELLOW
            else:
                color = Colors.BLUE
            
            # Create percentage bar
            bar_length = 20
            filled = int(bar_length * percentage / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"{icon} {color}{category:20s}{Colors.ENDC}: {Colors.BOLD}{count:6d}{Colors.ENDC} files [{bar}] {percentage:5.1f}%")
        
        print(f"\n{Colors.BOLD}{'─' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}Total processed:{Colors.ENDC} {Colors.CYAN}{total_files}{Colors.ENDC} files")
        
        if self.errors:
            print(f"\n{Colors.RED}⚠️  {len(self.errors)} errors occurred:{Colors.ENDC}")
            if len(self.errors) <= 10:
                for error in self.errors:
                    print(f"  {Colors.DIM}•{Colors.ENDC} {error}")
        
        if dry_run:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  DRY RUN COMPLETE{Colors.ENDC} {Colors.DIM}- No files were moved{Colors.ENDC}")
            print(f"{Colors.CYAN}💡 Tip:{Colors.ENDC} Run with {Colors.BOLD}--execute{Colors.ENDC} to actually move files")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SORT COMPLETE!{Colors.ENDC}")
            print(f"{Colors.CYAN}📁 Output:{Colors.ENDC} {self.config['output_dir']}")
        
        print(f"{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")


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
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    
    args = parser.parse_args()
    
    if args.no_color:
        Colors.disable()
    
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
