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
  - [ ] Aim for ≥80% test coverage on key modules

[ ] 1.2 Design and implement database schema (src/database/schema.py)
- Time-series data table design
  - [ ] Support multiple time granularities (Tick/1Min/Daily)
  - [ ] Create composite indexes (timestamp + symbol)
- Data storage optimization
  - [ ] Implement data sharding strategy
  - [ ] Compress historical data using Parquet/Arrow format
- Data integrity mechanisms
  - [ ] Build CHECKSUM verification procedures
  - [ ] Enforce foreign key constraints and transaction management

[ ] 1.3 Develop data ingestion module (src/core/data_ingest.py, src/core/mcp_data_ingest.py)
- Multi-source integration
  - [ ] Implement adapters for Yahoo/MCP/broker APIs
  - [ ] Standardize output data format
- Real-time streaming
  - [ ] Implement WebSocket auto-reconnection
  - [ ] Add backpressure control mechanism
- API management and fault tolerance
  - [ ] Request rate limiter
  - [ ] Automatic failover mechanism for data sources

[ ] 1.4 Implement historical data backfill and validation (src/core/historical_backfill.py)
- Batch processing optimization
  - [ ] Time-sliced parallel downloading
  - [ ] Identify incremental updates
- Data validation
  - [ ] Time-series continuity check
  - [ ] Automated outlier tagging system

[ ] 1.5 Data cleaning and preprocessing module (src/core/features.py)
- Feature engineering framework
  - [ ] Modularized technical indicator computation (MACD, RSI, Bollinger Bands)
  - [ ] Rolling window feature generator
- Data cleaning flow
  - [ ] Outlier detection and treatment (Z-score/IQR)
  - [ ] Missing value imputation (time series interpolation/ML-based)
- Distributed processing
  - [ ] Reserve integration hooks for Dask/Ray
  - [ ] Implement memory chunking mechanism

---

[ ] 2.1 Research and select preliminary trading indicators
- [ ] Technical indicators: SMA, EMA, MACD, RSI, Bollinger Bands, OBV, ATR
- [ ] Fundamental indicators: EPS growth, P/E, P/B
- [ ] Sentiment/topic-based indicators (if applicable)
- [ ] Standardize and compare indicators

[ ] 2.2 Implement signal generator (src/core/signal_gen.py)
- [ ] Integrate technical indicator calculations
- [ ] Design signal generation logic (breakout/crossover/divergence)
- [ ] Output signals for backtesting periods
- [ ] Build unit tests for signal module

[ ] 2.3 Develop backtest engine (src/core/backtest.py)
- [ ] Build strategy execution loop (including capital/position tracking)
- [ ] Integrate data simulator and historical data reader
- [ ] Output strategy performance metrics (return, Sharpe, max drawdown)
- [ ] Consider using open_source_libs/backtrader/ as core engine
- [ ] Support multi-strategy switching and comparison

[ ] 2.4 Develop portfolio management module (src/core/portfolio.py)
- [ ] Build asset allocation logic (equal weight, risk parity, etc.)
- [ ] Simulate multi-asset holding dynamics
- [ ] Record portfolio states and transaction logs per period

[ ] 2.5 Implement risk control module (src/core/risk_control.py)
- [ ] Define stop-loss/take-profit rules
- [ ] Configure capital allocation ratio
- [ ] Calculate risk metrics (e.g. VaR, volatility)
- [ ] Support risk control at strategy and portfolio levels

[ ] 2.6 Data source research and collection
- [ ] Research available stock market APIs (Yahoo, Alpha Vantage, Finnhub, broker APIs)
- [ ] Research financial statement sources and structure
- [ ] Research news sentiment data (if included)
- [ ] Confirm data update frequency and historical coverage

[ ] 2.7 Build data collection system
- [ ] Develop daily/minute K-line data collector
- [ ] Implement real-time quote API connector
- [ ] Develop financial statement collector
- [ ] Develop sentiment/news data collector (if applicable)
- [ ] Set up scheduled tasks (daily/hourly auto-fetch)
- [ ] Implement error handling and retry mechanism
- [ ] The main workflow will use custom Python crawlers for core financial news sources, with Maxun platform as a supplementary and backup solution for difficult or frequently changing websites.

[ ] 2.8 Data storage and validation
- [ ] Design database schema (expand market_data.db or use PostgreSQL/InfluxDB)
- [ ] Build data write and ingestion pipelines
- [ ] Implement data quality checks (continuity, nulls, etc.)
- [ ] Configure data backup and restore mechanism
- [ ] Manage data versioning and change tracking

[ ] 2.9 Data cleaning and processing
- [ ] Handle missing values (imputation, deletion, etc.)
- [ ] Handle outliers (Z-score, capping)
- [ ] Standardize prices and apply adjusted-close logic
- [ ] Design cleaning workflow and modular scripts

