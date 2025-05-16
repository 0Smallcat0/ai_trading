**Phase 1: 基礎建設與資料處理**
[X] 1.1 設定專案環境與安裝相依套件
　- 版本控制系統
　　[X] 初始化 Git 並設定 .gitignore 排除敏感資料
　　[X] 採用 Git Flow 分支策略 (develop/main 分支)
　- 環境隔離
　　[X] 使用 pyenv + poetry 管理套件依賴
　　[X] 建立多環境配置 (dev/test/prod)
　- 專案結構強化
　　[X] 新增模組化目錄結構：
　　　　models/ (AI模型)、strategies/ (交易策略)、execution/ (訂單執行)
　- 程式碼品質管控
　　[X] 整合 pre-commit hook (Black/Flake8/Mypy)
　　[X] 採用 Google Style Docstring 規範
　　[X] 設定 pylint 靜態程式碼分析
　- 測試框架與 CI/CD
　　[X] 使用 pytest 建立核心模組單元測試
　　[X] 設定 GitHub Actions CI/CD 流程
　　[X] 關鍵模組測試覆蓋率目標 ≥80%

[X] 1.2 設計並實作資料庫結構 (src/database/schema.py)
　- 時序資料表設計
　　[X] 支援多時間粒度 (Tick/1Min/Daily)
　　[X] 建立複合索引 (timestamp + symbol)
　- 資料儲存優化
　　[X] 實施分片儲存策略
　　[X] 壓縮歷史資料儲存格式 (Parquet/Arrow)
　- 資料完整性機制
　　[X] 建立 CHECKSUM 驗證程序
　　[X] 實施外鍵約束與事務管理

[X] 1.3 開發資料擷取模組 (src/core/data_ingest.py, src/core/mcp_data_ingest.py)
　- 多資料源整合
　　[X] 實現 Yahoo/MCP/券商 API 適配層
　　[X] 統一資料格式輸出規範
　- 即時串流處理
　　[X] WebSocket 斷線自動重連機制
　　[X] 實施背壓控制 (backpressure control)
　- API 管理與容錯
　　[X] 請求頻率限制器 (rate limiter)
　　[X] 自動切換備用資料源機制

[X] 1.4 實作歷史資料回填與驗證機制 (src/core/historical_backfill.py)
　- 批次處理優化
　　[X] 分時段平行下載機制
　　[X] 增量更新識別模式
　- 資料驗證
　　[X] 時間序列連續性檢查
　　[X] 異常值自動標記系統

[X] 1.5 資料清洗與預處理模組 (src/core/features.py)
　- 特徵工程框架
　　[X] 模組化技術指標計算 (MACD/RSI/Bollinger Bands)
　　[X] 滾動窗口特徵生成器
　- 數據清洗流程
　　[X] 離群值檢測與處理 (Z-score/IQR)
　　[X] 缺失值插補策略 (時序插值/機器學習補值)
　- 分散式處理
　　[X] Dask/Ray 框架整合預留接口
　　[X] 記憶體分塊處理機制

---

**Phase 2: 交易策略核心**
[X] 2.1 研究並選擇初步的交易訊號指標
　- [X] 技術指標研究：移動平均線 (SMA, EMA)、MACD、RSI、Bollinger Bands、OBV、ATR
　- [X] 基本面指標研究：EPS 成長率、P/E、P/B
　- [X] 輿情/主題指標研究（若納入考量）
　- [X] 指標標準化與比較分析

[X] 2.2 實作交易訊號產生器 (src/core/signal_gen.py)
　- [X] 整合技術指標計算邏輯
　- [X] 設計訊號生成邏輯（突破/交叉/背離等）
　- [X] 設定回測期間輸出訊號以供驗證
　- [X] 建立訊號模組單元測試

[X] 2.3 開發回測引擎 (src/core/backtest.py)
　- [X] 設計策略執行迴圈架構（含資金/部位追蹤）
　- [X] 整合資料模擬器與歷史資料讀取
　- [X] 輸出策略績效指標（報酬、夏普值、最大回落等）
　- [X] 可考慮整合 open_source_libs/backtrader/ 作為底層引擎
　- [X] 支援多策略切換與比較測試

[X] 2.4 實作投資組合管理模組 (src/core/portfolio.py)
　- [X] 建立資產配置邏輯（等權重、風險平衡等）
　- [X] 模擬多資產持倉變動
　- [X] 記錄每期資產狀態與部位交易紀錄

