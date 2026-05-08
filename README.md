# eToro Portfolio Manager

AI-assisted portfolio management and copy-trading analytics platform for eToro investors. Capital preservation, risk management, and semi-automated optimization for copy-trading portfolios.

## Features

- **Portfolio Dashboard** - Real-time portfolio metrics, P&L tracking, allocation breakdowns, and performance curves
- **Copied Trader Analytics Engine** - Classify traders (conservative/balanced/aggressive/high_risk), track performance trends, detect underperformance
- **AI-Powered Recommendations** - Claude API integration for intelligent portfolio analysis and actionable recommendations
- **Semi-Automation System** - Rule-based automation with configurable safeguards, cooldowns, and manual override
- **Telegram Bot Integration** - Real-time notifications, weekly summaries, and command-based portfolio queries
- **Risk Management System** - Multi-layered risk scoring (portfolio, trader, market), configurable limits, emergency stop protocols
- **Paper/Simulation Trading Mode** - Full simulation environment for testing strategies without real capital
- **Real-time Updates** - WebSocket connections for live portfolio streaming
- **Audit Trail** - Complete action logging with paginated history

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  ┌───────────┐ ┌───────────┐ ┌──────────────────────┐   │
│  │ Dashboard  │ │ Analytics │ │  Automation Control   │   │
│  └─────┬─────┘ └─────┬─────┘ └──────────┬───────────┘   │
│        │              │                  │               │
│  ┌─────┴──────────────┴──────────────────┴───────────┐   │
│  │             API Client (HTTP + WebSocket)          │   │
│  └─────────────────────┬─────────────────────────────┘   │
└────────────────────────┼─────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────┐
│              Backend (FastAPI + Python 3.11)              │
│  ┌─────────────────────┴─────────────────────────────┐   │
│  │              REST API + WebSocket                   │   │
│  └──┬──────────┬──────────┬──────────┬──────────┬─────┘   │
│     │          │          │          │          │         │
│  ┌──┴──┐  ┌───┴───┐  ┌──┴───┐  ┌──┴───┐  ┌───┴────┐    │
│  │Risk │  │Analyt-│  │Autom-│  │  AI  │  │Notifica│    │
│  │Mngmt│  │ ics   │  │ation │  │Claude│  │ tions  │    │
│  └──┬──┘  └───┬───┘  └──┬───┘  └──┬───┘  └───┬────┘    │
│     │         │         │         │          │          │
│  ┌──┴─────────┴─────────┴─────────┴──────────┴──────┐   │
│  │              SQLAlchemy ORM + AsyncSQLite         │   │
│  └──────────────────────┬───────────────────────────┘   │
└─────────────────────────┼───────────────────────────────┘
                          │
                   ┌──────┴──────┐
                   │  Database   │
                   │  (SQLite)   │
                   └─────────────┘
```

## Tech Stack

| Layer        | Technology                                    |
|-------------|-----------------------------------------------|
| Backend     | Python 3.11, FastAPI, SQLAlchemy 2.0, APScheduler |
| Frontend    | React 18, TypeScript, TailwindCSS, Recharts   |
| AI          | Claude API (Anthropic Claude 3.5 Sonnet)     |
| Bot         | python-telegram-bot 20.x                      |
| Database    | SQLite (MVP) / PostgreSQL 16 (production)     |
| Async       | asyncio, aiosqlite, httpx, websockets         |
| Auth        | Bearer token, rate limiting (slowapi)         |
| Logging     | structlog, python-json-logger                 |
| Infra       | Docker, Docker Compose, Nginx                 |
| Testing     | pytest, httpx AsyncClient                     |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm

### Installation

**Linux/macOS:**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

**Manual installation:**

```bash
# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..