[ ] 2.10 Feature engineering and governance
- [ ] Calculate indicators: SMA, RSI, MACD, Bollinger Bands, OBV, ATR
- [ ] Extract financial features (P/E, EPS growth, etc.)
- [ ] Extract sentiment features (topics, sentiment scores, etc.)
- [ ] Standardize and transform features (Z-score, Min-Max)
- [ ] Perform feature selection and dimensionality reduction (PCA, RFE)
- [ ] Build feature store and versioning (can integrate with MLflow)

---

[ ] 3.1 Strategy research and model selection
- [ ] Literature review and market analysis for strategy types (trend-following, mean-reversion, arbitrage, event-driven)
- [ ] Select model architecture (LSTM, GRU, Transformer, RandomForest, XGBoost, LightGBM, or rule-based)
- [ ] Define model input features and outputs (signal or price prediction)
- [ ] Split datasets into train/validation/test (ensure temporal order, avoid look-ahead bias)
- [ ] Prepare feature dataset (src/core/features.py)

[ ] 3.2 Model training and tuning (src/models/, src/strategies/)
- [ ] Implement training and inference pipeline
- [ ] Perform hyperparameter tuning (Grid/Random/Bayesian Optimization)
- [ ] Define performance metrics (Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, PnL Ratio)
- [ ] Set acceptance thresholds (e.g., Sharpe > 1.2)
- [ ] Add model interpretability (SHAP, LIME)
- [ ] Model governance:
  - [ ] Version tracking and management (e.g., MLflow)
  - [ ] Design deployment and rollback mechanisms

[ ] 3.3 Backtesting system integration (src/strategies/, open_source_libs/backtrader/)
- [ ] Learn and integrate backtrader or alternative backtest framework
- [ ] Implement custom Strategy class to combine model and logic
- [ ] Simulate transaction costs (commission, slippage, tax)
- [ ] Rigorously backtest with:
  - [ ] Strict prevention of look-ahead bias
  - [ ] In-sample / out-of-sample testing
  - [ ] Stress testing and abnormal scenario simulation (crashes, illiquidity)
- [ ] Analyze backtest reports (results/) to iterate strategies
- [ ] Conduct sensitivity and robustness analysis

[ ] 3.4 Integrate AI models into trading flow (src/core/signal_gen.py)
- [ ] Integrate trained models into signal generator
- [ ] Ensure output format compatibility with rule-based logic
- [ ] Ensure inference efficiency and stability during deployment

---

[ ] 4.1 Order execution module implementation (src/core/executor.py, src/execution/)
- [ ] Research and select broker APIs (considering cost, stability, and market support)
- [ ] Develop API modules for placing/querying/canceling orders
- [ ] Implement API key encryption and security management (Vault, KMS, environment variables)
- [ ] Handle order management (partial fills, queuing, retries)
- [ ] Design error handling and alert mechanisms
- [ ] Support live/simulated/backtest environment switching
- [ ] Set up paper trading environment
- [ ] Ensure configuration isolation between live and simulated modes
- [ ] Design rollback and data isolation strategy

[ ] 4.2 Event monitoring and logging system development (src/core/event_monitor.py, src/core/logger.py)
- [ ] Design and integrate complex event processing engine
- [ ] Implement transaction event logging and anomaly detection
- [ ] Define API interfaces between modules (consider OpenAPI/Swagger)
- [ ] Draw sequence diagrams, data flow, and control flow diagrams

[ ] 4.3 Real-time data stream processing
- [ ] Design real-time feature update and model inference flow
- [ ] Set up streaming data updates (Kafka, RabbitMQ, etc.)

[ ] 4.4 Risk management and protection module (src/core/risk_control.py, src/risk_management/)
- [ ] Implement stop-loss logic (percent-based, ATR, time-based)
- [ ] Implement take-profit and capital management rules (fixed amount, proportion, Kelly)
- [ ] Position sizing and max drawdown limits
- [ ] Portfolio-level risk control
- [ ] Define refined risk monitoring metrics:
  - [ ] Value at Risk (VaR)
  - [ ] Maximum daily loss
  - [ ] Account balance thresholds
  - [ ] Stock/portfolio concentration limits
- [ ] Design auto-order halt and manual intervention mechanisms

[ ] 4.5 Automation and workflow orchestration (n8n / FastAPI / src/integration/)
- [ ] Design n8n automation workflows:
  - [ ] Trigger by schedule or Webhook
  - [ ] Full pipeline: data ingestion → prediction → transformation → order placement → notification
  - [ ] Error handling, retry, and alert flows
- [ ] Develop custom nodes/API services (FastAPI/Flask)
- [ ] Provide YAML/JSON configuration examples and diagrams
- [ ] Consider integration with Model Context Protocol (MCP) as a model interface standard
- [ ] Test and validate full end-to-end automated trading workflow

