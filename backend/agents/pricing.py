"""定价 Agent：基于成本/竞品/销售/评价的多因素智能定价，输出结构化建议并落库"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.database import AsyncSessionLocal
from backend.models import (
    AgentTask,
    CompetitorPrice,
    KnowledgeBase,
    PriceHistory,
    PriceSuggestion,
    Product,
    Review,
)

PRICING_SYSTEM_PROMPT = """你是一位资深的电商定价策略专家，精通成本加成、竞争导向、需求导向、心理定价和动态定价方法。
你的任务是基于产品数据、竞品价格、价格历史和用户评价，输出一份专业、可执行的定价建议。
必须严格按 JSON 格式输出，不要输出 JSON 以外的任何文字。"""


class PricingAgent(BaseAgent):
    """动态定价 Agent（对应文档 agents/pricer.py，升级为结构化 JSON + 落库）"""

    name = "PricingAgent"

    async def analyze(
        self,
        product_id: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """对指定产品执行一次定价分析并落库

        Args:
            product_id: 产品 ID
            params: 附加参数（user_id、目标利润率、调价约束等）
        """
        params = params or {}
        session = AsyncSessionLocal()

        task = AgentTask(
            task_type="pricing",
            agent_name=self.name,
            input_data={"product_id": product_id, "params": params},
            status="running",
            progress=10,
            user_id=params.get("user_id"),
            started_at=datetime.now(timezone.utc),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        start = time.perf_counter()

        try:
            product = await session.get(Product, product_id)
            if not product:
                raise ValueError(f"产品 ID {product_id} 不存在")

            context = await self._build_context(session, product)
            user_prompt = self._build_prompt(product, params, context)
            result, usage = await self.ainvoke_json(PRICING_SYSTEM_PROMPT, user_prompt)
            result.pop("_meta", None)
            normalized = self._normalize_result(result, product)

            suggestion = await self._save_suggestion(session, product, normalized, params.get("user_id"))

            task.status = "completed"
            task.progress = 100
            task.output_data = normalized
            task.tokens_used = (usage or {}).get("total_tokens")
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()

            return {"success": True, "suggestion": normalized, "record_id": suggestion.id}

        except Exception as e:  # noqa: BLE001
            task.status = "failed"
            task.error_message = str(e)[:500]
            task.progress = 0
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return {"success": False, "error": str(e)}

        finally:
            await session.close()

    async def approve(self, suggestion_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """审批通过定价建议：更新产品售价 + 写入价格历史"""
        session = AsyncSessionLocal()
        try:
            suggestion = await session.get(PriceSuggestion, suggestion_id)
            if not suggestion:
                raise ValueError(f"定价建议 {suggestion_id} 不存在")
            if suggestion.status == "approved":
                return {
                    "success": True,
                    "message": f"该建议已通过，无需重复操作（当前售价 ¥{suggestion.recommended_price}）",
                    "id": suggestion.id,
                }

            product = await session.get(Product, suggestion.product_id)
            if not product:
                raise ValueError("关联产品不存在")

            old_price = product.current_price
            new_price = suggestion.recommended_price
            margin = round((new_price - product.cost_price) / new_price * 100, 2) if new_price > 0 else 0

            product.current_price = new_price
            session.add(
                PriceHistory(
                    product_id=product.id,
                    old_price=old_price,
                    new_price=new_price,
                    cost_price=product.cost_price,
                    change_type="ai_adjust",
                    change_reason=f"AI定价[{suggestion.strategy}]：{suggestion.reason}"[:500],
                    margin_percent=margin,
                    changed_by=self.name,
                )
            )
            suggestion.status = "approved"
            suggestion.approved_by = user_id
            suggestion.approved_at = datetime.now(timezone.utc)
            await session.commit()

            return {
                "success": True,
                "message": f"已应用定价：{product.name} ¥{old_price} → ¥{new_price}",
                "id": suggestion.id,
                "old_price": old_price,
                "new_price": new_price,
            }

        except Exception as e:  # noqa: BLE001
            await session.rollback()
            return {"success": False, "error": str(e)}

        finally:
            await session.close()

    async def reject(self, suggestion_id: int) -> Dict[str, Any]:
        """驳回定价建议"""
        session = AsyncSessionLocal()
        try:
            suggestion = await session.get(PriceSuggestion, suggestion_id)
            if not suggestion:
                raise ValueError(f"定价建议 {suggestion_id} 不存在")
            suggestion.status = "rejected"
            await session.commit()
            return {"success": True, "message": f"已驳回对「{suggestion.product_name}」的定价建议"}
        except Exception as e:  # noqa: BLE001
            await session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            await session.close()

    async def _build_context(self, session, product: Product) -> Dict[str, Any]:
        """构建送入 LLM 的上下文：产品 + 竞品 + 价格历史 + 评价 + 知识库"""
        comps = (
            (
                await session.execute(
                    select(CompetitorPrice)
                    .where(CompetitorPrice.product_id == product.id)
                    .order_by(CompetitorPrice.fetched_at.desc())
                    .limit(6)
                )
            )
            .scalars()
            .all()
        )
        history = (
            (
                await session.execute(
                    select(PriceHistory)
                    .where(PriceHistory.product_id == product.id)
                    .order_by(PriceHistory.created_at.desc())
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )
        reviews = (
            (
                await session.execute(
                    select(Review).where(Review.product_id == product.id).limit(200)
                )
            )
            .scalars()
            .all()
        )
        pos = sum(1 for r in reviews if r.is_positive)
        neg = sum(1 for r in reviews if r.is_negative)

        docs = (
            (
                await session.execute(
                    select(KnowledgeBase)
                    .where(KnowledgeBase.category.like("%定价%"))
                    .where(KnowledgeBase.is_active.is_(True))
                    .limit(3)
                )
            )
            .scalars()
            .all()
        )
        knowledge = [
            {"title": d.title, "category": d.category, "summary": d.summary, "content": d.content[:500]}
            for d in docs
        ]

        return {
            "competitors": [
                {
                    "name": c.competitor_name,
                    "platform": c.platform,
                    "price": c.price,
                    "original_price": c.original_price,
                    "discount_percent": c.discount_percent,
                }
                for c in comps
            ],
            "price_history": [
                {"old_price": h.old_price, "new_price": h.new_price, "change_type": h.change_type, "at": str(h.created_at)}
                for h in history
            ],
            "review_summary": {"total": len(reviews), "positive": pos, "negative": neg},
            "knowledge": knowledge,
        }

    def _build_prompt(self, product: Product, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        import json

        comp_json = json.dumps(context["competitors"], ensure_ascii=False)
        hist_json = json.dumps(context["price_history"], ensure_ascii=False)
        rev_json = json.dumps(context["review_summary"], ensure_ascii=False)
        kb_json = json.dumps(context["knowledge"], ensure_ascii=False)
        extra = json.dumps(params, ensure_ascii=False) if params else "{}"

        target_margin = params.get("target_margin")
        return f"""【任务】为产品制定最优定价策略