[X] 2.5 實作風險管理模組 (src/core/risk_control.py)
　- [X] 設定停損停利邏輯
　- [X] 設定資金控管比例
　- [X] 計算部位風險值（如 VaR、波動率）
　- [X] 支援策略級與投資組合級風控判斷

[X] 2.6 資料來源研究與收集
　- [X] 研究可用的股票市場資料 API（Yahoo Finance, Alpha Vantage, Finnhub, 券商 API）
　- [X] 研究財報資料來源與結構
　- [X] 研究新聞輿情資料（若納入）
　- [X] 確定資料更新頻率與歷史資料可取得範圍

[X] 2.7 建構資料收集系統
　- [X] 開發歷史日/分鐘 K 線收集模組
　- [X] 開發即時股價 API 串接與更新機制
　- [X] 開發財務報表收集模組
　- [X] 開發新聞輿情收集模組（若納入）
　- [X] 設定定時排程（每日/每小時自動抓取）
　- [X] 實作錯誤處理與重試機制

[X] 2.8 資料儲存與驗證
　- [X] 設計資料庫 schema（可擴充 market_data.db 或使用 PostgreSQL、InfluxDB）
　- [X] 建立寫入邏輯與資料入庫流程
　- [X] 建立資料品質驗證流程（時間連續性、空值偵測等）
　- [X] 設定資料備份與還原機制
　- [X] 資料版本治理（追蹤資料變動與版本控管）

[X] 2.9 資料清洗與處理
　- [X] 缺失值處理（插補、刪除等）
　- [X] 異常值處理（Z-score、蓋帽法）
　- [X] 股價資料標準化與復權轉換
　- [X] 設計處理流程與模組化清洗腳本

[X] 2.10 特徵工程與特徵治理
　- [X] 計算技術指標（SMA, RSI, MACD, Bollinger Bands, OBV, ATR 等）
　- [X] 財報特徵萃取（P/E、EPS成長等）
　- [X] 輿情特徵擷取（主題詞、情緒分數等，若納入）
　- [X] 特徵標準化與轉換（Z-score、Min-Max）
　- [X] 特徵選擇與降維（PCA、RFE）
　- [X] 建立特徵庫與特徵版本管理（可整合 MLflow）

---

**Phase 3: AI 模型整合與交易策略開發**
[X] 3.1 策略研究與模型選擇
　- [X] 文獻回顧與市場分析，研究交易策略類型（趨勢跟蹤、均值回歸、套利、事件驅動等）
　- [X] 選擇合適的模型架構（LSTM、GRU、Transformer、RandomForest、XGBoost、LightGBM 或規則型）
　- [X] 定義模型輸入（特徵集）與輸出（交易信號或價格預測）
　- [X] 劃分資料集：訓練 / 驗證 / 測試（需考慮時序性，避免 look-ahead bias）
　- [X] 準備模型所需特徵資料與資料集 (src/core/features.py)

[X] 3.2 模型訓練與調優 (src/models/, src/strategies/)
　- [X] 實現模型訓練與預測流程
　- [X] 進行超參數調整（Grid Search、Random Search、貝葉斯最佳化等）
　- [X] 設定並使用績效評估指標（Sharpe Ratio, Sortino Ratio, Calmar Ratio, Max Drawdown, 勝率, 盈虧比）
　- [X] 設定驗收門檻（如 Sharpe > 1.2）
　- [X] 處理模型可解釋性（SHAP, LIME）
　- [X] 模型治理：
　　　[X] 建立模型版本控制與追蹤（可考慮 MLflow）
　　　[X] 設計模型部署與回滾機制

[X] 3.3 回測系統開發與整合 (src/strategies/, open_source_libs/backtrader/)
　- [X] 學習並整合 backtrader 或其他回測框架
　- [X] 建立自定義 Strategy 類別，整合模型與策略邏輯
　- [X] 實作交易成本模擬（手續費、滑價、稅）
　- [X] 嚴謹的歷史資料回測：
　　　[X] 嚴格避免 look-ahead bias
　　　[X] 實施樣本內 / 樣本外測試
　　　[X] 執行壓力測試與異常情境模擬（市場崩盤、流動性風險等）
　- [X] 分析回測報告（results/），用於策略與模型的迭代優化
　- [X] 進行參數敏感性分析與穩健性驗證