[ ] 4.6 System security and regulatory compliance
- [ ] Manage API keys and sensitive data (Vault/KMS/HTTPS)
- [ ] Implement TLS data encryption and data-at-rest encryption
- [ ] Role-based access control (RBAC)
- [ ] Set rate limits, order limits, and login anomaly detection
- [ ] Research and implement AML/KYC compliance (per broker/market requirements)
- [ ] Establish immutable trade logs and audit trails

---

[ ] 5.1 n8n workflow design and automation integration
- [ ] Design complete n8n workflow architecture
- [ ] Configure schedules and triggers (Cron/Webhook)
- [ ] Wrap core trading logic as APIs or microservices for n8n to call (FastAPI/Flask)
- [ ] Develop custom n8n nodes (if standard nodes are insufficient)
- [ ] Deploy and test automated trading flow in n8n
- [ ] Set up error handling, retry, and multi-level alert workflows
- [ ] Provide YAML/JSON workflow configs and diagram documentation
- [ ] Consider integrating Model Context Protocol (MCP), if applicable

[ ] 5.2 System monitoring and alert mechanism
- [ ] Set up monitoring dashboards using Grafana/Prometheus/n8n
- [ ] Monitor key metrics:
  - [ ] API latency (target < 200ms)
  - [ ] Data update delay
  - [ ] Model prediction accuracy drift
  - [ ] Trade success rate, capital changes
  - [ ] System CPU/RAM/disk usage
- [ ] Configure critical event alerts (e.g. trade failures, model deviation, API issues, risk triggers, resource limits)
- [ ] Define SLA for anomaly response time (e.g. within 5 minutes)

[ ] 5.3 Logging system design and integration
- [ ] Use Python logging with JSON Formatter to build structured logs
- [ ] Log categories: system operations, data handling, model inference, trade execution, errors, security audits
- [ ] Centralized logging and analytics: integrate ELK Stack / Grafana Loki / Splunk (depending on feasibility)

[ ] 5.4 Documentation and knowledge management
- [ ] Write and update full technical and project documentation:
  - [ ] README.md: project overview, setup guide, todo list
  - [ ] System architecture and data flow diagrams
  - [ ] Module functionalities and API docs (Swagger/OpenAPI)
  - [ ] n8n workflow configs and screenshots
  - [ ] Strategy and model documentation (logic, parameters, performance reports)
  - [ ] Maintenance manual and troubleshooting guide
- [ ] Create onboarding docs and training materials for new members
- [ ] Provide internationalized support docs (multi-language API/UI guides)

[ ] 5.5 Continuous optimization and maintenance
- [ ] Periodically retrain models to adapt to market changes
- [ ] Reassess and refine trading strategies regularly
- [ ] Track and integrate new data sources, indicators, or algorithms
- [ ] Identify and optimize system performance bottlenecks
- [ ] Maintain compatibility with updates to n8n or broker APIs

---

[ ] 6.1 Performance profiling and system optimization
- [ ] Profile system performance (I/O, memory, CPU, latency)
- [ ] Identify bottlenecks and optimize data flow and module efficiency
- [ ] Optimize model inference speed and resource usage (e.g. ONNX, batch inference)

[ ] 6.2 Strategy backtesting and dynamic adjustment
- [ ] Re-backtest strategies based on market changes
- [ ] Tune parameters and logic based on performance results
- [ ] Document and version before/after comparisons and rationales

[ ] 6.3 Error handling and system stability improvement
- [ ] Compile known issues and exceptions from testing phases
- [ ] Design robust fallback/retry mechanisms
- [ ] Enhance module fault tolerance and self-recovery
- [ ] Improve real-time logging and alert readability

[ ] 6.4 Documentation and final delivery preparation (README.md)
- [ ] Complete user guide and installation manual
- [ ] Create final system architecture and deployment diagrams
- [ ] Write comprehensive strategy and model reports
- [ ] Organize version history and changelogs

[ ] 6.5 Define project delivery and acceptance criteria
- [ ] Define phase-specific "Definition of Done" (DoD)
  - [ ] e.g., data modules are stable and testable, models output with metrics
  - [ ] e.g., backtested annual Sharpe > 1.2, model versioning complete
- [ ] Define overall "Acceptance Criteria"
  - [ ] System runs N days stably without major failures
  - [ ] Critical API latency < Y ms
  - [ ] Alerts trigger within Z minutes
  - [ ] Technical documentation meets completeness standards

[ ] 6.6 Final testing and verification workflow
- [ ] Conduct unit, integration, and end-to-end tests
- [ ] Track and improve test coverage
- [ ] Perform performance and stress tests to ensure high-load stability

[ ] 6.7 CI/CD pipeline implementation
- [ ] Set up automated build and testing workflows
- [ ] Build staging/simulation deployment pipelines
- [ ] Safely promote to live deployment and validate rollback capability

---