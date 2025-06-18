"""
University Data Scraper - Main Module
Handles scraping logic for multiple universities
"""

import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time
import re
from urllib.parse import urljoin, urlparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UniversityScraper:
    """Base scraper class with common functionality"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.driver = None
        self.use_selenium = config.get('use_selenium', False)
        
    def setup_selenium(self):
        """Initialize Selenium WebDriver"""
        if not self.use_selenium:
            return
            
        chrome_options = Options()
        if self.config.get('headless', True):
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            self.driver = webdriver.Chrome(
                ChromeDriverManager().install(),
                options=chrome_options
            )
            logger.info("Selenium WebDriver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            self.use_selenium = False
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            if self.use_selenium and self.driver:
                self.driver.get(url)
                time.sleep(2)  # Wait for page load
                html = self.driver.page_source
                return BeautifulSoup(html, 'lxml')
            else:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return ' '.join(text.strip().split())
    
    def extract_number(self, text: str, pattern: str = r'\d+') -> Optional[int]:
        """Extract number from text"""
        match = re.search(pattern, str(text))
        return int(match.group()) if match else None
    
    def __del__(self):
        """Cleanup Selenium driver"""
        if self.driver:
            self.driver.quit()


class BolognaScraper(UniversityScraper):
    """Scraper for University of Bologna"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = "https://www.unibo.it"
        self.university_id = "UNIBO"
        
    def get_university_info(self) -> Dict:
        """Get basic university information"""
        return {
            'university_id': self.university_id,
            'university_name': 'Università di Bologna',
            'university_city': 'Bologna',
            'university_region': 'Emilia-Romagna',
            'university_website': self.base_url,
            'university_email': 'internationaldesk@unibo.it',
            'university_phone': '+39 051 2099111',
            'university_ranking_national': 1,
            'university_ranking_world': 133
        }
    
    def get_courses(self) -> List[Dict]:
        """Scrape course listings"""
        courses = []
        
        # URLs for different degree types
        urls = {
            'first_cycle': '/en/study/first-and-single-cycle-degree',
            'second_cycle': '/en/study/second-cycle-degree'
        }
        
        for degree_type, url_path in urls.items():
            url = urljoin(self.base_url, url_path)
            logger.info(f"Scraping {degree_type} courses from {url}")
            
            soup = self.fetch_page(url)
            if not soup:
                continue
            
            # Extract course links (simplified - actual selectors would be more specific)
            course_items = soup.find_all('div', class_='course-item') or \
                          soup.find_all('a', href=re.compile(r'/en/study/.*degree'))
            
            for item in course_items[:10]:  # Limit for testing
                course_data = self._parse_course_item(item, degree_type)
                if course_data:
                    courses.append(course_data)
                time.sleep(1)  # Rate limiting
                
        return courses
    
    def _parse_course_item(self, item, degree_type: str) -> Optional[Dict]:
        """Parse individual course information"""
        try:
            # Extract basic info from listing
            if item.name == 'a':
                name = self.clean_text(item.text)
                url = urljoin(self.base_url, item.get('href', ''))
            else:
                link = item.find('a')
                if not link:
                    return None
                name = self.clean_text(link.text)
                url = urljoin(self.base_url, link.get('href', ''))
            
            # Generate course code
            code = f"{self.university_id}_{name[:3].upper()}_{datetime.now().microsecond}"
            
            # Determine course type
            if degree_type == 'first_cycle':
                course_type = "Bachelor's Degree"
                years = 3
            else:
                course_type = "Master's Degree"
                years = 2
            
            return {
                'degree_course_code': code,
                'degree_course_name': name,
                'degree_course_language': 'English',  # Would need to detect
                'degree_course_period_years': years,
                'degree_course_type': course_type,
                'programme_access': 'Open access',
                'academic_year': '2025/2026',
                'course_area': self._determine_area(name),
                'remote_mode': 'In-person',
                'tuition_fees': '€2,925 - €3,295',
                'website_university': self.base_url,
                'website_course': url,
                'university_id': self.university_id
            }
        except Exception as e:
            logger.error(f"Error parsing course item: {e}")
            return None
    
    def _determine_area(self, course_name: str) -> str:
        """Determine course area from name"""
        areas = {
            'Engineering': ['Engineering', 'Computer', 'Electronic', 'Mechanical'],
            'Medicine': ['Medicine', 'Medical', 'Health', 'Pharmaceutical'],
            'Economics': ['Economics', 'Business', 'Finance', 'Management'],
            'Sciences': ['Physics', 'Chemistry', 'Biology', 'Mathematics'],
            'Humanities': ['History', 'Philosophy', 'Literature', 'Languages'],
            'Law': ['Law', 'Legal', 'Juridical']
        }
        
        course_upper = course_name.upper()
        for area, keywords in areas.items():
            if any(keyword.upper() in course_upper for keyword in keywords):
                return area
        return 'Other'


