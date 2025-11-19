import yaml
import os
from typing import Dict, Any
from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse


class DeliveryAgent(BaseAgent):
    def __init__(self, config_path: str):
        super().__init__(
            name="DeliveryAgent",
            description="Provides delivery options, shipping costs, and delivery estimates",
        )
        self.config_path = config_path
        self.delivery_data = self._load_delivery_config()

    def _load_delivery_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Delivery config file not found: {self.config_path}"
            )
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"[DeliveryAgent] Error loading config: {e}")
            return {}

    def can_handle(self, query: str) -> bool:
        keywords = [
            "delivery",
            "shipping",
            "ship",
            "send",
            "deliver",
            "eta",
            "arrival",
            "express",
            "overnight",
            "pickup",
            "cost",
            "price",
            "how long",
            "how fast",
        ]
        return any(keyword in query.lower() for keyword in keywords)

    async def process_query(self, request: QueryRequest) -> AgentResponse:
        try:
            query = request.query.lower()

            if any(word in query for word in ["cost", "price", "how much"]):
                response = self._format_cost_response(query)
            elif any(
                word in query for word in ["fast", "quick", "overnight", "express", "urgent"]
            ):
                response = self._format_fast_delivery_response()
            elif any(word in query for word in ["pickup", "collect"]):
                response = self._format_pickup_response()
            elif any(word in query for word in ["international", "overseas"]):
                response = self._format_international_response()
            elif any(word in query for word in ["free", "threshold"]):
                response = self._format_free_shipping_response()
            else:
                response = self._format_all_options()

            return AgentResponse(
                agent_name=self.name,
                response=response,
                data={"delivery_options": self.delivery_data},
                success=True,
            )

        except Exception as e:
            print(f"[DeliveryAgent] Error: {e}")
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while retrieving delivery information.",
                success=False,
                error=str(e),
            )

    def _format_all_options(self) -> str:
        options = self.delivery_data.get("delivery_options", [])

        lines = ["Here are all our delivery options:\n"]

        for option in options:
            lines.append(
                f"• {option['name']}: ${option['cost']:.2f} ({option['estimated_days']} days)"
            )
            lines.append(f"  {option['description']}")
            lines.append(f"  Coverage: {', '.join(option.get('coverage', []))}\n")

        policies = self.delivery_data.get("shipping_policies", {})
        threshold = policies.get("free_shipping_threshold")
        if threshold:
            lines.append(f"\nFree shipping on orders over ${threshold:.2f}!")

        return "\n".join(lines)

    def _format_cost_response(self, query: str) -> str:
        options = self.delivery_data.get("delivery_options", [])

        specific_option = None
        for option in options:
            if option["name"].lower() in query or option["code"].lower() in query:
                specific_option = option
                break

        if specific_option:
            lines = [f"{specific_option['name']}\n"]
            lines.append(f"Cost: ${specific_option['cost']:.2f}")
            lines.append(
                f"Delivery Time: {specific_option['estimated_days']} business days"
            )
            lines.append(f"{specific_option['description']}")

            if specific_option.get("features"):
                lines.append("\nFeatures:")
                for feature in specific_option["features"]:
                    lines.append(f"  • {feature}")

            return "\n".join(lines)

        lines = ["Here are our shipping costs:\n"]
        for option in sorted(options, key=lambda x: x["cost"]):
            lines.append(
                f"• {option['name']}: ${option['cost']:.2f} ({option['estimated_days']} days)"
            )

        return "\n".join(lines)

    def _format_fast_delivery_response(self) -> str:
        options = self.delivery_data.get("delivery_options", [])

        fast_options = sorted(options, key=lambda x: x["estimated_days"])[:3]

        lines = ["Here are our fastest delivery options:\n"]

        for option in fast_options:
            lines.append(
                f"• {option['name']}: {option['estimated_days']} days - ${option['cost']:.2f}"
            )
            lines.append(f"  {option['description']}")

            if option.get("restrictions"):
                lines.append(f"  Note: {'; '.join(option['restrictions'])}")

            lines.append("")

        return "\n".join(lines)

    def _format_pickup_response(self) -> str:
        options = self.delivery_data.get("delivery_options", [])

        pickup_options = [opt for opt in options if opt["code"] == "PICKUP"]

        if not pickup_options:
            return "Local pickup is not currently available. Please choose a shipping method."

        lines = ["Here are our pickup options:\n"]

        for option in pickup_options:
            lines.append(f"• {option['name']}: ${option['cost']:.2f}")
            lines.append(f"  {option['description']}\n")

            if option.get("features"):
                lines.append("  Features:")
                for feature in option["features"]:
                    lines.append(f"    • {feature}")

        return "\n".join(lines)

    def _format_international_response(self) -> str:
        options = self.delivery_data.get("delivery_options", [])

        intl_options = [
            opt for opt in options if "International" in opt.get("coverage", [])
        ]

        if not intl_options:
            return "We currently don't offer international shipping. Please contact customer service for special arrangements."

        lines = ["Here are our international shipping options:\n"]

        for option in intl_options:
            lines.append(f"• {option['name']}: ${option['cost']:.2f}")
            lines.append(f"  Delivery: {option['estimated_days']} business days")
            lines.append(f"  {option['description']}")

            if option.get("restrictions"):
                lines.append("\n  Important:")
                for restriction in option["restrictions"]:
                    lines.append(f"    • {restriction}")

            lines.append("")

        return "\n".join(lines)

    def _format_free_shipping_response(self) -> str:
        policies = self.delivery_data.get("shipping_policies", {})
        threshold = policies.get("free_shipping_threshold")

        if not threshold:
            return "We don't currently offer free shipping. Please see our delivery options for costs."

        lines = ["Free Shipping Available!\n"]
        lines.append(f"Get free standard shipping on orders over ${threshold:.2f}!\n")
        lines.append("Benefits:")
        lines.append("• No shipping charges")
        lines.append("• Same great tracking and service")
        lines.append("• Applies to standard ground shipping\n")
        lines.append(
            f"Orders under ${threshold:.2f} qualify for our regular shipping rates."
        )

        return "\n".join(lines)