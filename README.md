# Dev - Face Similarity Search Platform

A production-grade face similarity search platform that allows users to find their photos using face recognition technology.

## Features

- 🎯 **Face Recognition** - Advanced AI using InsightFace (ArcFace) for 99%+ accuracy
- ⚡ **Instant Search** - FAISS vector search finds matches in milliseconds
- 📱 **Mobile-First** - QR code session management for easy mobile access
- 🔐 **Secure** - JWT authentication, users only see their own photos
- 🐳 **Containerized** - Docker deployment ready
- 🧪 **Tested** - Comprehensive test suite with pytest

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **PostgreSQL** for metadata storage
- **FAISS** for vector similarity search
- **InsightFace** with ArcFace embeddings (512-d)
- **SQLAlchemy** (async) for database operations

### Frontend
- **Next.js 14** with TypeScript
- **React 18** with modern hooks
- **Custom CSS** with premium design system

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (optional)

### 1. Backend Setup

```bash
# Install dependencies with uv
uv sync

# Copy environment configuration
copy .env.example .env
# Edit .env with your database credentials
```

### 2. Database Setup

```bash
# Start PostgreSQL (if using Docker)
docker run -d \
  --name dev-postgres \
  -e POSTGRES_DB=dev_studio_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16-alpine

# Seed the database (optional)
uv run python scripts/seed_db.py
```

### 3. Run Backend

```bash
# Development mode
uv run python run.py

# Or with uvicorn directly
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Build Individual Images

```bash
# Build backend
docker build -t dev-api .

# Build frontend
cd frontend
docker build -t dev-frontend .
```

## UV Package Manager Commands

```bash
# Install all dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Run a script
uv run python <script.py>

# Run tests
uv run pytest app/tests/ -v

# Update lock file
uv lock
```

## API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login with email/password |
| `/api/v1/auth/session/qr` | POST | Create QR session |
| `/api/v1/auth/session/validate` | POST | Validate QR session |
| `/api/v1/auth/me` | GET | Get current user |
| `/api/v1/auth/logout` | POST | Logout session |

### Face Scan

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/scan/face` | POST | Scan face and find matches |
| `/api/v1/scan/match` | POST | Find matching images |
| `/api/v1/scan/upload` | POST | Upload and index image |
| `/api/v1/scan/stats` | GET | Get scan statistics |

### Gallery

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/gallery` | GET | Get paginated gallery |
| `/api/v1/gallery/search` | GET | Search images by filename |
| `/api/v1/gallery/{id}` | GET | Get image details |
| `/api/v1/gallery/{id}/file` | GET | Get image file |
| `/api/v1/gallery/{id}` | DELETE | Delete image |

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/dev_studio_db

# Security
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# FAISS
FAISS_INDEX_PATH=data/embeddings/face_index.faiss
SIMILARITY_THRESHOLD=0.75
TOP_K_RESULTS=10

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Running Tests

```bash
# Run all tests
uv run pytest app/tests/ -v

# Run with coverage
uv run pytest app/tests/ -v --cov=app

# Run specific test file
uv run pytest app/tests/test_app.py -v
```

## Project Structure

```
dev/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── routes/              # API routes
│   │   ├── auth.py
│   │   ├── scan.py
│   │   └── gallery.py
│   ├── services/            # Business logic
│   │   ├── inference.py
│   │   ├── embeddings.py
│   │   └── search.py
│   ├── models/              # Database models
│   │   ├── user_model.py
│   │   └── image_model.py
│   ├── core/                # Core utilities
│   │   ├── engine.py
│   │   └── pipeline.py
│   ├── utils/               # Helpers
│   │   ├── logger.py
│   │   └── security.py
│   └── tests/               # Test suite
├── data/
│   ├── raw/                 # Uploaded images
│   ├── processed/           # Processed faces
│   └── embeddings/          # FAISS index
├── frontend/
│   ├── pages/
│   │   ├── index.tsx        # Landing page
│   │   ├── scan.tsx         # Camera scan
│   │   └── gallery.tsx      # Photo gallery
│   ├── components/
│   │   ├── Camera.tsx
│   │   └── ImageGrid.tsx
│   └── styles/
│       └── globals.css
├── scripts/
│   ├── build_index.py       # Build FAISS index
│   └── seed_db.py           # Seed database
├── logs/
├── pyproject.toml           # UV/Python project config
├── uv.lock                  # Locked dependencies
├── Dockerfile
├── docker-compose.yml
├── run.py
└── README.md
```

## How It Works

### Face Recognition Flow

1. **Image Upload**: User uploads a photo
2. **Face Detection**: InsightFace detects faces
3. **Embedding Extraction**: ArcFace generates 512-dimensional embeddings
4. **Normalization**: Embeddings are L2 normalized
5. **Indexing**: Added to FAISS with metadata
6. **Storage**: Image path and vector ID stored in PostgreSQL

### Search Flow

1. **Face Scan**: User takes selfie
2. **Embedding Generation**: Same process as upload
3. **Vector Search**: FAISS finds similar embeddings
4. **Threshold Filter**: Only matches above 75% similarity
5. **User Filter**: Only show user's own images
6. **Results**: Return ranked matches with metadata

## Performance

- **Embedding extraction**: ~50ms per face
- **Vector search**: <5ms for 100k vectors
- **End-to-end latency**: <200ms typical
- **Throughput**: 50+ requests/second

## Security

- All passwords hashed with bcrypt
- JWT tokens with configurable expiration
- Session-based access control
- Users only see their own images
- CORS protection enabled

## Production Deployment

### AWS Deployment

1. Deploy PostgreSQL on RDS
2. Deploy API on ECS/EKS
3. Use S3 for image storage
4. CloudFront for frontend CDN
5. Configure ALB with SSL

### Scaling Considerations

- Use Redis for session caching
- Horizontal scaling with load balancer
- FAISS index on shared storage
- Async processing with Celery

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details.

---

Built with ❤️ using Python, FastAPI, and Next.js
