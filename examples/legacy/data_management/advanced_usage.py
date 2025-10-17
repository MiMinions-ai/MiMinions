#!/usr/bin/env python3
"""
Advanced usage example for the MiMinions Local Data Management System.

This example demonstrates:
1. Custom file handlers
2. Batch operations
3. Advanced search queries
4. Backup/restore workflows
5. Integration patterns
"""

import tempfile
import json
from pathlib import Path
from miminions.data.local import LocalDataManager, FileHandler


class JSONFileHandler(FileHandler):
    """Custom handler for JSON files."""
    
    def get_file_type(self) -> str:
        return "json"
    
    def can_handle(self, file_path, mime_type=None) -> bool:
        return Path(file_path).suffix.lower() == '.json'
    
    def extract_metadata(self, file_path) -> dict:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            metadata = {
                'encoding': 'utf-8',
                'keys': list(data.keys()) if isinstance(data, dict) else [],
                'is_array': isinstance(data, list),
                'is_object': isinstance(data, dict),
                'size': len(data) if isinstance(data, (list, dict)) else 0
            }
            
            return metadata
        except Exception as e:
            return {'error': str(e)}
    
    def get_content_preview(self, file_path, max_chars=500) -> str:
        try:
            with open(file_path, 'r') as f:
                content = f.read(max_chars)
            return content
        except Exception as e:
            return f"Error reading JSON file: {e}"
    
    def get_default_tags(self, file_path) -> list:
        tags = super().get_default_tags(file_path)
        
        # Add tags based on content analysis
        metadata = self.extract_metadata(file_path)
        if metadata.get('is_array'):
            tags.append('array')
        if metadata.get('is_object'):
            tags.append('object')
        
        return tags