# Environment
cp .env.example .env
mkdir -p logs data
```

### Configuration

Edit `.env` with your configuration:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | App secret key for auth | Yes |
| `DATABASE_URL` | SQLite or PostgreSQL URL | Yes |
| `ETORO_API_KEY` | eToro API credentials | No (optional) |
| `ETORO_USERNAME` | eToro account username | No (optional) |
| `CLAUDE_API_KEY` | Anthropic Claude API key | No (optional) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | No (optional) |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications | No (optional) |
| `PAPER_TRADING` | Enable paper trading mode | No (default: true) |

### Running

**Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**Docker:**
```bash
docker-compose -f docker/docker-compose.yml up
```

## API Documentation

Once running, the API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/portfolio` | Portfolio details |
| `GET /api/v1/portfolio/positions` | Open positions |
| `GET /api/v1/portfolio/history` | Performance history |
| `POST /api/v1/portfolio/sync` | Sync with eToro |
| `GET /api/v1/traders` | List copied traders |
| `GET /api/v1/traders/analysis` | AI trader analysis |
| `GET /api/v1/risk/summary` | Risk overview |
| `GET /api/v1/risk/metrics` | Historical risk data |
| `GET /api/v1/risk/limits` | Risk limit config |
| `PUT /api/v1/risk/limits` | Update risk limits |
| `POST /api/v1/risk/emergency-stop` | Emergency stop |
| `GET /api/v1/automation/rules` | Automation rules |
| `POST /api/v1/automation/rules` | Create automation rule |
| `GET /api/v1/automation/logs` | Automation logs |
| `GET /api/v1/ai/recommendations` | AI recommendations |
| `POST /api/v1/ai/analyze` | Trigger AI analysis |
| `GET /api/v1/alerts` | Portfolio alerts |
| `GET /api/v1/audit` | Audit trail |
| `WS /ws` | WebSocket live updates |

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/portfolio` | Portfolio summary |
| `/risk` | Current risk status |
| `/traders` | List copied traders with classifications |
| `/alerts` | Recent portfolio alerts |
| `/weekly` | Weekly performance summary |
| `/analyze` | Trigger AI portfolio analysis |
| `/emergency` | Emergency stop all copy relationships |
| `/help` | Show all available commands |

## Risk Management

The platform implements a three-layer risk scoring system:

### 1. Portfolio Risk Score
- **Concentration Risk** - HHI-based portfolio concentration measurement
- **Volatility Score** - Annualized volatility assessment
- **Drawdown Score** - Current vs maximum drawdown severity
- **Health Penalty** - Portfolio health score deductions
- **Leverage Impact** - Excessive leverage penalties
- **Correlation Risk** - Cross-asset correlation penalties

### 2. Trader Risk Score
- Classification-based base risk (conservative=5 to high_risk=50)
- Performance consistency assessment
- Win rate analysis
- Trade frequency consideration

### 3. Market Risk Score
- VIX-based volatility assessment
- Market trend evaluation
- Economic event impact scoring
- Sector and liquidity risk

### Emergency Stop Protocol

| Level | Name | Trigger | Actions |
|-------|------|---------|---------|
| 1 | Warning | Daily loss >5%, drawdown >12% | Notify, increase monitoring |
| 2 | Moderate | Drawdown >18%, risk >50 | Pause risky traders, reduce 25% |
| 3 | Severe | Drawdown >25%, risk >65 | Pause all copy, liquidate high-risk |
| 4 | Critical | Drawdown >35%, risk >80 | Full freeze, urgent notification |

## Automation Rules

| Rule Type | Description | Triggers |
|-----------|-------------|----------|
| **Take Profit** | Close positions at profit target | P&L > configured threshold |
| **Partial Profit** | Lock in partial profits | P&L > threshold, lock percentage |
| **Rebalance** | Rebalance allocation deviations | Allocation drift > threshold |
| **Reduce Allocation** | Reduce trader allocation on drawdown | Trader drawdown > threshold |
| **Pause Copy** | Pause underperforming traders | Drawdown or consecutive losses |
| **Dynamic Exposure** | Adjust exposure based on volatility | Volatility threshold breach |

Each rule supports: cooldown periods, max daily frequency, configurable thresholds, audit logging, and manual override.

## AI Assistant

The AI recommendation engine (Claude 3.5 Sonnet) analyzes:

- **Trader Performance** - Classification, risk metrics, trend analysis
- **Portfolio Health** - Concentration, volatility, drawdown assessment
- **Risk Alerts** - Threshold breaches and emerging risks
- **Rebalancing** - Allocation imbalance detection
- **Weekly Summaries** - Comprehensive performance reports

AI can be triggered manually via the API or runs on a configurable schedule.

## Project Structure

```
etoro-portfolio-manager/
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── backend/
│   ├── main.py               # FastAPI app, middleware, lifespan
│   ├── requirements.txt      # Python dependencies
│   ├── alembic.ini           # DB migration config
│   ├── alembic/
│   │   └── env.py            # Async Alembic environment
│   ├── __init__.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── client.py         # Claude API client
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── calculator.py     # PortfolioCalculator
│   │   ├── performance.py    # PerformanceAnalyzer
│   │   ├── risk_scorer.py    # RiskScorer
│   │   └── trader_analyzer.py # TraderAnalyzer
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py           # FastAPI dependencies
│   │   ├── routes.py         # API route handlers
│   │   └── websocket.py      # WebSocket manager
│   ├── automation/
│   │   ├── __init__.py
│   │   ├── executor.py       # AutomationExecutor
│   │   ├── rules_engine.py   # RulesEngine
│   │   └── safeguards.py     # Safeguards
│   ├── config/
│   │   ├── __init__.py
│   │   ├── logging_config.py # structlog configuration
│   │   └── settings.py       # Pydantic settings
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py             # Async engine, session
│   │   ├── models.py         # SQLAlchemy models
│   │   └── schema.py         # Pydantic schemas
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── telegram_bot.py   # Telegram integration
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── emergency.py      # EmergencyProtection
│   │   ├── limits.py         # RiskLimits
│   │   └── manager.py        # RiskManager
│   └── services/
│       ├── __init__.py
│       ├── alerts_service.py # AlertsService
│       ├── portfolio_service.py # PortfolioService
│       ├── scheduler.py      # APScheduler integration
│       └── trader_service.py # TraderService
├── config/
│   ├── config.yaml           # App configuration
│   └── logging.yaml          # Logging configuration
├── docker/
│   ├── docker-compose.yml    # Multi-service orchestration
│   ├── Dockerfile.backend    # Backend container
│   ├── Dockerfile.frontend   # Frontend container
│   └── nginx.conf            # Reverse proxy config
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── public/
│   └── src/
├── scripts/
│   ├── setup.sh              # Linux/macOS setup
│   └── setup.ps1             # Windows setup
└── tests/
    ├── __init__.py
    ├── test_analytics.py     # Analytics unit tests
    ├── test_api.py           # API endpoint tests
    ├── test_automation.py    # Automation unit tests
    └── test_risk.py          # Risk management tests
