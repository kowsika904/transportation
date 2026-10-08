from typing import List, Dict, Any
from app.models.schemas import PriorityItem, AffectedDelivery
from app.data.loader import DataLoader

class PriorityEngine:
    """
    Evaluates affected deliveries and computes dynamic priority scores (0-100) based on:
    1. SLA Window Pressure (0-35 pts)
    2. Cargo Criticality & Perishability (0-25 pts)
    3. Delay Severity (0-20 pts)
    4. Financial Penalty & SLA Risk (0-20 pts)
    """

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.customer_map = {c["customer_id"]: c for c in data_loader.customers}

    def rank_affected_deliveries(
        self, affected_deliveries: List[AffectedDelivery]
    ) -> List[PriorityItem]:
        prioritized_items: List[PriorityItem] = []

        for deliv in affected_deliveries:
            cust_id = deliv.customer_id
            c_info = self.customer_map.get(cust_id, {})

            # 1. SLA Pressure Points (0 - 35)
            # Compare delay vs SLA deadline
            sla_mins = c_info.get("sla_minutes_from_start", 180)
            orig_hrs, orig_m = map(int, deliv.original_eta.split(":"))
            orig_mins_from_start = (orig_hrs - 8) * 60 + orig_m
            minutes_until_sla = max(0.0, float(sla_mins - orig_mins_from_start))

            if deliv.sla_violated:
                sla_pts = 35.0
            elif minutes_until_sla < 30.0:
                sla_pts = 30.0
            elif minutes_until_sla < 60.0:
                sla_pts = 20.0
            elif minutes_until_sla < 120.0:
                sla_pts = 12.0
            else:
                sla_pts = 5.0

            # 2. Cargo Criticality & Perishability (0 - 25)
            is_perish = deliv.is_perishable
            item_val = deliv.item_value_usd
            tier = c_info.get("priority_tier", "MEDIUM")

            crit_pts = 0.0
            if is_perish:
                crit_pts += 15.0
            if item_val >= 25000.0:
                crit_pts += 10.0
            elif item_val >= 10000.0:
                crit_pts += 6.0
            elif tier == "CRITICAL":
                crit_pts += 8.0

            crit_pts = min(25.0, crit_pts)

            # 3. Delay Severity (0 - 20)
            delay_m = deliv.delay_minutes
            if delay_m >= 90.0:
                delay_pts = 20.0
            elif delay_m >= 60.0:
                delay_pts = 15.0
            elif delay_m >= 30.0:
                delay_pts = 10.0
            else:
                delay_pts = 5.0

            # 4. Financial Penalty & SLA Risk (0 - 20)
            penalty_rate = float(c_info.get("penalty_per_hour_late", 200.0))
            if penalty_rate >= 500.0:
                fin_pts = 20.0
            elif penalty_rate >= 300.0:
                fin_pts = 14.0
            elif penalty_rate >= 150.0:
                fin_pts = 8.0
            else:
                fin_pts = 4.0

            total_score = min(100.0, round(sla_pts + crit_pts + delay_pts + fin_pts, 1))

            if total_score >= 80.0:
                priority_tier = "CRITICAL"
            elif total_score >= 65.0:
                priority_tier = "HIGH"
            elif total_score >= 45.0:
                priority_tier = "MEDIUM"
            else:
                priority_tier = "LOW"

            reasons = []
            if deliv.sla_violated:
                reasons.append("Projected ETA breaches agreed SLA window.")
            if is_perish:
                reasons.append("Cargo is temperature-sensitive/perishable.")
            if penalty_rate >= 500.0:
                reasons.append(f"High SLA penalty rate of ${penalty_rate}/hr late.")
            if not reasons:
                reasons.append("Standard priority operational delivery.")

            reason_str = " ".join(reasons)

            prioritized_items.append(
                PriorityItem(
                    delivery_id=deliv.delivery_id,
                    customer_name=deliv.customer_name,
                    priority_score=total_score,
                    priority_tier=priority_tier,
                    sla_end_time=deliv.sla_window_end,
                    minutes_until_sla=minutes_until_sla,
                    delay_minutes=deliv.delay_minutes,
                    item_value_usd=deliv.item_value_usd,
                    is_perishable=is_perish,
                    penalty_usd_per_hour_late=penalty_rate,
                    score_breakdown={
                        "sla_urgency_pts": sla_pts,
                        "criticality_pts": crit_pts,
                        "delay_severity_pts": delay_pts,
                        "penalty_risk_pts": fin_pts,
                    },
                    reasoning=reason_str
                )
            )

        # Sort descending by priority score
        prioritized_items.sort(key=lambda x: x.priority_score, reverse=True)
        return prioritized_items
