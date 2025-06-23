# 100% by Claude

# 🏃‍♂️ Thử Thách Chạy Bộ - Running Challenge

Ứng dụng web để quản lý và theo dõi thử thách chạy bộ hàng tuần cho nhóm. Được phát triển bằng Flask và PostgreSQL, hỗ trợ đầy đủ trên thiết bị di động.

## ✨ Tính Năng

### 🎯 Quản Lý Thử Thách
- **Đăng ký thử thách hàng tuần** với mục tiêu khoảng cách tùy chỉnh (35-100km)
- **Theo dõi tiến độ** theo thời gian thực
- **Tích hợp Strava** để đồng bộ dữ liệu chạy bộ
- **Cập nhật tự động** thống kê chạy bộ (khoảng cách, số lần chạy, tốc độ trung bình, độ cao)
- **Crawler tự động** lấy dữ liệu từ Strava Club Leaderboard

### 📊 Hiển Thị Kết Quả
- **Bảng xếp hạng** theo tuần với nhiều chế độ xem
- **Chế độ xem bảng** và **chế độ thẻ** responsive
- **Lọc theo tuần** để xem kết quả các tuần trước
- **Trạng thái tiến độ** trực quan với màu sắc và biểu tượng

### 📱 Giao Diện Responsive
- **Tối ưu cho mobile** với navigation thu gọn
- **Bảng responsive** ẩn/hiện cột theo kích thước màn hình
- **Form touch-friendly** với các control lớn hơn
- **Typography responsive** cho mọi thiết bị

### 🔐 Bảo Mật
- **Xác thực admin** cho chức năng đăng ký
- **Session management** an toàn
- **Environment variables** cho tất cả thông tin nhạy cảm
- **Comprehensive .gitignore** bảo vệ khỏi commit credentials
- **No hardcoded secrets** trong source code
- **Logging** chi tiết cho monitoring và audit

### 🤖 Strava Data Crawler
- **Selenium-based crawler** để lấy dữ liệu từ Strava Club
- **Tự động tạo user** từ Strava leaderboard
- **Cập nhật thống kê** hàng ngày qua cronjob
- **Cookie authentication** cho Strava login

## 🚀 Cài Đặt

### Yêu Cầu Hệ Thống
- Python 3.8+
- PostgreSQL 12+
- Git

### Cài Đặt Dependencies

```bash
# Clone repository
git clone <repository-url>
cd strava_simple

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\\Scripts\\activate  # Windows

# Cài đặt packages
pip install -r requirements.txt

# Cài đặt Chrome browser và ChromeDriver cho Selenium (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y google-chrome-stable
sudo apt-get install -y chromium-chromedriver
```

### Cấu Hình Environment

Tạo file `.env` với các biến môi trường:

```env
# Database Configuration
DATABASE_URL=postgres://username:password@host:port/database_name

# Admin Password (REQUIRED - để bảo vệ trang đăng ký)
ADMIN_PASSWORD=your_secure_admin_password_here

# Optional: Logging
LOG_DIR=/path/to/logs

# Optional: Strava Configuration
STRAVA_COOKIE_FILE=./.credentials/cookies.pkl
GOOGLE_SERVICE_ACCOUNT=./.credentials/gg_sa.json

# Optional: Chrome/Selenium (for Heroku)
GOOGLE_CHROME_BIN=/usr/bin/google-chrome
CHROMEDRIVER_PATH=/usr/bin/chromedriver
```

⚠️ **QUAN TRỌNG**: 
- File `.env` chứa thông tin nhạy cảm và **KHÔNG BAO GIỜ** được commit vào git
- Sử dụng `.env.example` làm template và tạo `.env` riêng cho từng environment
- Đảm bảo `.env` có trong `.gitignore`

### Thiết Lập Database

```bash
# Tạo database PostgreSQL
createdb strava_hvr

# Ứng dụng sẽ tự động tạo tables khi khởi chạy lần đầu
python running_challenge_app.py
```

## 🖥️ Sử Dụng

### Khởi Chạy Ứng Dụng

```bash
# Khởi chạy Flask app
python running_challenge_app.py
```

Ứng dụng sẽ chạy tại: `http://localhost:5001`

### Chạy Strava Crawler

```bash
# Chạy crawler thủ công
python strava_leaderboard_crawler.py

# Hoặc sử dụng script với virtual environment
bash crontab.sh
```

### Truy Cập Chức Năng

- **Trang chủ**: `http://localhost:5001/` (chuyển hướng đến kết quả tuần)
- **Kết quả hàng tuần**: `http://localhost:5001/weekly-results`
- **Đăng ký thử thách**: `http://localhost:5001/register`

