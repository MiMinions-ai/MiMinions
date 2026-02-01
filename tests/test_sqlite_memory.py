"""SQLite Memory CRUD tests for Pydantic Agent."""
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent.pydantic_agent import create_pydantic_agent
from miminions.agent.pydantic_agent.models import ExecutionStatus


def test_create():
    print("test: create")
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("TestAgent", memory=memory)
    
    result = agent.execute("memory_store", text="Python is a programming language")
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result is not None
    
    result2 = agent.execute("memory_store", text="SQLite is a database", metadata={"source": "test"})
    assert result.result != result2.result
    memory.close()


def test_get_by_id():
    print("test: get by id")
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("TestAgent", memory=memory)
    
    store_result = agent.execute("memory_store", text="Test knowledge", metadata={"tag": "test"})
    id = store_result.result
    
    get_result = agent.execute("memory_get", id=id)
    assert get_result.status == ExecutionStatus.SUCCESS
    assert get_result.result["text"] == "Test knowledge"
    assert get_result.result["meta"]["tag"] == "test"
    memory.close()


def test_update():
    print("test: update")
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("TestAgent", memory=memory)
    
    store_result = agent.execute("memory_store", text="Original text")
    id = store_result.result
    
    update_result = agent.execute("memory_update", id=id, new_text="Updated text")
    assert update_result.result is True
    
    get_result = agent.execute("memory_get", id=id)
    assert get_result.result["text"] == "Updated text"
    memory.close()


def test_delete():
    print("test: delete")
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("TestAgent", memory=memory)
    
    store_result = agent.execute("memory_store", text="Test entry")
    id = store_result.result
    
    delete_result = agent.execute("memory_delete", id=id)
    assert delete_result.result is True
    
    get_result = agent.execute("memory_get", id=id)
    assert get_result.result is None
    memory.close()


def test_list_all():
    print("test: list all")
    memory = SQLiteMemory(db_path=":memory:")
    agent = create_pydantic_agent("TestAgent", memory=memory)
    
    agent.execute("memory_store", text="Entry 1")
    agent.execute("memory_store", text="Entry 2")
    agent.execute("memory_store", text="Entry 3")
    
    list_result = agent.execute("memory_list")
    assert len(list_result.result) == 3
    memory.close()


if __name__ == "__main__":
    print("Pydantic Agent SQLite CRUD Tests")
    tests = [test_create, test_get_by_id, test_update, test_delete, test_list_all]
    for test in tests:
        test()
    print("All tests passed")
