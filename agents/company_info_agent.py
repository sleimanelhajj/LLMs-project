import yaml
import os
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse


class CompanyInfoAgent(BaseAgent):
    def __init__(self, data_path: str):
        super().__init__(
            name="CompanyInfoAgent",
            description="Provides company information, contact details, locations, and business hours",
        )
        self.data_path = data_path
        self.company_data = self._load_company_info()

    def _load_company_info(self) -> Dict[str, Any]:
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Company info file not found: {self.data_path}")
        try:
            with open(self.data_path, "r") as f:
                data = yaml.safe_load(f)
                return data.get("company", {})
        except Exception as e:
            print(f"[CompanyInfoAgent] Error loading data: {e}")
            return {}

    def can_handle(self, query: str) -> bool:
        keywords = [
            "company",
            "contact",
            "phone",
            "email",
            "address",
            "location",
            "hours",
            "open",
            "close",
            "where",
            "when",
            "office",
            "warehouse",
            "about",
            "who",
            "website",
            "social",
        ]
        return any(keyword in query.lower() for keyword in keywords)

    async def process_query(self, request: QueryRequest) -> AgentResponse:
        try:
            query_lower = request.query.lower()
            response = self._route_to_formatter(query_lower)

            return AgentResponse(
                agent_name=self.name,
                response=response,
                data={"company_info": self.company_data},
                success=True,
            )

        except Exception as e:
            print(f"[CompanyInfoAgent] Error: {e}")
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while retrieving company information.",
                success=False,
                error=str(e),
            )

    def _route_to_formatter(self, query: str) -> str:
        intents = {
            "contact": ["phone", "call", "number", "contact"],
            "email": ["email", "mail", "write"],
            "location": ["location", "address", "where", "office", "warehouse"],
            "hours": ["hours", "open", "close", "when", "time"],
            "about": ["about", "who", "company", "mission", "what do you do"],
            "web": ["website", "web", "online", "social"],
        }

        for intent, keywords in intents.items():
            if any(keyword in query for keyword in keywords):
                return self._format_by_intent(intent, query)

        return self._format_general_info()

    def _format_by_intent(self, intent: str, query: str) -> str:
        formatters = {
            "contact": self._format_contact_response,
            "email": self._format_email_response,
            "location": lambda: self._format_location_response(query),
            "hours": self._format_hours_response,
            "about": self._format_about_response,
            "web": self._format_web_response,
        }

        formatter = formatters.get(intent, self._format_general_info)
        return formatter()

    def _format_contact_response(self) -> str:
        contact = self.company_data.get("contact", {})
        company_name = self.company_data.get("name", "Our Company")

        lines = [f"{company_name} - Contact Information\n"]

        if contact.get("main_phone"):
            lines.append(f"Main Phone: {contact['main_phone']}")
        if contact.get("toll_free"):
            lines.append(f"Toll Free: {contact['toll_free']}")
        if contact.get("fax"):
            lines.append(f"Fax: {contact['fax']}")

        lines.append("\nFor specific inquiries:")
        if contact.get("support_email"):
            lines.append(f"• Support: {contact['support_email']}")
        if contact.get("sales_email"):
            lines.append(f"• Sales: {contact['sales_email']}")

        return "\n".join(lines)

    def _format_email_response(self) -> str:
        contact = self.company_data.get("contact", {})
        company_name = self.company_data.get("name", "Our Company")

        lines = [f"{company_name} - Email Contacts\n"]

        if contact.get("email"):
            lines.append(f"General Inquiries: {contact['email']}")
        if contact.get("support_email"):
            lines.append(f"Technical Support: {contact['support_email']}")
        if contact.get("sales_email"):
            lines.append(f"Sales & Orders: {contact['sales_email']}")

        return "\n".join(lines)

    def _format_location_response(self, query: str) -> str:
        locations = self.company_data.get("locations", [])

        if not locations:
            return "Location information is not available."

        specific = self._find_specific_location(query, locations)

        if specific:
            return self._format_single_location(specific)
        else:
            return self._format_all_locations(locations)

    def _find_specific_location(
        self, query: str, locations: List[Dict]
    ) -> Dict[str, Any]:
        for location in locations:
            name = location.get("name", "").lower()
            loc_type = location.get("type", "").lower()
            city = location.get("city", "").lower()

            if (
                loc_type in query
                or city in query
                or any(word in query for word in name.split())
            ):
                return location

        return None

    def _format_single_location(self, location: Dict[str, Any]) -> str:
        lines = [f"{location.get('name')}\n"]

        lines.append("Address:")
        lines.append(location.get("address", ""))
        lines.append(
            f"{location.get('city')}, {location.get('state')} {location.get('zip')}"
        )
        lines.append(f"{location.get('country')}\n")

        if location.get("phone"):
            lines.append(f"Phone: {location['phone']}")
        if location.get("email"):
            lines.append(f"Email: {location['email']}")

        if location.get("hours"):
            lines.append("\nHours:")
            hours = location["hours"]
            if hours.get("weekday"):
                lines.append(f"• Weekdays: {hours['weekday']}")
            if hours.get("weekend"):
                lines.append(f"• Weekend: {hours['weekend']}")

        if location.get("services"):
            lines.append("\nServices:")
            for service in location["services"]:
                lines.append(f"• {service}")

        return "\n".join(lines)

    def _format_all_locations(self, locations: List[Dict[str, Any]]) -> str:
        company_name = self.company_data.get("name", "Our Company")
        lines = [f"{company_name} - Our Locations\n"]

        for i, location in enumerate(locations, 1):
            loc_name = location.get("name", "Unknown")
            loc_type = location.get("type", "N/A").title()
            city = location.get("city", "")
            state = location.get("state", "")
            phone = location.get("phone", "")

            lines.append(f"{i}. {loc_name} ({loc_type})")
            lines.append(f"   Location: {city}, {state}")
            lines.append(f"   Phone: {phone}")

            services = location.get("services", [])
            if services:
                service_preview = ", ".join(services[:2])
                if len(services) > 2:
                    service_preview += f" (+{len(services) - 2} more)"
                lines.append(f"   Services: {service_preview}")

            lines.append("")

        lines.append("Ask about a specific location for detailed information!")
        return "\n".join(lines)

    def _format_hours_response(self) -> str:
        hours = self.company_data.get("hours", {})

        if not hours:
            return "Business hours information is not available."

        company_name = self.company_data.get("name", "Our Company")
        lines = [f"{company_name} - Business Hours\n", "Regular Hours:"]

        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        weekday_hours = [hours.get(day) for day in weekdays if hours.get(day)]

        if weekday_hours and all(h == weekday_hours[0] for h in weekday_hours):
            lines.append(f"• Monday - Friday: {weekday_hours[0]}")
        else:
            for day in weekdays:
                if hours.get(day):
                    lines.append(f"• {day.title()}: {hours[day]}")

        weekend = ["saturday", "sunday"]
        for day in weekend:
            if hours.get(day):
                lines.append(f"• {day.title()}: {hours[day]}")

        if hours.get("holidays"):
            lines.append(f"\nHolidays: {hours['holidays']}")

        return "\n".join(lines)

    def _format_about_response(self) -> str:
        about = self.company_data.get("about", {})
        company_name = self.company_data.get("name", "Our Company")

        lines = [f"About {company_name}\n"]

        if about.get("description"):
            lines.append(about["description"].strip() + "\n")

        if about.get("mission"):
            lines.append("Our Mission:")
            lines.append(about["mission"].strip() + "\n")

        if self.company_data.get("founded"):
            lines.append(f"Founded: {self.company_data['founded']}")

        if about.get("employee_count"):
            lines.append(f"Team Size: {about['employee_count']}+ employees")

        if about.get("service_area"):
            lines.append(f"Service Area: {about['service_area']}")

        if about.get("certifications"):
            lines.append("\nCertifications:")
            for cert in about["certifications"]:
                lines.append(f"• {cert}")

        return "\n".join(lines)

    def _format_web_response(self) -> str:
        web = self.company_data.get("web", {})

        if not web:
            return "Web information is not available."

        company_name = self.company_data.get("name", "Our Company")
        lines = [f"{company_name} - Online Presence\n"]

        if web.get("website"):
            lines.append(f"Website: {web['website']}")
        if web.get("linkedin"):
            lines.append(f"LinkedIn: {web['linkedin']}")
        if web.get("twitter"):
            lines.append(f"Twitter: {web['twitter']}")

        return "\n".join(lines)

    def _format_general_info(self) -> str:
        company_name = self.company_data.get("name", "Our Company")
        lines = [f"{company_name}\n"]

        about = self.company_data.get("about", {})
        if about.get("description"):
            lines.append(about["description"].strip() + "\n")

        lines.append("Quick Info:")

        contact = self.company_data.get("contact", {})
        if contact.get("main_phone"):
            lines.append(f"Phone: {contact['main_phone']}")
        if contact.get("email"):
            lines.append(f"Email: {contact['email']}")

        web = self.company_data.get("web", {})
        if web.get("website"):
            lines.append(f"Web: {web['website']}")

        locations = self.company_data.get("locations", [])
        if locations:
            location_count = len(locations)
            lines.append(f"\nWe have {location_count} location(s) serving you!")

        lines.append("\nAsk me about:")
        lines.extend(
            [
                "• Contact information",
                "• Location details",
                "• Business hours",
                "• Company background",
            ]
        )

        return "\n".join(lines)
