"""产品相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Category, CompetitorPrice, PriceHistory, Product

router = APIRouter()


def _serialize(product: Product, category_name: str | None = None) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category_name": category_name,
        "cost_price": product.cost_price,
        "current_price": product.current_price,
        "original_price": product.original_price,
        "stock_quantity": product.stock_quantity,
        "stock_status": product.stock_status,
        "sales_month": product.sales_month,
        "rating": product.rating,
        "review_count": product.review_count,
        "positive_rate": product.positive_rate,
        "status": product.status,
        "margin_percent": product.margin_percent,
    }


@router.get("")
async def list_products(db: AsyncSession = Depends(get_db)):
    """产品列表（含分类名）"""
    stmt = (
        select(Product, Category.name)
        .outerjoin(Category, Product.category_id == Category.id)
        .order_by(Product.id)
    )
    rows = (await db.execute(stmt)).all()
    products = [_serialize(p, cat_name) for p, cat_name in rows]
    return {"success": True, "count": len(products), "products": products}


@router.get("/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """产品详情（含竞品价、价格历史）"""
    stmt = (
        select(Product, Category.name)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Product.id == product_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="产品不存在")
    product, cat_name = row

    competitors = (
        await db.execute(
            select(CompetitorPrice)
            .where(CompetitorPrice.product_id == product_id)
            .order_by(CompetitorPrice.fetched_at.desc())
            .limit(5)
        )
    ).scalars().all()

    price_history = (
        await db.execute(
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    data = _serialize(product, cat_name)
    data["competitors"] = [
        {
            "name": c.competitor_name,
            "platform": c.platform,
            "price": c.price,
            "original_price": c.original_price,
            "discount_percent": c.discount,
        }
        for c in competitors
    ]
    data["price_history"] = [
        {
            "old_price": h.old_price,
            "new_price": h.new_price,
            "change_type": h.change_type,
            "change_reason": h.change_reason,
            "created_at": str(h.created_at),
        }
        for h in price_history
    ]
    return {"success": True, "product": data}
