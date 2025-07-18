#!/usr/bin/env python3
"""
Example demonstrating the MiMinions Local Data Management System.

This example shows how to:
1. Initialize the data management system
2. Add files and content
3. Search and retrieve data
4. Track activity and metadata
5. Use different file types
"""

import tempfile
from pathlib import Path
from miminions.data.local import LocalDataManager


def main():
    """Demonstrate the local data management system."""
    print("🤖 MiMinions Local Data Management System Demo")
    print("=" * 50)
    
    # Create a temporary directory for this demo
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize the data management system
        print("\n📁 Initializing data management system...")
        manager = LocalDataManager(Path(temp_dir) / "demo_miminions", author="demo_user")
        
        # 1. Add text content directly
        print("\n📝 Adding text content...")
        text_content = """
        This is a sample document about AI and machine learning.
        It contains information about neural networks, deep learning,
        and natural language processing.
        """
        
        text_id = manager.add_content(
            content=text_content.strip(),
            name="ai_overview.txt",
            description="Overview of AI concepts",
            tags=["ai", "machine-learning", "documentation"]
        )
        print(f"   Added text file with ID: {text_id}")
        
        # 2. Add markdown content
        print("\n📄 Adding markdown content...")
        markdown_content = """
# Project Planning Document

## Overview
This document outlines the planning for our AI project.

## Goals
- Implement neural networks
- Train on large datasets
- Deploy to production

## Timeline
- Week 1: Data collection
- Week 2: Model training
- Week 3: Testing and validation

## Resources
- [TensorFlow Documentation](https://tensorflow.org)
- [PyTorch Tutorials](https://pytorch.org)
        """
        
        md_id = manager.add_content(
            content=markdown_content.strip(),
            name="project_plan.md",
            file_type="markdown",
            description="Project planning document",
            tags=["project", "planning", "ai"]
        )
        print(f"   Added markdown file with ID: {md_id}")
        
        # 3. Add CSV data
        print("\n📊 Adding CSV data...")
        csv_content = """
Name,Age,Department,Salary
Alice Johnson,28,Engineering,75000
Bob Smith,34,Marketing,65000
Carol Davis,29,Engineering,80000
David Wilson,31,Sales,70000
Eve Brown,26,Engineering,72000
        """
        
        csv_id = manager.add_content(
            content=csv_content.strip(),
            name="employee_data.csv",
            file_type="csv",
            description="Employee database",
            tags=["data", "employees", "hr"]
        )
        print(f"   Added CSV file with ID: {csv_id}")
        
        # 4. Create and add a physical file
        print("\n💾 Creating and adding a physical file...")
        temp_file = Path(temp_dir) / "temp_notes.txt"
        temp_file.write_text("These are temporary notes about the project.\nImportant reminders and todo items.")
        
        file_id = manager.add_file(
            temp_file,
            description="Temporary project notes",
            tags=["notes", "temporary", "project"]
        )
        print(f"   Added physical file with ID: {file_id}")
        
        # 5. Display system statistics
        print("\n📈 System Statistics:")
        stats = manager.get_stats()
        print(f"   Total files: {stats['index']['total_files']}")
        print(f"   Storage size: {stats['storage']['total_size_mb']} MB")
        print(f"   Supported file types: {', '.join(stats['supported_file_types'])}")
        print(f"   Available tags: {', '.join(manager.get_tags())}")
        
        # 6. Search functionality
        print("\n🔍 Search Examples:")
        
        # Search by tags
        ai_files = manager.search_files(tags=["ai"])
        print(f"   Files tagged with 'ai': {len(ai_files)}")
        for file_meta in ai_files:
            print(f"     - {file_meta.original_name}: {file_meta.description}")
        
        # Search by file type
        engineering_files = manager.search_files(tags=["engineering"])
        if engineering_files:
            print(f"   Files tagged with 'engineering': {len(engineering_files)}")
        
        # Search by name pattern
        project_files = manager.search_files(name_pattern="project")
        print(f"   Files with 'project' in name: {len(project_files)}")
        for file_meta in project_files:
            print(f"     - {file_meta.original_name}")
        
        # 7. Retrieve and display content
        print("\n📖 Content Retrieval:")
        
        # Get the markdown content
        md_content = manager.get_content(md_id)
        if md_content:
            preview = md_content[:100] + "..." if len(md_content) > 100 else md_content
            print(f"   Markdown content preview:\n{preview}")
        
        # 8. Update metadata
        print("\n✏️  Updating metadata...")
        manager.update_metadata(text_id, {
            "description": "Updated: Comprehensive overview of AI concepts",
            "tags": manager.get_file(text_id).tags + ["updated"]
        })
        
        updated_file = manager.get_file(text_id)
        print(f"   Updated description: {updated_file.description}")
        print(f"   Updated tags: {', '.join(updated_file.tags)}")
        
        # 9. Activity tracking
        print("\n📋 Recent Activity:")
        recent_activity = manager.get_recent_activity(5)
        for activity in recent_activity:
            print(f"   {activity.timestamp[:19]}: {activity.transaction_type.value} - {activity.file_name or 'N/A'}")
        
        # 10. File details
        print("\n📋 File Details:")
        all_files = manager.list_files()
        for file_meta in all_files:
            print(f"\n   📄 {file_meta.original_name}")
            print(f"      ID: {file_meta.id}")
            print(f"      Type: {file_meta.file_type}")
            print(f"      Size: {file_meta.size_bytes} bytes")
            print(f"      Tags: {', '.join(file_meta.tags)}")
            print(f"      Accessed: {file_meta.access_count} times")
            print(f"      Created: {file_meta.created_at[:19]}")
        
        # 11. Demonstrate file extraction
        print("\n💾 File Extraction Demo:")
        extract_dir = Path(temp_dir) / "extracted"
        extract_dir.mkdir(exist_ok=True)
        
        extract_path = extract_dir / "extracted_ai_overview.txt"
        if manager.extract_file(text_id, extract_path):
            print(f"   Successfully extracted file to: {extract_path}")
            print(f"   Extracted content: {extract_path.read_text()[:50]}...")
        
        print("\n✅ Demo completed successfully!")
        print(f"\n📊 Final Statistics:")
        final_stats = manager.get_stats()
        print(f"   Index entries: {final_stats['index']['total_files']}")
        print(f"   Storage files: {final_stats['storage']['total_files']}")
        print(f"   Transaction records: {final_stats['transaction_log']['total_records']}")
        print(f"   Data directory: {final_stats['base_directory']}")


if __name__ == "__main__":
    main()