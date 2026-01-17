#!/usr/bin/env python3
"""
Smart Media Sorter - Automatically classify and organize photos/videos
Separates family/personal media from app icons, game assets, and cached files

Architecture:
    - ImageAnalyzer: Handles image dimension detection
    - FileClassifier: Classifies files based on patterns and analysis
    - CacheManager: Manages classification cache for performance
    - MediaSorter: Orchestrates the sorting process

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
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    # python-magic is optional - script will work without it using mimetypes module
import mimetypes
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional, Tuple, Dict, List


# ============================================================================
# SECTION 1: UTILITIES & CONFIGURATION
# ============================================================================

class Colors:
    """ANSI color codes for terminal styling"""
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
        """Disable all color codes"""
        Colors.HEADER = Colors.BLUE = Colors.CYAN = ''
        Colors.GREEN = Colors.YELLOW = Colors.RED = ''
        Colors.ENDC = Colors.BOLD = Colors.UNDERLINE = Colors.DIM = ''


# Auto-detect color support
if os.environ.get('TERM_PROGRAM') == 'vscode' or sys.stdout.isatty():
    pass  # Colors enabled
else:
    Colors.disable()


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


# ============================================================================
# SECTION 2: IMAGE ANALYSIS
# ============================================================================

class ImageAnalyzer:
    """Analyzes image files to extract dimensions and properties"""
    
    @staticmethod
    def get_dimensions(filepath: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract image dimensions by reading file headers directly.
        
        Supports: PNG, JPEG, GIF
        
        Args:
            filepath: Path to image file
            
        Returns:
            Tuple of (width, height) or (None, None) if unable to read
        """
        try:
            with open(filepath, 'rb') as f:
                header = f.read(24)
            
            # PNG: Fixed header structure
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                with open(filepath, 'rb') as f:
                    f.seek(16)  # Skip to IHDR chunk
                    width = int.from_bytes(f.read(4), 'big')
                    height = int.from_bytes(f.read(4), 'big')
                return width, height
            
            # JPEG: Scan for Start of Frame markers
            elif header.startswith(b'\xff\xd8'):
                with open(filepath, 'rb') as f:
                    f.seek(0)
                    while True:
                        marker = f.read(2)
                        if not marker or marker[0] != 0xFF:
                            break
                        
                        # SOF markers (baseline, progressive, etc.)
                        if marker[1] in [0xC0, 0xC1, 0xC2]:
                            f.read(3)  # Skip precision and length
                            height = int.from_bytes(f.read(2), 'big')
                            width = int.from_bytes(f.read(2), 'big')
                            return width, height
                        
                        # Skip to next marker
                        size = int.from_bytes(f.read(2), 'big')
                        f.seek(size - 2, 1)
            
            # GIF: Simple fixed structure
            elif header.startswith(b'GIF'):
                width = int.from_bytes(header[6:8], 'little')
                height = int.from_bytes(header[8:10], 'little')
                return width, height
                
        except Exception:
            pass
        
        return None, None


# ============================================================================
# SECTION 3: FILE CLASSIFICATION
# ============================================================================