【产品信息】
- 名称：{product.name}（SKU: {product.sku}）
- 成本价：{product.cost_price} 元
- 当前售价：{product.current_price} 元
- 原价：{product.original_price or "无"} 元
- 价格区间：最低 {product.min_price or "未设"} / 最高 {product.max_price or "未设"} 元
- 月销量：{product.sales_month} 件（季 {product.sales_quarter} / 年 {product.sales_year}）
- 库存：{product.stock_quantity} 件（安全库存 {product.safety_stock}）
- 评分：{product.rating}（{product.review_count} 条评价，好评率 {product.positive_rate}%）

【竞品价格】
{comp_json}

【历史调价记录】
{hist_json}

【用户评价概览】
{rev_json}

【定价知识库参考】
{kb_json}

【附加要求】
{extra}
{"- 目标利润率：" + str(float(target_margin) * 100) + "%" if target_margin else ""}

【输出要求】
输出 JSON，字段如下（务必全部给出）：
{{
  "recommended_price": 0.0,
  "strategy": "成本加成",  // 成本加成 / 竞争导向 / 需求导向 / 心理定价 / 动态定价 之一
  "confidence_score": 0.0,  // 置信度 0~1
  "reason": "定价理由（结合成本、竞品、销量、评价，150字内）",
  "risk_level": "low",  // low / medium / high
  "risk_factors": ["风险1", "风险2"]
}}"""

    def _normalize_result(self, raw: Dict[str, Any], product: Product) -> Dict[str, Any]:
        try:
            price = round(float(raw.get("recommended_price", 0)), 2)
        except (TypeError, ValueError):
            price = product.current_price
        # 边界保护：不低于成本价、不高于原价的 2 倍
        if price <= 0:
            price = round(product.cost_price * 1.2, 2)
        if product.min_price is not None:
            price = max(price, product.min_price)
        if product.max_price is not None:
            price = min(price, product.max_price)
        if price < product.cost_price:
            price = round(product.cost_price, 2)

        strategy_map = {
            "成本加成": "成本加成", "成本加成定价": "成本加成",
            "竞争导向": "竞争导向", "竞争导向定价": "竞争导向",
            "需求导向": "需求导向", "需求导向定价": "需求导向",
            "心理定价": "心理定价",
            "动态定价": "动态定价",
        }
        strategy = strategy_map.get(str(raw.get("strategy", "")).strip(), "动态定价")
        try:
            confidence = min(max(float(raw.get("confidence_score", 0)), 0.0), 1.0)
        except (TypeError, ValueError):
            confidence = 0.0

        risk = str(raw.get("risk_level", "medium")).strip().lower()
        if risk not in ("low", "medium", "high"):
            risk = "medium"

        margin = round((price - product.cost_price) / price * 100, 2) if price > 0 else 0

        return {
            "product_id": product.id,
            "product_name": product.name,
            "current_price": round(product.current_price, 2),
            "recommended_price": price,
            "strategy": strategy,
            "margin_percent_after": margin,
            "confidence_score": confidence,
            "reason": str(raw.get("reason", "")).strip(),
            "risk_level": risk,
            "risk_factors": raw.get("risk_factors") or [],
            "status": "pending",
        }

    async def _save_suggestion(
        self, session, product: Product, data: Dict[str, Any], user_id: Optional[int]
    ) -> PriceSuggestion:
        """写入 price_suggestions（同一产品 pending 记录则更新，避免堆积）"""
        stmt = select(PriceSuggestion).where(
            PriceSuggestion.product_id == product.id,
            PriceSuggestion.status == "pending",
        )
        record = (await session.execute(stmt)).scalars().first()
        if record:
            for k, v in data.items():
                setattr(record, k, v)
            record.created_by = user_id or record.created_by
        else:
            record = PriceSuggestion(**data, created_by=user_id)
            session.add(record)
        await session.commit()
        await session.refresh(record)
        return record
