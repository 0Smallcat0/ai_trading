# AI 股票自動交易系統 - Todo List / AI Stock Automated Trading System - Todo List

## <a name="english-version"></a>English Version

---

[X] 1.1 Set up project environment and install dependencies
- Version control system
  - [X] Initialize Git and configure .gitignore to exclude sensitive data
  - [X] Adopt Git Flow branching strategy (develop/main branches)
- Environment isolation
  - [X] Use pyenv + poetry for dependency management
  - [X] Set up multi-environment configuration (dev/test/prod)
- Project structure enhancement
  - [X] Create modular directory structure: models/ (AI models), strategies/ (trading strategies), execution/ (order execution)
- Code quality control
  - [X] Integrate pre-commit hooks (Black / Flake8 / Mypy)
  - [X] Follow Google Style Docstring convention
  - [X] Configure pylint for static code analysis
- Testing framework and CI/CD
  - [X] Use pytest to build unit tests for core modules
  - [X] Set up GitHub Actions for CI/CD pipeline
  - [X] Aim for ≥80% test coverage on key modules

[X] 1.2 Design and implement database schema (src/database/schema.py)
- Time-series data table design
  - [X] Support multiple time granularities (Tick/1Min/Daily)
  - [X] Create composite indexes (timestamp + symbol)
- Data storage optimization
  - [X] Implement data sharding strategy
  - [X] Compress historical data using Parquet/Arrow format
- Data integrity mechanisms
  - [X] Build CHECKSUM verification procedures
  - [X] Enforce foreign key constraints and transaction management

[X] 1.3 Develop data ingestion module (src/core/data_ingest.py, src/core/mcp_data_ingest.py)
- Multi-source integration
  - [X] Implement adapters for Yahoo/MCP/broker APIs
  - [X] Standardize output data format
- Real-time streaming
  - [X] Implement WebSocket auto-reconnection
  - [X] Add backpressure control mechanism
- API management and fault tolerance
  - [X] Request rate limiter
  - [X] Automatic failover mechanism for data sources

[X] 1.4 Implement historical data backfill and validation (src/core/historical_backfill.py)
- Batch processing optimization
  - [X] Time-sliced parallel downloading
  - [X] Identify incremental updates
- Data validation
  - [X] Time-series continuity check
  - [X] Automated outlier tagging system

[X] 1.5 Data cleaning and preprocessing module (src/core/features.py)
- Feature engineering framework
  - [X] Modularized technical indicator computation (MACD, RSI, Bollinger Bands)
  - [X] Rolling window feature generator
- Data cleaning flow
  - [X] Outlier detection and treatment (Z-score/IQR)
  - [X] Missing value imputation (time series interpolation/ML-based)
- Distributed processing
  - [X] Reserve integration hooks for Dask/Ray
  - [X] Implement memory chunking mechanism

---

[X] 2.1 Research and select preliminary trading indicators
- [X] Technical indicators: SMA, EMA, MACD, RSI, Bollinger Bands, OBV, ATR
- [X] Fundamental indicators: EPS growth, P/E, P/B
- [X] Sentiment/topic-based indicators (if applicable)
- [X] Standardize and compare indicators

[X] 2.2 Implement signal generator (src/core/signal_gen.py)
- [X] Integrate technical indicator calculations
- [X] Design signal generation logic (breakout/crossover/divergence)
- [X] Output signals for backtesting periods
- [X] Build unit tests for signal module

[X] 2.3 Develop backtest engine (src/core/backtest.py)
- [X] Build strategy execution loop (including capital/position tracking)
- [X] Integrate data simulator and historical data reader
- [X] Output strategy performance metrics (return, Sharpe, max drawdown)
- [X] Consider using open_source_libs/backtrader/ as core engine
- [X] Support multi-strategy switching and comparison

[X] 2.4 Develop portfolio management module (src/core/portfolio.py)
- [X] Build asset allocation logic (equal weight, risk parity, etc.)
- [X] Simulate multi-asset holding dynamics
- [X] Record portfolio states and transaction logs per period

[X] 2.5 Implement risk control module (src/core/risk_control.py)
- [X] Define stop-loss/take-profit rules
- [X] Configure capital allocation ratio
- [X] Calculate risk metrics (e.g. VaR, volatility)
- [X] Support risk control at strategy and portfolio levels

[X] 2.6 Data source research and collection
- [X] Research available stock market APIs (Yahoo, Alpha Vantage, Finnhub, broker APIs)
- [X] Research financial statement sources and structure
- [X] Research news sentiment data (if included)
- [X] Confirm data update frequency and historical coverage

[X] 2.7 Build data collection system
- [X] Develop daily/minute K-line data collector
- [X] Implement real-time quote API connector
- [X] Develop financial statement collector
- [X] Develop sentiment/news data collector (if applicable)
- [X] Set up scheduled tasks (daily/hourly auto-fetch)
- [X] Implement error handling and retry mechanism
- [X] The main workflow will use custom Python crawlers for core financial news sources, with Maxun platform as a supplementary and backup solution for difficult or frequently changing websites.

