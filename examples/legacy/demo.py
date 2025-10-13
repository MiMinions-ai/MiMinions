"""
Example usage of MiMinions Generic Tool Module
"""

from miminions.tools import tool
from miminions.agent.simple_agent import Agent


# Define some example tools
@tool(name="weather_lookup", description="Get weather information for a location")
def get_weather(location: str, units: str = "celsius") -> str:
    """Get weather information for a location"""
    # This is a mock implementation
    temp = 22 if units == "celsius" else 72
    return f"The weather in {location} is {temp}°{units[0].upper()}"


@tool(name="currency_converter", description="Convert between currencies")
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert currency amounts"""
    # Mock conversion rates
    rates = {"USD": 1.0, "EUR": 0.85, "GBP": 0.73, "JPY": 110.0}
    
    if from_currency not in rates or to_currency not in rates:
        return "Unsupported currency"
    
    # Convert to USD first, then to target currency
    usd_amount = amount / rates[from_currency]
    converted_amount = usd_amount * rates[to_currency]
    
    return f"{amount} {from_currency} = {converted_amount:.2f} {to_currency}"


@tool(name="text_analyzer", description="Analyze text content")
def analyze_text(text: str) -> str:
    """Analyze text and return statistics"""
    words = text.split()
    chars = len(text)
    sentences = text.count('.') + text.count('!') + text.count('?')
    
    return f"Text analysis: {len(words)} words, {chars} characters, {sentences} sentences"


def main():
    """Demo the generic tool system"""
    print("MiMinions Generic Tool Demo")
    print("=" * 40)
    
    # Create an agent
    agent = Agent("demo_agent", "A demo agent with various tools")
    
    # Add tools to the agent
    agent.add_tool(get_weather)
    agent.add_tool(convert_currency)
    agent.add_tool(analyze_text)
    
    print(f"Agent created: {agent}")
    print(f"Available tools: {agent.list_tools()}")
    print()
    
    # Test the tools
    print("Testing tools directly:")
    print(f"Weather: {get_weather.run(location='London')}")
    print(f"Currency: {convert_currency.run(amount=100, from_currency='USD', to_currency='EUR')}")
    print(f"Text Analysis: {analyze_text.run(text='Hello world! This is a test.')}")
    print()
    
    # Test via agent
    print("Testing tools via agent:")
    print(f"Weather: {agent.execute_tool('weather_lookup', location='Tokyo', units='fahrenheit')}")
    print(f"Currency: {agent.execute_tool('currency_converter', amount=50, from_currency='GBP', to_currency='JPY')}")
    print(f"Text Analysis: {agent.execute_tool('text_analyzer', text='The quick brown fox jumps over the lazy dog.')}")
    print()
    
    # Show framework compatibility
    print("Framework compatibility:")
    print(f"LangChain tools: {len(agent.to_langchain_tools())}")
    print(f"AutoGen tools: {len(agent.to_autogen_tools())}")
    print(f"AGNO tools: {len(agent.to_agno_tools())}")
    print()
    
    # Show tool schemas
    print("Tool schemas:")
    for i, schema in enumerate(agent.get_tools_schema(), 1):
        print(f"{i}. {schema['name']}: {schema['description']}")
    
    print("\nDemo completed!")


if __name__ == "__main__":
    main()