[X] 3.4 整合 AI 模型至交易流程 (src/core/signal_gen.py)
　- [X] 將訓練好的模型整合進訊號產生模組
　- [X] 設計推論流程與輸出格式與原始規則型邏輯兼容
　- [X] 確保模型部署在推論端時具備效率與穩定性

---

**Phase 4: 執行與監控系統整合**
[X] 4.1 訂單執行模組實作 (src/core/executor.py, src/execution/)
　- [X] 研究與選擇券商 API（考量費用、穩定性、支援市場）
　- [X] 開發下單/查詢/取消訂單 API 串接模組
　- [X] 安全性管理：API 金鑰加密與保護（Vault、KMS、環境變數）
　- [X] 訂單管理邏輯（部分成交、排隊、重試處理）
　- [X] 設計錯誤處理與異常通知機制
　- [X] 實作實盤 / 模擬 / 回測環境切換
　　- [X] 建立 paper trading 環境
　　- [X] 確保實盤與模擬配置隔離
　　- [X] 設計狀態回溯與資料隔離策略

[X] 4.2 事件監控與日誌系統開發 (src/core/event_monitor.py, src/core/logger.py)
　- [X] 設計並整合複雜事件處理引擎
　- [X] 撰寫交易事件記錄與異常偵測流程
　- [X] 模組間 API 規格與介面定義（考慮 OpenAPI/Swagger）
　- [X] 繪製模組互動序列圖與資料流、控制流圖示

[X] 4.3 建立即時資料流處理機制
　- [X] 設計即時特徵更新與模型推論流程
　- [X] 建立 streaming 資料更新機制（Kafka/RabbitMQ 等可擴充）

[X] 4.4 風險管理與異常防護模組 (src/core/risk_control.py, src/risk_management/)
　- [X] 實作停損邏輯（百分比、ATR、時間停損）
　- [X] 實作停利邏輯與資金控管策略（固定金額、比例、Kelly）
　- [X] 倉位控制與最大回撤限制
　- [X] 投資組合層級風險控制
　- [X] 細化風險監控指標：
　　　[X] Value at Risk (VaR)
　　　[X] 最大單日損失
　　　[X] 帳戶資金水位限制
　　　[X] 個股/總體持倉集中度限制
　- [X] 設計自動停單與人工介入機制

[X] 4.5 自動化整合與流程串接（n8n / FastAPI / src/integration/）
　- [X] 設計 n8n 自動化工作流程：
　　　[X] 定時觸發、Webhook 觸發
　　　[X] 資料獲取 → 預測 → 轉換 → 下單 → 通知 全流程節點
　　　[X] 錯誤處理、延遲重試、告警流程
　- [X] 開發自定義節點 / API 化服務（使用 FastAPI/Flask）
　- [X] 提供 n8n YAML/JSON 配置範例與圖示文件
　- [X] 考慮整合 Model Context Protocol（MCP）作為模型介面標準
　- [X] 部署測試完整交易自動化流程，確保穩定性

[X] 4.6 系統安全性與合規性強化
　- [X] API 金鑰與敏感資料加密管理（Vault/KMS/HTTPS）
　- [X] 實作 TLS 資料傳輸加密與靜態資料加密
　- [X] 基於角色的存取權限管理（RBAC）
　- [X] 設定頻率限制、訂單限額、登入異常偵測
　- [X] 研究並實施 AML/KYC 法規要求（視券商與市場）
　- [X] 建立不可篡改的交易記錄與審計追蹤機制

---

**Phase 5: n8n 平台整合與系統維護**
[X] 5.1 n8n Workflow 架構設計與自動化整合
　- [X] 設計完整 n8n workflow 架構
　- [X] 設定排程與觸發機制（定時/Webhook）
　- [X] 將交易系統核心邏輯封裝成 API 或微服務供 n8n 呼叫（FastAPI/Flask）
　- [X] 開發 n8n 自定義節點（若標準節點無法滿足需求）
　- [X] 在 n8n 平台部署並測試自動化交易流程
　- [X] 建立完整的錯誤處理、延遲重試與多層級告警流程
　- [X] 提供 YAML/JSON workflow 配置與圖示文件
　- [X] 考慮 MCP（Model Context Protocol）整合機制（若適用）