class FileClassifier:
    """Classifies files based on patterns, dimensions, and heuristics"""
    
    def __init__(self, config: dict):
        """
        Initialize classifier with configuration.
        
        Args:
            config: Configuration dictionary with patterns and thresholds
        """
        self.config = config
        self.patterns = config['patterns']
        self.thresholds = config['thresholds']
        self.errors = []
    
    def classify_by_filename(self, filename: str) -> Optional[str]:
        """
        Classify file based on filename patterns.
        
        Priority order: cache > personal > app_icons > game_assets
        
        Args:
            filename: Name of the file to classify
            
        Returns:
            Category name or None if no pattern matches
        """
        filename_lower = filename.lower()
        
        # Check cache patterns first (highest priority)
        for pattern in self.patterns['cache']:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                return 'system_cache'
        
        # Check personal media patterns
        for pattern in self.patterns['personal']:
            if re.search(pattern, filename, re.IGNORECASE):
                return 'personal'
        
        # Check app icons
        for pattern in self.patterns['app_icons']:
            if re.search(pattern, filename_lower):
                return 'app_icons'
        
        # Check game assets
        for pattern in self.patterns['game_assets']:
            if re.search(pattern, filename_lower):
                return 'game_assets'
        
        return None
    
    def classify_by_dimensions(self, filepath: str) -> str:
        """
        Classify image based on its dimensions.
        
        Args:
            filepath: Path to image file
            
        Returns:
            Category name based on size thresholds
        """
        try:
            width, height = ImageAnalyzer.get_dimensions(filepath)
            
            if width is None or height is None:
                return 'review'
            
            max_dim = max(width, height)
            min_dim = min(width, height)
            
            # Apply size-based classification
            if max_dim <= self.thresholds['icon_max_dimension']:
                return 'app_icons'
            
            if max_dim <= self.thresholds['thumbnail_max_dimension']:
                return 'thumbnails'
            
            if min_dim >= self.thresholds['min_photo_dimension']:
                return 'personal'
            
            return 'review'
            
        except Exception as e:
            self.errors.append(f"Dimension analysis error for {filepath}: {e}")
            return 'review'
    
    def classify_video(self, filepath: str, filename: str) -> str:
        """
        Classify video file based on size and patterns.
        
        Args:
            filepath: Path to video file
            filename: Name of the file
            
        Returns:
            Category name
        """
        # Check filename patterns first
        for pattern in self.patterns['personal']:
            if re.search(pattern, filename, re.IGNORECASE):
                return 'personal'
        
        # Large videos are likely personal
        try:
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb > self.thresholds['min_video_size_mb']:
                return 'personal'
        except Exception:
            pass
        
        return 'review'
    
    def classify_file(self, filepath: str) -> str:
        """
        Main classification method - orchestrates all classification strategies.
        
        Classification flow:
        1. Try filename patterns
        2. Detect MIME type
        3. For images: use dimensional analysis
        4. For videos: use size analysis
        5. Default to 'review' if uncertain
        
        Args:
            filepath: Path to file to classify
            
        Returns:
            Category name
        """
        filename = os.path.basename(filepath)
        
        # Strategy 1: Filename patterns (fast)
        category = self.classify_by_filename(filename)
        if category:
            return category
        
        # Strategy 2: MIME type detection
        mime, _ = mimetypes.guess_type(filepath)
        if not mime and HAS_MAGIC:
            try:
                mime = magic.from_file(filepath, mime=True)
            except Exception:
                pass
        
        if not mime:
            return 'review'
        
        # Strategy 3: Type-specific analysis
        if mime.startswith('image/'):
            return self.classify_by_dimensions(filepath)
        
        if mime.startswith('video/'):
            return self.classify_video(filepath, filename)
        
        return 'review'


# ============================================================================
# SECTION 4: CACHE MANAGEMENT
# ============================================================================

class CacheManager:
    """Manages classification cache for performance optimization"""
    
    @staticmethod
    def save(cache_file: str, classifications: Dict[str, str], 
             stats: Dict[str, int], source_dir: str, output_dir: str) -> None:
        """
        Save classification results to JSON cache file.
        
        Args:
            cache_file: Path to cache file
            classifications: Dict mapping filepath to category
            stats: Statistics dictionary
            source_dir: Source directory path (for validation)
            output_dir: Output directory path (for validation)
        """
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'source_dir': source_dir,
            'output_dir': output_dir,
            'classifications': classifications,
            'stats': stats
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    @staticmethod
    def load(cache_file: str, source_dir: str, output_dir: str) -> Optional[Tuple[Dict, Dict]]:
        """
        Load classification results from cache file.
        
        Validates that cache is for the same directories.
        
        Args:
            cache_file: Path to cache file
            source_dir: Expected source directory
            output_dir: Expected output directory
            
        Returns:
            Tuple of (classifications, stats) or None if invalid/missing
        """
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate cache matches current directories
            if (cache_data.get('source_dir') != source_dir or
                cache_data.get('output_dir') != output_dir):
                print(f"{Colors.YELLOW}⚠️  Cache is for different directories, ignoring{Colors.ENDC}")
                return None
            
            classifications = cache_data.get('classifications', {})
            stats = cache_data.get('stats', {})
            return classifications, stats
            
        except Exception as e:
            print(f"{Colors.RED}Error loading cache: {e}{Colors.ENDC}")
            return None


