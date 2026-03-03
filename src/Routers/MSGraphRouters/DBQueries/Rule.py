from typing import Optional
from uuid import UUID

from sqlalchemy import select

from Database import ApplicationRule
from Schemas import GetRulesResponseSchema, RulesSchema, GetRuleResponseSchema


async def query_rules(session, application_id: Optional[UUID] = None) -> GetRulesResponseSchema:
    try:
        stmt = select(ApplicationRule)
        if application_id:
            stmt = stmt.where(ApplicationRule.application_id == application_id)

        result = await session.execute(stmt)
        rules = result.scalars().all()

        app_dict: dict[UUID, list[RulesSchema]] = {}
        for rule in rules:
            if rule.application_id not in app_dict:
                app_dict[rule.application_id] = []
            app_dict[rule.application_id].append(
                RulesSchema(
                    rule_id=rule.id,
                    rule_name=rule.rule_name,
                    rule_description=rule.rule_description
                )
            )

        applications_list = [
            GetRuleResponseSchema(application_id=app_id, rules=rules_list)
            for app_id, rules_list in app_dict.items()
        ]

        return GetRulesResponseSchema(application=applications_list).model_dump(mode="json")
    except Exception as _ex:
        raise _ex