### Đăng Ký Thử Thách

1. Truy cập `/register`
2. Nhập mật khẩu admin để xác thực
3. Chọn người dùng từ dropdown
4. Chọn mục tiêu khoảng cách (35-100km)
5. Nhấn "Đăng Ký Thử Thách Hàng Tuần"

## 🗂️ Cấu Trúc Project

```
strava_simple/
├── running_challenge_app.py       # Main Flask application
├── strava_leaderboard_crawler.py  # Strava data crawler
├── crontab.sh                     # Cronjob script
├── templates/                     # HTML templates
│   ├── base.html                 # Base template với responsive design
│   ├── register.html             # Trang đăng ký thử thách
│   └── weekly_results.html       # Trang hiển thị kết quả
├── migration/                     # Database migration scripts
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Docker setup
├── Dockerfile                     # Docker image definition
├── chavahieucn.pkl               # Strava authentication cookies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore patterns
└── README.md                     # Documentation này
```

## 🐳 Docker Deployment

### Sử dụng Docker Compose

```bash
# Khởi chạy với Docker Compose
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng services
docker-compose down
```

### Build Manual

```bash
# Build image
docker build -t strava-challenge .

# Run container
docker run -d \
  -p 5001:5001 \
  -e DATABASE_URL="postgres://user:pass@host:5432/db" \
  -e ADMIN_PASSWORD="your_password" \
  strava-challenge
```

## 📊 Database Schema

### Bảng `users`
- `id`: Primary key
- `username`: Tên đăng nhập unique
- `first_name`: Tên
- `last_name`: Họ
- `is_external`: Flag cho user Strava
- `created_at`: Timestamp tạo

### Bảng `weekly_challenges`
- `id`: Primary key
- `user_id`: Foreign key đến users
- `start_date`: Ngày bắt đầu tuần
- `end_date`: Ngày kết thúc tuần
- `distance_goal`: Mục tiêu khoảng cách (km)
- `total_distance`: Tổng khoảng cách đã chạy (km)
- `runs`: Số lần chạy
- `average_pace`: Tốc độ trung bình (giây/km)
- `elevation_gain`: Tổng độ cao tích lũy (m)
- `created_at`, `updated_at`: Timestamps

## 🔄 API Endpoints

- `GET /` - Redirect đến weekly results
- `GET /weekly-results` - Hiển thị kết quả tuần (với filter và view mode)
- `GET /register` - Form đăng ký thử thách
- `POST /register` - Xử lý đăng ký thử thách
- `GET /logout` - Đăng xuất session admin

## 🤖 Strava Data Crawler

### Chức Năng Crawler
Crawler `strava_leaderboard_crawler.py` thực hiện:
- **Lấy dữ liệu** từ Strava Club leaderboard bằng Selenium
- **Tự động tạo users** từ danh sách runners trong club
- **Cập nhật thống kê** hàng tuần (distance, runs, pace, elevation)
- **Logging** chi tiết các hoạt động crawler

### Cấu Hình Crawler

```python
# Environment variables cần thiết
DATABASE_URL=postgres://user:pass@host:port/db
GOOGLE_CHROME_BIN=/usr/bin/google-chrome  # Optional for Heroku
CHROMEDRIVER_PATH=/usr/bin/chromedriver   # Optional for Heroku
```

### Cài Đặt Strava Authentication

1. **Lấy cookies từ browser**:
   - Đăng nhập vào Strava trên Chrome
   - Xuất cookies bằng extension như "EditThisCookie"
   - Lưu cookies thành file `chavahieucn.pkl`

2. **Pickle format**:
```python
import pickle
cookies = [{'name': 'cookie_name', 'value': 'cookie_value', 'domain': '.strava.com'}]
with open('chavahieucn.pkl', 'wb') as f:
    pickle.dump(cookies, f)
```

### Chạy Crawler Thủ Công

```bash
# Chạy với force refresh
python strava_leaderboard_crawler.py

# Hoặc import và sử dụng functions
python -c "from strava_leaderboard_crawler import get_new_data_if_needed; get_new_data_if_needed(force_refresh=True)"
```

## 🎨 Responsive Design Features

### Mobile Optimizations
- **Navigation**: Hamburger menu cho mobile
- **Tables**: Ẩn cột ít quan trọng trên màn hình nhỏ
- **Forms**: Control lớn hơn, dễ touch
- **Typography**: Font size adaptive
- **Spacing**: Padding và margin tối ưu

