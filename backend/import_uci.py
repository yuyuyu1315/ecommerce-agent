"""UCI Online Retail 真实数据集导入脚本（替代演示种子数据）

数据源: https://archive.ics.uci.edu/dataset/352/online+retail
- 541,909 条真实交易（英国在线零售，2010-12 ~ 2011-12）
- 本脚本: 清洗 → 聚合 → 抽样 Top-N 商品 → 映射写入项目数据库

透明标注原则（数据工程口径）：
- 真实字段：商品名、SKU、价格、销量、销售额、市场（来自数据集本身）
- 派生字段：分类（按商品名关键词归类）、竞品价（同分类价格带衍生）
- 估算字段：成本价（售价×0.6 行业毛利率口径）、库存（按月销量×15 天）、评分（默认 4.5）
- 缺失字段：用户评价（数据集无评价文本，reviews 表为空，明确标注）
"""
import asyncio
import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from backend.database import AsyncSessionLocal, close_database, init_database
from backend.models import (
    AgentTask,
    Campaign,
    CampaignProduct,
    Category,
    CompetitorPrice,
    KnowledgeBase,
    MarketingContent,
    PriceSuggestion,
    Product,
    ProductSelection,
    Review,
    User,
)

RAW_XLSX = Path(__file__).resolve().parent.parent / "data" / "raw_uci" / "Online Retail.xlsx"
TOP_N = 300          # 抽样商品数（按销售额 Top N）
COST_RATIO = 0.60    # 成本估算系数（行业平均毛利率口径，透明标注）
ORIGINAL_RATIO = 1.20  # 原价估算系数
STOCK_DAYS = 15      # 库存估算天数（月销量×天数）
DEFAULT_RATING = 4.5  # 数据集无评分字段，取平台典型默认值（透明标注）

# 用户密码哈希（复用 seed.py 演示账号）
DEMO_PWD = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.5L5t5O6Yu"

# ---------- 商品名关键词 → 分类 ----------
CATEGORY_RULES = [
    ("家居照明", ["LIGHT", "CANDLE", "LANTERN", "T-LIGHT", "BULB", "LAMP"]),
    ("厨具餐具", ["MUG", "CUP", "PLATE", "BOWL", "JAR", "TRAY", "DISH", "SPOON", "KNIFE", "CAKE", "BAKING"]),
    ("玩具礼品", ["TOY", "BABUSHKA", "DOLL", "PUZZLE", "BALL", "GAME", "GLIDER", "PLANE", "ORNAMENT", "PAINT"]),
    ("衣架收纳", ["HANGER", "BOX", "BASKET", "STORAGE", "RACK"]),
    ("杯壶水具", ["BOTTLE", "FLASK", "THERMOS", "GLASS"]),
    ("包袋配件", ["BAG", "WALLET", "PURSE", "BELT", "SCARF"]),
    ("节庆装饰", ["CHRISTMAS", "HEART", "LOVE", "PARTY", "BIRTHDAY", "WEDDING", "HALLOWEEN"]),
    ("文具贺卡", ["CARD", "PEN", "NOTE", "PAPER", "BOOK", "DIARY"]),
    ("家居杂货", []),  # 兜底
]


def classify(description: str) -> str:
    desc = (description or "").upper()
    for name, keywords in CATEGORY_RULES:
        if any(k in desc for k in keywords):
            return name
    return "家居杂货"


# ---------- 非商品 StockCode 前缀（退货/手续费/邮费等记录） ----------
NON_PRODUCT_PREFIX = ("BANK", "POST", "DOT", "M", "PADS", "C2", "DCGS", "GIFT", "AMAZON")


def load_and_aggregate():
    """读取 xlsx → 清洗 → 按商品聚合"""
    df = pd.read_excel(RAW_XLSX, dtype={"CustomerID": str})
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    # 清洗：剔除负数量（退货）、零价格、空描述、非商品记录
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df = df[df["Description"].notna() & (df["Description"].str.strip() != "")]
    df = df[~df["StockCode"].astype(str).str.upper().str.startswith(NON_PRODUCT_PREFIX)]

    # 覆盖月份数（用于月销量换算）
    span_days = (df["InvoiceDate"].max() - df["InvoiceDate"].min()).days
    months = max(1, math.ceil(span_days / 30))

    agg = (
        df.groupby(["StockCode", "Description"])
        .agg(
            total_qty=("Quantity", "sum"),
            revenue=("Quantity", "sum"),
            price=("UnitPrice", "median"),
            countries=("Country", lambda s: s.value_counts().index[0]),
            order_days=("InvoiceDate", "nunique"),
        )
        .reset_index()
    )
    # 排序取销售额 Top N（同 StockCode 可能对应多个描述，保留销售额最高的一条，避免 SKU 重复）
    agg = agg.sort_values("revenue", ascending=False).drop_duplicates("StockCode", keep="first")
    agg = agg.head(TOP_N).reset_index(drop=True)
    agg["sales_month"] = (agg["total_qty"] / months).round().astype(int)
    agg["category"] = agg["Description"].apply(classify)
    return agg, months