[X] 5.2 系統監控與告警機制建立
　- [X] 建立 Grafana/Prometheus/n8n 內建的監控儀表板
　- [X] 監控項目包含：
　　　[X] API 延遲（目標 < 200ms）
　　　[X] 資料更新延遲
　　　[X] 模型預測準確度變化
　　　[X] 交易成功率、資金變動
　　　[X] 系統 CPU/RAM/磁碟使用率
　- [X] 設定關鍵事件警報（交易失敗、模型偏差、API 異常、風險觸發、資源超限）
　- [X] 設定異常事件回報時間 SLA（如 5 分鐘內）

[X] 5.3 日誌系統設計與整合
　- [X] 使用 Python logging 搭配 JSON Formatter 建立結構化日誌系統
　- [X] 記錄項目：系統運行、資料處理、模型推論、交易執行、錯誤與安全審計
　- [X] 集中管理與分析：整合 ELK Stack / Grafana Loki / Splunk（依實作可行性選擇）

[X] 5.4 文件撰寫與知識管理
　- [X] 撰寫與更新完整技術文件與專案說明：
　　　[X] README.md：含專案概觀、部署步驟、Todo List
　　　[X] 系統架構圖與資料流圖
　　　[X] 各模組功能與 API 文件（Swagger/OpenAPI）
　　　[X] n8n 工作流程配置與截圖說明
　　　[X] 策略與模型文件（邏輯、參數、結果報告）
　　　[X] 維護手冊與常見錯誤排查（Troubleshooting Guide）
　- [X] 建立新成員 onboarding 文件與內部培訓材料
　- [X] 國際化支援文件（如 API 文件與 UI 操作指南多語版）

[X] 5.5 系統持續優化與維運
　- [X] 定期檢視與重新訓練模型以因應市場變化或衰退
　- [X] 定期評估與優化交易策略表現
　- [X] 追蹤並整合新的資料來源、技術指標或演算法
　- [X] 系統效能優化：識別與改善瓶頸點
　- [X] 隨 n8n 平台與券商 API 更新進行相容性調整

---

**Phase 6: 優化與迭代**
[X] 6.1 效能分析與系統優化
　- [X] 收集與分析系統執行效能（I/O、記憶體、CPU、延遲）
　- [X] 識別瓶頸並優化資料流程與模組效能
　- [X] 優化模型推論速度與資源配置（如使用 ONNX、Batch Inference）

[X] 6.2 策略回測與動態調整
　- [X] 依據市場變化重新執行策略回測
　- [X] 根據績效結果微調參數與交易邏輯
　- [X] 記錄與版本化調整前後的比較與說明

[X] 6.3 錯誤處理與穩定性提升
　- [X] 彙整實測階段發生錯誤與異常事件
　- [X] 設計更完整的 fallback / retry 機制
　- [X] 增強模組間異常容忍與自我恢復能力
　- [X] 改善 log 與告警系統的即時性與可讀性

[X] 6.4 文件撰寫與最終交付準備 (README.md)
　- [X] 完成專案使用說明與安裝手冊
　- [X] 製作最終系統架構圖與部署拓撲圖
　- [X] 撰寫完整策略與模型說明書
　- [X] 整理版本歷程與變更紀錄（Changelog）

[X] 6.5 專案交付與驗收標準制定
　- [X] 定義各階段「完成標準」DoD（Definition of Done）
　　　- 例如：資料模組可穩定執行與測試、模型有明確輸出與效能指標
　　　- 例如：策略回測年化 Sharpe > 1.2，模型版本化已上線
　- [X] 定義整體專案的「驗收指標」Acceptance Criteria
　　　- 系統穩定運行 X 天無重大故障
　　　- 關鍵 API 延遲 < Y ms
　　　- 告警系統可在 Z 分鐘內發出異常通報
　　　- 技術文件完整度達標

[X] 6.6 測試與驗證流程完整化
　- [X] 執行單元測試、整合測試、E2E 測試
　- [X] 定期追蹤與提升測試覆蓋率
　- [X] 執行效能壓力測試，確保系統高載穩定

[X] 6.7 建立與執行 CI/CD 流程
　- [X] 建立自動化建置、測試流程
　- [X] 建立 staging / 模擬交易自動部署管線
　- [X] 安全推進至實盤部署流程並驗證 rollback 能力