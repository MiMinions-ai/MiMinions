"""
Custom Tools Example for MiMinions BaseAgent

This example demonstrates how to create and manage custom tools
with the BaseAgent for extending functionality.
"""

from miminions.agents import BaseAgent
import asyncio
import json
import math


def basic_tools_example():
    """Demonstrate basic tool management"""
    print("=== Basic Custom Tools Example ===")
    
    agent = BaseAgent(name="ToolAgent")
    
    # Add simple calculator tool
    def calculator(operation, a, b):
        """Simple calculator tool"""
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else "Division by zero!"
        }
        return operations.get(operation, "Unknown operation")(a, b)
    
    agent.add_tool("calculator", calculator)
    
    # Use the calculator
    print("Calculator tool examples:")
    print(f"2 + 3 = {agent.execute_tool('calculator', 'add', 2, 3)}")
    print(f"10 - 4 = {agent.execute_tool('calculator', 'subtract', 10, 4)}")
    print(f"5 * 6 = {agent.execute_tool('calculator', 'multiply', 5, 6)}")
    print(f"15 / 3 = {agent.execute_tool('calculator', 'divide', 15, 3)}")
    
    # List tools
    print(f"\nAvailable tools: {agent.list_tools()}")
    print(f"Has calculator tool: {agent.has_tool('calculator')}")
    
    # Remove tool
    agent.remove_tool("calculator")
    print(f"Tools after removal: {agent.list_tools()}")
    
    agent.close()


def advanced_tools_example():
    """Demonstrate advanced tool features"""
    print("\n=== Advanced Custom Tools Example ===")
    
    agent = BaseAgent(name="AdvancedAgent")
    
    # Add text processing tool
    def text_processor(text, operation="clean"):
        """Advanced text processing tool"""
        if operation == "clean":
            return text.strip().lower()
        elif operation == "word_count":
            return len(text.split())
        elif operation == "reverse":
            return text[::-1]
        elif operation == "capitalize":
            return text.title()
        else:
            return f"Unknown operation: {operation}"
    
    # Add JSON tool
    def json_tool(data, operation="validate"):
        """JSON manipulation tool"""
        try:
            if operation == "validate":
                json.loads(data) if isinstance(data, str) else data
                return True
            elif operation == "pretty":
                parsed = json.loads(data) if isinstance(data, str) else data
                return json.dumps(parsed, indent=2)
            elif operation == "minify":
                parsed = json.loads(data) if isinstance(data, str) else data
                return json.dumps(parsed, separators=(',', ':'))
        except json.JSONDecodeError:
            return f"Invalid JSON for operation: {operation}"
    
    # Add math tool
    def math_tool(operation, *args):
        """Advanced math operations"""
        if operation == "sqrt":
            return math.sqrt(args[0])
        elif operation == "power":
            return math.pow(args[0], args[1])
        elif operation == "factorial":
            return math.factorial(int(args[0]))
        elif operation == "average":
            return sum(args) / len(args)
        elif operation == "max":
            return max(args)
        elif operation == "min":
            return min(args)
        else:
            return f"Unknown math operation: {operation}"
    
    # Add all tools
    agent.add_tool("text_processor", text_processor)
    agent.add_tool("json_tool", json_tool)
    agent.add_tool("math_tool", math_tool)
    
    # Demonstrate text processing
    print("Text processing examples:")
    text = "  Hello World!  "
    print(f"Original: '{text}'")
    print(f"Clean: '{agent.execute_tool('text_processor', text, 'clean')}'")
    print(f"Word count: {agent.execute_tool('text_processor', text, 'word_count')}")
    print(f"Reverse: '{agent.execute_tool('text_processor', text, 'reverse')}'")
    print(f"Capitalize: '{agent.execute_tool('text_processor', text, 'capitalize')}'")
    
    # Demonstrate JSON tool
    print("\nJSON tool examples:")
    json_data = '{"name": "John", "age": 30, "city": "New York"}'
    print(f"Valid JSON: {agent.execute_tool('json_tool', json_data, 'validate')}")
    print("Pretty JSON:")
    print(agent.execute_tool('json_tool', json_data, 'pretty'))
    
    # Demonstrate math tool
    print("\nMath tool examples:")
    print(f"sqrt(16) = {agent.execute_tool('math_tool', 'sqrt', 16)}")
    print(f"2^3 = {agent.execute_tool('math_tool', 'power', 2, 3)}")
    print(f"5! = {agent.execute_tool('math_tool', 'factorial', 5)}")
    print(f"average(1,2,3,4,5) = {agent.execute_tool('math_tool', 'average', 1, 2, 3, 4, 5)}")
    
    print(f"\nAll tools: {agent.list_tools()}")
    
    agent.close()


async def async_tools_example():
    """Demonstrate async tool functionality"""
    print("\n=== Async Custom Tools Example ===")
    
    agent = BaseAgent(name="AsyncAgent")
    
    # Add async tool
    async def async_data_fetcher(source, delay=1):
        """Simulate async data fetching"""
        await asyncio.sleep(delay)
        data_sources = {
            "weather": {"temperature": 22, "humidity": 65, "condition": "sunny"},
            "news": {"headline": "AI Advances Continue", "category": "technology"},
            "stocks": {"AAPL": 150.25, "GOOGL": 2800.50, "MSFT": 300.75}
        }
        return data_sources.get(source, {"error": "Unknown data source"})
    
    # Add async processing tool
    async def async_processor(data_list, operation="sum"):
        """Async data processing"""
        await asyncio.sleep(0.5)  # Simulate processing time
        
        if operation == "sum":
            return sum(data_list)
        elif operation == "average":
            return sum(data_list) / len(data_list)
        elif operation == "sort":
            return sorted(data_list)
        elif operation == "unique":
            return list(set(data_list))
        else:
            return f"Unknown operation: {operation}"
    
    agent.add_tool("async_fetcher", async_data_fetcher)
    agent.add_tool("async_processor", async_processor)
    
    # Use async tools
    print("Fetching weather data...")
    weather = await agent.execute_tool_async("async_fetcher", "weather", 0.5)
    print(f"Weather: {weather}")
    
    print("\nFetching stock data...")
    stocks = await agent.execute_tool_async("async_fetcher", "stocks", 0.3)
    print(f"Stocks: {stocks}")
    
    print("\nProcessing data...")
    data = [1, 2, 3, 4, 5, 2, 3, 1]
    result = await agent.execute_tool_async("async_processor", data, "unique")
    print(f"Unique values from {data}: {result}")
    
    await agent.close_async()