[X] 2.8 Data storage and validation
- [X] Design database schema (expand market_data.db or use PostgreSQL/InfluxDB)
- [X] Build data write and ingestion pipelines
- [X] Implement data quality checks (continuity, nulls, etc.)
- [X] Configure data backup and restore mechanism
- [X] Manage data versioning and change tracking

[X] 2.9 Data cleaning and processing
- [X] Handle missing values (imputation, deletion, etc.)
- [X] Handle outliers (Z-score, capping)
- [X] Standardize prices and apply adjusted-close logic
- [X] Design cleaning workflow and modular scripts

[X] 2.10 Feature engineering and governance
- [X] Calculate indicators: SMA, RSI, MACD, Bollinger Bands, OBV, ATR
- [X] Extract financial features (P/E, EPS growth, etc.)
- [X] Extract sentiment features (topics, sentiment scores, etc.)
- [X] Standardize and transform features (Z-score, Min-Max)
- [X] Perform feature selection and dimensionality reduction (PCA, RFE)
- [X] Build feature store and versioning (can integrate with MLflow)

---

[X] 3.1 Strategy research and model selection
- [X] Literature review and market analysis for strategy types (trend-following, mean-reversion, arbitrage, event-driven)
- [X] Select model architecture (LSTM, GRU, Transformer, RandomForest, XGBoost, LightGBM, or rule-based)
- [X] Define model input features and outputs (signal or price prediction)
- [X] Split datasets into train/validation/test (ensure temporal order, avoid look-ahead bias)
- [X] Prepare feature dataset (src/core/features.py)

[X] 3.2 Model training and tuning (src/models/, src/strategies/)
- [X] Implement training and inference pipeline
- [X] Perform hyperparameter tuning (Grid/Random/Bayesian Optimization)
- [X] Define performance metrics (Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, PnL Ratio)
- [X] Set acceptance thresholds (e.g., Sharpe > 1.2)
- [X] Add model interpretability (SHAP, LIME)
- [X] Model governance:
  - [X] Version tracking and management (e.g., MLflow)
  - [X] Design deployment and rollback mechanisms

[X] 3.3 Backtesting system integration (src/strategies/, open_source_libs/backtrader/)
- [X] Learn and integrate backtrader or alternative backtest framework
- [X] Implement custom Strategy class to combine model and logic
- [X] Simulate transaction costs (commission, slippage, tax)
- [X] Rigorously backtest with:
  - [X] Strict prevention of look-ahead bias
  - [X] In-sample / out-of-sample testing
  - [X] Stress testing and abnormal scenario simulation (crashes, illiquidity)
- [X] Analyze backtest reports (results/) to iterate strategies
- [X] Conduct sensitivity and robustness analysis

[X] 3.4 Integrate AI models into trading flow (src/core/signal_gen.py)
- [X] Integrate trained models into signal generator
- [X] Ensure output format compatibility with rule-based logic
- [X] Ensure inference efficiency and stability during deployment

---

[X] 4.1 Order execution module implementation (src/core/executor.py, src/execution/)
- [X] Research and select broker APIs (considering cost, stability, and market support)
- [X] Develop API modules for placing/querying/canceling orders
- [X] Implement API key encryption and security management (Vault, KMS, environment variables)
- [X] Handle order management (partial fills, queuing, retries)
- [X] Design error handling and alert mechanisms
- [X] Support live/simulated/backtest environment switching
- [X] Set up paper trading environment
- [X] Ensure configuration isolation between live and simulated modes
- [X] Design rollback and data isolation strategy

[X] 4.2 Event monitoring and logging system development (src/core/event_monitor.py, src/core/logger.py)
- [X] Design and integrate complex event processing engine
- [X] Implement transaction event logging and anomaly detection
- [X] Define API interfaces between modules (consider OpenAPI/Swagger)
- [X] Draw sequence diagrams, data flow, and control flow diagrams

[X] 4.3 Real-time data stream processing
- [X] Design real-time feature update and model inference flow
- [X] Set up streaming data updates (Kafka, RabbitMQ, etc.)

[X] 4.4 Risk management and protection module (src/core/risk_control.py, src/risk_management/)
- [X] Implement stop-loss logic (percent-based, ATR, time-based)
- [X] Implement take-profit and capital management rules (fixed amount, proportion, Kelly)
- [X] Position sizing and max drawdown limits
- [X] Portfolio-level risk control
- [X] Define refined risk monitoring metrics:
  - [X] Value at Risk (VaR)
  - [X] Maximum daily loss
  - [X] Account balance thresholds
  - [X] Stock/portfolio concentration limits
- [X] Design auto-order halt and manual intervention mechanisms

[X] 4.5 Automation and workflow orchestration (n8n / FastAPI / src/integration/)
- [X] Design n8n automation workflows:
  - [X] Trigger by schedule or Webhook
  - [X] Full pipeline: data ingestion → prediction → transformation → order placement → notification
  - [X] Error handling, retry, and alert flows
