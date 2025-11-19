"""
Delivery Agent

Handles delivery and shipping queries using YAML configuration.
Provides delivery options, costs, ETAs, and shipping policies.
"""

import asyncio
import yaml
import os
from typing import List, Dict, Any, Optional
from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse


class DeliveryAgent(BaseAgent):
    """Agent for handling delivery and shipping queries using YAML configuration."""
    
    def __init__(self, config_path: str):
        super().__init__(
            name="DeliveryAgent",
            description="Provides delivery options, shipping costs, and delivery estimates"
        )
        self.config_path = config_path
        self.delivery_data = self._load_delivery_config()
    
    def _load_delivery_config(self) -> Dict[str, Any]:
        """Load delivery configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Delivery config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading delivery config: {e}")
            return {}
    
    def can_handle(self, query: str) -> bool:
        """Check if query is delivery-related."""
        keywords = [
            "delivery", "shipping", "ship", "send", "deliver",
            "eta", "arrival", "express", "overnight", "pickup",
            "cost", "price", "how long", "how fast"
        ]
        return any(keyword in query.lower() for keyword in keywords)
    
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process delivery query."""
        try:
            query = request.query.lower()
            
            # Determine query type
            if any(word in query for word in ["cost", "price", "how much"]):
                response = self._format_cost_response(query)
            elif any(word in query for word in ["fast", "quick", "overnight", "express", "urgent"]):
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
                success=True
            )
        
        except Exception as e:
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while retrieving delivery information.",
                success=False,
                error=str(e)
            )
    
    def _format_all_options(self) -> str:
        """Format all delivery options."""
        options = self.delivery_data.get("delivery_options", [])
        
        response = "Here are all our delivery options:\n\n"
        
        for option in options:
            response += f"• **{option['name']}**: ${option['cost']:.2f} ({option['estimated_days']} days)\n"
            response += f"  {option['description']}\n"
            response += f"  Coverage: {', '.join(option.get('coverage', []))}\n\n"
        
        # Add free shipping info
        policies = self.delivery_data.get("shipping_policies", {})
        threshold = policies.get("free_shipping_threshold")
        if threshold:
            response += f"\n💡 **Free shipping** on orders over ${threshold:.2f}!"
        
        return response
    
    def _format_cost_response(self, query: str) -> str:
        """Format response focused on costs."""
        options = self.delivery_data.get("delivery_options", [])
        
        # Check if query mentions specific method
        specific_option = None
        for option in options:
            if option['name'].lower() in query or option['code'].lower() in query:
                specific_option = option
                break
        
        if specific_option:
            response = f"**{specific_option['name']}**\n\n"
            response += f"💰 **Cost:** ${specific_option['cost']:.2f}\n"
            response += f"📅 **Delivery Time:** {specific_option['estimated_days']} business days\n"
            response += f"📦 {specific_option['description']}\n"
            
            if specific_option.get('features'):
                response += f"\n✨ **Features:**\n"
                for feature in specific_option['features']:
                    response += f"  • {feature}\n"
            
            return response
        
        # Show all costs
        response = "Here are our shipping costs:\n\n"
        for option in sorted(options, key=lambda x: x['cost']):
            response += f"• {option['name']}: ${option['cost']:.2f} ({option['estimated_days']} days)\n"
        
        return response
    
    def _format_fast_delivery_response(self) -> str:
        """Format response for fast delivery options."""
        options = self.delivery_data.get("delivery_options", [])
        
        # Sort by estimated days
        fast_options = sorted(options, key=lambda x: x['estimated_days'])[:3]
        
        response = "Here are our fastest delivery options:\n\n"
        
        for option in fast_options:
            response += f"• **{option['name']}**: {option['estimated_days']} days - ${option['cost']:.2f}\n"
            response += f"  {option['description']}\n"
            
            if option.get('restrictions'):
                response += f"  ⚠️  Note: {'; '.join(option['restrictions'])}\n"
            
            response += "\n"
        
        return response
    
    def _format_pickup_response(self) -> str:
        """Format response for pickup options."""
        options = self.delivery_data.get("delivery_options", [])
        
        pickup_options = [opt for opt in options if opt['code'] == 'PICKUP']
        
        if not pickup_options:
            return "Local pickup is not currently available. Please choose a shipping method."
        
        response = "Here are our pickup options:\n\n"
        
        for option in pickup_options:
            response += f"• **{option['name']}**: ${option['cost']:.2f}\n"
            response += f"  {option['description']}\n\n"
            
            if option.get('features'):
                response += "  ✨ Features:\n"
                for feature in option['features']:
                    response += f"    • {feature}\n"
        
        return response
    
    def _format_international_response(self) -> str:
        """Format response for international shipping."""
        options = self.delivery_data.get("delivery_options", [])
        
        intl_options = [opt for opt in options if 'International' in opt.get('coverage', [])]
        
        if not intl_options:
            return "We currently don't offer international shipping. Please contact customer service for special arrangements."
        
        response = "Here are our international shipping options:\n\n"
        
        for option in intl_options:
            response += f"• **{option['name']}**: ${option['cost']:.2f}\n"
            response += f"  Delivery: {option['estimated_days']} business days\n"
            response += f"  {option['description']}\n"
            
            if option.get('restrictions'):
                response += f"\n  ⚠️  Important:\n"
                for restriction in option['restrictions']:
                    response += f"    • {restriction}\n"
            
            response += "\n"
        
        return response
    
    def _format_free_shipping_response(self) -> str:
        """Format response about free shipping."""
        policies = self.delivery_data.get("shipping_policies", {})
        threshold = policies.get("free_shipping_threshold")
        
        if not threshold:
            return "We don't currently offer free shipping. Please see our delivery options for costs."
        
        response = f"🎁 **Free Shipping Available!**\n\n"
        response += f"Get **free standard shipping** on orders over **${threshold:.2f}**!\n\n"
        response += "Benefits:\n"
        response += "• No shipping charges\n"
        response += "• Same great tracking and service\n"
        response += "• Applies to standard ground shipping\n\n"
        response += f"💡 Orders under ${threshold:.2f} qualify for our regular shipping rates."
        
        return response


# Test function
async def test_delivery_agent():
    """Test the DeliveryAgent with sample queries."""
    
    print("=" * 80)
    print("DELIVERY AGENT TEST")
    print("=" * 80 + "\n")
    
    agent = DeliveryAgent(config_path="data/delivery_rules.yaml")
    
    test_queries = [
        "What are the delivery options?",
        "How much does express shipping cost?",
        "Can I get overnight delivery?",
        "What's the fastest delivery method?",
        "Do you offer pickup?",
        "What about international shipping?",
        "Is there free shipping?",
    ]
    
    for query in test_queries:
        print(f"👤 USER: {query}")
        
        request = QueryRequest(query=query, session_id="test")
        response = await agent.process_query(request)
        
        print(f"🤖 {response.agent_name}:")
        print(response.response)
        print("\n" + "-" * 80 + "\n")
        await asyncio.sleep(0.5)
    
    print("=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_delivery_agent())
