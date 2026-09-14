-- ============================================================
-- 电商运营 Agent 数据库初始化脚本（SQLite 本地版）
-- 对应 PostgreSQL 原版：sql/init_database.sql（部署 Docker 时使用）
-- 差异说明：
--   * SERIAL → INTEGER PRIMARY KEY AUTOINCREMENT
--   * JSONB/TEXT[] → TEXT（存 JSON 字符串）
--   * TIMESTAMP WITH TIME ZONE → TEXT
--   * GIN 全文索引 / 触发器 / 视图为 PostgreSQL 特性，本地版暂不含
--     （updated_at 由应用层 SQLAlchemy onupdate 维护）
-- ============================================================

-- ============================================================
-- 1. 用户与权限表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'operator',
    is_active INTEGER NOT NULL DEFAULT 1,
    is_superuser INTEGER NOT NULL DEFAULT 0,
    last_login TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL UNIQUE,
    ip_address TEXT,
    user_agent TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    module TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    details TEXT,
    ip_address TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_logs_user ON operation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_module ON operation_logs(module);
CREATE INDEX IF NOT EXISTS idx_logs_created ON operation_logs(created_at);

-- ============================================================
-- 2. 产品分类表
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    path TEXT,
    level INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    icon_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_categories_name_parent UNIQUE (name, parent_id)
);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_path ON categories(path);
CREATE INDEX IF NOT EXISTS idx_categories_active ON categories(is_active);

-- ============================================================
-- 3. 产品表
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    cost_price NUMERIC NOT NULL DEFAULT 0,
    current_price NUMERIC NOT NULL,
    original_price NUMERIC,
    target_price NUMERIC,
    min_price NUMERIC,
    max_price NUMERIC,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    safety_stock INTEGER DEFAULT 10,
    stock_status TEXT DEFAULT 'normal',
    sales_month INTEGER DEFAULT 0,
    sales_quarter INTEGER DEFAULT 0,
    sales_year INTEGER DEFAULT 0,
    rating NUMERIC DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    positive_rate NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'active',
    image_url TEXT,
    detail_url TEXT,
    description TEXT,
    attributes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(current_price);
CREATE INDEX IF NOT EXISTS idx_products_sales ON products(sales_month DESC);

-- ============================================================
-- 4. 价格历史表
-- ============================================================
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    old_price NUMERIC,
    new_price NUMERIC NOT NULL,
    cost_price NUMERIC,
    change_type TEXT NOT NULL,
    change_reason TEXT,
    margin_percent NUMERIC,
    changed_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_created ON price_history(created_at DESC);

-- ============================================================
-- 5. 竞品价格表
-- ============================================================
CREATE TABLE IF NOT EXISTS competitor_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    competitor_name TEXT NOT NULL,
    competitor_sku TEXT,
    product_name TEXT,
    price NUMERIC NOT NULL,
    original_price NUMERIC,
    discount_percent NUMERIC,
    product_url TEXT,
    image_url TEXT,
    stock_status TEXT,
    platform TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_competitor_product ON competitor_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_competitor_name ON competitor_prices(competitor_name);
CREATE INDEX IF NOT EXISTS idx_competitor_fetched ON competitor_prices(fetched_at DESC);

-- ============================================================
-- 6. 用户评价表
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    external_id TEXT,
    user_name TEXT,
    user_level TEXT,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title TEXT,
    content TEXT,
    sentiment TEXT,
    keywords TEXT,
    keywords_extracted TEXT,
    is_verified INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    reply_content TEXT,
    review_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_platform ON reviews(platform);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews(sentiment);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);

-- ============================================================
-- 7. 选品记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS product_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    selection_reason TEXT NOT NULL,
    confidence_score NUMERIC DEFAULT 0,
    estimated_margin NUMERIC,
    estimated_sales INTEGER,
    estimated_revenue NUMERIC,
    risk_level TEXT,
    risk_factors TEXT,
    opportunity_factors TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    tags TEXT,
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at TEXT,
    executed INTEGER DEFAULT 0,
    executed_at TEXT,
    actual_sales INTEGER,
    actual_revenue NUMERIC,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_selections_product ON product_selections(product_id);
CREATE INDEX IF NOT EXISTS idx_selections_status ON product_selections(status);
CREATE INDEX IF NOT EXISTS idx_selections_category ON product_selections(category);
CREATE INDEX IF NOT EXISTS idx_selections_score ON product_selections(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_selections_created ON product_selections(created_at DESC);

-- ============================================================
-- 8. 营销活动表
-- ============================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    description TEXT,
    goal TEXT,
    target_audience TEXT,
    strategy_summary TEXT,
    discount_type TEXT,
    discount_value NUMERIC,
    min_order_amount NUMERIC,
    max_discount NUMERIC,
    start_date TEXT NOT NULL,
    end_date TEXT,
    budget NUMERIC,
    actual_spend NUMERIC,
    expected_roi NUMERIC,
    actual_roi NUMERIC,
    expected_revenue NUMERIC,
    actual_revenue NUMERIC,
    status TEXT DEFAULT 'draft',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaigns_type ON campaigns(campaign_type);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_created ON campaigns(created_at DESC);

-- ============================================================
-- 9. 活动产品关联表
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    custom_discount NUMERIC,
    discount_percent NUMERIC,
    priority INTEGER DEFAULT 1,
    is_featured INTEGER DEFAULT 0,
    expected_sales INTEGER,
    actual_sales INTEGER,
    CONSTRAINT uk_campaign_product UNIQUE (campaign_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_campaign_products_campaign ON campaign_products(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_products_product ON campaign_products(product_id);

-- ============================================================
-- 10. 营销内容表
-- ============================================================
CREATE TABLE IF NOT EXISTS marketing_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    content_type TEXT NOT NULL,
    platform TEXT,
    tone TEXT,
    title TEXT,
    content TEXT NOT NULL,
    variant TEXT,
    keywords TEXT,
    hashtags TEXT,
    media_urls TEXT,
    ab_test_id INTEGER,
    ab_variant TEXT,
    metrics TEXT,
    created_by TEXT DEFAULT 'AI',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_marketing_campaign ON marketing_contents(campaign_id);
CREATE INDEX IF NOT EXISTS idx_marketing_type ON marketing_contents(content_type);
CREATE INDEX IF NOT EXISTS idx_marketing_platform ON marketing_contents(platform);

-- ============================================================
-- 11. 知识库表
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    tags TEXT,
    source TEXT,
    author TEXT,
    embedding_id TEXT,
    embedding_model TEXT,
    is_active INTEGER DEFAULT 1,
    view_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_active ON knowledge_base(is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_base(embedding_id);

-- ============================================================
-- 12. Agent 任务记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    input_data TEXT NOT NULL,
    output_data TEXT,
    error_message TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    tokens_used INTEGER,
    duration_ms INTEGER,
    cost_amount NUMERIC,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_type ON agent_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON agent_tasks(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_user ON agent_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_created ON agent_tasks(created_at DESC);

-- ============================================================
-- 完成（触发器/视图/种子数据：见 seed_data.sql 与 PostgreSQL 原版）
-- ============================================================
