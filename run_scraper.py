#!/usr/bin/env python
"""
Entry point for the university scraper
Handles command-line arguments and orchestrates the scraping process
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from university_scraper import main, DatabaseManager, logger


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        # Return default configuration
        return {
            "database": "data/universities.db",
            "export_path": "data/exports",
            "log_path": "data/logs",
            "universities": ["bologna", "lse"],
            "use_selenium": False,
            "headless": True,
            "timeout": 30,
            "rate_limit_delay": 1
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        sys.exit(1)


def create_directories(config: dict):
    """Create necessary directories if they don't exist"""
    directories = [
        os.path.dirname(config['database']),
        config['export_path'],
        config['log_path'],
        f"{config['export_path']}/json",
        f"{config['export_path']}/csv",
        f"{config['export_path']}/excel"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='University Data Scraper - Collect course information from universities'
    )
    
    parser.add_argument(
        '--config',
        default='config/config.json',
        help='Path to configuration file (default: config/config.json)'
    )
    
    parser.add_argument(
        '--universities',
        nargs='+',
        choices=['bologna', 'lse', 'all'],
        help='Universities to scrape (default: all configured)'
    )
    
    parser.add_argument(
        '--export',
        choices=['json', 'csv', 'excel', 'all'],
        help='Export data after scraping'
    )
    
    parser.add_argument(
        '--selenium',
        action='store_true',
        help='Use Selenium for JavaScript-heavy pages'
    )
    
    parser.add_argument(
        '--no-scrape',
        action='store_true',
        help='Skip scraping and only export existing data'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean database before scraping'
    )
    
    return parser.parse_args()


def export_data(db: DatabaseManager, export_type: str, config: dict):
    """Export data in specified format"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = config['export_path']
    
    if export_type in ['json', 'all']:
        output_file = f"{export_path}/json/university_data_{timestamp}.json"
        db.export_to_json(output_file)
        print(f"✓ Exported to JSON: {output_file}")
    
    if export_type in ['csv', 'all']:
        output_dir = f"{export_path}/csv/{timestamp}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        db.export_to_csv(output_dir)
        print(f"✓ Exported to CSV: {output_dir}")
    
    if export_type in ['excel', 'all']:
        output_file = f"{export_path}/excel/university_data_{timestamp}.xlsx"
        db.export_to_excel(output_file)
        print(f"✓ Exported to Excel: {output_file}")


def show_statistics(db: DatabaseManager):
    """Display database statistics"""
    stats = db.get_statistics()
    
    print("\n" + "="*50)
    print("DATABASE STATISTICS")
    print("="*50)
    print(f"Total Universities: {stats['universities']}")
    print(f"Total Courses: {stats['courses']}")
    
    if stats['by_university']:
        print("\nCourses by University:")
        for uni, count in stats['by_university'].items():
            print(f"  - {uni}: {count}")
    
    if stats['by_area']:
        print("\nCourses by Area:")
        for area, count in stats['by_area'].items():
            print(f"  - {area}: {count}")
    
    print("="*50 + "\n")


def clean_database(config: dict):
    """Clean/reset the database"""
    db_path = config['database']
    if os.path.exists(db_path):
        # Backup existing database
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(db_path, backup_path)
        print(f"✓ Database backed up to: {backup_path}")
    
    # Create new database
    db = DatabaseManager(db_path)
    print("✓ Database cleaned and initialized")
    return db


def main_cli():
    """Main CLI function"""
    print("\n🎓 University Data Scraper")
    print("="*50)
    
    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments
    if args.selenium:
        config['use_selenium'] = True
    
    if args.universities and 'all' not in args.universities:
        config['universities'] = args.universities
    
    # Create necessary directories
    create_directories(config)
    
    # Initialize database
    if args.clean:
        db = clean_database(config)
    else:
        db = DatabaseManager(config['database'])
    
    # Show statistics if requested
    if args.stats:
        show_statistics(db)
        if not args.export and not args.no_scrape:
            return
    
    # Run scraping unless skipped
    if not args.no_scrape:
        print(f"\n🔍 Starting scrape for: {', '.join(config['universities'])}")
        print(f"   Selenium: {'Enabled' if config.get('use_selenium') else 'Disabled'}")
        print("="*50 + "\n")
        
        try:
            db = main(config)
            print("\n✅ Scraping completed successfully!")
        except KeyboardInterrupt:
            print("\n\n⚠️  Scraping interrupted by user")
            return
        except Exception as e:
            print(f"\n❌ Scraping failed: {e}")
            logger.error(f"Fatal error: {e}", exc_info=True)
            return
    
    # Export data if requested
    if args.export:
        print(f"\n📤 Exporting data...")
        export_data(db, args.export, config)
    
    # Show final statistics
    print("\n📊 Final Statistics:")
    show_statistics(db)
    
    print("✨ All done!\n")


if __name__ == "__main__":
    main_cli()