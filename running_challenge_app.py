from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import pytz
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

# Timezone configuration for UTC+7 (Vietnam/Ho Chi Minh)
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
UTC_TZ = pytz.UTC

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
        
        logger.info("Creating feedback table...")
        # Feedback table for user suggestions and comments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                user_name VARCHAR(255),
                email VARCHAR(255),
                feedback_type VARCHAR(50) NOT NULL DEFAULT 'suggestion',
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                priority VARCHAR(20) DEFAULT 'medium',
                status VARCHAR(20) DEFAULT 'pending',
                admin_notes TEXT,
                implementation_status VARCHAR(20) DEFAULT 'not_started',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        logger.info("Creating feature_generations table...")
        # Table to track AI-generated features from feedback
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_generations (
                id SERIAL PRIMARY KEY,
                feedback_id INTEGER NOT NULL,
                generated_code TEXT,
                file_changes TEXT,
                deployment_status VARCHAR(20) DEFAULT 'pending',
                deployment_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deployed_at TIMESTAMP,
                FOREIGN KEY (feedback_id) REFERENCES feedback (id)
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

def get_vietnam_time():
    """Get current time in Vietnam timezone (UTC+7)"""
    return datetime.now(VIETNAM_TZ)

def get_current_week_range():
    """Get current week's Monday to Sunday range in Vietnam timezone"""
    today = get_vietnam_time().date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

def format_vietnam_time(dt, format_str='%d/%m/%Y %H:%M:%S'):
    """Format datetime to Vietnam timezone"""
    if dt is None:
        return None
    
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    
    # Convert to Vietnam timezone
    vietnam_dt = dt.astimezone(VIETNAM_TZ)
    return vietnam_dt.strftime(format_str)

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
                             last_update=last_update,
                             format_vietnam_time=format_vietnam_time)
    
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
            'last_update': format_vietnam_time(last_update) if last_update else 'Chưa có',
            'total_users': total_users,
            'recent_logs': recent_logs
        })
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'}), 500

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """User feedback submission form"""
    if request.method == 'POST':
        try:
            user_name = request.form.get('user_name', '').strip()
            email = request.form.get('email', '').strip()
            feedback_type = request.form.get('feedback_type', 'suggestion')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', 'medium')
            
            # Validation
            if not title or not description:
                flash('Vui lòng điền đầy đủ tiêu đề và mô tả!', 'error')
                return render_template('feedback.html')
            
            # Save to database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (user_name, email, feedback_type, title, description, priority)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user_name, email, feedback_type, title, description, priority))
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"New feedback submitted: {title} by {user_name or 'Anonymous'}")
            flash('Cảm ơn bạn đã gửi phản hồi! Chúng tôi sẽ xem xét và cải thiện hệ thống.', 'success')
            return redirect(url_for('feedback'))
            
        except Exception as e:
            logger.error(f"Error saving feedback: {str(e)}", exc_info=True)
            flash('Đã xảy ra lỗi khi gửi phản hồi. Vui lòng thử lại.', 'error')
    
    return render_template('feedback.html')

