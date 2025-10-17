# Memory module specification

## Overview

The memory module provides a comprehensive foundation for creating memory management system for MiMinions agents.

## Features

- Specify memory messages and memory management policies
- Specify memory storage and retrieval
- Identify policies and strategies for memory management to choose from
- Create compression, assessment and merge solutions

## Architecture

The memory module is designed to be modular and extensible.

### Core Components

1. **MemoryController** (`src/miminions/memory/controller.py`)
   - Main controller class for memory management
   - Handles message creation, concatenation, merging, assessment, and compression
   - Provides memory storage and retrieval
   - Manages memory policies and strategies

2. **MemoryBase** (`src/miminions/memory/base.py`)
   - Base class for memory management

3. **MemoryConfig** (`src/miminions/memory/config.py`)
   - Configuration class for memory management
