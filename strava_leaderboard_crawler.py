import requests
from bs4 import BeautifulSoup
import re
import os
import selenium
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import pickle
from dotenv import load_dotenv

load_dotenv()

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.getenv('LOG_DIR', os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = f"{LOG_DIR}/.logs"
if 'hieusv' in LOG_DIR:
    LOG_FILE = os.path.join(LOG_DIR, 'crawl.log')
else:
    LOG_FILE = os.path.join(LOG_DIR, '.log')

# Set up logging with 7-day rotation
def setup_logging():
    """Configure logging with file rotation (7 days)"""
    # Create log directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler with daily rotation, keep 7 days
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logging
logger = setup_logging()

class StravaLeaderboardCrawler:
    """
    Service to crawl Strava group leaderboard and add users
    """
    def __init__(self, group_url, database_url=None):
        """
        Initialize crawler with Strava group URL
        
        :param group_url: Full URL of the Strava group leaderboard
        :param database_url: PostgreSQL database URL
        """
        self.group_url = group_url
        self.database_url = database_url or os.getenv('DATABASE_URL')

    def get_chrome_driver(self):
        """Initialize Chrome WebDriver with proper configuration"""
        from selenium import webdriver
        
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        if "GOOGLE_CHROME_BIN" in os.environ:  # Heroku
            chrome_options.binary_location = os.environ["GOOGLE_CHROME_BIN"]

            if selenium.__version__.split(".")[0] == '4':
                from selenium.webdriver.chrome.service import Service
                service = Service(executable_path=os.environ["CHROMEDRIVER_PATH"])
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(executable_path=os.environ["CHROMEDRIVER_PATH"], chrome_options=chrome_options)
        else:
            if selenium.__version__.split(".")[0] == '4':
                driver = webdriver.Chrome(options=chrome_options)
            else:
                driver = webdriver.Chrome(chrome_options=chrome_options)
        
        return driver

    def load_strava_cookies(self, driver):
        """Load Strava authentication cookies"""
        import pickle
        try:
            cookie_file = os.getenv('STRAVA_COOKIE_FILE')
            cookies = pickle.load(open(cookie_file, "rb"))
            logger.info(f"Loaded {len(cookies)} cookies from {cookie_file}")
        except FileNotFoundError:
            logger.warning("Cookie file not found, continuing without authentication")
            cookies = []
        
        for cookie in cookies:
            driver.add_cookie(cookie)
        
        return len(cookies) > 0

    def get_data_from_driver(self, driver, week_start, week_end):
        """Extract runner data from current driver state"""
        from selenium.webdriver.common.by import By
        
        table = driver.find_element(By.CSS_SELECTOR, "div.leaderboard > table > tbody").get_attribute("innerHTML")
        soup = BeautifulSoup(table, "html.parser")

        runners = []
        
        def get_average_pace_in_seconds(minute_second):
            if minute_second == "--":
                return 0.0
            else:
                minute = minute_second.split(":")[0]
                second = minute_second.split(":")[1]
                return 60 * float(minute) + float(second)
        
        def get_elevation_gain(text):
            if text == "--":
                return 0.0
            else:
                return float(text.split()[0].replace(",", ""))

        for row in soup.find_all("tr"):
            runner = {
                "id": int(row.find("td", class_="athlete").find("a")["href"].split("/")[-1]),
                "name": row.find("a", class_="athlete-name").text.strip(),
                "distance": float(str(row.find("td", class_="distance").text.split()[0]).replace("km","").replace(",",".")),
                "runs": int(row.find("td", class_="num-activities").text),
                "longest_run": 0,
                "average_pace": get_average_pace_in_seconds(
                    row.find("td", class_="average-pace").text.split("/")[0].strip()),
                "elevation_gain": get_elevation_gain(row.find("td", class_="elev-gain").text.strip()),
                "week_start": week_start,
                "week_end": week_end
            }
            runners.append(runner)

        return runners

    def crawl_leaderboard(self, include_last_week=True):
        """
        Crawl the Strava group leaderboard and add/update users
        
        :param include_last_week: Whether to also fetch last week's data
        :return: Tuple of (this_week_runners, last_week_runners)
        """
        try:
            from selenium import webdriver
            from selenium.common.exceptions import TimeoutException
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions
            from selenium.webdriver.support.wait import WebDriverWait

            driver = self.get_chrome_driver()

            # Navigate to Strava and load cookies
            driver.get("https://www.strava.com/")
            self.load_strava_cookies(driver)
            driver.get("https://www.strava.com/clubs/hienvuong")
            
            # Wait for page to load
            try:
                WebDriverWait(driver, 30).until(expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.page")))
            except TimeoutException:
                logger.warning("Request timed out waiting for page to load")

            # Get current week's data
            week_start, week_end = self.get_current_week_range()
            logger.info(f"Fetching current week data: {week_start} to {week_end}")
            
            this_week_runners = self.get_data_from_driver(driver, week_start, week_end)
            logger.info(f"Found {len(this_week_runners)} runners for current week")
            
            last_week_runners = []
            if include_last_week:
                try:
                    # Click last week button
                    last_week_btn = driver.find_element(By.CSS_SELECTOR, "span.button.last-week")
                    last_week_btn.click()
                    
                    # Wait a moment for data to load
                    WebDriverWait(driver, 10).until(
                        expected_conditions.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.leaderboard > table > tbody")
                        )
                    )
                    
                    # Get last week's data
                    last_week_start, last_week_end = self.get_last_week_range()
                    logger.info(f"Fetching last week data: {last_week_start} to {last_week_end}")
                    
                    last_week_runners = self.get_data_from_driver(driver, last_week_start, last_week_end)
                    logger.info(f"Found {len(last_week_runners)} runners for last week")
                    
                except Exception as e:
                    logger.warning(f"Could not fetch last week data: {e}")
            
            driver.quit()
            
            # Process current week data
            self.process_athletes(this_week_runners, week_start, week_end)
            
            return this_week_runners, last_week_runners

        except Exception as e:
            logger.error(f"Error crawling leaderboard: {e}")
            return [], []

    def get_current_week_range(self):
        """Get current week's Monday to Sunday range using ISO week calculation"""
        today = datetime.now().date()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    def get_last_week_range(self):
        """Get last week's Monday to Sunday range"""
        this_week_start, _ = self.get_current_week_range()
        last_week_end = this_week_start - timedelta(days=1)
        last_week_start = last_week_end - timedelta(days=6)
        return last_week_start, last_week_end

    def get_last_week_year_and_week_num(self):
        """Get last week's year and ISO week number"""
        last_week_start, _ = self.get_last_week_range()
        iso_calendar = last_week_start.isocalendar()
        return iso_calendar[0], iso_calendar[1]

    def get_db_connection(self):
        """Get database connection"""
        conn = psycopg2.connect(self.database_url)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn

    def get_user_by_username(self, username):
        """Get user by username"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user

    def create_user(self, username, first_name, last_name="", is_external=True):
        """Create a new user"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, first_name, last_name, is_external)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (username, first_name, last_name, is_external))
            user_id = cursor.fetchone()['id']
            conn.commit()
            cursor.close()
            return user_id
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            conn.close()

    def should_update_last_week_leaderboard(self):
        """Check if last week's leaderboard should be updated based on update time"""
        last_week_start, _ = self.get_last_week_range()
        current_week_start, _ = self.get_current_week_range()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Check if any last week record was updated before this week started
        cursor.execute('''
            SELECT MAX(updated_at) as last_updated FROM weekly_challenges
            WHERE start_date = %s
        ''', (last_week_start,))
        
        last_update_result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not last_update_result or not last_update_result['last_updated']:
            logger.info(f"No last week records found for {last_week_start}, will update")
            return True
            
        last_updated = last_update_result['last_updated']
        current_week_start_datetime = datetime.combine(current_week_start, datetime.min.time())
        
        if last_updated < current_week_start_datetime:
            logger.info(f"Last week records updated before this week ({last_updated} < {current_week_start_datetime}), will update")
            return True
        else:
            logger.info(f"Last week records already updated this week ({last_updated} >= {current_week_start_datetime}), skipping")
            return False

    def create_or_update_challenge(self, user_id, week_start, week_end, distance_goal, athlete_details):
        """Create or update weekly challenge for user"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Check if challenge exists
        cursor.execute('''
            SELECT * FROM weekly_challenges 
            WHERE user_id = %s AND start_date = %s
        ''', (user_id, week_start))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing challenge
            cursor.execute('''
                UPDATE weekly_challenges 
                SET total_distance = %s, runs = %s, 
                    average_pace = %s, elevation_gain = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND start_date = %s
            ''', (athlete_details['distance'], athlete_details['runs'],
                  athlete_details['average_pace'], athlete_details['elevation_gain'],
                  user_id, week_start))
        else:
            # Create new challenge
            cursor.execute('''
                INSERT INTO weekly_challenges 
                (user_id, start_date, end_date, distance_goal, total_distance, runs, average_pace, elevation_gain)
                VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
            ''', (user_id, week_start, week_end, 0, athlete_details['distance'],
                  athlete_details['runs'], athlete_details['average_pace'], athlete_details['elevation_gain']))
        
        conn.commit()
        cursor.close()
        conn.close()

    def process_athletes(self, runners, week_start, week_end):
        """Process each athlete and update database"""
        for athlete_details in runners:
            username = "strava_" + str(athlete_details['id'])
            
            # Get or create user
            user = self.get_user_by_username(username)
            
            if not user:
                # Create new user
                user_id = self.create_user(
                    username=username,
                    first_name=athlete_details['name'],
                    last_name="",
                    is_external=True
                )
                if not user_id:
                    logger.error(f"Failed to create user {username}")
                    continue
            else:
                user_id = user['id']

            # Determine appropriate challenge goal
            challenge_goals = [35, 45, 55, 65, 75, 85, 100]
            distance_goal = next(
                (goal for goal in challenge_goals if goal >= athlete_details['distance']), 
                100
            )

            # Create or update challenge
            self.create_or_update_challenge(
                user_id, week_start, week_end, distance_goal, athlete_details
            )

            logger.info(f"Processed external user {athlete_details['name']}: {athlete_details['distance']}km")

# Usage functions
def sync_group_leaderboard(group_url="https://www.strava.com/clubs/hienvuong", database_url=None, time_aware=False):
    """
    Sync users from a Strava group leaderboard - always updates this week, conditionally updates last week
    
    :param group_url: Full URL of the Strava group leaderboard
    :param database_url: PostgreSQL database URL
    :param time_aware: If True, skip updates on Monday before 8am
    :return: Tuple of (this_week_runners, last_week_runners)
    """
    # Time-aware logic (similar to reference implementation)
    if time_aware:
        current_time = datetime.now()
        if current_time.weekday() == 0 and current_time.hour < 8:  # Monday before 8am
            logger.info("Not updating leaderboard because it's Monday before 8am")
            return [], []
    
    crawler = StravaLeaderboardCrawler(group_url, database_url)
    
    # Always get and process current week data
    logger.info("Fetching Strava Leaderboards")
    this_week_runners, last_week_runners = crawler.crawl_leaderboard(include_last_week=True)
    logger.info("This week leaderboard update complete")
    
    # Always process this week data (this week data is always updated)
    # Last week data processing is conditional based on should_update_last_week_leaderboard()
    
    # Check if we should process last week data (conditional update)
    if last_week_runners and crawler.should_update_last_week_leaderboard():
        logger.info("Updating Last Week Progress Table") 
        last_week_start, last_week_end = crawler.get_last_week_range()
        crawler.process_athletes(last_week_runners, last_week_start, last_week_end)
        logger.info("Last week leaderboard update complete")
    elif last_week_runners:
        logger.info("Skipping last week leaderboard update (already updated this week)")
    else:
        logger.info("No last week data available")
    
    return this_week_runners, last_week_runners

def get_new_data_if_needed(database_url=None, force_refresh=False, time_aware=False):
    """
    Get new data from Strava - always updates this week, conditionally updates last week
    
    :param database_url: PostgreSQL database URL
    :param force_refresh: Force refresh regardless of timing
    :param time_aware: If True, apply time-aware logic for Monday morning
    :return: Tuple of (this_week_runners, last_week_runners)
    """
    database_url = database_url or os.getenv('DATABASE_URL')
    
    # Always update this week, but check timing for current week updates
    should_update_this_week = force_refresh
    
    if not force_refresh:
        # Check if we should update based on timing (e.g., hourly updates)
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        today = datetime.now().date()
        days_since_monday = today.weekday()
        current_week_start = today - timedelta(days=days_since_monday)
        
        cursor.execute('''
            SELECT MAX(updated_at) as last_update FROM weekly_challenges
            WHERE start_date = %s
        ''', (current_week_start,))
        last_update = cursor.fetchone()
        
        if last_update and last_update['last_update']:
            last_update_time = last_update['last_update']
            time_diff = datetime.now() - last_update_time
            # Update if data is older than 1 hour
            should_update_this_week = time_diff.total_seconds() > 3600
        else:
            # No data exists for current week, should update
            should_update_this_week = True
        
        cursor.close()
        conn.close()
    
    if should_update_this_week:
        logger.info("Fetching new data from Strava...")
        return sync_group_leaderboard(database_url=database_url, time_aware=time_aware)
    else:
        logger.info("This week data is recent, no update needed")
        return None, None

def demo_enhanced_features():
    """Demonstrate the enhanced last week data functionality"""
    print("=== Enhanced Strava Leaderboard Crawler Demo ===")
    
    # Create crawler instance
    crawler = StravaLeaderboardCrawler('https://www.strava.com/clubs/hienvuong')
    
    # Show date calculations
    current_week = crawler.get_current_week_range()
    last_week = crawler.get_last_week_range()
    last_week_iso = crawler.get_last_week_year_and_week_num()
    
    print(f"Current week range: {current_week[0]} to {current_week[1]}")
    print(f"Last week range: {last_week[0]} to {last_week[1]}")
    print(f"Last week ISO calendar: Year {last_week_iso[0]}, Week {last_week_iso[1]}")
    
    # Show update logic
    try:
        should_update = crawler.should_update_last_week_leaderboard()
        print(f"Should update last week data: {should_update}")
    except Exception as e:
        print(f"Cannot check update status (no database connection): {e}")
    
    print("\nNew features added:")
    print("✓ Last week data fetching")
    print("✓ Smart update logic (only update last week if not updated since current week started)")
    print("✓ Time-aware scheduling (skip Monday mornings before 8am)")
    print("✓ Enhanced error handling and logging")
    print("✓ Improved code structure with better separation of concerns")

if __name__ == "__main__":
    # Check if running in demo mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo_enhanced_features()
    else:
        # Example usage with enhanced last week support
        print("Starting Strava leaderboard sync...")
        this_week_runners, last_week_runners = get_new_data_if_needed(force_refresh=True, time_aware=True)
        
        if this_week_runners is not None:
            print(f"Successfully processed {len(this_week_runners)} current week runners")
            if last_week_runners:
                print(f"Successfully processed {len(last_week_runners)} last week runners")
            else:
                print("No last week data updated")
        else:
            print("No update needed")