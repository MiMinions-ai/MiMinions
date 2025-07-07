"""
Knowledge management commands for MiMinions CLI.
"""

import click
import json
import uuid
from pathlib import Path
from .auth import get_config_dir, is_authenticated


def get_knowledge_file():
    """Get the knowledge configuration file path."""
    return get_config_dir() / "knowledge.json"


def load_knowledge():
    """Load knowledge from configuration."""
    knowledge_file = get_knowledge_file()
    if not knowledge_file.exists():
        return {}
    
    with open(knowledge_file, "r") as f:
        return json.load(f)


def save_knowledge(knowledge):
    """Save knowledge to configuration."""
    knowledge_file = get_knowledge_file()
    with open(knowledge_file, "w") as f:
        json.dump(knowledge, f, indent=2)


def require_auth():
    """Decorator to require authentication."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                click.echo("Please sign in first using 'miminions auth signin'", err=True)
                return
            return f(*args, **kwargs)
        return wrapper
    return decorator


@click.group()
def knowledge_cli():
    """Knowledge management commands."""
    pass


@knowledge_cli.command("list")
@require_auth()
def list_knowledge():
    """List all knowledge entries."""
    knowledge = load_knowledge()
    
    if not knowledge:
        click.echo("No knowledge entries found.")
        return
    
    click.echo("Knowledge entries:")
    for entry_id, entry_data in knowledge.items():
        title = entry_data.get("title", entry_id)
        category = entry_data.get("category", "general")
        version = entry_data.get("version", "1.0")
        status = entry_data.get("status", "active")
        click.echo(f"  {entry_id}: {title} (v{version}, {category}, {status})")


@knowledge_cli.command("add")
@click.option("--title", prompt="Knowledge title", help="Title of the knowledge entry")
@click.option("--content", prompt="Content", help="Content of the knowledge entry")
@click.option("--category", default="general", help="Category of the knowledge entry")
@click.option("--tags", help="Comma-separated tags")
@require_auth()
def add_knowledge(title, content, category, tags):
    """Add a new knowledge entry."""
    knowledge = load_knowledge()
    
    # Generate a unique ID
    entry_id = str(uuid.uuid4())[:8]
    
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
    
    knowledge[entry_id] = {
        "title": title,
        "content": content,
        "category": category,
        "tags": tag_list,
        "version": "1.0",
        "status": "active",
        "created_at": click.get_current_context().meta.get("timestamp", ""),
        "updated_at": None,
        "versions": [
            {
                "version": "1.0",
                "content": content,
                "timestamp": click.get_current_context().meta.get("timestamp", "")
            }
        ]
    }
    
    save_knowledge(knowledge)
    click.echo(f"Knowledge entry '{title}' added successfully with ID: {entry_id}")


@knowledge_cli.command("update")
@click.argument("entry_id")
@click.option("--title", help="New title for the knowledge entry")
@click.option("--content", help="New content for the knowledge entry")
@click.option("--category", help="New category for the knowledge entry")
@click.option("--tags", help="Comma-separated tags")
@require_auth()
def update_knowledge(entry_id, title, content, category, tags):
    """Update an existing knowledge entry."""
    knowledge = load_knowledge()
    
    if entry_id not in knowledge:
        click.echo(f"Knowledge entry '{entry_id}' not found.", err=True)
        return
    
    entry = knowledge[entry_id]
    
    # If content is being updated, create a new version
    if content and content != entry["content"]:
        current_version = float(entry["version"])
        new_version = f"{current_version + 0.1:.1f}"
        
        # Add new version to history
        entry["versions"].append({
            "version": new_version,
            "content": content,
            "timestamp": click.get_current_context().meta.get("timestamp", "")
        })
        
        entry["version"] = new_version
        entry["content"] = content
    
    if title:
        entry["title"] = title
    if category:
        entry["category"] = category
    if tags:
        entry["tags"] = [tag.strip() for tag in tags.split(",")]
    
    entry["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_knowledge(knowledge)
    click.echo(f"Knowledge entry '{entry_id}' updated successfully")


@knowledge_cli.command("remove")
@click.argument("entry_id")
@click.confirmation_option(prompt="Are you sure you want to remove this knowledge entry?")
@require_auth()
def remove_knowledge(entry_id):
    """Remove a knowledge entry."""
    knowledge = load_knowledge()
    
    if entry_id not in knowledge:
        click.echo(f"Knowledge entry '{entry_id}' not found.", err=True)
        return
    
    del knowledge[entry_id]
    save_knowledge(knowledge)
    click.echo(f"Knowledge entry '{entry_id}' removed successfully")


@knowledge_cli.command("revert")
@click.argument("entry_id")
@click.option("--version", prompt="Version to revert to", help="Version to revert to")
@require_auth()
def revert_knowledge(entry_id, version):
    """Revert a knowledge entry to a previous version."""
    knowledge = load_knowledge()
    
    if entry_id not in knowledge:
        click.echo(f"Knowledge entry '{entry_id}' not found.", err=True)
        return
    
    entry = knowledge[entry_id]
    
    # Find the version to revert to
    target_version = None
    for v in entry["versions"]:
        if v["version"] == version:
            target_version = v
            break
    
    if not target_version:
        click.echo(f"Version '{version}' not found for entry '{entry_id}'.", err=True)
        return
    
    # Revert to the target version
    entry["content"] = target_version["content"]
    entry["version"] = target_version["version"]
    entry["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_knowledge(knowledge)
    click.echo(f"Knowledge entry '{entry_id}' reverted to version {version}")


@knowledge_cli.command("version")
@click.argument("entry_id")
@require_auth()
def show_versions(entry_id):
    """Show version history of a knowledge entry."""
    knowledge = load_knowledge()
    
    if entry_id not in knowledge:
        click.echo(f"Knowledge entry '{entry_id}' not found.", err=True)
        return
    
    entry = knowledge[entry_id]
    
    click.echo(f"Version history for '{entry['title']}' ({entry_id}):")
    for version in entry["versions"]:
        marker = " (current)" if version["version"] == entry["version"] else ""
        click.echo(f"  v{version['version']}{marker} - {version['timestamp']}")


@knowledge_cli.command("customize")
@click.argument("entry_id")
@click.option("--template", help="Template to apply")
@click.option("--format", type=click.Choice(["json", "markdown", "plain"]), default="plain", help="Output format")
@require_auth()
def customize_knowledge(entry_id, template, format):
    """Customize knowledge entry format or template."""
    knowledge = load_knowledge()
    
    if entry_id not in knowledge:
        click.echo(f"Knowledge entry '{entry_id}' not found.", err=True)
        return
    
    entry = knowledge[entry_id]
    
    if template:
        # Apply template (this is a simplified implementation)
        entry["template"] = template
        entry["updated_at"] = click.get_current_context().meta.get("timestamp", "")
        save_knowledge(knowledge)
        click.echo(f"Template '{template}' applied to knowledge entry '{entry_id}'")
    
    # Display the entry in the requested format
    if format == "json":
        click.echo(json.dumps(entry, indent=2))
    elif format == "markdown":
        click.echo(f"# {entry['title']}\n")
        click.echo(f"**Category:** {entry['category']}\n")
        click.echo(f"**Version:** {entry['version']}\n")
        click.echo(f"**Tags:** {', '.join(entry['tags'])}\n")
        click.echo(f"**Content:**\n{entry['content']}")
    else:
        click.echo(f"Title: {entry['title']}")
        click.echo(f"Content: {entry['content']}")


@knowledge_cli.command("show")
@click.argument("entry_id")
@require_auth()
def show_knowledge(entry_id):
    """Show detailed information about a knowledge entry."""
    knowledge = load_knowledge()
    
    if entry_id not in knowledge:
        click.echo(f"Knowledge entry '{entry_id}' not found.", err=True)
        return
    
    entry = knowledge[entry_id]
    
    click.echo(f"Entry ID: {entry_id}")
    click.echo(f"Title: {entry['title']}")
    click.echo(f"Category: {entry['category']}")
    click.echo(f"Version: {entry['version']}")
    click.echo(f"Status: {entry['status']}")
    click.echo(f"Tags: {', '.join(entry['tags']) if entry['tags'] else 'None'}")
    click.echo(f"Created: {entry['created_at']}")
    if entry.get('updated_at'):
        click.echo(f"Updated: {entry['updated_at']}")
    click.echo(f"Content:\n{entry['content']}")