def error_handling_example():
    """Demonstrate error handling in tools"""
    print("\n=== Tool Error Handling Example ===")
    
    agent = BaseAgent(name="ErrorHandlingAgent")
    
    def safe_divider(a, b):
        """Tool with error handling"""
        try:
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
        except Exception as e:
            return f"Error: {str(e)}"
    
    def file_reader(filename):
        """Tool that might fail"""
        try:
            with open(filename, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File '{filename}' not found"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    agent.add_tool("safe_divider", safe_divider)
    agent.add_tool("file_reader", file_reader)
    
    # Test error scenarios
    print("Error handling examples:")
    print(f"10 / 2 = {agent.execute_tool('safe_divider', 10, 2)}")
    print(f"10 / 0 = {agent.execute_tool('safe_divider', 10, 0)}")
    print(f"Read existing file: {agent.execute_tool('file_reader', '/etc/hostname')}")
    print(f"Read non-existing file: {agent.execute_tool('file_reader', 'nonexistent.txt')}")
    
    # Test tool that doesn't exist
    try:
        agent.execute_tool("nonexistent_tool", "arg")
    except ValueError as e:
        print(f"Expected error for missing tool: {e}")
    
    agent.close()


def tool_composition_example():
    """Demonstrate composing tools together"""
    print("\n=== Tool Composition Example ===")
    
    agent = BaseAgent(name="CompositionAgent")
    
    # Add individual tools
    def text_splitter(text, delimiter=" "):
        """Split text into list"""
        return text.split(delimiter)
    
    def list_processor(items, operation="count"):
        """Process list of items"""
        if operation == "count":
            return len(items)
        elif operation == "unique":
            return len(set(items))
        elif operation == "longest":
            return max(items, key=len) if items else ""
        elif operation == "shortest":
            return min(items, key=len) if items else ""
        else:
            return items
    
    def text_analyzer(text):
        """Compose tools to analyze text"""
        # Use other tools
        words = agent.execute_tool("text_splitter", text)
        word_count = agent.execute_tool("list_processor", words, "count")
        unique_count = agent.execute_tool("list_processor", words, "unique")
        longest_word = agent.execute_tool("list_processor", words, "longest")
        
        return {
            "total_words": word_count,
            "unique_words": unique_count,
            "longest_word": longest_word,
            "words": words
        }
    
    agent.add_tool("text_splitter", text_splitter)
    agent.add_tool("list_processor", list_processor)
    agent.add_tool("text_analyzer", text_analyzer)
    
    # Use composed tool
    text = "The quick brown fox jumps over the lazy dog"
    analysis = agent.execute_tool("text_analyzer", text)
    
    print(f"Text: '{text}'")
    print(f"Analysis: {json.dumps(analysis, indent=2)}")
    
    agent.close()


def dynamic_tools_example():
    """Demonstrate dynamic tool creation"""
    print("\n=== Dynamic Tool Creation Example ===")
    
    agent = BaseAgent(name="DynamicAgent")
    
    # Tool factory function
    def create_converter_tool(from_unit, to_unit, factor):
        """Create a unit conversion tool dynamically"""
        def converter(value):
            return value * factor
        
        converter.__name__ = f"{from_unit}_to_{to_unit}"
        converter.__doc__ = f"Convert {from_unit} to {to_unit}"
        return converter
    
    # Create multiple conversion tools
    conversions = [
        ("celsius", "fahrenheit", lambda c: c * 9/5 + 32),
        ("meters", "feet", lambda m: m * 3.28084),
        ("kg", "pounds", lambda kg: kg * 2.20462),
        ("miles", "km", lambda mi: mi * 1.60934)
    ]
    
    # Add dynamic tools
    for from_unit, to_unit, formula in conversions:
        tool_name = f"{from_unit}_to_{to_unit}"
        agent.add_tool(tool_name, lambda value, f=formula: f(value))
    
    # Use dynamic tools
    print("Dynamic conversion tools:")
    print(f"25°C to °F: {agent.execute_tool('celsius_to_fahrenheit', 25):.1f}°F")
    print(f"100 meters to feet: {agent.execute_tool('meters_to_feet', 100):.1f} ft")
    print(f"70 kg to pounds: {agent.execute_tool('kg_to_pounds', 70):.1f} lbs")
    print(f"10 miles to km: {agent.execute_tool('miles_to_km', 10):.1f} km")
    
    print(f"\nDynamic tools created: {agent.list_tools()}")
    
    agent.close()


if __name__ == "__main__":
    # Run all examples
    basic_tools_example()
    advanced_tools_example()
    error_handling_example()
    tool_composition_example()
    dynamic_tools_example()
    
    # Run async example
    asyncio.run(async_tools_example())
    
    print("\n=== Custom Tools Examples Completed ===")