```

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_analytics.py -v

# Run specific test class
python -m pytest tests/test_analytics.py::TestCalculateTotalValue -v

# Run with verbose output
python -m pytest tests/ -v --tb=short
```

### Test Coverage

| Module | Tests | Focus |
|--------|-------|-------|
| `test_analytics.py` | 50+ | PortfolioCalculator, TraderAnalyzer, RiskScorer, PerformanceAnalyzer |
| `test_risk.py` | 30+ | RiskManager, RiskLimits, EmergencyProtection |
| `test_automation.py` | 25+ | Safeguards, RulesEngine, AutomationExecutor |
| `test_api.py` | 10+ | Health, portfolio, CORS, 404 handling |

## Deployment

### Docker (Recommended)

```bash
# Build and start
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop
docker-compose -f docker/docker-compose.yml down
```

### Production Considerations

1. **Database**: Migrate from SQLite to PostgreSQL (uncomment in docker-compose.yml)
2. **Secrets**: Use Docker secrets or HashiCorp Vault instead of .env
3. **TLS**: Configure SSL termination at the load balancer or in Nginx
4. **Rate Limiting**: Adjust slowapi limits for production traffic
5. **Monitoring**: Integrate with Prometheus/Grafana or Sentry
6. **Backups**: Schedule automated database backups
7. **CI/CD**: Run `pytest tests/` in CI pipeline before deployment

## License

MIT

Copyright (c) 2024 eToro Portfolio Manager

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
