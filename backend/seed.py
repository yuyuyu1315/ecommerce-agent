"""种子数据（对应文档 sql/seed_data.sql 的落地版，通过 SQLAlchemy 写入 SQLite）"""
import asyncio
from datetime import date, datetime, timezone
from pathlib import Path

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
    Product,
    ProductSelection,
    Review,
    User,
)

# 文档 seed_data.sql 中复用的密码哈希（演示用）
DEMO_PWD = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.5L5t5O6Yu"


async def _count(session, model) -> int:
    return (await session.scalar(select(func.count()).select_from(model))) or 0


async def seed():
    await init_database()
    async with AsyncSessionLocal() as s:
        if await _count(s, User) > 0:
            print("⚠️ 已有数据，跳过种子导入（如需重灌请删除 data/ecommerce.db）")
            return

        # ---------- 1. 用户 ----------
        s.add_all([
            User(username="admin", email="admin@example.com", password_hash=DEMO_PWD,
                 full_name="系统管理员", role="admin", is_active=True, is_superuser=True),
            User(username="operator", email="operator@example.com", password_hash=DEMO_PWD,
                 full_name="运营专员", role="operator", is_active=True, is_superuser=False),
            User(username="analyst", email="analyst@example.com", password_hash=DEMO_PWD,
                 full_name="数据分析师", role="analyst", is_active=True, is_superuser=False),
        ])
        await s.flush()

        # ---------- 2. 分类 ----------
        s.add_all([
            Category(id=1, name="女装", parent_id=None, path="/1", level=1, sort_order=1, is_active=True),
            Category(id=2, name="男装", parent_id=None, path="/2", level=1, sort_order=2, is_active=True),
            Category(id=3, name="数码", parent_id=None, path="/3", level=1, sort_order=3, is_active=True),
            Category(id=4, name="美妆", parent_id=None, path="/4", level=1, sort_order=4, is_active=True),
            Category(id=5, name="家居", parent_id=None, path="/5", level=1, sort_order=5, is_active=True),
            Category(id=11, name="连衣裙", parent_id=1, path="/1/11", level=2, sort_order=1, is_active=True),
            Category(id=12, name="T恤", parent_id=1, path="/1/12", level=2, sort_order=2, is_active=True),
            Category(id=13, name="牛仔裤", parent_id=1, path="/1/13", level=2, sort_order=3, is_active=True),
            Category(id=14, name="外套", parent_id=1, path="/1/14", level=2, sort_order=4, is_active=True),
            Category(id=31, name="手机配件", parent_id=3, path="/3/31", level=2, sort_order=1, is_active=True),
            Category(id=32, name="智能穿戴", parent_id=3, path="/3/32", level=2, sort_order=2, is_active=True),
            Category(id=33, name="耳机音箱", parent_id=3, path="/3/33", level=2, sort_order=3, is_active=True),
        ])

        # ---------- 3. 产品 ----------
        products = [
            Product(name="法式复古碎花连衣裙女夏", sku="DRESS001", category_id=11, cost_price=85.00,
                    current_price=189.00, original_price=259.00, stock_quantity=156, safety_stock=50,
                    sales_month=423, rating=4.8, review_count=286, positive_rate=92.5, status="active"),
            Product(name="气质收腰显瘦连衣裙", sku="DRESS002", category_id=11, cost_price=92.00,
                    current_price=219.00, original_price=299.00, stock_quantity=89, safety_stock=50,
                    sales_month=267, rating=4.7, review_count=198, positive_rate=89.4, status="active"),
            Product(name="小清新碎花半身裙", sku="DRESS003", category_id=11, cost_price=58.00,
                    current_price=129.00, original_price=169.00, stock_quantity=234, safety_stock=50,
                    sales_month=512, rating=4.9, review_count=342, positive_rate=95.2, status="active"),
            Product(name="纯棉宽松短袖T恤女", sku="TSHIRT001", category_id=12, cost_price=35.00,
                    current_price=79.00, original_price=99.00, stock_quantity=445, safety_stock=100,
                    sales_month=892, rating=4.6, review_count=567, positive_rate=88.3, status="active"),
            Product(name="卡通印花圆领T恤", sku="TSHIRT002", category_id=12, cost_price=28.00,
                    current_price=59.00, original_price=79.00, stock_quantity=312, safety_stock=100,
                    sales_month=678, rating=4.5, review_count=423, positive_rate=86.7, status="active"),
            Product(name="蓝牙耳机无线入耳式", sku="DIGITAL001", category_id=33, cost_price=65.00,
                    current_price=159.00, original_price=199.00, stock_quantity=267, safety_stock=80,
                    sales_month=534, rating=4.7, review_count=389, positive_rate=91.2, status="active"),
            Product(name="智能手表运动手环", sku="DIGITAL002", category_id=32, cost_price=120.00,
                    current_price=299.00, original_price=399.00, stock_quantity=89, safety_stock=60,
                    sales_month=234, rating=4.6, review_count=156, positive_rate=87.8, status="active"),
            Product(name="快充数据线三合一", sku="DIGITAL003", category_id=31, cost_price=12.00,
                    current_price=29.90, original_price=39.90, stock_quantity=1024, safety_stock=200,
                    sales_month=2156, rating=4.4, review_count=1024, positive_rate=84.5, status="active"),
        ]
        s.add_all(products)
        await s.flush()
        pid = {p.sku: p.id for p in products}

        # ---------- 4. 竞品价格 ----------
        s.add_all([
            CompetitorPrice(product_id=pid["DRESS001"], competitor_name="淘宝旗舰店A", competitor_sku="TB-DRESS001",
                            product_name="法式复古碎花连衣裙", price=179.00, original_price=239.00, platform="淘宝", stock_status="有货"),
            CompetitorPrice(product_id=pid["DRESS001"], competitor_name="京东自营B", competitor_sku="JD-DRESS001",
                            product_name="法式复古碎花连衣裙", price=199.00, original_price=259.00, platform="京东", stock_status="有货"),
            CompetitorPrice(product_id=pid["DRESS001"], competitor_name="拼多多店铺C", competitor_sku="PDD-DRESS001",
                            product_name="法式复古碎花连衣裙", price=159.00, original_price=199.00, platform="拼多多", stock_status="有货"),
            CompetitorPrice(product_id=pid["TSHIRT001"], competitor_name="淘宝旗舰店A", competitor_sku="TB-TSHIRT001",
                            product_name="纯棉宽松短袖T恤", price=75.00, original_price=95.00, platform="淘宝", stock_status="有货"),
            CompetitorPrice(product_id=pid["TSHIRT001"], competitor_name="京东自营B", competitor_sku="JD-TSHIRT001",
                            product_name="纯棉宽松短袖T恤", price=85.00, original_price=99.00, platform="京东", stock_status="有货"),
            CompetitorPrice(product_id=pid["DIGITAL001"], competitor_name="京东自营B", competitor_sku="JD-BT001",
                            product_name="蓝牙耳机无线入耳式", price=169.00, original_price=199.00, platform="京东", stock_status="有货"),
            CompetitorPrice(product_id=pid["DIGITAL001"], competitor_name="天猫旗舰店D", competitor_sku="TM-BT001",
                            product_name="蓝牙耳机无线入耳式", price=149.00, original_price=189.00, platform="天猫", stock_status="有货"),
            CompetitorPrice(product_id=pid["DIGITAL002"], competitor_name="京东自营B", competitor_sku="JD-WATCH001",
                            product_name="智能手表运动手环", price=279.00, original_price=359.00, platform="京东", stock_status="有货"),
            CompetitorPrice(product_id=pid["DIGITAL002"], competitor_name="拼多多店铺C", competitor_sku="PDD-WATCH001",
                            product_name="智能手表运动手环", price=259.00, original_price=329.00, platform="拼多多", stock_status="有货"),
        ])

        # ---------- 5. 用户评价 ----------
        s.add_all([
            Review(product_id=pid["DRESS001"], platform="淘宝", user_name="小*花", rating=5, title="超喜欢！",
                   content="质量很好，面料舒适，穿上显瘦，颜色和图片一样，很满意的一次购物！",
                   sentiment="positive", keywords=["质量好", "显瘦", "颜色正"]),
            Review(product_id=pid["DRESS001"], platform="淘宝", user_name="甜*蜜", rating=4, title="总体满意",
                   content="款式好看，就是稍微有点大，可能我比较瘦。物流很快。",
                   sentiment="positive", keywords=["款式好", "物流快"]),
            Review(product_id=pid["DRESS001"], platform="淘宝", user_name="阳*光", rating=5, title="推荐购买",
                   content="第二次购买了，这次给闺蜜也买了一件，她也很喜欢！",
                   sentiment="positive", keywords=["回购", "推荐"]),
            Review(product_id=pid["TSHIRT001"], platform="京东", user_name="清*风", rating=5, title="质量不错",
                   content="纯棉面料，穿着舒服，洗涤后不变形。性价比很高！",
                   sentiment="positive", keywords=["纯棉", "性价比高"]),
            Review(product_id=pid["TSHIRT001"], platform="淘宝", user_name="月*亮", rating=3, title="一般般",
                   content="面料还可以，但是颜色比图片深一些，有点失望。",
                   sentiment="neutral", keywords=["色差"]),
            Review(product_id=pid["DIGITAL001"], platform="京东", user_name="科*技", rating=5, title="音质很好",
                   content="蓝牙连接稳定，音质清晰，续航时间长，值得推荐！",
                   sentiment="positive", keywords=["音质好", "续航长"]),
            Review(product_id=pid["DIGITAL001"], platform="淘宝", user_name="电*子", rating=4, title="性价比高",
                   content="这个价位能有这种音质很不错了，就是降噪效果一般。",
                   sentiment="positive", keywords=["性价比", "降噪一般"]),
            Review(product_id=pid["DIGITAL002"], platform="京东", user_name="运*动", rating=4, title="功能齐全",
                   content="运动记录准确，心率监测也不错，就是屏幕有点小。",
                   sentiment="positive", keywords=["功能全", "屏幕小"]),
        ])

        # ---------- 6. 选品记录 ----------
        s.add_all([
            ProductSelection(product_id=pid["DRESS001"], product_name="法式复古碎花连衣裙女夏", category="女装/连衣裙",
                             selection_reason="市场需求旺盛，搜索热度上升；竞品定价合理，利润空间充足；用户评价正面率达92%，复购意愿强",
                             confidence_score=0.87, estimated_margin=55.0, estimated_sales=500,
                             risk_level="low", status="approved", created_by=2),
            ProductSelection(product_id=pid["DIGITAL001"], product_name="蓝牙耳机无线入耳式", category="数码/耳机音箱",
                             selection_reason="品类增长迅速，年轻用户接受度高；竞品价格区间稳定，差异化竞争机会存在",
                             confidence_score=0.82, estimated_margin=58.5, estimated_sales=350,
                             risk_level="medium", status="pending", created_by=2),
            ProductSelection(product_id=pid["DIGITAL002"], product_name="智能手表运动手环", category="数码/智能穿戴",
                             selection_reason="健康监测趋势明显，市场需求增长；但竞争激烈，需要差异化策略",
                             confidence_score=0.75, estimated_margin=59.8, estimated_sales=200,
                             risk_level="high", status="pending", created_by=2),
        ])

        # ---------- 7. 营销活动 ----------
        s.add_all([
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
        ])
        await s.flush()

        campaigns = {c.name: c.id for c in (await s.execute(select(Campaign))).scalars()}
        s.add_all([
            CampaignProduct(campaign_id=campaigns["春季焕新季"], product_id=pid["DRESS001"], priority=1, is_featured=True),
            CampaignProduct(campaign_id=campaigns["春季焕新季"], product_id=pid["DRESS002"], priority=2, is_featured=False),
            CampaignProduct(campaign_id=campaigns["春季焕新季"], product_id=pid["TSHIRT001"], priority=3, is_featured=False),
            CampaignProduct(campaign_id=campaigns["会员日特惠"], product_id=pid["DRESS001"], custom_discount=20.00, priority=1, is_featured=True),
            CampaignProduct(campaign_id=campaigns["会员日特惠"], product_id=pid["DIGITAL001"], priority=2, is_featured=True),
            CampaignProduct(campaign_id=campaigns["新品首发"], product_id=pid["DIGITAL002"], priority=1, is_featured=True),
        ])

        # ---------- 8. 营销内容 ----------
        s.add_all([
            MarketingContent(campaign_id=campaigns["春季焕新季"], content_type="banner", platform="all", tone="活泼",
                             title="春季焕新季",
                             content="🌸 春季焕新季来啦！全场满200减30，新品尝鲜价！快来选购你的春日穿搭吧～",
                             keywords=["春季", "焕新", "满减"]),
            MarketingContent(campaign_id=campaigns["春季焕新季"], content_type="social_post", platform="wechat", tone="亲切",
                             title="春日穿搭指南",
                             content="【春日穿搭推荐】法式碎花连衣裙，显瘦又气质，约会通勤两不误！点击查看更多春日心动单品→",
                             keywords=["穿搭", "连衣裙", "春季"]),
            MarketingContent(campaign_id=campaigns["会员日特惠"], content_type="push", platform="app", tone="简洁",
                             title="会员日提醒",
                             content="【会员专属】今日会员日，积分翻倍！精选好货低至85折，仅限3天！",
                             keywords=["会员", "积分翻倍"]),
            MarketingContent(campaign_id=campaigns["会员日特惠"], content_type="email", platform="email", tone="正式",
                             title="会员日专属邀请",
                             content="尊敬的会员，您好！\n\n感谢您一直以来的支持。本次会员日，我们为您准备了专属优惠：\n\n✨ 积分翻倍赚取\n✨ 精选商品85折\n✨ 新品优先购\n\n活动时间：4月15日-17日\n点击立即参与 →",
                             keywords=["会员专属", "积分", "折扣"]),
        ])

        # ---------- 9. 知识库 ----------
        s.add_all([
            KnowledgeBase(category="选品策略", title="电商选品黄金法则",
                          content="## 选品核心原则\n\n### 1. 需求优先\n选择市场需求大、搜索热度高的品类。\n\n### 2. 利润保障\n确保毛利率在30%以上。\n\n### 3. 差异化竞争\n避开红海市场，寻找细分赛道。\n\n### 4. 供应链稳定\n确保供应商可靠，供货稳定。",
                          summary="选品需关注需求、利润、差异化和供应链四大要素",
                          tags='["选品", "策略", "利润", "供应链"]', source="内部培训资料", author="运营团队"),
            KnowledgeBase(category="定价策略", title="动态定价方法论",
                          content="## 动态定价策略\n\n### 成本加成法\n售价 = 成本 × (1 + 目标利润率)\n\n### 竞争导向法\n- 高价策略：差异化明显的产品\n- 等价策略：跟随市场\n- 低价策略：引流款、清仓款\n\n### 需求导向法\n- 高峰期适当提价\n- 淡季促销降价",
                          summary="定价需结合成本、竞争和需求三因素",
                          tags='["定价", "动态", "竞争", "成本"]', source="运营手册", author="运营团队"),
            KnowledgeBase(category="营销策划", title="活动策划完整流程",
                          content="## 活动策划步骤\n\n### 1. 明确目标\n拉新/促活/转化/品牌\n\n### 2. 选择形式\n满减/折扣、买赠、抽奖、限时特惠\n\n### 3. 制定节奏\n预热期3-5天、爆发期、返场期1-2天\n\n### 4. 效果复盘\n指标达成、用户反馈、经验总结",
                          summary="活动策划需明确目标、选择形式、制定节奏并复盘",
                          tags='["营销", "活动", "策划", "复盘"]', source="运营手册", author="运营团队"),
            KnowledgeBase(category="用户分析", title="用户画像构建方法",
                          content="## 用户画像要素\n\n### 人口统计\n年龄、性别、职业、收入\n\n### 行为特征\n浏览习惯、购买频率、客单价、偏好类目\n\n### 心理特征\n价格敏感度、品牌忠诚度、决策因素\n\n### 标签体系\n建立多维度标签，支持精准营销",
                          summary="用户画像包含人口统计、行为和心理特征",
                          tags='["用户画像", "分析", "标签"]', source="数据分析文档", author="分析师团队"),
        ])

        # ---------- 10. Agent 任务记录 ----------
        s.add_all([
            AgentTask(task_type="selection", agent_name="ProductSelectionAgent",
                      input_data={"type": "analyze_category", "params": {"category": "连衣裙"}},
                      output_data={"success": True, "analysis": "完成品类分析..."},
                      status="completed", tokens_used=2845, duration_ms=12500, user_id=2),
            AgentTask(task_type="pricing", agent_name="PricingAgent",
                      input_data={"type": "suggest_price", "params": {"product_name": "蓝牙耳机", "cost_price": 65}},
                      output_data={"success": True, "recommended_price": 159},
                      status="completed", tokens_used=1523, duration_ms=8300, user_id=2),
            AgentTask(task_type="marketing", agent_name="MarketingAgent",
                      input_data={"type": "generate_copy", "params": {"product_name": "连衣裙", "platform": "wechat"}},
                      output_data={"success": True, "content": "春季新品上市..."},
                      status="completed", tokens_used=1892, duration_ms=9200, user_id=2),
        ])

        await s.commit()
        print(f"✅ 种子数据导入完成：3 用户 / 12 分类 / {len(products)} 产品 / 9 竞品价 / 8 评价 / 3 选品 / 3 活动 / 4 内容 / 4 知识 / 3 Agent任务")
    await close_database()


if __name__ == "__main__":
    # 首次执行时重建数据库（原库为空，安全）
    db = Path(__file__).resolve().parent.parent / "data" / "ecommerce.db"
    if db.exists() and db.stat().st_size < 1024 * 1024:
        db.unlink()
        print("已重置空数据库（由模型重建表结构）")
    asyncio.run(seed())
