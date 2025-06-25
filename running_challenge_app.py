from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import io

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-only-not-for-production')

# Configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # Password for registration access
DATABASE_URL = os.getenv('DATABASE_URL')
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

# Log Flask app startup
@app.before_request
def log_request():
    """Log each request for debugging"""
    logger.info(f"Request: {request.method} {request.url} - IP: {request.remote_addr} - User-Agent: {request.headers.get('User-Agent', 'Unknown')}")

@app.after_request 
def log_response(response):
    """Log response status for debugging"""
    logger.info(f"Response: {response.status_code} for {request.method} {request.url}")
    return response

def init_db():
    """Initialize the database with required tables"""
    try:
        logger.info("Initializing database connection...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        logger.info("Creating users table...")
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255),
                is_external BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        logger.info("Creating weekly_challenges table...")
        # Weekly challenges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_challenges (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                distance_goal REAL NOT NULL,
                total_distance REAL DEFAULT 0,
                runs INTEGER DEFAULT 0,
                average_pace REAL DEFAULT 0,
                elevation_gain REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, start_date)
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        logger.debug("Database connection established successfully")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise

def get_current_week_range():
    """Get current week's Monday to Sunday range"""
    today = datetime.now().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

def get_user_by_username(username):
    """Get user by username"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def create_user(username, first_name, last_name="", is_external=False):
    """Create a new user"""
    conn = get_db_connection()
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

def create_or_update_challenge(user_id, distance_goal):
    """Create or update weekly challenge for user"""
    week_start, week_end = get_current_week_range()
    conn = get_db_connection()
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
            SET distance_goal = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND start_date = %s
        ''', (distance_goal, user_id, week_start))
    else:
        # Create new challenge
        cursor.execute('''
            INSERT INTO weekly_challenges 
            (user_id, start_date, end_date, distance_goal)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, week_start, week_end, distance_goal))
    
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def home():
    """Home page redirects to weekly results"""
    return redirect(url_for('weekly_results'))

@app.route('/weekly-results')
def weekly_results():
    """Display weekly challenge results with optional week filter"""
    try:
        # Get selected week from query parameters
        selected_week = request.args.get('week')
        view_mode = request.args.get('view', 'table')  # Default to table view
        
        logger.info(f"Weekly results requested - selected_week: {selected_week}, view_mode: {view_mode}")
        
        if selected_week:
            try:
                week_start = datetime.strptime(selected_week, '%Y-%m-%d').date()
                week_end = week_start + timedelta(days=6)
                logger.info(f"Using selected week: {week_start} to {week_end}")
            except ValueError:
                # Invalid date format, use current week
                week_start, week_end = get_current_week_range()
                logger.warning(f"Invalid date format for selected_week: {selected_week}, using current week: {week_start} to {week_end}")
        else:
            week_start, week_end = get_current_week_range()
            logger.info(f"Using current week: {week_start} to {week_end}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get available weeks for the filter dropdown
        logger.info("Fetching available weeks for filter dropdown...")
        cursor.execute('''
            SELECT DISTINCT start_date, end_date 
            FROM weekly_challenges 
            ORDER BY start_date DESC
            LIMIT 10
        ''')
        available_weeks_raw = cursor.fetchall()
        logger.info(f"Found {len(available_weeks_raw)} available weeks")
        
        # Convert string dates to date objects for template
        available_weeks = []
        for week in available_weeks_raw:
            start_date = week['start_date'] if isinstance(week['start_date'], datetime) else datetime.strptime(str(week['start_date']), '%Y-%m-%d').date()
            end_date = week['end_date'] if isinstance(week['end_date'], datetime) else datetime.strptime(str(week['end_date']), '%Y-%m-%d').date()
            available_weeks.append({
                'start_date': start_date,
                'end_date': end_date,
                'start_date_str': str(week['start_date'])  # Keep string for form value
            })
        
        # Get users with registered challenges
        logger.info(f"Fetching registered challenges for week {week_start}...")
        cursor.execute('''
            SELECT u.first_name, u.last_name, u.username, u.is_external, 'https://www.strava.com/athletes/'||replace(u.username,'strava_','') AS strava_url,
                   wc.distance_goal, wc.total_distance, wc.runs, 
                   wc.average_pace, wc.elevation_gain,
                   CASE WHEN COALESCE(wc.distance_goal,0)=0 THEN 0 ELSE 
                    ROUND(CAST((wc.total_distance / wc.distance_goal) * 100 AS NUMERIC), 1) END as progress_percentage,
                   CASE 
                       WHEN COALESCE(wc.distance_goal,0)=0 THEN 'Chạy chui'
                       WHEN current_date > end_date and ROUND(CAST((wc.total_distance / wc.distance_goal) * 100 AS NUMERIC), 1) < 100 THEN 'Đóng phạt'
                       WHEN ROUND(CAST((wc.total_distance / wc.distance_goal) * 100 AS NUMERIC), 1) < 100 THEN 'Cần bào thêm nữa'
                       WHEN ROUND(CAST((wc.total_distance / wc.distance_goal) * 100 AS NUMERIC), 1) BETWEEN 100 AND 120 THEN 'Hoàn thành kế hoạch'
                       WHEN ROUND(CAST((wc.total_distance / wc.distance_goal) * 100 AS NUMERIC), 1) > 120 THEN 'Chạy hơi lố'
                   END as status
            FROM users u
            JOIN weekly_challenges wc ON u.id = wc.user_id
            WHERE wc.start_date = %s
            ORDER BY case when COALESCE(wc.distance_goal,0)>0 then 0 else 1 end, 
                       progress_percentage desc, wc.total_distance DESC
        ''', (week_start,))
        results = cursor.fetchall()
        logger.info(f"Found {len(results)} registered challenges")
        
        # For current week only, show unregistered users
        current_week_start, _ = get_current_week_range()
        unregistered_users = []
        if week_start == current_week_start:
            logger.info("Fetching unregistered users for current week...")
            cursor.execute('''
                SELECT u.first_name, u.last_name, u.username, u.is_external,
                       NULL as distance_goal, 
                       NULL as total_distance, 
                       NULL as runs,
                       NULL as average_pace, 
                       NULL as elevation_gain,
                       NULL as progress_percentage,
                       'Chạy chui' as status
                FROM users u
                WHERE u.id NOT IN (
                    SELECT DISTINCT wc.user_id 
                    FROM weekly_challenges wc 
                    WHERE wc.start_date = %s
                )
                ORDER BY u.first_name
            ''', (week_start,))
            unregistered_users = cursor.fetchall()
            logger.info(f"Found {len(unregistered_users)} unregistered users")
        
        # Combine results
        all_results = list(results) + list(unregistered_users)
        logger.info(f"Total results to display: {len(all_results)}")
        
        # Get last crawl success timestamp
        logger.info("Fetching last crawl success timestamp...")
        cursor.execute('''
            SELECT MAX(updated_at) as last_update
            FROM weekly_challenges 
            WHERE start_date = %s
        ''', (week_start,))
        last_update_result = cursor.fetchone()
        last_update = last_update_result['last_update'] if last_update_result and last_update_result['last_update'] else None
        logger.info(f"Last update timestamp: {last_update}")
        
        cursor.close()
        conn.close()
        
        logger.info(f"Rendering weekly_results.html with view_mode: {view_mode}")
        return render_template('weekly_results.html', 
                             results=all_results, 
                             week_start=week_start, 
                             week_end=week_end,
                             available_weeks=available_weeks,
                             selected_week=week_start.strftime('%Y-%m-%d'),
                             view_mode=view_mode,
                             last_update=last_update)
    
    except Exception as e:
        logger.error(f"Error in weekly_results: {str(e)}", exc_info=True)
        flash('Đã xảy ra lỗi khi tải kết quả. Vui lòng thử lại.', 'error')
        return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register_challenge():
    """Register for weekly challenge (password protected)"""
    if request.method == 'POST':
        password = request.form.get('password')
        
        # Check admin password first
        if 'authenticated' not in session:
            if password != ADMIN_PASSWORD:
                flash('Mật khẩu không đúng!', 'error')
                return render_template('register.html')
            session['authenticated'] = True
        
        # Process registration
        if 'authenticated' in session:
            username = request.form.get('username')
            distance_goal = float(request.form.get('distance_goal', 35))
            
            if not username:
                flash('Vui lòng chọn người dùng!', 'error')
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT username, first_name, last_name FROM users ORDER BY first_name')
                existing_users = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('register.html', authenticated=True, existing_users=existing_users)
            
            # Get user details
            existing_user = get_user_by_username(username)
            
            if existing_user:
                # Update existing user's challenge
                create_or_update_challenge(existing_user['id'], distance_goal)
                flash(f'Đã cập nhật thử thách cho {existing_user["first_name"]}!', 'success')
            else:
                flash('Không tìm thấy người dùng!', 'error')
            
            return redirect(url_for('register_challenge'))
    
    # GET request - get existing users for dropdown
    authenticated = 'authenticated' in session
    existing_users = []
    
    if authenticated:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, first_name, last_name, is_external 
            FROM users 
            ORDER BY first_name
        ''')
        existing_users = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('register.html', authenticated=authenticated, existing_users=existing_users)

@app.route('/logout')
def logout():
    """Logout from admin session"""
    session.pop('authenticated', None)
    flash('Đã đăng xuất thành công!', 'info')
    return redirect(url_for('register_challenge'))

@app.route('/sync-strava', methods=['POST'])
def sync_strava():
    """Manually trigger Strava data sync (admin only)"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Chưa xác thực admin'}), 403
    
    try:
        # Import crawler function
        from strava_leaderboard_crawler import get_new_data_if_needed
        
        logger.info("Importing crawler and setting up log capture...")
        
        # Capture logs during crawler execution
        log_capture = io.StringIO()
        
        # Create a custom handler to capture logs
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        log_handler.setFormatter(formatter)
        
        # Add handler to root logger temporarily
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        
        logger.info("Manual Strava sync triggered via web interface")
        logger.info("Starting crawler execution...")
        
        # Run the crawler synchronously with detailed logging
        logger.info("Calling get_new_data_if_needed(force_refresh=True)...")
        runners = get_new_data_if_needed(force_refresh=True)
        logger.info(f"Crawler execution completed. Result type: {type(runners)}, Length: {len(runners) if runners else 0}")
        
        # Log the actual runners data for debugging
        if runners:
            logger.info(f"First few runners: {runners[:2] if len(runners) >= 2 else runners}")
        else:
            logger.info("No runners data returned from crawler")
        
        # Remove the temporary handler
        root_logger.removeHandler(log_handler)
        
        # Get captured logs
        log_output = log_capture.getvalue()
        log_capture.close()
        
        if runners and len(runners) > 0:
            message = f"Đã xử lý thành công {len(runners)} vận động viên từ Strava"
            logger.info(f"Manual sync completed: {len(runners)} runners processed")
        else:
            message = "Crawler đã chạy nhưng không có dữ liệu mới hoặc không cần cập nhật"
            logger.info("Manual sync completed: no new data or no update needed")
        
        return jsonify({
            'success': True, 
            'message': message,
            'logs': log_output,
            'runners_count': len(runners) if runners else 0
        })
        
    except Exception as e:
        error_msg = f"Lỗi khi đồng bộ dữ liệu Strava: {str(e)}"
        logger.error(f"Manual sync failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': error_msg, 'logs': str(e)}), 500

@app.route('/sync-strava-status')
def sync_strava_status():
    """Get current sync status and recent logs"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Chưa xác thực admin'}), 403
    
    try:
        # Get last sync time from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(updated_at) as last_update, COUNT(*) as total_users
            FROM weekly_challenges 
            WHERE start_date = (SELECT start_date FROM weekly_challenges ORDER BY start_date DESC LIMIT 1)
        ''')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        last_update = result['last_update'] if result and result['last_update'] else None
        total_users = result['total_users'] if result else 0
        
        # Read recent logs from file
        recent_logs = ""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Get last 10 lines that contain crawler info
                crawler_lines = [line for line in lines[-50:] if 'strava' in line.lower() or 'crawler' in line.lower() or 'sync' in line.lower()]
                recent_logs = ''.join(crawler_lines[-10:])
        except FileNotFoundError:
            recent_logs = "Log file không tồn tại"
        
        return jsonify({
            'success': True,
            'last_update': last_update.strftime('%d/%m/%Y %H:%M:%S') if last_update else 'Chưa có',
            'total_users': total_users,
            'recent_logs': recent_logs
        })
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'}), 500

# Template files
# @app.before_first_request
def create_templates():
    """Create template files if they don't exist"""
    pass 

if __name__ == '__main__':
    # Initialize logging first
    logger.info("Starting Running Challenge application...")
    
    # Initialize database and templates
    try:
        init_db()
        logger.info("Database initialization completed")
        create_templates()
        logger.info("Template creation completed")
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}", exc_info=True)
        exit(1)
    
    print("🏃‍♂️ Website Thử Thách Chạy Bộ")
    print("=" * 40)
    print("📊 Kết Quả Hàng Tuần: http://localhost:5000/weekly-results")
    print("📝 Đăng Ký Thử Thách: http://localhost:5000/register")
    print(f"🔑 Mật Khẩu Admin: {ADMIN_PASSWORD}")
    print(f"📝 File Log: {LOG_FILE}")
    print("=" * 40)
    
    logger.info("Flask application starting on http://0.0.0.0:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)