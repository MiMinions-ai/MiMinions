"""SQLite Memory CRUD Example for Pydantic Agent."""
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent.pydantic_agent import create_pydantic_agent
from miminions.agent.pydantic_agent.models import ExecutionStatus


def demo_crud():
    print("Pydantic Agent SQLite Memory CRUD Demo")
    
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("CRUDAgent", memory=memory)
    
    print("Creating entries")
    result = agent.execute("memory_store", text="Python is a programming language", metadata={"source": "demo"})
    print(f"  Status: {result.status.value}")
    print(f"  ID: {result.result[:8]}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")
    id1 = result.result
    
    result2 = agent.execute("memory_store", text="SQLite is a database")
    id2 = result2.result
    
    print("Reading by ID")
    result = agent.execute("memory_get", id=id1)
    print(f"  Text: {result.result['text']}")
    print(f"  Meta: {result.result['meta']}")
    
    print("Updating entry")
    result = agent.execute("memory_update", id=id1, new_text="Python is a versatile programming language")
    print(f"  Success: {result.result}")
    
    get_result = agent.execute("memory_get", id=id1)
    print(f"  New text: {get_result.result['text']}")
    
    print("Listing all")
    result = agent.execute("memory_list")
    print(f"  Total: {len(result.result)} entries")
    
    print("Deleting entry")
    result = agent.execute("memory_delete", id=id2)
    print(f"  Deleted: {result.result}")
    
    list_result = agent.execute("memory_list")
    print(f"  Remaining: {len(list_result.result)} entries")
    
    memory.close()
    print("Done")


if __name__ == "__main__":
    demo_crud()