# ============================================================================
# SECTION 5: MAIN ORCHESTRATOR
# ============================================================================

class MediaSorter:
    """Main orchestrator for media sorting operations"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize media sorter with configuration.
        
        Args:
            config: Configuration dictionary (uses DEFAULT_CONFIG if None)
        """
        self.config = config or DEFAULT_CONFIG
        self.classifier = FileClassifier(self.config)
        self.stats = defaultdict(int)
        self.duplicates = defaultdict(list)
        self.classifications = {}
        self.errors = []
    
    def get_file_hash(self, filepath: str) -> Optional[str]:
        """
        Calculate MD5 hash of entire file for duplicate detection.
        
        Args:
            filepath: Path to file
            
        Returns:
            MD5 hash string or None on error
        """
        try:
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.errors.append(f"Hash error for {filepath}: {e}")
            return None
    
    def load_cache(self, cache_file: str) -> bool:
        """
        Load classifications from cache file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            True if cache loaded successfully
        """
        result = CacheManager.load(
            cache_file,
            self.config['source_dir'],
            self.config['output_dir']
        )
        
        if result:
            self.classifications, stats_dict = result
            self.stats = defaultdict(int, stats_dict)
            return True
        return False
    
    def save_cache(self, cache_file: str) -> None:
        """
        Save classifications to cache file.
        
        Args:
            cache_file: Path to cache file
        """
        CacheManager.save(
            cache_file,
            self.classifications,
            dict(self.stats),
            self.config['source_dir'],
            self.config['output_dir']
        )
    
    def check_output_dirs(self) -> Tuple[bool, int]:
        """
        Check if output directories exist and count existing files.
        
        Returns:
            Tuple of (directories_exist, file_count)
        """
        output_base = self.config['output_dir']
        if not os.path.exists(output_base):
            return False, 0
        
        total_existing = 0
        for category_dir in self.config['categories'].values():
            cat_path = os.path.join(output_base, category_dir)
            if os.path.exists(cat_path):
                files = [f for f in os.listdir(cat_path) 
                        if os.path.isfile(os.path.join(cat_path, f))]
                total_existing += len(files)
        
        return True, total_existing
    
    def create_output_dirs(self) -> None:
        """Create all output category directories"""
        output_base = self.config['output_dir']
        for category_dir in self.config['categories'].values():
            os.makedirs(os.path.join(output_base, category_dir), exist_ok=True)
    
    def format_time(self, seconds: float) -> str:
        """
        Format elapsed time in human-readable format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string (e.g., "12m 34.5s", "1h 5m 30s")
        """
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}h {minutes}m {secs:.0f}s"
    
    def process_files(self, dry_run: bool = True, verbose: bool = False,
                     use_cache: bool = False, save_cache_file: Optional[str] = None) -> None:
        """
        Process all files in source directory.
        
        Args:
            dry_run: If True, only classify without moving files
            verbose: If True, show more detailed progress
            use_cache: If True, use cached classifications
            save_cache_file: Path to save cache file (None to skip)
        """
        source_dir = self.config['source_dir']
        
        # Print header
        self._print_header(dry_run)
        
        # Check for existing output
        exists, existing_count = self.check_output_dirs()
        if exists and existing_count > 0:
            print(f"{Colors.YELLOW}⚠️  Warning:{Colors.ENDC} Output directory already contains {Colors.BOLD}{existing_count}{Colors.ENDC} files")
            print(f"{Colors.DIM}   Files will be added to existing categories{Colors.ENDC}\n")
        
        print(f"{Colors.CYAN}📂 Source:{Colors.ENDC}  {Colors.BOLD}{source_dir}{Colors.ENDC}")
        print(f"{Colors.CYAN}📁 Output:{Colors.ENDC}  {Colors.BOLD}{self.config['output_dir']}{Colors.ENDC}\n")
        
        # Scan directory
        print(f"{Colors.DIM}Scanning directory...{Colors.ENDC}")
        files = list(Path(source_dir).rglob('*'))
        file_list = [f for f in files if f.is_file()]
        total_files = len(file_list)
        
        if total_files == 0:
            print(f"{Colors.RED}❌ No files found in {source_dir}{Colors.ENDC}")
            return
        
        print(f"{Colors.GREEN}✓{Colors.ENDC} Found {Colors.BOLD}{total_files}{Colors.ENDC} files to process\n")
        
        # Show cache status
        if use_cache and self.classifications:
            print(f"{Colors.CYAN}📦 Using cached classifications{Colors.ENDC}")
        
        print(f"{Colors.DIM}{'─' * 70}{Colors.ENDC}\n" if use_cache else f"{Colors.DIM}{'─' * 70}{Colors.ENDC}")
        
        # Process files
        start_time = time.time()
        self._process_file_list(file_list, total_files, dry_run, use_cache, verbose)
        elapsed_time = time.time() - start_time
        
        # Save cache if requested
        if save_cache_file and not use_cache:
            self.save_cache(save_cache_file)
        
        # Print results
        self._print_results(total_files, dry_run, elapsed_time)
    
    def _print_header(self, dry_run: bool) -> None:
        """Print operation header"""
        print(f"\n{Colors.BOLD}{'═' * 70}{Colors.ENDC}")
        if dry_run:
            print(f"{Colors.YELLOW}{Colors.BOLD}🔍 DRY RUN MODE{Colors.ENDC} {Colors.DIM}(preview only - no files will be moved){Colors.ENDC}")
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}🚀 LIVE MODE{Colors.ENDC} {Colors.DIM}(files will be moved){Colors.ENDC}")
        print(f"{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")
    
    def _process_file_list(self, file_list: List[Path], total_files: int,
                          dry_run: bool, use_cache: bool, verbose: bool) -> None:
        """Process list of files"""
        processed = 0
        for filepath in file_list:
            processed += 1
            filepath_str = str(filepath)
            
            # Show progress
            if processed % 100 == 0 or (verbose and processed % 10 == 0):
                self._show_progress(processed, total_files, dry_run)
            
            # Classify or use cache
            if use_cache and filepath_str in self.classifications:
                category = self.classifications[filepath_str]
            else:
                category = self._classify_with_duplicate_check(filepath_str)
            
            # Move file if not dry run
            if not dry_run:
                self._move_file(filepath, category)
        
        # Final progress update
        self._show_progress(total_files, total_files, dry_run)
    
    def _classify_with_duplicate_check(self, filepath: str) -> str:
        """Classify file and check for duplicates"""
        file_hash = self.get_file_hash(filepath)
        
        # Check if duplicate
        if file_hash and file_hash in self.duplicates and len(self.duplicates[file_hash]) > 0:
            self.stats['duplicates'] += 1
            category = 'system_cache'
        else:
            if file_hash:
                self.duplicates[file_hash].append(filepath)
            category = self.classifier.classify_file(filepath)
        
        self.stats[category] += 1
        self.classifications[filepath] = category
        return category
    
    def _move_file(self, filepath: Path, category: str) -> None:
        """Move file to appropriate category directory"""
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
    
    def _show_progress(self, current: int, total: int, dry_run: bool) -> None:
        """Display progress bar"""
        percentage = current * 100 // total
        bar_length = 30
        filled = int(bar_length * current / total)
        bar = '█' * filled + '░' * (bar_length - filled)
        action = "Moving" if not dry_run else "Classifying"
        print(f"\r{Colors.CYAN}{action}:{Colors.ENDC} [{bar}] {Colors.BOLD}{percentage}%{Colors.ENDC} ({current}/{total})", end='', flush=True)
    
    def _print_results(self, total_files: int, dry_run: bool, elapsed_time: float) -> None:
        """Print final classification results"""
        print(f"\n\n{Colors.BOLD}{'═' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}📊 CLASSIFICATION RESULTS{Colors.ENDC}")
        print(f"{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")
        
        # Category icons
        icons = {
            'personal': '📸', 'app_icons': '📱', 'game_assets': '🎮',
            'thumbnails': '🖼️', 'system_cache': '🗑️', 'duplicates': '🔄', 'review': '❓'
        }
        
        # Print each category
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
            
            # Progress bar
            bar_length = 20
            filled = int(bar_length * percentage / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"{icon}  {color}{category:20s}{Colors.ENDC}: {Colors.BOLD}{count:6d}{Colors.ENDC} files [{bar}] {percentage:5.1f}%")
        
        # Summary
        print(f"\n{Colors.BOLD}{'─' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}Total processed:{Colors.ENDC} {Colors.CYAN}{total_files}{Colors.ENDC} files")
        print(f"{Colors.BOLD}Processing time:{Colors.ENDC} {Colors.CYAN}{self.format_time(elapsed_time)}{Colors.ENDC}")
        
        # Errors
        if self.errors:
            print(f"\n{Colors.RED}⚠️  {len(self.errors)} errors occurred:{Colors.ENDC}")
            if len(self.errors) <= 10:
                for error in self.errors:
                    print(f"  {Colors.DIM}•{Colors.ENDC} {error}")
        
        # Final message
        if dry_run:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  DRY RUN COMPLETE{Colors.ENDC} {Colors.DIM}- No files were moved{Colors.ENDC}")
            print(f"{Colors.CYAN}💡 Tip:{Colors.ENDC} Run with {Colors.BOLD}--execute{Colors.ENDC} to actually move files")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SORT COMPLETE!{Colors.ENDC}")
            print(f"{Colors.CYAN}📁 Output:{Colors.ENDC} {self.config['output_dir']}")
        
        print(f"{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")


