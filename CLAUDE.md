# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Local development
python running_challenge_app.py    # Starts Flask app on port 5001

# With virtual environment
source .venv/bin/activate
python running_challenge_app.py

# Docker development
docker-compose up -d              # Build and run with Docker
docker-compose logs -f            # View logs
docker-compose down               # Stop services
```

### Database Operations
```bash
# The application auto-creates PostgreSQL tables on first run
# Ensure DATABASE_URL is set in .env file
createdb strava_hvr               # Create database (manual setup)
```

### Strava Data Crawler
```bash
# Manual crawler execution (with enhanced last week support)
python strava_leaderboard_crawler.py

# Via cron script (includes venv activation)
bash crontab.sh

# Force refresh with last week data
python -c "from strava_leaderboard_crawler import get_new_data_if_needed; get_new_data_if_needed(force_refresh=True, time_aware=True)"

# Sync both current and last week data
python -c "from strava_leaderboard_crawler import sync_group_leaderboard; sync_group_leaderboard(time_aware=True)"

# Demo enhanced features (shows date calculations and new functionality)
python strava_leaderboard_crawler.py --demo
```

### Dependencies
```bash
pip install -r requirements.txt
```

No test commands or linting commands are available in this codebase.

## Architecture Overview

This is a Flask-based running challenge tracking application that integrates with Strava data.

### Core Components

**Main Application** (`running_challenge_app.py`):
- Flask web server with PostgreSQL backend
- Handles user registration for weekly challenges (35-100km goals)
- Displays weekly leaderboards with responsive UI
- Admin authentication required for registration page
- Automatic database table creation on startup

**Strava Crawler** (`strava_leaderboard_crawler.py`):
- Selenium-based scraper for Strava Club leaderboard data
- **Enhanced with last week data fetching capability**
- Auto-creates users from Strava club members
- Updates both current week and last week statistics (distance, runs, pace, elevation)
- Smart update logic: only fetches last week data if not updated since current week started
- Time-aware scheduling: skips updates on Monday mornings before 8am
- Uses cookie-based authentication (pickled in `chavahieucn.pkl`)
- Designed to run via cronjob every 30 minutes

**Database Schema**:
- `users`: Stores runner profiles (internal + external Strava users)
- `weekly_challenges`: Stores weekly goals and actual performance stats

### Key Patterns

**Environment Configuration**:
- All sensitive data in `.env` file (never committed)
- Required: `DATABASE_URL`, `ADMIN_PASSWORD`
- Optional: `LOG_DIR`, `STRAVA_COOKIE_FILE`, Chrome paths for Heroku

**Responsive Design**:
- Mobile-first Bootstrap templates
- Hamburger navigation, collapsible table columns
- Card and table view modes for results

**Logging**:
- Rotating daily logs (7-day retention)
- Separate logs for main app (`.log`) and crawler (`crawl.log`)
- Timezone handling for Vietnam (UTC+7)

**Automated Data Sync**:
- Cronjob runs `crontab.sh` to activate venv and execute crawler
- Crawler syncs Strava club data to local database
- Auto-creates missing users from leaderboard

### File Structure
- `templates/`: Jinja2 HTML templates with responsive design
- `migration/`: Database migration and cleanup scripts
- `.venv/`: Python virtual environment (not committed)
- `logs/`: Application log files (not committed)
- `.credentials/`: Sensitive files like service accounts (not committed)

### Security Features
- No hardcoded credentials in source code
- Comprehensive `.gitignore` for sensitive files
- Admin password protection for registration
- Session-based authentication
- Environment variable externalization

## Important Notes

- Application runs on port 5001 by default
- Requires PostgreSQL database and Chrome/Chromium for Selenium
- Strava authentication via exported browser cookies
- Vietnamese timezone (UTC+7) for date calculations
- Auto-creates database tables but not the database itself