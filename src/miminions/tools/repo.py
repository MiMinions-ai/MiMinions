from datetime import datetime
from typing import Optional, List, Dict, Union
from pathlib import Path
import git
from git import Repo
from phi.tool.toolkit import Toolkit
from phi.tool.tool import Tool
from phi.tool.parameter import Parameter

class RepoAnalysisTool(Toolkit):
    """A toolkit for analyzing Git repositories, both local and from GitHub."""
    
    def __init__(self):
        super().__init__(
            name="repo_analysis",
            description="Analyze Git repositories for commit history and changes",
            tools=[
                self.analyze_repo
            ]
        )
    
    def analyze_repo(
        self,
        repo_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        branches: Optional[List[str]] = None,
        is_github: bool = False
    ) -> Dict:
        """
        Analyze a Git repository for commit history and changes.
        
        Args:
            repo_path: Path to local repository or GitHub repository URL
            start_date: Start date for analysis in YYYY-MM-DD format
            end_date: End date for analysis in YYYY-MM-DD format
            branches: List of branch names to analyze. If None, analyzes all branches
            is_github: Whether the repo_path is a GitHub URL
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Clone GitHub repository if needed
            if is_github:
                temp_dir = Path("temp_repo")
                if temp_dir.exists():
                    import shutil
                    shutil.rmtree(temp_dir)
                repo = Repo.clone_from(repo_path, temp_dir)
            else:
                repo = Repo(repo_path)
            
            # Convert date strings to datetime objects
            start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
            
            # Get branches to analyze
            if branches is None:
                branches = [branch.name for branch in repo.heads]
            
            analysis_results = {
                "total_commits": 0,
                "branches": {},
                "authors": {},
                "date_range": {
                    "start": start_date,
                    "end": end_date
                }
            }
            
            # Analyze each branch
            for branch_name in branches:
                try:
                    branch = repo.heads[branch_name]
                    branch_commits = []
                    
                    # Iterate through commits
                    for commit in branch.iter_commits():
                        commit_date = datetime.fromtimestamp(commit.committed_datetime.timestamp())
                        
                        # Filter by date range if specified
                        if start_dt and commit_date < start_dt:
                            continue
                        if end_dt and commit_date > end_dt:
                            continue
                        
                        commit_info = {
                            "hash": commit.hexsha,
                            "author": commit.author.name,
                            "date": commit_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "message": commit.message,
                            "files_changed": len(commit.stats.files),
                            "insertions": commit.stats.total["insertions"],
                            "deletions": commit.stats.total["deletions"]
                        }
                        
                        branch_commits.append(commit_info)
                        
                        # Update author statistics
                        if commit.author.name in analysis_results["authors"]:
                            analysis_results["authors"][commit.author.name] += 1
                        else:
                            analysis_results["authors"][commit.author.name] = 1
                    
                    analysis_results["branches"][branch_name] = {
                        "total_commits": len(branch_commits),
                        "commits": branch_commits
                    }
                    analysis_results["total_commits"] += len(branch_commits)
                    
                except git.exc.GitCommandError as e:
                    print(f"Error analyzing branch {branch_name}: {str(e)}")
                    continue
            
            # Clean up temporary directory if it was a GitHub repository
            if is_github and temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
            
            return analysis_results
            
        except Exception as e:
            return {"error": str(e)}
    
    @property
    def analyze_repo_tool(self) -> Tool:
        """Get the analyze_repo tool with its parameters."""
        return Tool(
            name="analyze_repo",
            description="Analyze a Git repository for commit history and changes",
            parameters=[
                Parameter(
                    name="repo_path",
                    type="string",
                    description="Path to local repository or GitHub repository URL",
                    required=True
                ),
                Parameter(
                    name="start_date",
                    type="string",
                    description="Start date for analysis in YYYY-MM-DD format",
                    required=False
                ),
                Parameter(
                    name="end_date",
                    type="string",
                    description="End date for analysis in YYYY-MM-DD format",
                    required=False
                ),
                Parameter(
                    name="branches",
                    type="array",
                    description="List of branch names to analyze. If None, analyzes all branches",
                    required=False
                ),
                Parameter(
                    name="is_github",
                    type="boolean",
                    description="Whether the repo_path is a GitHub URL",
                    required=False,
                    default=False
                )
            ],
            function=self.analyze_repo
        )