# ============================================================================
# SECTION 6: CLI & CONFIGURATION
# ============================================================================

def load_config(config_file: str) -> dict:
    """Load configuration from JSON file, merging with defaults"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            user_config = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    return DEFAULT_CONFIG


def save_default_config(output_file: str = 'config.json') -> None:
    """Save default configuration to JSON file"""
    with open(output_file, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Default configuration saved to {output_file}")


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Smart Media Sorter - Organize photos/videos by separating personal media from system files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview only)
  python media-sorter.py --source ./photos --output ./sorted
  
  # Execute the sort
  python media-sorter.py --source ./photos --output ./sorted --execute
  
  # Use cached classifications from previous dry run
  python media-sorter.py --source ./photos --output ./sorted --execute --use-cache /tmp/cache.json
  
  # Use custom config
  python media-sorter.py --config my_config.json --execute
  
  # Generate default config
  python media-sorter.py --generate-config
        """
    )
    
    parser.add_argument('--source', '-s', help='Source directory containing files to sort')
    parser.add_argument('--output', '-o', help='Output directory for sorted files')
    parser.add_argument('--config', '-c', help='Path to JSON config file')
    parser.add_argument('--execute', action='store_true', help='Actually move files (default is dry run)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--generate-config', action='store_true', help='Generate default config.json file')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--use-cache', metavar='FILE', help='Use cached classifications from previous dry run')
    parser.add_argument('--save-cache', metavar='FILE', help='Save classifications to cache file for faster execution')
    
    args = parser.parse_args()
    
    # Handle special modes
    if args.no_color:
        Colors.disable()
    
    if args.generate_config:
        save_default_config()
        return 0
    
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
    
    # Load cache if specified
    use_cache = False
    if args.use_cache:
        use_cache = sorter.load_cache(args.use_cache)
        if not use_cache:
            print(f"{Colors.RED}Failed to load cache from {args.use_cache}{Colors.ENDC}")
            return 1
    
    # Create output dirs if executing
    if args.execute:
        sorter.create_output_dirs()
    
    # Process files
    sorter.process_files(
        dry_run=not args.execute,
        verbose=args.verbose,
        use_cache=use_cache,
        save_cache_file=args.save_cache
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
