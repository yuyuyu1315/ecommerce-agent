-- 源：飞书知识库《Agent项目-电商运营Agent》4.1 节（PostgreSQL 15）
SQL
-- ============================================================
-- 电商运营 Agent 数据库初始化脚本
-- 数据库: PostgreSQL 15+
-- 创建时间: 2026-04-15
-- ============================================================

-- 创建数据库（需要超级用户权限）
-- CREATE DATABASE ecommerce_agent ENCODING 'UTF8';

-- 连接到数据库
-- \c ecommerce_agent;

-- ============================================================
-- 1. 用户与权限表
-- ============================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'operator',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    module VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_logs_user ON operation_logs(user_id);
CREATE INDEX idx_logs_module ON operation_logs(module);
CREATE INDEX idx_logs_created ON operation_logs(created_at);

-- ============================================================
-- 2. 产品分类表
-- ============================================================

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    path VARCHAR(500),
    level INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    icon_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_categories_name_parent UNIQUE (name, parent_id)
);

-- 索引
CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_path ON categories(path);
CREATE INDEX idx_categories_active ON categories(is_active);

-- ============================================================
-- 3. 产品表
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    
    -- 价格信息
    cost_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    current_price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2),
    target_price DECIMAL(10, 2),
    min_price DECIMAL(10, 2),
    max_price DECIMAL(10, 2),
    
    -- 库存信息
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    safety_stock INTEGER DEFAULT 10,
    stock_status VARCHAR(20) DEFAULT 'normal',
    
    -- 销售信息
    sales_month INTEGER DEFAULT 0,
    sales_quarter INTEGER DEFAULT 0,
    sales_year INTEGER DEFAULT 0,
    
    -- 评价信息
    rating DECIMAL(3, 2) DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    positive_rate DECIMAL(5, 2) DEFAULT 0,
    
    -- 产品属性
    status VARCHAR(20) DEFAULT 'active',
    image_url VARCHAR(500),
    detail_url VARCHAR(500),
    description TEXT,
    attributes JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_name ON products USING gin(to_tsvector('simple', name));
CREATE INDEX idx_products_price ON products(current_price);
CREATE INDEX idx_products_sales ON products(sales_month DESC);

-- ============================================================
-- 4. 价格历史表
-- ============================================================

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    old_price DECIMAL(10, 2),
    new_price DECIMAL(10, 2) NOT NULL,
    cost_price DECIMAL(10, 2),
    change_type VARCHAR(20) NOT NULL,
    change_reason TEXT,
    margin_percent DECIMAL(5, 2),
    changed_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_price_history_product ON price_history(product_id);
CREATE INDEX idx_price_history_created ON price_history(created_at DESC);

-- ============================================================
-- 5. 竞品价格表
-- ============================================================

CREATE TABLE IF NOT EXISTS competitor_prices (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    competitor_name VARCHAR(100) NOT NULL,
    competitor_sku VARCHAR(100),
    product_name VARCHAR(255),
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2),
    discount_percent DECIMAL(5, 2),
    product_url VARCHAR(500),
    image_url VARCHAR(500),
    stock_status VARCHAR(20),
    platform VARCHAR(50),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_competitor_product ON competitor_prices(product_id);
CREATE INDEX idx_competitor_name ON competitor_prices(competitor_name);
CREATE INDEX idx_competitor_fetched ON competitor_prices(fetched_at DESC);

-- ============================================================
-- 6. 用户评价表
-- ============================================================

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    external_id VARCHAR(100),
    user_name VARCHAR(100),
    user_level VARCHAR(50),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    content TEXT,
    sentiment VARCHAR(20),
    keywords TEXT[],
    keywords_extracted JSONB,
    is_verified BOOLEAN DEFAULT false,
    helpful_count INTEGER DEFAULT 0,
    reply_content TEXT,
    review_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_platform ON reviews(platform);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_reviews_sentiment ON reviews(sentiment);
CREATE INDEX idx_reviews_created ON reviews(created_at DESC);
CREATE INDEX idx_reviews_content ON reviews USING gin(to_tsvector('simple', content));

-- ============================================================
-- 7. 选品记录表
-- ============================================================