class LSEScraper(UniversityScraper):
    """Scraper for London School of Economics"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = "https://www.lse.ac.uk"
        self.university_id = "LSE"
        
    def get_university_info(self) -> Dict:
        """Get basic university information"""
        return {
            'university_id': self.university_id,
            'university_name': 'London School of Economics and Political Science',
            'university_city': 'London',
            'university_region': 'Greater London',
            'university_website': self.base_url,
            'university_email': 'admissions@lse.ac.uk',
            'university_phone': '+44 (0)20 7405 7686',
            'university_ranking_national': 1,
            'university_ranking_world': 50
        }
    
    def get_courses(self) -> List[Dict]:
        """Scrape LSE course listings"""
        courses = []
        
        # LSE course search page
        url = urljoin(self.base_url, "/programmes/search-courses")
        logger.info(f"Scraping LSE courses from {url}")
        
        soup = self.fetch_page(url)
        if not soup:
            return courses
        
        # Find course listings
        course_items = soup.find_all('div', class_='programme-item') or \
                      soup.find_all('article', class_='course')
        
        for item in course_items[:10]:  # Limit for testing
            course_data = self._parse_course_item(item)
            if course_data:
                courses.append(course_data)
            time.sleep(1)
            
        return courses
    
    def _parse_course_item(self, item) -> Optional[Dict]:
        """Parse individual course information"""
        try:
            # Extract title
            title_elem = item.find(['h2', 'h3', 'h4'])
            if not title_elem:
                return None
            
            name = self.clean_text(title_elem.text)
            
            # Extract link
            link = item.find('a')
            url = urljoin(self.base_url, link.get('href', '')) if link else ''
            
            # Determine course type and duration
            if 'BSc' in name or 'BA' in name:
                course_type = "Bachelor's Degree"
                years = 3
            elif 'MSc' in name or 'MA' in name:
                course_type = "Master's Degree"
                years = 1
            else:
                course_type = "Other"
                years = 1
            
            # Generate course code
            code = f"{self.university_id}_{name[:4].upper()}_{datetime.now().microsecond}"
            
            return {
                'degree_course_code': code,
                'degree_course_name': name,
                'degree_course_language': 'English',
                'degree_course_period_years': years,
                'degree_course_type': course_type,
                'programme_access': 'Competitive selection',
                'academic_year': '2025/2026',
                'course_area': self._determine_area(name),
                'remote_mode': 'In-person',
                'tuition_fees': '£9,250 (UK), £26,328 (International)',
                'website_university': self.base_url,
                'website_course': url,
                'university_id': self.university_id
            }
        except Exception as e:
            logger.error(f"Error parsing LSE course: {e}")
            return None
    
    def _determine_area(self, course_name: str) -> str:
        """Determine course area from name"""
        areas = {
            'Economics': ['Economics', 'Econometrics', 'Economic'],
            'Finance': ['Finance', 'Accounting', 'Actuarial'],
            'Politics': ['Politics', 'Government', 'International Relations'],
            'Social Sciences': ['Sociology', 'Anthropology', 'Social'],
            'Management': ['Management', 'Business'],
            'Data Science': ['Data', 'Statistics'],
            'Law': ['Law', 'Legal']
        }
        
        course_upper = course_name.upper()
        for area, keywords in areas.items():
            if any(keyword.upper() in course_upper for keyword in keywords):
                return area
        return 'Other'


class DatabaseManager:
    """Manage SQLite database operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Universities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS universities (
                    university_id TEXT PRIMARY KEY,
                    university_name TEXT NOT NULL,
                    university_city TEXT,
                    university_region TEXT,
                    university_website TEXT,
                    university_email TEXT,
                    university_phone TEXT,
                    university_ranking_national INTEGER,
                    university_ranking_world INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Courses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS degree_courses (
                    degree_course_code TEXT PRIMARY KEY,
                    degree_course_name TEXT NOT NULL,
                    degree_course_language TEXT,
                    degree_course_period_years INTEGER,
                    degree_course_type TEXT,
                    programme_access TEXT,
                    academic_year TEXT,
                    course_area TEXT,
                    remote_mode TEXT,
                    tuition_fees TEXT,
                    website_university TEXT,
                    website_course TEXT,
                    university_id TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (university_id) REFERENCES universities(university_id)
                )
            ''')
            
            # Learning modules table (simplified for now)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_modules (
                    learning_code TEXT PRIMARY KEY,
                    learning_ssd TEXT,
                    learning_cfu INTEGER,
                    learning_hour INTEGER,
                    learning_language TEXT,
                    learning_ref TEXT,
                    degree_course_code TEXT,
                    university_id TEXT,
                    semester TEXT,
                    FOREIGN KEY (degree_course_code) REFERENCES degree_courses(degree_course_code),
                    FOREIGN KEY (university_id) REFERENCES universities(university_id)
                )
            ''')
            
            # Admission requirements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admission_requirements (
                    requirement_id TEXT PRIMARY KEY,
                    requirement_type TEXT,
                    requirement_description TEXT,
                    is_mandatory BOOLEAN,
                    degree_course_code TEXT,
                    FOREIGN KEY (degree_course_code) REFERENCES degree_courses(degree_course_code)
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def save_university(self, university_data: Dict):
        """Save university information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO universities 
                (university_id, university_name, university_city, university_region,
                 university_website, university_email, university_phone,
                 university_ranking_national, university_ranking_world)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                university_data['university_id'],
                university_data['university_name'],
                university_data['university_city'],
                university_data['university_region'],
                university_data['university_website'],
                university_data.get('university_email'),
                university_data.get('university_phone'),
                university_data.get('university_ranking_national'),
                university_data.get('university_ranking_world')
            ))
            conn.commit()
    
    def save_courses(self, courses: List[Dict]):
        """Save course information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for course in courses:
                cursor.execute('''
                    INSERT OR REPLACE INTO degree_courses
                    (degree_course_code, degree_course_name, degree_course_language,
                     degree_course_period_years, degree_course_type, programme_access,
                     academic_year, course_area, remote_mode, tuition_fees,
                     website_university, website_course, university_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    course['degree_course_code'],
                    course['degree_course_name'],
                    course['degree_course_language'],
                    course['degree_course_period_years'],
                    course['degree_course_type'],
                    course['programme_access'],
                    course['academic_year'],
                    course['course_area'],
                    course['remote_mode'],
                    course['tuition_fees'],
                    course['website_university'],
                    course['website_course'],
                    course['university_id']
                ))
            conn.commit()
            logger.info(f"Saved {len(courses)} courses")
    
    def export_to_json(self, output_file: str):
        """Export database to JSON"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            data = {
                'export_date': datetime.now().isoformat(),
                'universities': [],
                'courses': [],
                'modules': [],
                'requirements': []
            }
            
            # Export universities
            cursor.execute("SELECT * FROM universities")
            data['universities'] = [dict(row) for row in cursor.fetchall()]
            
            # Export courses
            cursor.execute("SELECT * FROM degree_courses")
            data['courses'] = [dict(row) for row in cursor.fetchall()]
            
            # Export modules
            cursor.execute("SELECT * FROM learning_modules")
            data['modules'] = [dict(row) for row in cursor.fetchall()]
            
            # Export requirements
            cursor.execute("SELECT * FROM admission_requirements")
            data['requirements'] = [dict(row) for row in cursor.fetchall()]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data exported to {output_file}")
    
    def export_to_csv(self, output_dir: str):
        """Export database tables to CSV files"""
        with sqlite3.connect(self.db_path) as conn:
            # Export universities
            df = pd.read_sql_query("SELECT * FROM universities", conn)
            df.to_csv(f"{output_dir}/universities.csv", index=False)
            
            # Export courses
            df = pd.read_sql_query("SELECT * FROM degree_courses", conn)
            df.to_csv(f"{output_dir}/courses.csv", index=False)
            
            logger.info(f"Data exported to CSV in {output_dir}")
    
    def export_to_excel(self, output_file: str):
        """Export database to Excel with multiple sheets"""
        with sqlite3.connect(self.db_path) as conn:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Universities sheet
                df = pd.read_sql_query("SELECT * FROM universities", conn)
                df.to_excel(writer, sheet_name='Universities', index=False)
                
                # Courses sheet
                df = pd.read_sql_query("SELECT * FROM degree_courses", conn)
                df.to_excel(writer, sheet_name='Courses', index=False)
                
                # Modules sheet
                df = pd.read_sql_query("SELECT * FROM learning_modules", conn)
                df.to_excel(writer, sheet_name='Modules', index=False)
                
                # Requirements sheet
                df = pd.read_sql_query("SELECT * FROM admission_requirements", conn)
                df.to_excel(writer, sheet_name='Requirements', index=False)
                
            logger.info(f"Data exported to {output_file}")
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count universities
            cursor.execute("SELECT COUNT(*) FROM universities")
            stats['universities'] = cursor.fetchone()[0]
            
            # Count courses
            cursor.execute("SELECT COUNT(*) FROM degree_courses")
            stats['courses'] = cursor.fetchone()[0]
            
            # Count by university
            cursor.execute("""
                SELECT u.university_name, COUNT(c.degree_course_code) as course_count
                FROM universities u
                LEFT JOIN degree_courses c ON u.university_id = c.university_id
                GROUP BY u.university_id
            """)
            stats['by_university'] = dict(cursor.fetchall())
            
            # Count by course area
            cursor.execute("""
                SELECT course_area, COUNT(*) as count
                FROM degree_courses
                GROUP BY course_area
            """)
            stats['by_area'] = dict(cursor.fetchall())
            
            return stats


def main(config: Dict):
    """Main scraping function"""
    # Initialize database
    db = DatabaseManager(config['database'])
    
    # Initialize scrapers
    scrapers = {
        'bologna': BolognaScraper(config),
        'lse': LSEScraper(config)
    }
    
    # Process each university
    for uni_name, scraper in scrapers.items():
        if uni_name not in config.get('universities', []):
            continue
            
        logger.info(f"Starting scrape for {uni_name}")
        
        try:
            # Setup Selenium if needed
            scraper.setup_selenium()
            
            # Get university info
            uni_info = scraper.get_university_info()
            db.save_university(uni_info)
            logger.info(f"Saved university info for {uni_name}")
            
            # Get courses
            courses = scraper.get_courses()
            if courses:
                db.save_courses(courses)
                logger.info(f"Saved {len(courses)} courses for {uni_name}")
            else:
                logger.warning(f"No courses found for {uni_name}")
                
        except Exception as e:
            logger.error(f"Error scraping {uni_name}: {e}")
            continue
    
    # Print statistics
    stats = db.get_statistics()
    logger.info(f"Scraping complete. Statistics: {stats}")
    
    return db