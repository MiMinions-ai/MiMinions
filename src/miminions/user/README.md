# MiMinions User Module

A simple and lightweight user management module for MiMinions.

## Overview

The User module provides basic user management capabilities with minimal complexity. It handles user creation, retrieval, and management using simple data structures.

## Features

- **Simple User Model**: Basic user with name, id, and API key
- **CRUD Operations**: Create, read, update, and delete users
- **File-based Storage**: JSON file persistence for user data
- **API Key Management**: Generate and validate API keys for user access

## User Model

```python
@dataclass
class User:
    id: str
    name: str
    api_key: str
    created_at: datetime
    updated_at: datetime
```

### Fields

- **id**: Unique identifier for the user
- **name**: Display name for the user
- **api_key**: Secret key for API authentication
- **created_at**: Timestamp when user was created
- **updated_at**: Timestamp when user was last updated

## Usage

### Basic Operations

```python
from miminions.user import UserController

# Initialize controller
controller = UserController()

# Create a new user
user = controller.create_user("John Doe")

# Get user by ID
user = controller.get_user("user_123")

# Update user
controller.update_user("user_123", name="Jane Doe")

# Delete user
controller.delete_user("user_123")

# List all users
users = controller.list_users()
```

### API Key Management

```python
# Generate new API key
new_key = controller.generate_api_key("user_123")

# Validate API key
is_valid = controller.validate_api_key("user_123", "api_key_here")
```

## API Reference

### UserController

Main class for managing users.

#### Methods

- `create_user(name: str) -> User`: Create a new user
- `get_user(user_id: str) -> Optional[User]`: Retrieve user by ID
- `update_user(user_id: str, name: str = None) -> bool`: Update user information
- `delete_user(user_id: str) -> bool`: Delete a user
- `list_users() -> List[User]`: Get all users
- `generate_api_key(user_id: str) -> str`: Generate new API key for user
- `validate_api_key(user_id: str, api_key: str) -> bool`: Validate user's API key

## Data Storage

User data is stored in JSON format in the configured data directory. Each user is saved as a separate file for easy management and backup.

## Error Handling

The module provides clear error messages for common scenarios:
- User not found
- Invalid user ID format
- Duplicate user names
- API key validation failures

## Examples

See the test files for comprehensive usage examples and edge cases.