def demonstrate_custom_handlers():
    """Demonstrate custom file handler registration."""
    print("🔧 Demonstrating Custom File Handlers")
    print("-" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = LocalDataManager(Path(temp_dir) / "custom_demo", author="demo_user")
        
        # Register our custom JSON handler
        manager.file_handlers.register(JSONFileHandler())
        
        # Create and add JSON files
        json_data = {
            "name": "Sample Project",
            "version": "1.0.0",
            "dependencies": ["numpy", "pandas", "scikit-learn"],
            "config": {
                "debug": True,
                "max_workers": 4
            }
        }
        
        json_file = Path(temp_dir) / "config.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Add the JSON file
        file_id = manager.add_file(json_file, description="Project configuration")
        metadata = manager.get_file(file_id)
        
        print(f"Added JSON file: {metadata.original_name}")
        print(f"File type: {metadata.file_type}")
        print(f"Tags: {', '.join(metadata.tags)}")
        
        # Show that our custom handler was used
        json_files = manager.search_files(file_type="json")
        print(f"Found {len(json_files)} JSON files")
        
        return manager


def demonstrate_batch_operations():
    """Demonstrate batch file operations."""
    print("\n📦 Demonstrating Batch Operations")
    print("-" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = LocalDataManager(Path(temp_dir) / "batch_demo", author="batch_user")
        
        # Create multiple files for batch processing
        file_data = [
            ("report_2023_q1.txt", "Q1 2023 quarterly report data", ["report", "2023", "q1"]),
            ("report_2023_q2.txt", "Q2 2023 quarterly report data", ["report", "2023", "q2"]),
            ("report_2023_q3.txt", "Q3 2023 quarterly report data", ["report", "2023", "q3"]),
            ("analysis_jan.md", "# January Analysis\n\nDetailed analysis for January", ["analysis", "january"]),
            ("analysis_feb.md", "# February Analysis\n\nDetailed analysis for February", ["analysis", "february"]),
            ("data_export.csv", "name,value\nitem1,100\nitem2,200", ["data", "export", "csv"]),
        ]
        
        # Batch add files
        print("Adding files in batch...")
        file_ids = []
        for filename, content, tags in file_data:
            file_id = manager.add_content(
                content=content,
                name=filename,
                description=f"Batch processed file: {filename}",
                tags=tags + ["batch_processed"]
            )
            file_ids.append(file_id)
        
        print(f"Added {len(file_ids)} files")
        
        # Batch search operations
        print("\nBatch search results:")
        
        # Find all 2023 reports
        reports_2023 = manager.search_files(tags=["2023"])
        print(f"2023 Reports: {len(reports_2023)}")
        
        # Find all analysis files
        analysis_files = manager.search_files(tags=["analysis"])
        print(f"Analysis files: {len(analysis_files)}")
        
        # Find all batch processed files
        batch_files = manager.search_files(tags=["batch_processed"])
        print(f"Batch processed files: {len(batch_files)}")
        
        # Batch metadata updates
        print("\nPerforming batch metadata updates...")
        for file_meta in reports_2023:
            manager.update_metadata(file_meta.id, {
                "tags": file_meta.tags + ["reviewed"],
                "description": f"REVIEWED: {file_meta.description}"
            })
        
        # Verify updates
        reviewed_files = manager.search_files(tags=["reviewed"])
        print(f"Reviewed files: {len(reviewed_files)}")
        
        return manager


def demonstrate_advanced_search():
    """Demonstrate advanced search capabilities."""
    print("\n🔍 Demonstrating Advanced Search")
    print("-" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = LocalDataManager(Path(temp_dir) / "search_demo", author="search_user")
        
        # Add diverse content for searching
        test_files = [
            {
                "content": "Machine learning algorithms for data analysis",
                "name": "ml_guide.txt",
                "description": "Comprehensive guide to ML algorithms",
                "tags": ["machine-learning", "algorithms", "guide", "technical"]
            },
            {
                "content": "# Project Documentation\n\n## Machine Learning Module",
                "name": "project_docs.md", 
                "description": "Technical documentation for the project",
                "tags": ["documentation", "project", "technical"]
            },
            {
                "content": "name,algorithm,accuracy\nSVM,Support Vector Machine,0.95\nRF,Random Forest,0.87",
                "name": "results.csv",
                "description": "Algorithm performance results",
                "tags": ["results", "performance", "data"]
            },
            {
                "content": "Personal notes about machine learning concepts",
                "name": "personal_notes.txt",
                "description": "Personal study notes",
                "tags": ["personal", "notes", "study"]
            }
        ]
        
        # Add all test files
        for file_data in test_files:
            manager.add_content(
                content=file_data["content"],
                name=file_data["name"],
                description=file_data["description"],
                tags=file_data["tags"]
            )
        
        print(f"Added {len(test_files)} files for search testing")
        
        # Demonstrate various search strategies
        search_queries = [
            ("Technical files", {"tags": ["technical"]}),
            ("Machine learning content", {"name_pattern": "machine"}),
            ("Documentation files", {"tags": ["documentation"]}),
            ("CSV data files", {"file_type": "csv"}),
            ("Project-related files", {"name_pattern": "project"}),
            ("Files by search_user", {"author": "search_user"}),
        ]
        
        print("\nSearch results:")
        for query_name, query_params in search_queries:
            results = manager.search_files(**query_params)
            print(f"  {query_name}: {len(results)} files")
            for result in results:
                print(f"    - {result.original_name}")
        
        return manager


def demonstrate_backup_restore():
    """Demonstrate backup and restore functionality."""
    print("\n💾 Demonstrating Backup & Restore")
    print("-" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create initial data
        original_dir = Path(temp_dir) / "original"
        manager = LocalDataManager(original_dir, author="backup_user")
        
        # Add some data
        files_added = []
        for i in range(3):
            file_id = manager.add_content(
                content=f"Content for file {i+1}",
                name=f"file_{i+1}.txt",
                description=f"Test file number {i+1}",
                tags=["backup_test", f"file_{i+1}"]
            )
            files_added.append(file_id)
        
        print(f"Created original data with {len(files_added)} files")
        
        # Create backup
        backup_dir = Path(temp_dir) / "backup"
        backup_success = manager.backup_system(backup_dir)
        print(f"Backup created: {backup_success}")
        
        # Show backup contents
        backup_info_file = backup_dir / "backup_info.json"
        if backup_info_file.exists():
            with open(backup_info_file) as f:
                backup_info = json.load(f)
            print(f"Backup info: {backup_info['stats']['index']['total_files']} files backed up")
        
        # Simulate data corruption by adding more files
        corruption_file = manager.add_content("Corrupted data", "corruption.txt", tags=["corruption"])
        print(f"Simulated corruption by adding file: {manager.get_file(corruption_file).original_name}")
        
        current_files = len(manager.list_files())
        print(f"Current files before restore: {current_files}")
        
        # Restore from backup
        restore_success = manager.restore_from_backup(backup_dir)
        print(f"Restore completed: {restore_success}")
        
        restored_files = len(manager.list_files())
        print(f"Files after restore: {restored_files}")
        
        # Verify restoration
        if restored_files == len(files_added):
            print("✅ Restore successful - file count matches original")
        else:
            print("❌ Restore issue - file count mismatch")
        
        return manager


def demonstrate_activity_tracking():
    """Demonstrate activity tracking and analytics."""
    print("\n📊 Demonstrating Activity Tracking")
    print("-" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = LocalDataManager(Path(temp_dir) / "activity_demo", author="activity_user")
        
        # Create and manipulate files to generate activity
        file_id = manager.add_content("Original content", "test.txt", description="Test file")
        
        # Generate various activities
        manager.get_content(file_id)  # Read
        manager.get_content(file_id)  # Another read
        manager.update_metadata(file_id, {"description": "Updated test file"})  # Update
        
        # Add more files
        file_id2 = manager.add_content("Second file content", "test2.txt")
        file_id3 = manager.add_content("Third file content", "test3.txt")
        
        # More activity
        manager.get_content(file_id2)
        manager.delete_file(file_id3)
        
        # Show activity summary
        print("Recent activity:")
        recent_activity = manager.get_recent_activity(10)
        
        activity_summary = {}
        for activity in recent_activity:
            activity_type = activity.transaction_type.value
            activity_summary[activity_type] = activity_summary.get(activity_type, 0) + 1
        
        for activity_type, count in activity_summary.items():
            print(f"  {activity_type}: {count} operations")
        
        # Show file-specific history
        print(f"\nHistory for {manager.get_file(file_id).original_name}:")
        file_history = manager.get_file_history(file_id)
        for record in file_history:
            print(f"  {record.timestamp[:19]}: {record.transaction_type.value}")
        
        # Show access statistics
        file_meta = manager.get_file(file_id)
        print(f"\nFile access statistics:")
        print(f"  Access count: {file_meta.access_count}")
        print(f"  Last accessed: {file_meta.last_accessed[:19] if file_meta.last_accessed else 'Never'}")
        
        return manager


def main():
    """Run all advanced demonstrations."""
    print("🚀 MiMinions Local Data Management - Advanced Examples")
    print("=" * 60)
    
    try:
        # Run all demonstrations
        demonstrate_custom_handlers()
        demonstrate_batch_operations()
        demonstrate_advanced_search()
        demonstrate_backup_restore()
        demonstrate_activity_tracking()
        
        print("\n✅ All advanced demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        raise


if __name__ == "__main__":
    main()