### Breakpoints
- **Extra Small** (`<576px`): Phone portrait
- **Small** (`576px-767px`): Phone landscape
- **Medium** (`768px-991px`): Tablet
- **Large** (`992px-1199px`): Desktop
- **Extra Large** (`≥1200px`): Large desktop

## 📝 Logging

Ứng dụng sử dụng rotating file logging:
- **File**: `.log` trong thư mục gốc
- **Rotation**: Hàng ngày, giữ 7 ngày
- **Level**: INFO và cao hơn
- **Format**: Timestamp, function, line number, message

## ⏰ Cronjob Setup

### Cài Đặt Cronjob Tự Động

```bash
# Mở crontab editor
crontab -e

# Thêm job chạy mỗi 30 phút
*/30 * * * * /home/hieusv/strava_simple/crontab.sh >> /home/hieusv/strava_simple/cron.log 2>&1

# Hoặc chạy mỗi giờ
0 * * * * /home/hieusv/strava_simple/crontab.sh >> /home/hieusv/strava_simple/cron.log 2>&1

# Kiểm tra cronjob đang chạy
crontab -l
```

### Script Cronjob
File `crontab.sh` bao gồm:
- Kích hoạt virtual environment
- Chuyển đến thư mục project
- Chạy crawler với logging
- Error handling

### Monitoring Cronjob

```bash
# Xem log cronjob
tail -f /home/hieusv/strava_simple/cron.log

# Xem log ứng dụng
tail -f /home/hieusv/strava_simple/.log

# Kiểm tra status service
sudo systemctl status cron
```

## 🔧 Troubleshooting

### Lỗi Database Connection
```bash
# Kiểm tra PostgreSQL service
sudo systemctl status postgresql

# Kiểm tra connection string trong .env
echo $DATABASE_URL
```

### Lỗi Permission
```bash
# Đảm bảo user có quyền tạo database và tables
GRANT ALL PRIVILEGES ON DATABASE strava_hvr TO username;
```

### Lỗi Selenium/Chrome
```bash
# Cài đặt Chrome dependencies
sudo apt-get install -y fonts-liberation libasound2 libatk-bridge2.0-0 libdrm2 libgtk-3-0 libnspr4 libnss3 libxss1 libxtst6 xdg-utils

# Kiểm tra Chrome version
google-chrome --version
chromium-browser --version

# Test ChromeDriver
chromedriver --version
```

### Lỗi Strava Authentication
```bash
# Kiểm tra cookie file
ls -la chavahieucn.pkl

# Test crawler với debug
python -c "from strava_leaderboard_crawler import *; sync_group_leaderboard()"
```

### Mobile Display Issues
- Kiểm tra viewport meta tag
- Xóa cache browser trên mobile
- Test trên nhiều thiết bị/browser

### Cronjob Issues
```bash
# Kiểm tra cron service
sudo systemctl status cron

# Test script thủ công
bash /home/hieusv/strava_simple/crontab.sh

# Xem system cron logs
sudo tail -f /var/log/syslog | grep CRON
```

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Tạo Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Support

Nếu gặp vấn đề hoặc có câu hỏi:
- Tạo Issue trên GitHub
- Check logs tại `.log` file
- Xem database logs trong PostgreSQL
- Check cronjob logs tại `cron.log`
- Kiểm tra Selenium logs khi crawler fails

## 🔒 Bảo Mật & Publishing

### ✅ Security Checklist
- [x] **No hardcoded credentials** trong source code
- [x] **Environment variables** cho tất cả thông tin nhạy cảm
- [x] **Comprehensive .gitignore** bảo vệ files nhạy cảm
- [x] **Template .env.example** với placeholder values
- [x] **Database credentials** externalized
- [x] **Admin passwords** từ environment
- [x] **Cookie files** excluded from git
- [x] **Log files** excluded from git

### 🛡️ Files Được Bảo Vệ
Các file sau được .gitignore tự động loại trừ:
- `.env*` files (environment variables)
- `*.pkl` files (authentication cookies)  
- `*service-account*.json` (Google service accounts)
- `*.db*` files (database files)
- `*.log` files (log files)
- `/.credentials/` directory
- SSH keys và certificates

### ⚠️ Lưu Ý Khi Deploy
1. **Tạo `.env` riêng** cho production với credentials thật
2. **Không share** admin password qua chat/email
3. **Backup database** thường xuyên
4. **Monitor logs** để phát hiện access bất thường
5. **Update dependencies** định kỳ

---

**Made with ❤️ for the running community**

*🤖 100% Generated by Claude Code*