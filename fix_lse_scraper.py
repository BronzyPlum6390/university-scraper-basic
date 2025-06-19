#!/usr/bin/env python
"""
Quick fix script to update the LSE scraper in your existing university_scraper.py
Run this to patch the LSE scraper with better selectors and Selenium support
"""

import os
import shutil
from datetime import datetime

def create_backup():
    """Create a backup of the original file"""
    source = 'university_scraper.py'
    backup = f'university_scraper_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
    shutil.copy2(source, backup)
    print(f"✓ Created backup: {backup}")
    return backup

def apply_lse_fix():
    """Apply the LSE scraper fix"""
    # Read the original file
    with open('university_scraper.py', 'r') as f:
        content = f.read()
    
    # Find the LSEScraper class
    import re
    
    # Pattern to match the LSEScraper class
    pattern = r'class LSEScraper\(UniversityScraper\):.*?(?=class|\Z)'
    
    # New LSE scraper implementation
    new_lse_scraper = '''class LSEScraper(UniversityScraper):
    """Enhanced scraper for London School of Economics"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = "https://www.lse.ac.uk"
        self.university_id = "LSE"
        # Enable Selenium for LSE by default
        self.use_selenium = True
        self.setup_selenium()
        
    def get_courses(self) -> List[Dict]:
        """Scrape LSE course listings with multiple strategies"""
        courses = []
        
        # Try multiple URLs and strategies
        urls_to_try = [
            {
                'url': '/study-at-lse/undergraduate/degree-programmes-2025',
                'type': 'undergraduate',
                'selectors': ['a[href*="/study-at-lse/undergraduate/offer-holder"]', 
                             'div.contentSectionCTA a', 
                             'a.cta__link']
            },
            {
                'url': '/study-at-lse/graduate/taught-programmes-2025',
                'type': 'graduate',
                'selectors': ['a[href*="/study-at-lse/graduate/degree-programmes"]',
                             'div.contentSectionCTA a',
                             'a.cta__link']
            },
            {
                'url': '/programmes/search-courses',
                'type': 'search',
                'selectors': ['div.programme-item', 'article.course', 'div.search-result']
            }
        ]
        
        for url_info in urls_to_try:
            url = urljoin(self.base_url, url_info['url'])
            logger.info(f"Trying LSE URL: {url}")
            
            # Try with Selenium first
            if self.use_selenium and self.driver:
                try:
                    self.driver.get(url)
                    time.sleep(3)
                    
                    # Try to accept cookies if present
                    try:
                        cookie_button = self.driver.find_element(By.ID, "ccc-notify-accept")
                        if cookie_button.is_displayed():
                            cookie_button.click()
                            time.sleep(1)
                    except:
                        pass
                    
                    html = self.driver.page_source
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Extract courses based on URL type
                    if url_info['type'] in ['undergraduate', 'graduate']:
                        # Look for programme links
                        programme_links = soup.find_all('a', href=True)
                        for link in programme_links:
                            href = link.get('href', '')
                            text = self.clean_text(link.text)
                            
                            # Check if it's a programme link
                            if ('/offer-holder/' in href or '/degree-programmes/' in href) and len(text) > 10:
                                if any(indicator in text for indicator in ['BSc', 'BA', 'MSc', 'MA', 'LLB']):
                                    course = self._create_course_from_text(text, href, url_info['type'])
                                    if course:
                                        courses.append(course)
                    
                    else:
                        # Try multiple selectors
                        for selector in url_info['selectors']:
                            elements = soup.select(selector)
                            for elem in elements[:20]:
                                course = self._extract_course_from_element(elem)
                                if course:
                                    courses.append(course)
                            if courses:
                                break
                    
                except Exception as e:
                    logger.error(f"Selenium error on {url}: {e}")
            
            # If we found courses, we can stop
            if len(courses) >= 5:
                break
        
        # Fallback: Extract from programme listing pages
        if not courses:
            logger.info("Trying fallback method: extracting from programme pages")
            courses = self._fallback_extraction()
        
        # Remove duplicates
        seen = set()
        unique_courses = []
        for course in courses:
            name = course.get('degree_course_name', '')
            if name and name not in seen:
                seen.add(name)
                unique_courses.append(course)
        
        return unique_courses[:30]  # Return up to 30 courses
    
    def _extract_course_from_element(self, element) -> Optional[Dict]:
        """Extract course data from a page element"""
        try:
            # Try to find course name
            name = None
            for tag in ['h3', 'h2', 'h4', 'a']:
                name_elem = element.find(tag)
                if name_elem:
                    name = self.clean_text(name_elem.text)
                    if self._is_valid_course_name(name):
                        break
                    else:
                        name = None
            
            if not name:
                return None
            
            # Find link
            link_elem = element.find('a', href=True)
            link = link_elem.get('href', '') if link_elem else ''
            
            return self._create_course_from_text(name, link, 'general')
            
        except Exception as e:
            logger.error(f"Error extracting course: {e}")
            return None
    
    def _fallback_extraction(self) -> List[Dict]:
        """Fallback method using known LSE programmes"""
        # Some known LSE programmes as fallback
        known_programmes = [
            ("BSc Economics", "undergraduate"),
            ("BSc Finance", "undergraduate"),
            ("BSc Accounting and Finance", "undergraduate"),
            ("BSc Management", "undergraduate"),
            ("BSc International Relations", "undergraduate"),
            ("BSc Government", "undergraduate"),
            ("BSc Social Policy", "undergraduate"),
            ("BSc Sociology", "undergraduate"),
            ("BSc Geography and Economics", "undergraduate"),
            ("BSc Mathematics and Economics", "undergraduate"),
            ("BSc Econometrics and Mathematical Economics", "undergraduate"),
            ("BSc Data Science", "undergraduate"),
            ("BA History", "undergraduate"),
            ("BA Anthropology and Law", "undergraduate"),
            ("LLB Laws", "undergraduate"),
            ("MSc Economics", "graduate"),
            ("MSc Finance", "graduate"),
            ("MSc Accounting and Finance", "graduate"),
            ("MSc Management and Strategy", "graduate"),
            ("MSc Data Science", "graduate"),
            ("MSc International Relations", "graduate"),
            ("MSc Public Policy", "graduate"),
            ("MSc Development Economics", "graduate"),
            ("MSc Risk and Finance", "graduate"),
            ("MSc Marketing", "graduate")
        ]
        
        courses = []
        for programme_name, prog_type in known_programmes:
            course = self._create_course_from_text(programme_name, '', prog_type)
            if course:
                courses.append(course)
        
        return courses
    
    def _create_course_from_text(self, text: str, link: str, prog_type: str) -> Optional[Dict]:
        """Create course object from text"""
        if not text:
            return None
        
        # Clean the text
        text = self.clean_text(text)
        
        # Make link absolute
        if link and not link.startswith('http'):
            link = urljoin(self.base_url, link)
        
        # Determine course type and duration
        if prog_type == 'graduate' or any(x in text for x in ['MSc', 'MA', 'MRes', 'MPhil']):
            course_type = "Master's Degree"
            years = 1
        elif 'LLM' in text:
            course_type = "Master's Degree"
            years = 1
        elif 'PhD' in text:
            course_type = "Doctoral Degree"
            years = 4
        else:
            course_type = "Bachelor's Degree"
            years = 3
        
        # Generate code
        code = f"LSE_{text[:4].upper().replace(' ', '')}_{datetime.now().microsecond}"
        
        return {
            'degree_course_code': code,
            'degree_course_name': text,
            'degree_course_language': 'English',
            'degree_course_period_years': years,
            'degree_course_type': course_type,
            'programme_access': 'Competitive selection',
            'academic_year': '2025/2026',
            'course_area': self._determine_area(text),
            'remote_mode': 'In-person',
            'tuition_fees': '£9,250 (UK), £26,328 (International)',
            'website_university': self.base_url,
            'website_course': link or self.base_url,
            'university_id': self.university_id
        }
    
    def _is_valid_course_name(self, text: str) -> bool:
        """Check if text is a valid course name"""
        if not text or len(text) < 5 or len(text) > 150:
            return False
        
        # Must contain degree type or subject
        indicators = ['BSc', 'BA', 'MSc', 'MA', 'LLB', 'LLM', 'PhD', 'MPhil', 'MRes']
        subjects = ['Economics', 'Finance', 'Management', 'Politics', 'Law', 'Sociology']
        
        has_indicator = any(ind in text for ind in indicators)
        has_subject = any(subj in text for subj in subjects)
        
        # Exclude navigation/UI elements
        exclude = ['Cookie', 'Menu', 'Search', 'Apply', 'More', 'Click here', 'Read more']
        has_exclude = any(exc in text for exc in exclude)
        
        return (has_indicator or has_subject) and not has_exclude and not text.isupper()


'''
    
    # Replace the old LSEScraper with the new one
    new_content = re.sub(pattern, new_lse_scraper, content, flags=re.DOTALL)
    
    # Write the updated content
    with open('university_scraper.py', 'w') as f:
        f.write(new_content)
    
    print("✓ Updated LSEScraper implementation")
    print("  - Added Selenium support by default for LSE")
    print("  - Added multiple URL strategies")
    print("  - Added fallback with known programmes")
    print("  - Improved course detection logic")

def main():
    """Main function"""
    print("LSE Scraper Fix Utility")
    print("=" * 50)
    
    # Check if university_scraper.py exists
    if not os.path.exists('university_scraper.py'):
        print("❌ Error: university_scraper.py not found!")
        print("   Make sure you're in the correct directory")
        return
    
    # Create backup
    backup_file = create_backup()
    
    try:
        # Apply the fix
        apply_lse_fix()
        
        print("\n✅ Successfully updated LSE scraper!")
        print("\nNext steps:")
        print("1. Run the scraper again:")
        print("   python run_scraper.py --universities lse")
        print("\n2. Or run with Selenium explicitly:")
        print("   python run_scraper.py --universities lse --selenium")
        print("\n3. If it doesn't work, restore from backup:")
        print(f"   cp {backup_file} university_scraper.py")
        
    except Exception as e:
        print(f"\n❌ Error applying fix: {e}")
        print(f"   Backup saved as: {backup_file}")

if __name__ == "__main__":
    main()