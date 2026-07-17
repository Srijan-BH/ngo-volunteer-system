# NGO Volunteer Management System

A **production-ready full-stack web application** for managing NGO volunteers, events, registrations, and analytics. Built with **Python Flask**, **MongoDB**, **JWT authentication**, and **Bootstrap 5**.

---

## 🗂 Project Structure

```
ngo-volunteer-system/
│
├── app.py                        # Application factory & entry point
│
├── config/
│   ├── __init__.py
│   └── settings.py               # All configuration classes (Dev/Test/Prod)
│
├── database/
│   ├── __init__.py
│   ├── connection.py             # MongoDB connection manager
│   └── indexes.py                # Collection index definitions
│
├── models/                       # Data access layer (MVC Model)
│   ├── __init__.py
│   ├── user.py
│   ├── volunteer.py
│   ├── event.py
│   ├── registration.py
│   └── notification.py
│
├── controllers/                  # Business logic layer (MVC Controller)
│   ├── __init__.py
│   ├── auth_controller.py
│   ├── user_controller.py
│   ├── volunteer_controller.py
│   ├── event_controller.py
│   ├── notification_controller.py
│   └── dashboard_controller.py
│
├── routes/                       # Flask Blueprints (URL routing)
│   ├── __init__.py               # Registers all blueprints
│   ├── auth_routes.py
│   ├── user_routes.py
│   ├── volunteer_routes.py
│   ├── event_routes.py
│   ├── notification_routes.py
│   └── dashboard_routes.py
│
├── middleware/
│   ├── __init__.py
│   ├── auth_middleware.py        # JWT decorators: require_auth, require_role, optional_auth
│   ├── error_handlers.py         # Global HTTP error handlers
│   └── request_logger.py         # Request/response logging middleware
│
├── utils/
│   ├── __init__.py
│   ├── jwt_helper.py             # Token generation, decoding, blacklisting
│   ├── security.py               # bcrypt password hashing & verification
│   ├── validators.py             # Input validation helpers
│   ├── response.py               # Standardised JSON response builders
│   ├── pagination.py             # Pagination parameter extraction
│   ├── file_upload.py            # Secure file upload handling
│   ├── helpers.py                # Miscellaneous utilities
│   └── logger.py                 # Logger setup (rotating file + console)
│
├── uploads/
│   ├── profiles/                 # User profile pictures
│   └── events/                   # Event images/documents
│
├── templates/
│   ├── base.html                 # Jinja2 base template (Bootstrap 5)
│   └── errors/
│       ├── 404.html
│       └── 500.html
│
├── static/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   ├── api.js                # Axios API client
│   │   └── app.js
│   └── images/
│
├── logs/                         # Auto-created on first run
├── requirements.txt
├── .env                          # Active environment config (git-ignored)
├── .env.example                  # Template for .env
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Navigate
```bash
git clone <repo-url>
cd ngo-volunteer-system
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your MongoDB URI, secret keys, etc.
```

### 5. Run the Application
```bash
python app.py
```
The API will be available at `http://localhost:5000`.

---

## 🗄️ Database Setup

### Create MongoDB Indexes
```bash
python -m database.indexes
```

---

## 🔌 API Endpoints

### Authentication (`/api/auth`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | ❌ | Register a new user |
| POST | `/login` | ❌ | Login and receive tokens |
| POST | `/logout` | ✅ | Invalidate current token |
| POST | `/refresh` | ❌ | Refresh access token |
| GET | `/me` | ✅ | Get current user profile |
| PUT | `/change-password` | ✅ | Change password |

### Users (`/api/users`) — Admin Only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all users |
| GET | `/<id>` | Get user by ID |
| PUT | `/<id>` | Update user |
| DELETE | `/<id>` | Soft delete user |
| PATCH | `/<id>/activate` | Reactivate user |

### Volunteers (`/api/volunteers`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | Admin/Staff | List all volunteers |
| GET | `/me` | Volunteer | Own profile |
| PUT | `/me` | Volunteer | Update own profile |
| POST | `/me/picture` | Volunteer | Upload profile picture |
| GET | `/<id>` | Admin/Staff | Get volunteer by ID |
| PATCH | `/<id>/status` | Admin/Staff | Update status |
| GET | `/stats` | Admin | Aggregate statistics |

### Events (`/api/events`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | Optional | List/filter events |
| GET | `/search` | Optional | Full-text search |
| GET | `/<id>` | Optional | Event detail |
| POST | `/` | Admin/Staff | Create event |
| PUT | `/<id>` | Admin/Staff | Update event |
| DELETE | `/<id>` | Admin | Delete event |
| PATCH | `/<id>/status` | Admin/Staff | Change status |
| POST | `/<id>/register` | Volunteer | Register for event |
| DELETE | `/<id>/register` | Volunteer | Cancel registration |
| GET | `/<id>/registrations` | Admin/Staff | List registrations |
| POST | `/<id>/image` | Admin/Staff | Upload event image |

### Notifications (`/api/notifications`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List my notifications |
| GET | `/unread-count` | Unread count |
| PATCH | `/read-all` | Mark all as read |
| PATCH | `/<id>/read` | Mark one as read |
| DELETE | `/<id>` | Delete notification |

### Dashboard (`/api/dashboard`) — Admin/Staff
| Endpoint | Description |
|----------|-------------|
| `/overview` | KPI summary |
| `/event-trends` | Monthly event trends |
| `/skills` | Volunteer skills breakdown |
| `/categories` | Events by category |

---

## 🔐 Authentication Flow

1. Register → Receive `access_token` + `refresh_token`
2. Include `Authorization: Bearer <access_token>` on every protected request
3. When access token expires (24h), call `POST /api/auth/refresh` with `refresh_token`
4. On logout, the token is blacklisted in MongoDB (auto-expires via TTL index)

---

## 👥 Roles & Permissions

| Role | Capabilities |
|------|-------------|
| `admin` | Full access to everything |
| `staff` | Manage events and view volunteers |
| `volunteer` | Browse events, manage own profile, register |

---

## ⚙️ Configuration

All settings are in `config/settings.py` and controlled via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | Flask session secret |
| `MONGO_URI` | `mongodb://localhost:27017/...` | MongoDB connection string |
| `JWT_SECRET_KEY` | — | JWT signing secret |
| `JWT_ACCESS_TOKEN_EXPIRES_HOURS` | `24` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRES_DAYS` | `30` | Refresh token lifetime |
| `MAX_CONTENT_LENGTH` | `16777216` | Max file upload size (16 MB) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🧪 Testing

```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Flask 3.x |
| Database | MongoDB 7.x, PyMongo |
| Auth | JWT (PyJWT), bcrypt |
| CORS | Flask-Cors |
| Frontend | Bootstrap 5, Jinja2, Vanilla JS |
| Uploads | Werkzeug secure file handling |

---

## 📄 License

MIT License — Free for personal and commercial use.
