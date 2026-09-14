"""营销 Agent：基于活动与产品数据生成营销策划方案与文案，落库并更新活动信息"""
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.database import AsyncSessionLocal
from backend.models import (
    AgentTask,
    Campaign,
    CampaignProduct,
    KnowledgeBase,
    MarketingContent,
    Product,
    Review,
)

MARKETING_SYSTEM_PROMPT = """你是一位资深的电商营销专家，精通活动策划、文案创作、渠道投放和用户心理。
你的任务是基于活动背景、参与产品数据和用户评价，输出一份可执行的营销策划方案和营销文案。
必须严格按 JSON 格式输出，不要输出 JSON 以外的任何文字。"""


class MarketingAgent(BaseAgent):
    """营销 Agent（对应文档 agents/marketer.py，升级为结构化策划 + 落库）"""

    name = "MarketingAgent"

    async def analyze(
        self,
        campaign_id: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """对指定营销活动执行一次策划分析并落库

        Args:
            campaign_id: 活动 ID
            params: 附加参数（user_id、预算上限、目标等）
        """
        params = params or {}
        session = AsyncSessionLocal()

        task = AgentTask(
            task_type="marketing",
            agent_name=self.name,
            input_data={"campaign_id": campaign_id, "params": params},
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
            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                raise ValueError(f"活动 ID {campaign_id} 不存在")

            context = await self._build_context(session, campaign)
            user_prompt = self._build_prompt(campaign, params, context)
            result, usage = await self.ainvoke_json(MARKETING_SYSTEM_PROMPT, user_prompt)
            result.pop("_meta", None)
            plan = self._normalize_plan(result, campaign)

            # 1. 更新活动信息
            updated = self._apply_to_campaign(campaign, plan)
            # 2. 写入营销文案（替换旧的 AI 生成内容，避免堆积）
            contents = await self._save_contents(session, campaign, plan.get("contents", []))
            await session.commit()

            task.status = "completed"
            task.progress = 100
            task.output_data = plan
            task.tokens_used = (usage or {}).get("total_tokens")
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()

            return {
                "success": True,
                "plan": plan,
                "campaign": updated,
                "contents_count": len(contents),
            }

        except Exception as e:  # noqa: BLE001
            import traceback

            task.status = "failed"
            task.error_message = traceback.format_exc()[-1500:]
            task.progress = 0
            task.duration_ms = int((time.perf_counter() - start) * 1000)
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return {"success": False, "error": str(e)}

        finally:
            await session.close()

    async def _build_context(self, session, campaign: Campaign) -> Dict[str, Any]:
        """构建送入 LLM 的上下文：活动 + 参与产品 + 已有内容 + 评价 + 知识库"""
        # 显式 JOIN 查询，避免异步环境下关系懒加载
        cp_rows = (
            (
                await session.execute(
                    select(CampaignProduct, Product)
                    .join(Product, CampaignProduct.product_id == Product.id)
                    .where(CampaignProduct.campaign_id == campaign.id)
                )
            )
            .all()
        )
        products = []
        for cp, p in cp_rows[:8]:
            reviews = (
                (
                    await session.execute(
                        select(Review).where(Review.product_id == p.id).limit(100)
                    )
                )
                .scalars()
                .all()
            )
            pos = sum(1 for r in reviews if r.is_positive)
            products.append(
                {
                    "name": p.name,
                    "price": p.current_price,
                    "cost": p.cost_price,
                    "sales_month": p.sales_month,
                    "rating": p.rating,
                    "positive_rate": p.positive_rate,
                    "discount_percent": cp.discount_percent,
                    "custom_discount": cp.custom_discount,
                    "is_featured": cp.is_featured,
                    "review_positive_count": pos,
                }
            )

        contents = (
            (
                await session.execute(
                    select(MarketingContent)
                    .where(MarketingContent.campaign_id == campaign.id)
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )
        docs = (
            (
                await session.execute(
                    select(KnowledgeBase)
                    .where(KnowledgeBase.category.like("%营销%"))
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
            "products": products,
            "existing_contents": [
                {"content_type": c.content_type, "platform": c.platform, "title": c.title}
                for c in contents
            ],
            "knowledge": knowledge,
        }

    def _build_prompt(self, campaign: Campaign, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        prods_json = json.dumps(context["products"], ensure_ascii=False)
        exist_json = json.dumps(context["existing_contents"], ensure_ascii=False)
        kb_json = json.dumps(context["knowledge"], ensure_ascii=False)
        extra = json.dumps(params, ensure_ascii=False) if params else "{}"

        return f"""【任务】为营销活动制定完整策划方案并生成文案

【活动信息】
- 名称：{campaign.name}
- 类型：{campaign.campaign_type}
- 描述：{campaign.description or "（无）"}
- 目标：{campaign.goal or "（未定）"}
- 预算：{campaign.budget or "未设"} 元
- 周期：{campaign.start_date} 至 {campaign.end_date or "未定"}
- 当前状态：{campaign.status}

【参与产品数据】
{prods_json}

【已有营销内容】
{exist_json}

【营销知识库参考】
{kb_json}

【附加要求】
{extra}

【输出要求】
输出 JSON，字段如下（务必全部给出）：
{{
  "theme": "活动主题",
  "objective": "活动目标",
  "target_audience": "目标人群描述",
  "channels": ["渠道1", "渠道2", "渠道3"],
  "discount_strategy": "促销策略说明",
  "budget_allocation": {{"渠道1": 金额, "渠道2": 金额}},
  "timeline": "节奏安排",
  "kpis": {{"曝光": 数值, "转化率": "x%"}},
  "risks": ["风险1", "风险2"],
  "contents": [
    {{
      "content_type": "主图文案",
      "platform": "小红书",
      "tone": "种草",
      "title": "标题",
      "content": "正文内容（120字内）",
      "hashtags": ["话题1", "话题2"]
    }}
  ]
}}

contents 数组输出 3 条，分别覆盖：主图文案（平台自选）、详情页/公众号文案、短信/推送文案。"""

    def _normalize_plan(self, raw: Dict[str, Any], campaign: Campaign) -> Dict[str, Any]:
        plan = {
            "theme": str(raw.get("theme", "")).strip() or campaign.name,
            "objective": str(raw.get("objective", "")).strip(),
            "target_audience": str(raw.get("target_audience", "")).strip(),
            "channels": raw.get("channels") or [],
            "discount_strategy": str(raw.get("discount_strategy", "")).strip(),
            "budget_allocation": raw.get("budget_allocation") or {},
            "timeline": str(raw.get("timeline", "")).strip(),
            "kpis": raw.get("kpis") or {},
            "risks": raw.get("risks") or [],
        }
        contents = []
        for c in (raw.get("contents") or [])[:3]:
            contents.append(
                {
                    "content_type": str(c.get("content_type", "主图文案")).strip(),
                    "platform": str(c.get("platform", "通用")).strip(),
                    "tone": str(c.get("tone", "亲切")).strip(),
                    "title": str(c.get("title", "")).strip(),
                    "content": str(c.get("content", "")).strip(),
                    "hashtags": c.get("hashtags") or [],
                }
            )
        plan["contents"] = contents
        return plan

    def _apply_to_campaign(self, campaign: Campaign, plan: Dict[str, Any]) -> Dict[str, Any]:
        """把策划结果回写到活动记录"""
        if plan.get("objective"):
            campaign.goal = plan["objective"][:50]
        if plan.get("target_audience"):
            campaign.target_audience = plan["target_audience"]
        campaign.strategy_summary = json.dumps(
            {
                "theme": plan.get("theme"),
                "channels": plan.get("channels"),
                "discount_strategy": plan.get("discount_strategy"),
                "budget_allocation": plan.get("budget_allocation"),
                "timeline": plan.get("timeline"),
                "kpis": plan.get("kpis"),
                "risks": plan.get("risks"),
            },
            ensure_ascii=False,
        )
        kpis = plan.get("kpis") or {}
        try:
            if kpis.get("销售额"):
                campaign.expected_revenue = float(str(kpis["销售额"]).replace(",", "").replace("万", "")) * 10000 if "万" in str(kpis["销售额"]) else float(str(kpis["销售额"]).replace(",", ""))
        except (TypeError, ValueError):
            pass
        if campaign.status == "draft":
            campaign.status = "planning"
        return {
            "id": campaign.id,
            "name": campaign.name,
            "goal": campaign.goal,
            "target_audience": campaign.target_audience,
            "status": campaign.status,
            "expected_revenue": campaign.expected_revenue,
        }

    async def _save_contents(self, session, campaign: Campaign, contents: list) -> list:
        """写入营销文案（删除该活动旧的 AI 内容，避免重复堆积）"""
        old = (
            (
                await session.execute(
                    select(MarketingContent).where(
                        MarketingContent.campaign_id == campaign.id,
                        MarketingContent.created_by == "AI",
                    )
                )
            )
            .scalars()
            .all()
        )
        for o in old:
            await session.delete(o)
        await session.flush()

        saved = []
        for c in contents:
            mc = MarketingContent(
                campaign_id=campaign.id,
                content_type=c["content_type"],
                platform=c["platform"],
                tone=c["tone"],
                title=c["title"] or c["content_type"],
                content=c["content"],
                hashtags=c["hashtags"],
                created_by="AI",
            )
            session.add(mc)
            saved.append(mc)
        await session.flush()
        return saved
