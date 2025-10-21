# DID WebVH Server - Complete Guide

A comprehensive DID WebVH (Decentralized Identifier Web Verifiable History) server implementation with web explorer interface.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL (optional, SQLite default)

### Installation
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/decentralized-identity/didwebvh-server-py
cd didwebvh-server-py/server

# Install dependencies
uv sync

# Run server
uv run python main.py
```

Visit `http://localhost:8000` for the web interface.

## ⚙️ Configuration

Create `.env` file:
```env
# Server
DOMAIN=localhost
API_KEY=your-secret-key

# Database (choose one)
DATABASE_URL=sqlite:///app.db
# OR PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost:5432/didwebvh

# WebVH Policies
WEBVH_VERSION=1.0
WEBVH_WITNESS=true
WEBVH_WATCHER=
WEBVH_PORTABILITY=true
WEBVH_PREROTATION=true
WEBVH_ENDORSEMENT=false

# Branding (Optional)
APP_NAME=DID WebVH Explorer
APP_DESCRIPTION=Visual interface for DID WebVH logs
APP_PRIMARY_COLOR=#1a365d
APP_SECONDARY_COLOR=#38a169
APP_ACCENT_COLOR=#3182ce
```

## 🎨 Themes

### Halloween Theme
```env
APP_NAME=👻 Spooky DID WebVH Explorer 🎃
APP_DESCRIPTION=A hauntingly good interface... if you dare! 👻
APP_PRIMARY_COLOR=#2d1b69
APP_SECONDARY_COLOR=#ff6b35
APP_ACCENT_COLOR=#ffd700
```

### BC Government Theme
```env
APP_NAME=BC Gov DID Explorer
APP_DESCRIPTION=Citizen services
APP_PRIMARY_COLOR=#003366
APP_SECONDARY_COLOR=#FCBA19
APP_ACCENT_COLOR=#38598A
```

## 🗄️ Storage Options

### SQLite (Default)
- File-based, no setup required
- Good for development and small deployments
- `DATABASE_URL=sqlite:///app.db`

### PostgreSQL (Production)
- Better performance and scalability
- ACID compliance and advanced features
- `DATABASE_URL=postgresql://user:pass@host:port/db`

### Migration from Askar to PostgreSQL
```bash
# Start migration as background task
curl -X POST "http://localhost:8000/admin/tasks?task_type=migrate_askar_to_postgres" \
  -H "x-api-key: YOUR_API_KEY"

# Check migration progress
curl "http://localhost:8000/admin/tasks/{task_id}" \
  -H "x-api-key: YOUR_API_KEY"
```

**Migration Process:**
- Creates PostgreSQL tables automatically
- Migrates all DID records, resource records, and generic records
- Creates automatic backup of Askar database
- Provides detailed progress updates and statistics
- Runs as background task with real-time status monitoring

## 🔧 Development

### Adding Dependencies
```bash
uv add package-name          # Production
uv add --dev package-name    # Development
```

### Running Tests
```bash
uv run pytest
uv run pytest --cov=app     # With coverage
```

### Linting
```bash
uv run ruff check .          # Check
uv run ruff format .         # Format
uv run ruff check --fix .    # Auto-fix
```

### Docker
```bash
# Build
docker build -t didwebvh-server .

# Run
docker run -p 8000:8000 didwebvh-server

# Demo with compose
cd demo && docker-compose up
```

## 📊 Load Testing

Built-in load testing for performance benchmarking:

```bash
# Start load test
curl -X POST "http://localhost:8000/admin/tasks?task_type=load_test&num_requests=1000&concurrent_workers=20" \
  -H "x-api-key: YOUR_API_KEY"

# Check progress
curl "http://localhost:8000/admin/tasks/{task_id}" \
  -H "x-api-key: YOUR_API_KEY"
```

**Metrics:**
- Response times (avg/min/max)
- Throughput (requests/second)
- Success/error rates
- Concurrent worker performance

## 🌐 API Endpoints

### Core DID Operations
- `POST /dids` - Create DID
- `GET /dids/{did}` - Resolve DID
- `POST /dids/{did}/log-entries` - Add log entry
- `GET /dids/{did}/log-entries` - Get log entries

### Resource Management
- `POST /resources` - Upload resource
- `GET /resources/{resource_id}` - Get resource
- `GET /resources` - List resources

### Explorer Interface
- `GET /` - Landing page
- `GET /dids` - DID explorer
- `GET /resources` - Resource explorer
- `GET /docs` - API documentation

### Admin Tasks
- `POST /admin/tasks` - Start background task
- `GET /admin/tasks/{task_id}` - Check task status

## 🎯 Features

### Web Explorer
- **DID Browser**: Search, filter, and explore DIDs
- **Resource Manager**: View and manage attested resources
- **Interactive Modals**: Detailed DID/resource information
- **Real-time Updates**: Live data refresh
- **Responsive Design**: Works on all devices

### Advanced Features
- **Witness Network**: Distributed verification
- **Version History**: Track DID changes over time
- **Resource Types**: Support for schemas, credential definitions, revocation registries
- **Pagination**: Efficient large dataset handling
- **Filtering**: Advanced search capabilities

### Security
- **API Key Authentication**: Secure admin operations
- **Input Validation**: Comprehensive request validation
- **SQL Injection Protection**: Parameterized queries
- **CORS Support**: Cross-origin resource sharing

## 🔍 Troubleshooting

### Common Issues

**Database Connection**
```bash
# Check PostgreSQL connection
psql -h localhost -U user -d didwebvh

# Verify SQLite file
ls -la app.db
```

**Dependencies**
```bash
# Clear cache and reinstall
uv cache clean
uv sync --reinstall
```

**Virtual Environment**
```bash
# Recreate environment
rm -rf .venv
uv sync
```

### Logs
- Application logs: Check console output
- Database logs: PostgreSQL logs or SQLite file integrity
- Task logs: Available via `/admin/tasks/{task_id}` endpoint

## 📚 Architecture

### Components
- **FastAPI**: Web framework and API
- **SQLAlchemy**: Database ORM
- **Jinja2**: Template engine
- **Tabler**: UI framework
- **uv**: Package management

### Data Flow
1. **DID Creation**: Client → API → Storage
2. **Resolution**: Client → API → Storage → DID Document
3. **Explorer**: Browser → Templates → API → Storage
4. **Background Tasks**: API → Task Queue → Processing

### Storage Schema
- **explorer_did_records**: DID data with indexes
- **explorer_resource_records**: Resource data with metadata
- **askar_generic_records**: Generic storage records

## 🚀 Deployment

### Production Checklist
- [ ] Set strong `API_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set proper `DOMAIN`
- [ ] Enable HTTPS
- [ ] Configure reverse proxy (nginx)
- [ ] Set up monitoring
- [ ] Backup strategy

### Environment Variables
```env
# Required
DOMAIN=your-domain.com
API_KEY=secure-random-key

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional
WEBVH_WITNESS=true
WEBVH_PORTABILITY=true
STORAGE_BACKEND=postgres
```

## 📖 Additional Resources

- [DID WebVH Specification](https://identity.foundation/didwebvh)
- [uv Documentation](https://docs.astral.sh/uv/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests: `uv run pytest`
5. Submit pull request

## 📄 License

This project is licensed under the Apache License 2.0.

---

**Need Help?** Check the troubleshooting section or open an issue on GitHub.