- [X] Develop custom nodes/API services (FastAPI/Flask)
- [X] Provide YAML/JSON configuration examples and diagrams
- [X] Consider integration with Model Context Protocol (MCP) as a model interface standard
- [X] Test and validate full end-to-end automated trading workflow

[X] 4.6 System security and regulatory compliance
- [X] Manage API keys and sensitive data (Vault/KMS/HTTPS)
- [X] Implement TLS data encryption and data-at-rest encryption
- [X] Role-based access control (RBAC)
- [X] Set rate limits, order limits, and login anomaly detection
- [X] Research and implement AML/KYC compliance (per broker/market requirements)
- [X] Establish immutable trade logs and audit trails

---

[X] 5.1 n8n workflow design and automation integration
- [X] Design complete n8n workflow architecture
- [X] Configure schedules and triggers (Cron/Webhook)
- [X] Wrap core trading logic as APIs or microservices for n8n to call (FastAPI/Flask)
- [X] Develop custom n8n nodes (if standard nodes are insufficient)
- [X] Deploy and test automated trading flow in n8n
- [X] Set up error handling, retry, and multi-level alert workflows
- [X] Provide YAML/JSON workflow configs and diagram documentation
- [X] Consider integrating Model Context Protocol (MCP), if applicable

[X] 5.2 System monitoring and alert mechanism
- [X] Set up monitoring dashboards using Grafana/Prometheus/n8n
- [X] Monitor key metrics:
  - [X] API latency (target < 200ms)
  - [X] Data update delay
  - [X] Model prediction accuracy drift
  - [X] Trade success rate, capital changes
  - [X] System CPU/RAM/disk usage
- [X] Configure critical event alerts (e.g. trade failures, model deviation, API issues, risk triggers, resource limits)
- [X] Define SLA for anomaly response time (e.g. within 5 minutes)

[X] 5.3 Logging system design and integration
- [X] Use Python logging with JSON Formatter to build structured logs
- [X] Log categories: system operations, data handling, model inference, trade execution, errors, security audits
- [X] Centralized logging and analytics: integrate ELK Stack / Grafana Loki / Splunk (depending on feasibility)

[X] 5.4 Documentation and knowledge management
- [X] Write and update full technical and project documentation:
  - [X] README.md: project overview, setup guide, todo list
  - [X] System architecture and data flow diagrams
  - [X] Module functionalities and API docs (Swagger/OpenAPI)
  - [X] n8n workflow configs and screenshots
  - [X] Strategy and model documentation (logic, parameters, performance reports)
  - [X] Maintenance manual and troubleshooting guide
- [X] Create onboarding docs and training materials for new members
- [X] Provide internationalized support docs (multi-language API/UI guides)

[X] 5.5 Continuous optimization and maintenance
- [X] Periodically retrain models to adapt to market changes
- [X] Reassess and refine trading strategies regularly
- [X] Track and integrate new data sources, indicators, or algorithms
- [X] Identify and optimize system performance bottlenecks
- [X] Maintain compatibility with updates to n8n or broker APIs

---

[X] 6.1 Performance profiling and system optimization
- [X] Profile system performance (I/O, memory, CPU, latency)
- [X] Identify bottlenecks and optimize data flow and module efficiency
- [X] Optimize model inference speed and resource usage (e.g. ONNX, batch inference)

[X] 6.2 Strategy backtesting and dynamic adjustment
- [X] Re-backtest strategies based on market changes
- [X] Tune parameters and logic based on performance results
- [X] Document and version before/after comparisons and rationales

[X] 6.3 Error handling and system stability improvement
- [X] Compile known issues and exceptions from testing phases
- [X] Design robust fallback/retry mechanisms
- [X] Enhance module fault tolerance and self-recovery
- [X] Improve real-time logging and alert readability

[X] 6.4 Documentation and final delivery preparation (README.md)
- [X] Complete user guide and installation manual
- [X] Create final system architecture and deployment diagrams
- [X] Write comprehensive strategy and model reports
- [X] Organize version history and changelogs

[X] 6.5 Define project delivery and acceptance criteria
- [X] Define phase-specific "Definition of Done" (DoD)
  - [X] e.g., data modules are stable and testable, models output with metrics
  - [X] e.g., backtested annual Sharpe > 1.2, model versioning complete
- [X] Define overall "Acceptance Criteria"
  - [X] System runs N days stably without major failures
  - [X] Critical API latency < Y ms
  - [X] Alerts trigger within Z minutes
  - [X] Technical documentation meets completeness standards

[X] 6.6 Final testing and verification workflow
- [X] Conduct unit, integration, and end-to-end tests
- [X] Track and improve test coverage
- [X] Perform performance and stress tests to ensure high-load stability

[X] 6.7 CI/CD pipeline implementation
- [X] Set up automated build and testing workflows
- [X] Build staging/simulation deployment pipelines
- [X] Safely promote to live deployment and validate rollback capability

---