async def run():
    print(">>> 读取并聚合 UCI Online Retail ...")
    agg, months = load_and_aggregate()
    print(f"    聚合完成: Top {len(agg)} 商品, 数据覆盖 {months} 个月")

    # 删库重建
    await init_database()
    async with AsyncSessionLocal() as s:
        # 清空已有业务数据（避免与旧种子混合）
        for model in [Review, CompetitorPrice, Product, CampaignProduct, MarketingContent,
                      Campaign, KnowledgeBase, AgentTask, PriceSuggestion, ProductSelection,
                      User, Category]:
            await s.execute(model.__table__.delete())

        # ---------- 1. 用户（系统账号，业务配置） ----------
        users = [
            User(username="admin", email="admin@example.com", password_hash=DEMO_PWD,
                 full_name="系统管理员", role="admin", is_active=True, is_superuser=True),
            User(username="operator", email="operator@example.com", password_hash=DEMO_PWD,
                 full_name="运营专员", role="operator", is_active=True, is_superuser=False),
            User(username="analyst", email="analyst@example.com", password_hash=DEMO_PWD,
                 full_name="数据分析师", role="analyst", is_active=True, is_superuser=False),
        ]
        s.add_all(users)
        await s.flush()

        # ---------- 2. 分类 ----------
        cats = [Category(id=i + 1, name=name, parent_id=None, path=f"/{i+1}", level=1,
                         sort_order=i + 1, is_active=True)
                for i, (name, _) in enumerate(CATEGORY_RULES)]
        s.add_all(cats)
        await s.flush()
        cat_id = {c.name: c.id for c in cats}

        # ---------- 3. 产品（真实数据 + 透明标注的估算字段） ----------
        products = []
        for _, row in agg.iterrows():
            price = round(float(row["price"]), 2)
            products.append(Product(
                name=str(row["Description"]).strip()[:250],
                sku=str(row["StockCode"]),
                category_id=cat_id[row["category"]],
                cost_price=round(price * COST_RATIO, 2),          # 估算：行业毛利率口径
                current_price=price,                               # 真实：数据集价格
                original_price=round(price * ORIGINAL_RATIO, 2),   # 估算：原价口径
                stock_quantity=int(row["sales_month"] * STOCK_DAYS),  # 估算：库存≈月销×15天
                safety_stock=50,
                stock_status="normal",
                sales_month=int(row["sales_month"]),               # 真实：聚合月销量
                rating=DEFAULT_RATING,                             # 估算：无评分字段
                review_count=0,                                    # 真实：数据集无评价
                positive_rate=0,                                   # 真实：数据集无评价
                status="active",
                description=f"UCI Online Retail 真实商品 | 主市场: {row['countries']} | 总销量: {int(row['total_qty'])}",
            ))
        s.add_all(products)
        await s.flush()
        pid = [p.id for p in products]
        # 每分类价格带（用于竞品衍生）
        price_bands = {}
        for _, row in agg.iterrows():
            price_bands.setdefault(row["category"], []).append(float(row["price"]))
        price_band = {cat: sorted(v) for cat, v in price_bands.items()}

        # ---------- 4. 竞品价（同分类价格带衍生，透明标注） ----------
        import statistics
        competitors = []
        for p in products:
            band = price_band.get(p.category.name if p.category else "家居杂货", [])
            if len(band) < 3:
                band = price_band.get("家居杂货", band) or [p.current_price]
            p25, p50, p75 = (
                statistics.quantiles(band, n=4)[0] if len(band) >= 4 else band[0],
                statistics.median(band),
                statistics.quantiles(band, n=4)[2] if len(band) >= 4 else band[-1],
            )
            for name, price, idx in [("同分类价格带-P25", p25, 1), ("同分类价格带-P50", p50, 2), ("同分类价格带-P75", p75, 3)]:
                competitors.append(CompetitorPrice(
                    product_id=p.id, competitor_name=name,
                    competitor_sku=f"{p.sku}-C{idx}", product_name=p.name,
                    price=round(price, 2), original_price=round(price, 2),
                    stock_status="有货", platform="Market（衍生）",
                ))
        s.add_all(competitors)

        # ---------- 5. 营销活动（业务配置，复用种子口径） ----------
        campaigns = [
            Campaign(name="春季焕新季", campaign_type="discount", description="春季新品促销活动，全场满减",
                     goal="conversion", discount_type="amount", discount_value=30.00,
                     start_date=date(2026, 4, 1), end_date=date(2026, 4, 30),
                     budget=50000.00, status="active", created_by=1),
            Campaign(name="会员日特惠", campaign_type="member", description="会员专属优惠，积分翻倍",
                     goal="retention", discount_type="percent", discount_value=15.00,
                     start_date=date(2026, 4, 15), end_date=date(2026, 4, 17),
                     budget=20000.00, status="active", created_by=1),
            Campaign(name="新品首发", campaign_type="launch", description="新品首发限时折扣",
                     goal="awareness", discount_type="percent", discount_value=20.00,
                     start_date=date(2026, 4, 20), end_date=date(2026, 4, 25),
                     budget=30000.00, status="draft", created_by=2),
        ]
        s.add_all(campaigns)
        await s.flush()
        cid = {c.name: c.id for c in campaigns}
        # 活动商品：关联 Top 商品中评分最高的 6 个（按销售额）
        top_products = sorted(products, key=lambda p: p.sales_month, reverse=True)[:6]
        s.add_all([
            CampaignProduct(campaign_id=cid["春季焕新季"], product_id=top_products[0].id, priority=1, is_featured=True),
            CampaignProduct(campaign_id=cid["春季焕新季"], product_id=top_products[1].id, priority=2),
            CampaignProduct(campaign_id=cid["春季焕新季"], product_id=top_products[2].id, priority=3),
            CampaignProduct(campaign_id=cid["会员日特惠"], product_id=top_products[0].id, custom_discount=20.00, priority=1, is_featured=True),
            CampaignProduct(campaign_id=cid["会员日特惠"], product_id=top_products[3].id, priority=2),
            CampaignProduct(campaign_id=cid["新品首发"], product_id=top_products[4].id, priority=1, is_featured=True),
        ])

        # ---------- 6. 营销内容（业务配置） ----------
        s.add_all([
            MarketingContent(campaign_id=cid["春季焕新季"], content_type="banner", platform="all", tone="活泼",
                             title="春季焕新季", content="春季焕新季来啦！全场满减，精选好物抢先购～",
                             keywords=["春季", "焕新", "满减"]),
            MarketingContent(campaign_id=cid["春季焕新季"], content_type="social_post", platform="wechat", tone="亲切",
                             title="春日好物推荐", content="【春日好物推荐】精选热销单品，品质与性价比兼得！",
                             keywords=["好物", "热销", "春季"]),
            MarketingContent(campaign_id=cid["会员日特惠"], content_type="push", platform="app", tone="简洁",
                             title="会员日提醒", content="【会员专属】今日会员日，精选好货低至85折，仅限3天！",
                             keywords=["会员", "折扣"]),
            MarketingContent(campaign_id=cid["会员日特惠"], content_type="email", platform="email", tone="正式",
                             title="会员日专属邀请", content="尊敬的会员：会员日专属优惠已上线，精选商品低至85折，欢迎选购。",
                             keywords=["会员专属", "折扣"]),
        ])

        # ---------- 7. 知识库（业务配置，供 RAG 检索） ----------
        s.add_all([
            KnowledgeBase(category="选品策略", title="选品评估框架",
                          content="## 选品核心评估维度\n\n### 1. 需求强度\n看品类销量规模与增长趋势。\n\n### 2. 利润空间\n售价与成本之间的毛利是否足够。\n\n### 3. 竞争格局\n同分类价格带分布与价格中位数。\n\n### 4. 市场特征\n主销市场与客群分布。",
                          summary="选品需综合需求、利润、竞争、市场四维评估", tags='["选品","策略","利润"]',
                          source="UCI 数据集分析", author="运营团队"),
            KnowledgeBase(category="定价策略", title="定价决策框架",
                          content="## 定价方法\n\n### 成本加成法\n售价 = 成本 × (1 + 目标利润率)\n\n### 竞争导向法\n参考同分类价格带（P25/P50/P75）定价\n\n### 需求导向法\n按销量与价格关系动态调整",
                          summary="定价需结合成本、竞争与需求", tags='["定价","竞争","成本"]',
                          source="UCI 数据集分析", author="运营团队"),
            KnowledgeBase(category="营销策划", title="活动策划流程",
                          content="## 活动策划步骤\n\n### 1. 明确目标\n拉新/促活/转化/品牌\n\n### 2. 选择形式\n满减、折扣、限时特惠\n\n### 3. 制定节奏\n预热期-爆发期-返场期\n\n### 4. 效果复盘\n指标达成、用户反馈、经验总结",
                          summary="活动策划需目标-形式-节奏-复盘闭环", tags='["营销","活动","复盘"]',
                          source="运营手册", author="运营团队"),
            KnowledgeBase(category="数据分析", title="电商数据分析方法",
                          content="## 常用分析维度\n\n### 销售分析\n销量、销售额、价格带分布、趋势\n\n### 商品分析\nTop 商品、长尾商品、滞销品\n\n### 市场分析\n国家/地区销售分布与差异",
                          summary="用数据驱动选品、定价、营销决策", tags='["数据分析","销售","市场"]',
                          source="UCI 数据集分析", author="分析师团队"),
        ])

        await s.commit()
        print(f">>> 导入完成：{len(products)} 商品 / {len(cats)} 分类 / {len(competitors)} 竞品价 / "
              f"{len(campaigns)} 活动 / 4 营销内容 / 4 知识库 / {len(users)} 用户 / 0 评价（数据集无评价字段）")
        print(">>> 数据口径：真实=商品/价格/销量/市场；派生=分类/竞品；估算=成本/库存/评分（均透明标注）")
    await close_database()


if __name__ == "__main__":
    asyncio.run(run())