CREATE TABLE IF NOT EXISTS product_selections (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    
    -- 分析结果
    selection_reason TEXT NOT NULL,
    confidence_score DECIMAL(3, 2) DEFAULT 0,
    estimated_margin DECIMAL(5, 2),
    estimated_sales INTEGER,
    estimated_revenue DECIMAL(12, 2),
    
    -- 风险评估
    risk_level VARCHAR(20),
    risk_factors JSONB,
    opportunity_factors JSONB,
    
    -- 状态与审核
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    tags TEXT[],
    
    -- 审核信息
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- 执行信息
    executed BOOLEAN DEFAULT false,
    executed_at TIMESTAMP WITH TIME ZONE,
    actual_sales INTEGER,
    actual_revenue DECIMAL(12, 2),
    
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_selections_product ON product_selections(product_id);
CREATE INDEX idx_selections_status ON product_selections(status);
CREATE INDEX idx_selections_category ON product_selections(category);
CREATE INDEX idx_selections_score ON product_selections(confidence_score DESC);
CREATE INDEX idx_selections_created ON product_selections(created_at DESC);

-- ============================================================
-- 8. 营销活动表
-- ============================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    campaign_type VARCHAR(50) NOT NULL,
    description TEXT,
    
    -- 目标与策略
    goal VARCHAR(50),
    target_audience TEXT,
    strategy_summary TEXT,
    
    -- 折扣设置
    discount_type VARCHAR(20),
    discount_value DECIMAL(10, 2),
    min_order_amount DECIMAL(10, 2),
    max_discount DECIMAL(10, 2),
    
    -- 时间设置
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- 预算与效果
    budget DECIMAL(12, 2),
    actual_spend DECIMAL(12, 2),
    expected_roi DECIMAL(5, 2),
    actual_roi DECIMAL(5, 2),
    expected_revenue DECIMAL(12, 2),
    actual_revenue DECIMAL(12, 2),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'draft',
    
    -- 创建信息
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_campaigns_type ON campaigns(campaign_type);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_dates ON campaigns(start_date, end_date);
CREATE INDEX idx_campaigns_created ON campaigns(created_at DESC);

-- ============================================================
-- 9. 活动产品关联表
-- ============================================================

CREATE TABLE IF NOT EXISTS campaign_products (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    custom_discount DECIMAL(10, 2),
    discount_percent DECIMAL(5, 2),
    priority INTEGER DEFAULT 1,
    is_featured BOOLEAN DEFAULT false,
    expected_sales INTEGER,
    actual_sales INTEGER,
    
    CONSTRAINT uk_campaign_product UNIQUE (campaign_id, product_id)
);

-- 索引
CREATE INDEX idx_campaign_products_campaign ON campaign_products(campaign_id);
CREATE INDEX idx_campaign_products_product ON campaign_products(product_id);

-- ============================================================
-- 10. 营销内容表
-- ============================================================

CREATE TABLE IF NOT EXISTS marketing_contents (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    content_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50),
    tone VARCHAR(50),
    title VARCHAR(255),
    content TEXT NOT NULL,
    variant VARCHAR(10),
    keywords JSONB,
    hashtags TEXT[],
    media_urls JSONB,
    
    -- A/B 测试
    ab_test_id INTEGER,
    ab_variant VARCHAR(10),
    
    -- 效果指标
    metrics JSONB,
    
    created_by VARCHAR(100) DEFAULT 'AI',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_marketing_campaign ON marketing_contents(campaign_id);
CREATE INDEX idx_marketing_type ON marketing_contents(content_type);
CREATE INDEX idx_marketing_platform ON marketing_contents(platform);

-- ============================================================
-- 11. 知识库表
-- ============================================================

CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    tags TEXT[],
    source VARCHAR(255),
    author VARCHAR(100),
    
    -- 向量存储信息
    embedding_id VARCHAR(100),
    embedding_model VARCHAR(100),
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    view_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_knowledge_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_tags ON knowledge_base USING gin(tags);
CREATE INDEX idx_knowledge_active ON knowledge_base(is_active);
CREATE INDEX idx_knowledge_embedding ON knowledge_base(embedding_id);
CREATE INDEX idx_knowledge_search ON knowledge_base USING gin(to_tsvector('simple', title || ' ' || content));

-- ============================================================
-- 12. Agent 任务记录表
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    
    -- 输入输出
    input_data JSONB NOT NULL,
    output_data JSONB,
    error_message TEXT,
    
    -- 执行状态
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    
    -- 性能指标
    tokens_used INTEGER,
    duration_ms INTEGER,
    cost_amount DECIMAL(10, 4),
    
    -- 关联信息
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_agent_tasks_type ON agent_tasks(task_type);
CREATE INDEX idx_agent_tasks_agent ON agent_tasks(agent_name);
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX idx_agent_tasks_user ON agent_tasks(user_id);
CREATE INDEX idx_agent_tasks_created ON agent_tasks(created_at DESC);

-- ============================================================
-- 13. 触发器：自动更新时间戳
-- ============================================================

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 应用触发器
CREATE TRIGGER trigger_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_categories_updated
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_products_updated
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_selections_updated
    BEFORE UPDATE ON product_selections
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_campaigns_updated
    BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_knowledge_updated
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================
-- 14. 触发器：自动更新产品统计
-- ============================================================

CREATE OR REPLACE FUNCTION update_product_stats()
RETURNS TRIGGER AS $$
DECLARE
    avg_rating DECIMAL(3, 2);
    total_reviews INTEGER;
    pos_rate DECIMAL(5, 2);
BEGIN
    -- 计算平均评分
    SELECT 
        COALESCE(AVG(rating), 0),
        COUNT(*),
        COALESCE(100.0 * SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 0)
    INTO avg_rating, total_reviews, pos_rate
    FROM reviews
    WHERE product_id = COALESCE(NEW.product_id, OLD.product_id);
    
    -- 更新产品表
    UPDATE products
    SET 
        rating = avg_rating,
        review_count = total_reviews,
        positive_rate = pos_rate,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.product_id, OLD.product_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_product_stats
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_product_stats();

-- ============================================================
-- 15. 视图：产品摘要视图
-- ============================================================

CREATE OR REPLACE VIEW v_product_summary AS
SELECT 
    p.id,
    p.name,
    p.sku,
    c.name AS category_name,
    p.current_price,
    p.cost_price,
    ROUND((p.current_price - p.cost_price) / NULLIF(p.current_price, 0) * 100, 2) AS margin_percent,
    p.stock_quantity,
    p.sales_month,
    p.rating,
    p.review_count,
    p.positive_rate,
    p.status,
    -- 竞品价格统计
    cp.avg_competitor_price,
    cp.min_competitor_price,
    cp.max_competitor_price,
    cp.competitor_count,
    -- 价格对比
    CASE 
        WHEN cp.avg_competitor_price IS NULL THEN NULL
        ELSE ROUND((p.current_price - cp.avg_competitor_price) / cp.avg_competitor_price * 100, 2)
    END AS price_diff_percent,
    p.created_at,
    p.updated_at
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN (
    SELECT 
        product_id,
        AVG(price) AS avg_competitor_price,
        MIN(price) AS min_competitor_price,
        MAX(price) AS max_competitor_price,
        COUNT(*) AS competitor_count
    FROM competitor_prices
    WHERE fetched_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
    GROUP BY product_id
) cp ON p.id = cp.product_id;

-- ============================================================
-- 16. 视图：活动效果视图
-- ============================================================

CREATE OR REPLACE VIEW v_campaign_performance AS
SELECT 
    c.id,
    c.name,
    c.campaign_type,
    c.start_date,
    c.end_date,
    c.status,
    c.budget,
    c.actual_spend,
    c.expected_roi,
    c.actual_roi,
    -- 产品统计
    COALESCE(cp.product_count, 0) AS product_count,
    COALESCE(cp.total_expected_sales, 0) AS expected_sales,
    COALESCE(cp.total_actual_sales, 0) AS actual_sales,
    -- 内容统计
    COALESCE(mc.content_count, 0) AS content_count,
    c.created_at
FROM campaigns c
LEFT JOIN (
    SELECT 
        campaign_id,
        COUNT(*) AS product_count,
        SUM(COALESCE(expected_sales, 0)) AS total_expected_sales,
        SUM(COALESCE(actual_sales, 0)) AS total_actual_sales
    FROM campaign_products
    GROUP BY campaign_id
) cp ON c.id = cp.campaign_id
LEFT JOIN (
    SELECT 
        campaign_id,
        COUNT(*) AS content_count
    FROM marketing_contents
    GROUP BY campaign_id
) mc ON c.id = mc.campaign_id;

-- ============================================================
-- 完成
-- ============================================================
