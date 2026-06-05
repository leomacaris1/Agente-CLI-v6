import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


DEFAULT_BUDGET = {
    "mode": "supervised",
    "currency": "USD",
    "daily_limit": 0,
    "monthly_limit": 0,
    "single_action_limit": 0,
    "allowed_categories": ["research", "content_generation", "hosting"],
    "blocked_categories": ["ads", "subscriptions", "outsourcing", "domain_purchase"],
    "notes": [
        "Por defecto el agente no puede gastar dinero.",
        "Todo gasto, publicacion comercial o activacion de servicio pago requiere aprobacion.",
    ],
}


class BudgetPolicy:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.policy_file = self.state_dir / "budget_policy.json"
        self.ledger_file = self.state_dir / "budget_ledger.jsonl"
        self._ensure_policy()

    def summary(self) -> str:
        policy = self.load_policy()
        spent_today = self._sum_period("day")
        spent_month = self._sum_period("month")
        return (
            "Politica economica\n"
            f"- Modo: {policy.get('mode', 'supervised')}\n"
            f"- Moneda: {policy.get('currency', 'USD')}\n"
            f"- Limite diario: {policy.get('daily_limit', 0)}\n"
            f"- Limite mensual: {policy.get('monthly_limit', 0)}\n"
            f"- Limite por accion: {policy.get('single_action_limit', 0)}\n"
            f"- Gastado hoy registrado: {spent_today:.2f}\n"
            f"- Gastado este mes registrado: {spent_month:.2f}\n"
            f"- Categorias permitidas: {', '.join(policy.get('allowed_categories', [])) or 'ninguna'}\n"
            f"- Categorias bloqueadas: {', '.join(policy.get('blocked_categories', [])) or 'ninguna'}"
        )

    def evaluate(self, amount: float, category: str, description: str = "") -> Dict:
        policy = self.load_policy()
        category = category.strip().lower() or "uncategorized"
        amount = float(amount)

        if amount <= 0:
            return {"decision": "allow", "reason": "No hay gasto economico."}

        if category in set(policy.get("blocked_categories", [])):
            return {"decision": "approval", "reason": f"Categoria bloqueada o sensible: {category}."}

        if category not in set(policy.get("allowed_categories", [])):
            return {"decision": "approval", "reason": f"Categoria no permitida explicitamente: {category}."}

        single_limit = float(policy.get("single_action_limit", 0) or 0)
        daily_limit = float(policy.get("daily_limit", 0) or 0)
        monthly_limit = float(policy.get("monthly_limit", 0) or 0)

        if single_limit <= 0 or amount > single_limit:
            return {"decision": "approval", "reason": "Supera el limite por accion o no hay limite preaprobado."}

        if daily_limit <= 0 or self._sum_period("day") + amount > daily_limit:
            return {"decision": "approval", "reason": "Supera el limite diario o no hay limite diario preaprobado."}

        if monthly_limit <= 0 or self._sum_period("month") + amount > monthly_limit:
            return {"decision": "approval", "reason": "Supera el limite mensual o no hay limite mensual preaprobado."}

        return {
            "decision": "allow",
            "reason": f"Gasto dentro de politica: {amount:.2f} {policy.get('currency', 'USD')} en {category}.",
            "description": description,
        }

    def record(self, amount: float, category: str, description: str, status: str = "planned") -> Dict:
        record = {
            "timestamp": datetime.now().isoformat(),
            "amount": float(amount),
            "category": category,
            "description": description,
            "status": status,
        }
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def load_policy(self) -> Dict:
        try:
            with open(self.policy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else dict(DEFAULT_BUDGET)
        except Exception:
            return dict(DEFAULT_BUDGET)

    def _ensure_policy(self):
        if not self.policy_file.exists():
            with open(self.policy_file, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_BUDGET, f, ensure_ascii=False, indent=2)

    def _sum_period(self, period: str) -> float:
        now = datetime.now()
        total = 0.0
        if not self.ledger_file.exists():
            return total
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    if record.get("status") not in {"approved", "spent", "planned"}:
                        continue
                    timestamp = datetime.fromisoformat(record.get("timestamp"))
                    same_day = timestamp.date() == now.date()
                    same_month = timestamp.year == now.year and timestamp.month == now.month
                    if period == "day" and same_day:
                        total += float(record.get("amount", 0))
                    if period == "month" and same_month:
                        total += float(record.get("amount", 0))
        except Exception:
            return total
        return total