@app.route('/admin/feedback', methods=['GET', 'POST'])
def admin_feedback():
    """Admin interface to manage feedback (password protected)"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password != ADMIN_PASSWORD:
            flash('Mật khẩu không đúng!', 'error')
            return render_template('admin_feedback.html', authenticated=False)
        session['authenticated'] = True
        return redirect(url_for('admin_feedback'))
    
    # Check if already authenticated
    if 'authenticated' not in session:
        return render_template('admin_feedback.html', authenticated=False)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all feedback ordered by newest first
        cursor.execute('''
            SELECT f.*, fg.deployment_status as feature_status, fg.created_at as feature_generated_at
            FROM feedback f
            LEFT JOIN feature_generations fg ON f.id = fg.feedback_id
            ORDER BY f.created_at DESC
        ''')
        feedback_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin_feedback.html', feedback_list=feedback_list, authenticated=True, format_vietnam_time=format_vietnam_time)
        
    except Exception as e:
        logger.error(f"Error loading admin feedback: {str(e)}", exc_info=True)
        flash('Đã xảy ra lỗi khi tải danh sách phản hồi.', 'error')
        return render_template('admin_feedback.html', authenticated=False)

@app.route('/admin/generate-feature/<int:feedback_id>', methods=['POST'])
def generate_feature(feedback_id):
    """Generate feature from feedback using AI"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Chưa xác thực admin'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get feedback details
        cursor.execute('SELECT * FROM feedback WHERE id = %s', (feedback_id,))
        feedback_data = cursor.fetchone()
        
        if not feedback_data:
            return jsonify({'success': False, 'message': 'Không tìm thấy phản hồi'}), 404
        
        # Generate AI response for feature implementation using our AI service
        try:
            from ai_feature_generator import AIFeatureGenerator
            ai_generator = AIFeatureGenerator()
            generated_plan = ai_generator.generate_implementation_plan(feedback_data)
            logger.info(f"AI generated implementation plan for feedback {feedback_id}")
        except Exception as ai_error:
            logger.warning(f"AI generation failed, using fallback: {str(ai_error)}")
            # Fallback to basic template
            generated_plan = f"""
AI IMPLEMENTATION PLAN - Generated at {format_vietnam_time(get_vietnam_time())}
{'='*80}

📋 FEEDBACK ANALYSIS
Title: {feedback_data['title']}
Type: {feedback_data['feedback_type']}
Priority: {feedback_data['priority']}

📝 USER REQUEST
{feedback_data['description']}

🎯 BASIC IMPLEMENTATION PLAN
1. Backend Changes:
   - Add new route in running_challenge_app.py
   - Create database migrations if needed
   - Implement business logic

2. Frontend Changes:
   - Create new template files
   - Update existing templates
   - Add new CSS/JavaScript if needed

3. Database Updates:
   - Schema modifications: TBD based on feature requirements
   - Data migration scripts: TBD

4. Testing:
   - Unit tests for new functionality
   - Integration tests
   - UI/UX testing

Priority: {feedback_data['priority']}
Note: This is a basic plan. For detailed analysis, ensure ai_feature_generator.py is properly configured.
            """
        
        # Save generated plan
        cursor.execute('''
            INSERT INTO feature_generations (feedback_id, generated_code, deployment_status)
            VALUES (%s, %s, 'generated')
        ''', (feedback_id, generated_plan))
        
        # Update feedback status
        cursor.execute('''
            UPDATE feedback SET status = 'in_progress', implementation_status = 'planned', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (feedback_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Generated implementation plan for feedback ID: {feedback_id}")
        return jsonify({
            'success': True, 
            'message': 'Đã tạo kế hoạch triển khai tính năng',
            'plan': generated_plan
        })
        
    except Exception as e:
        logger.error(f"Error generating feature: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'}), 500

@app.route('/admin/deploy-feature/<int:feedback_id>', methods=['POST'])
def deploy_feature(feedback_id):
    """Deploy generated feature and restart Docker container"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Chưa xác thực admin'}), 403
    
    try:
        import subprocess
        import os
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get feature generation details
        cursor.execute('''
            SELECT fg.*, f.title, f.description 
            FROM feature_generations fg
            JOIN feedback f ON fg.feedback_id = f.id
            WHERE fg.feedback_id = %s
        ''', (feedback_id,))
        feature_data = cursor.fetchone()
        
        if not feature_data:
            return jsonify({'success': False, 'message': 'Không tìm thấy kế hoạch triển khai'}), 404
        
        # Create deployment log
        deployment_log = f"Starting deployment for: {feature_data['title']}\n"
        deployment_log += f"Generated at: {feature_data['created_at']}\n"
        deployment_log += f"Feature description: {feature_data['description']}\n\n"
        
        # Update deployment status
        cursor.execute('''
            UPDATE feature_generations 
            SET deployment_status = 'deploying', deployment_log = %s
            WHERE feedback_id = %s
        ''', (deployment_log, feedback_id))
        
        cursor.execute('''
            UPDATE feedback 
            SET implementation_status = 'deploying', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (feedback_id,))
        
        conn.commit()
        
        try:
            # Use enhanced Docker manager for deployment
            from docker_manager import DockerManager
            docker_manager = DockerManager()
            
            deployment_log += "Using AI-powered Docker deployment manager...\n"
            deployment_result = docker_manager.deploy_feature(feedback_id)
            
            deployment_log += deployment_result['log']
            
            if deployment_result['success']:
                deployment_status = deployment_result['status']
                implementation_status = 'completed'
                deployment_log += f"\n✅ Deployment successful! Container: {deployment_result.get('container', 'unknown')}\n"
            else:
                deployment_status = deployment_result.get('status', 'failed')
                implementation_status = 'failed'
                deployment_log += f"\n❌ Deployment failed: {deployment_result['message']}\n"
                
        except ImportError:
            deployment_log += "Docker manager not available, using basic restart...\n"
            # Fallback to basic Docker restart
            try:
                import subprocess
                container_result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                                               capture_output=True, text=True, timeout=10)
                
                if container_result.returncode == 0:
                    containers = container_result.stdout.strip().split('\n')
                    app_container = None
                    
                    for container in containers:
                        if any(keyword in container.lower() for keyword in ['strava', 'running', 'challenge', 'app']):
                            app_container = container
                            break
                    
                    if app_container:
                        deployment_log += f"Found container: {app_container}\n"
                        restart_result = subprocess.run(['docker', 'restart', app_container], 
                                                      capture_output=True, text=True, timeout=30)
                        
                        if restart_result.returncode == 0:
                            deployment_log += "Container restarted successfully!\n"
                            deployment_status = 'deployed'
                            implementation_status = 'completed'
                        else:
                            deployment_log += f"Container restart failed: {restart_result.stderr}\n"
                            deployment_status = 'failed'
                            implementation_status = 'failed'
                    else:
                        deployment_log += "No matching container found\n"
                        deployment_status = 'manual_restart_needed'
                        implementation_status = 'pending_restart'
                else:
                    deployment_log += f"Docker command failed: {container_result.stderr}\n"
                    deployment_status = 'failed'
                    implementation_status = 'failed'
                    
            except Exception as basic_error:
                deployment_log += f"Basic deployment error: {str(basic_error)}\n"
                deployment_status = 'failed'
                implementation_status = 'failed'
                
        except Exception as deploy_error:
            deployment_log += f"Deployment manager error: {str(deploy_error)}\n"
            deployment_status = 'failed'
            implementation_status = 'failed'
        
        # Update final status
        cursor.execute('''
            UPDATE feature_generations 
            SET deployment_status = %s, deployment_log = %s, deployed_at = CURRENT_TIMESTAMP
            WHERE feedback_id = %s
        ''', (deployment_status, deployment_log, feedback_id))
        
        cursor.execute('''
            UPDATE feedback 
            SET implementation_status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (implementation_status, feedback_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Deployment attempted for feedback ID: {feedback_id}, status: {deployment_status}")
        
        return jsonify({
            'success': True, 
            'message': f'Triển khai hoàn tất với trạng thái: {deployment_status}',
            'status': deployment_status,
            'log': deployment_log
        })
        
    except Exception as e:
        logger.error(f"Error deploying feature: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi triển khai: {str(e)}'}), 500

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