from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.event_collectors.base import BaseEventCollector, CollectorResult, EventItem
from app.services.event_collectors.news_utils import fetch_google_news_events


class SecurityCalendarCollector(BaseEventCollector):
    event_type = "security"
    category = "网络安全"

    async def collect(self, days: int = 30) -> CollectorResult:
        items: list[EventItem] = []
        errors: list[str] = []
        now = datetime.now(timezone.utc)
        # Microsoft Patch Tuesday: second Tuesday of each month.
        for month_offset in range(2):
            month_start = (now.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
            tuesdays = [month_start + timedelta(days=i) for i in range(31) if (month_start + timedelta(days=i)).month == month_start.month and (month_start + timedelta(days=i)).weekday() == 1]
            if len(tuesdays) >= 2:
                patch_day = tuesdays[1].replace(hour=9, minute=0, second=0, microsecond=0)
                if now <= patch_day <= now + timedelta(days=days):
                    items.append(
                        EventItem(
                            event_name="Microsoft Patch Tuesday 安全补丁日",
                            event_type=self.event_type,
                            category=self.category,
                            event_time=patch_day,
                            source="Microsoft Security Response Center",
                            source_url="https://msrc.microsoft.com/update-guide",
                            description="微软每月安全补丁发布节点，具体漏洞和影响范围以官方公告为准。",
                            keywords=["Patch Tuesday", "Microsoft Security", "CVE"],
                            importance_level="high",
                            impact_score=78,
                        )
                    )
        found, error = await fetch_google_news_events(
            '("CVE" OR "zero-day" OR "security advisory" OR "ransomware") ("will disclose" OR "scheduled" OR "July" OR "August")',
            self.event_type,
            self.category,
            "Google News Security",
            ["CVE", "zero-day", "security advisory", "ransomware", "CISA"],
            days,
        )
        items.extend(found)
        if error:
            errors.append(error)
        return CollectorResult(items=items, errors=errors)
