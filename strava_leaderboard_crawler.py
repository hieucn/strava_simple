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

    def crawl_leaderboard(self):
        """
        Crawl the Strava group leaderboard and add/update users
        
        :return: List of added or updated users
        """
        try:
            
            from selenium import webdriver
            from selenium.common.exceptions import TimeoutException
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions
            from selenium.webdriver.support.wait import WebDriverWait

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

            # navigate to Strava group page
            driver.get("https://www.strava.com/")
            driver.get("https://www.strava.com/clubs/hienvuong")
            import pickle
            # Load cookies for authentication - update this path as needed
            try:
                cookie_file = os.getenv('STRAVA_COOKIE_FILE')
                cookies = pickle.load(open(cookie_file, "rb"))
            except FileNotFoundError:
                logger.warning("Cookie file not found, continuing without authentication")
                cookies = []
            for cookie in cookies:
                driver.add_cookie(cookie)
            driver.get("https://www.strava.com/clubs/hienvuong")
            #print(driver.page_source)
            # get "This Week's Leaderboard"
            try:
                WebDriverWait(driver, 30).until(expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.page")))
            except TimeoutException:
                logger.info("Request Timed Out")

            table = driver.find_element(By.CSS_SELECTOR, "div.leaderboard > table > tbody").get_attribute("innerHTML")
            soup = BeautifulSoup(table, "html.parser")

            runners = []
            
            def get_average_pace_in_seconds(minute_second):
                if minute_second == "--":
                    return 0.0
                else:
                    print("print(minute_second)")
                    print(minute_second)
                    minute = minute_second.split(":")[0]
                    second = minute_second.split(":")[1]
                    return 60 * float(minute) + float(second)
            
            
            def get_elevation_gain(text):
                if text == "--":
                    return 0.0
                else:
                    return float(text.split()[0].replace(",", ""))
                
            # Get current week's date range
            week_start, week_end = self.get_current_week_range()

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
                    # "week_start": week_start,
                    # "week_end": week_end
                }

                runners.append(runner)

            # Process each athlete
            self.process_athletes(runners, week_start, week_end)
            
            driver.quit()
            return runners

        except Exception as e:
            print(f"Error crawling leaderboard: {e}")
            return []

    def get_current_week_range(self):
        """Get current week's Monday to Sunday range using ISO week calculation"""
        today = datetime.now().date()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

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
def sync_group_leaderboard(group_url="https://www.strava.com/clubs/hienvuong", database_url=None):
    """
    Sync users from a Strava group leaderboard
    
    :param group_url: Full URL of the Strava group leaderboard
    :param database_url: PostgreSQL database URL
    :return: List of processed users
    """
    crawler = StravaLeaderboardCrawler(group_url, database_url)
    return crawler.crawl_leaderboard()

def get_new_data_if_needed(database_url=None, force_refresh=False):
    """
    Get new data from Strava if needed (checks if data is older than 1 hour)
    
    :param database_url: PostgreSQL database URL
    :param force_refresh: Force refresh regardless of timing
    :return: List of processed users or None if no update needed
    """
    database_url = database_url or os.getenv('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check last update time
    cursor.execute('''
        SELECT MAX(updated_at) as last_update FROM weekly_challenges
    ''')
    last_update = cursor.fetchone()
    
    should_update = force_refresh
    
    if last_update and last_update['last_update']:
        last_update_time = last_update['last_update']
        time_diff = datetime.now() - last_update_time
        # Update if data is older than 1 hour
        should_update = time_diff.total_seconds() > 0
    else:
        # No data exists, should update
        should_update = True
    should_update = True
    
    cursor.close()
    conn.close()
    
    if should_update:
        logger.info("Fetching new data from Strava...")
        return sync_group_leaderboard(database_url=database_url)
    else:
        logger.info("Data is recent, no update needed")
        return None

if __name__ == "__main__":
    # Example usage
    print("Starting Strava leaderboard sync...")
    runners = get_new_data_if_needed(force_refresh=True)
    if runners:
        print(f"Successfully processed {len(runners)} runners")
    else:
        print("No update needed")