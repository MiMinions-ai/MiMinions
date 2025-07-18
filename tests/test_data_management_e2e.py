"""
End-to-end tests for the local data management system.

These tests validate the complete workflow and integration between
all components of the data management system.
"""

import tempfile
import unittest
from pathlib import Path

from src.miminions.data.local import LocalDataManager


class TestDataManagementE2E(unittest.TestCase):
    """End-to-end tests for the data management system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = LocalDataManager(Path(self.temp_dir) / "test_miminions", author="test_user")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_complete_workflow(self):
        """Test complete workflow from adding files to cleanup."""
        
        # 1. Add different types of content
        text_id = self.manager.add_content(
            content="This is a test document.",
            name="test.txt",
            description="Test document",
            tags=["test", "documentation"]
        )
        
        markdown_id = self.manager.add_content(
            content="# Test\n\nThis is markdown content.",
            name="test.md",
            file_type="markdown",
            description="Test markdown",
            tags=["test", "markdown"]
        )
        
        csv_id = self.manager.add_content(
            content="name,value\ntest1,100\ntest2,200",
            name="test.csv",
            file_type="csv",
            description="Test data",
            tags=["test", "data"]
        )
        
        # 2. Verify files were added correctly
        self.assertEqual(len(self.manager.list_files()), 3)
        
        # 3. Test search functionality
        test_files = self.manager.search_files(tags=["test"])
        self.assertEqual(len(test_files), 3)
        
        doc_files = self.manager.search_files(tags=["documentation"])
        self.assertEqual(len(doc_files), 1)
        
        data_files = self.manager.search_files(file_type="csv")
        self.assertEqual(len(data_files), 1)
        
        # 4. Test content retrieval
        text_content = self.manager.get_content(text_id)
        self.assertEqual(text_content, "This is a test document.")
        
        # 5. Test metadata updates
        success = self.manager.update_metadata(text_id, {
            "description": "Updated test document"
        })
        self.assertTrue(success)
        
        updated_metadata = self.manager.get_file(text_id)
        self.assertEqual(updated_metadata.description, "Updated test document")
        
        # 6. Test file extraction
        extract_path = Path(self.temp_dir) / "extracted_test.txt"
        success = self.manager.extract_file(text_id, extract_path)
        self.assertTrue(success)
        self.assertTrue(extract_path.exists())
        self.assertEqual(extract_path.read_text(), "This is a test document.")
        
        # 7. Test activity tracking
        activity = self.manager.get_recent_activity(10)
        self.assertGreater(len(activity), 0)
        
        file_history = self.manager.get_file_history(text_id)
        self.assertGreater(len(file_history), 0)
        
        # 8. Test system statistics
        stats = self.manager.get_stats()
        self.assertEqual(stats['index']['total_files'], 3)
        self.assertEqual(stats['storage']['total_files'], 3)
        self.assertGreater(stats['transaction_log']['total_records'], 0)
        
        # 9. Test file deletion
        success = self.manager.delete_file(csv_id)
        self.assertTrue(success)
        
        self.assertEqual(len(self.manager.list_files()), 2)
        self.assertIsNone(self.manager.get_file(csv_id))
        
        # 10. Test backup and restore
        backup_dir = Path(self.temp_dir) / "backup"
        backup_success = self.manager.backup_system(backup_dir)
        self.assertTrue(backup_success)
        
        # Verify backup files exist
        self.assertTrue((backup_dir / "backup_info.json").exists())
        self.assertTrue((backup_dir / "miminions_backup").exists())
        
        # Test restore
        original_files = len(self.manager.list_files())
        
        # Add a file to differentiate state
        temp_id = self.manager.add_content("temp content", "temp.txt")
        self.assertEqual(len(self.manager.list_files()), original_files + 1)
        
        # Restore from backup
        restore_success = self.manager.restore_from_backup(backup_dir)
        self.assertTrue(restore_success)
        
        # Should be back to original state
        self.assertEqual(len(self.manager.list_files()), original_files)
        self.assertIsNone(self.manager.get_file(temp_id))
    
    def test_physical_file_integration(self):
        """Test integration with physical files."""
        
        # Create test files
        test_files = {
            "test.txt": "This is a text file",
            "test.md": "# Markdown\n\nContent here",
            "test.csv": "name,age\nJohn,25\nJane,30"
        }
        
        file_ids = []
        for filename, content in test_files.items():
            file_path = Path(self.temp_dir) / filename
            file_path.write_text(content)
            
            file_id = self.manager.add_file(file_path, description=f"Test {filename}")
            file_ids.append(file_id)
        
        # Verify all files were added
        self.assertEqual(len(self.manager.list_files()), 3)
        
        # Test that content matches
        for file_id, (filename, original_content) in zip(file_ids, test_files.items()):
            retrieved_content = self.manager.get_content(file_id)
            self.assertEqual(retrieved_content, original_content)
            
            metadata = self.manager.get_file(file_id)
            self.assertEqual(metadata.original_name, filename)
    
    def test_deduplication(self):
        """Test that identical content is deduplicated."""
        
        # Add the same content multiple times
        content = "This is identical content"
        
        id1 = self.manager.add_content(content, "file1.txt")
        id2 = self.manager.add_content(content, "file2.txt")
        id3 = self.manager.add_content(content, "file3.txt")
        
        # Should have 3 index entries
        self.assertEqual(len(self.manager.list_files()), 3)
        
        # But should have only 1 storage file (deduplication)
        stats = self.manager.get_stats()
        self.assertEqual(stats['storage']['total_files'], 1)
        
        # All should return the same content
        content1 = self.manager.get_content(id1)
        content2 = self.manager.get_content(id2)
        content3 = self.manager.get_content(id3)
        
        self.assertEqual(content1, content)
        self.assertEqual(content2, content)
        self.assertEqual(content3, content)
    
    def test_large_scale_operations(self):
        """Test system with many files."""
        
        # Add multiple files
        file_ids = []
        for i in range(20):
            file_id = self.manager.add_content(
                content=f"Content for file {i}",
                name=f"file_{i:02d}.txt",
                description=f"Test file number {i}",
                tags=["batch", f"group_{i // 5}"]
            )
            file_ids.append(file_id)
        
        # Verify all files were added
        self.assertEqual(len(self.manager.list_files()), 20)
        
        # Test search with many results
        batch_files = self.manager.search_files(tags=["batch"])
        self.assertEqual(len(batch_files), 20)
        
        # Test search with subset
        group_0_files = self.manager.search_files(tags=["group_0"])
        self.assertEqual(len(group_0_files), 5)
        
        # Test statistics with many files
        stats = self.manager.get_stats()
        self.assertEqual(stats['index']['total_files'], 20)
        self.assertEqual(stats['storage']['total_files'], 20)  # All unique content
        
        # Test recent activity
        recent = self.manager.get_recent_activity(25)
        self.assertGreaterEqual(len(recent), 20)  # At least 20 write operations
    
    def test_error_handling(self):
        """Test error handling and edge cases."""
        
        # Test adding non-existent file
        with self.assertRaises(FileNotFoundError):
            self.manager.add_file("/non/existent/file.txt")
        
        # Test getting non-existent file
        fake_id = "fake-id-12345"
        self.assertIsNone(self.manager.get_file(fake_id))
        self.assertIsNone(self.manager.get_content(fake_id))
        
        # Test updating non-existent file
        success = self.manager.update_metadata(fake_id, {"description": "test"})
        self.assertFalse(success)
        
        # Test deleting non-existent file
        success = self.manager.delete_file(fake_id)
        self.assertFalse(success)
        
        # Test extracting non-existent file
        extract_path = Path(self.temp_dir) / "fake_extract.txt"
        success = self.manager.extract_file(fake_id, extract_path)
        self.assertFalse(success)
        self.assertFalse(extract_path.exists())


if __name__ == '__main__':
    unittest.main()