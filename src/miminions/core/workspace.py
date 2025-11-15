"""
Core workspace module for MiMinions.

Provides workspace management with inherited rule sets, network of nodes,
and structured logic based on internal state.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum


class NodeType(Enum):
    """Types of nodes in a workspace."""
    AGENT = "agent"
    TASK = "task"  
    WORKFLOW = "workflow"
    KNOWLEDGE = "knowledge"
    CUSTOM = "custom"


class RulePriority(Enum):
    """Priority levels for rules."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Node:
    """Represents a node in the workspace network."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: NodeType = NodeType.CUSTOM
    properties: Dict[str, Any] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)  # IDs of connected nodes
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Create node from dictionary."""
        if 'type' in data:
            data['type'] = NodeType(data['type'])
        return cls(**data)


@dataclass
class Rule:
    """Represents a rule with conditions and actions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    condition: Dict[str, Any] = field(default_factory=dict)  # Condition expression
    action: Dict[str, Any] = field(default_factory=dict)    # Action to take
    priority: RulePriority = RulePriority.MEDIUM
    inherited_from: Optional[str] = None  # Source workspace/rule set
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        """Create rule from dictionary."""
        if 'priority' in data:
            data['priority'] = RulePriority(data['priority'])
        return cls(**data)


@dataclass
class Workspace:
    """Represents a workspace with nodes, rules, and state."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    nodes: Dict[str, Node] = field(default_factory=dict)
    rules: Dict[str, Rule] = field(default_factory=dict)
    inherited_rules: Dict[str, Rule] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    parent_workspace: Optional[str] = None  # For rule inheritance
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def add_node(self, node: Node) -> None:
        """Add a node to the workspace."""
        self.nodes[node.id] = node
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the workspace."""
        if node_id in self.nodes:
            # Remove connections to this node from other nodes
            for other_node in self.nodes.values():
                if node_id in other_node.connections:
                    other_node.connections.remove(node_id)
            
            del self.nodes[node_id]
            self.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False
    
    def connect_nodes(self, node1_id: str, node2_id: str) -> bool:
        """Create a bidirectional connection between two nodes."""
        if node1_id in self.nodes and node2_id in self.nodes:
            if node2_id not in self.nodes[node1_id].connections:
                self.nodes[node1_id].connections.append(node2_id)
            if node1_id not in self.nodes[node2_id].connections:
                self.nodes[node2_id].connections.append(node1_id)
            self.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False
    
    def disconnect_nodes(self, node1_id: str, node2_id: str) -> bool:
        """Remove connection between two nodes."""
        success = False
        if node1_id in self.nodes and node2_id in self.nodes[node1_id].connections:
            self.nodes[node1_id].connections.remove(node2_id)
            success = True
        if node2_id in self.nodes and node1_id in self.nodes[node2_id].connections:
            self.nodes[node2_id].connections.remove(node1_id)
            success = True
        
        if success:
            self.updated_at = datetime.now(timezone.utc).isoformat()
        return success
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the workspace."""
        self.rules[rule.id] = rule
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the workspace."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False
    
    def inherit_rules_from(self, parent_workspace: 'Workspace') -> None:
        """Inherit rules from a parent workspace."""
        self.parent_workspace = parent_workspace.id
        
        # Inherit all rules from parent
        for rule_id, rule in parent_workspace.rules.items():
            inherited_rule = Rule(
                id=str(uuid.uuid4()),
                name=rule.name,
                description=rule.description,
                condition=rule.condition.copy(),
                action=rule.action.copy(),
                priority=rule.priority,
                inherited_from=f"{parent_workspace.name}:{rule_id}",
                enabled=rule.enabled
            )
            self.inherited_rules[inherited_rule.id] = inherited_rule
        
        # Also inherit the parent's inherited rules
        for rule_id, rule in parent_workspace.inherited_rules.items():
            inherited_rule = Rule(
                id=str(uuid.uuid4()),
                name=rule.name,
                description=rule.description,
                condition=rule.condition.copy(),
                action=rule.action.copy(),
                priority=rule.priority,
                inherited_from=rule.inherited_from,
                enabled=rule.enabled
            )
            self.inherited_rules[inherited_rule.id] = inherited_rule
        
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def get_all_rules(self) -> List[Rule]:
        """Get all rules (own + inherited) sorted by priority."""
        all_rules = list(self.rules.values()) + list(self.inherited_rules.values())
        return sorted([r for r in all_rules if r.enabled], 
                     key=lambda r: r.priority.value, reverse=True)
    
    def evaluate_state_logic(self) -> List[Dict[str, Any]]:
        """Evaluate structured logic based on current state and return applicable actions."""
        applicable_actions = []
        
        for rule in self.get_all_rules():
            if self._evaluate_condition(rule.condition):
                action_result = {
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'action': rule.action,
                    'priority': rule.priority.value,
                    'inherited_from': rule.inherited_from
                }
                applicable_actions.append(action_result)
        
        return applicable_actions
    
    def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """Evaluate a rule condition against current workspace state."""
        if not condition:
            return True  # Empty condition is always true
        
        # Simple condition evaluation - can be extended
        condition_type = condition.get('type', 'always')
        
        if condition_type == 'always':
            return True
        elif condition_type == 'state_equals':
            key = condition.get('key')
            value = condition.get('value')
            return self.state.get(key) == value
        elif condition_type == 'node_count':
            operator = condition.get('operator', '>=')
            count = condition.get('count', 0)
            node_count = len(self.nodes)
            
            if operator == '>=':
                return node_count >= count
            elif operator == '<=':
                return node_count <= count
            elif operator == '==':
                return node_count == count
            elif operator == '>':
                return node_count > count
            elif operator == '<':
                return node_count < count
        elif condition_type == 'node_type_exists':
            node_type = condition.get('node_type')
            return any(node.type.value == node_type for node in self.nodes.values())
        
        return False
    
    def get_network_summary(self) -> Dict[str, Any]:
        """Get a summary of the workspace network structure."""
        node_types = {}
        total_connections = 0
        
        for node in self.nodes.values():
            node_type = node.type.value
            node_types[node_type] = node_types.get(node_type, 0) + 1
            total_connections += len(node.connections)
        
        # Connections are bidirectional, so divide by 2
        unique_connections = total_connections // 2
        
        return {
            'total_nodes': len(self.nodes),
            'node_types': node_types,
            'total_connections': unique_connections,
            'total_rules': len(self.rules),
            'inherited_rules': len(self.inherited_rules),
            'current_state_keys': list(self.state.keys())
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workspace to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'rules': {k: v.to_dict() for k, v in self.rules.items()},
            'inherited_rules': {k: v.to_dict() for k, v in self.inherited_rules.items()},
            'state': self.state,
            'parent_workspace': self.parent_workspace,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workspace':
        """Create workspace from dictionary."""
        workspace = cls()
        workspace.id = data.get('id', workspace.id)
        workspace.name = data.get('name', '')
        workspace.description = data.get('description', '')
        workspace.state = data.get('state', {})
        workspace.parent_workspace = data.get('parent_workspace')
        workspace.created_at = data.get('created_at', workspace.created_at)
        workspace.updated_at = data.get('updated_at', workspace.updated_at)
        
        # Load nodes
        workspace.nodes = {}
        for node_id, node_data in data.get('nodes', {}).items():
            workspace.nodes[node_id] = Node.from_dict(node_data)
        
        # Load rules
        workspace.rules = {}
        for rule_id, rule_data in data.get('rules', {}).items():
            workspace.rules[rule_id] = Rule.from_dict(rule_data)
        
        # Load inherited rules
        workspace.inherited_rules = {}
        for rule_id, rule_data in data.get('inherited_rules', {}).items():
            workspace.inherited_rules[rule_id] = Rule.from_dict(rule_data)
        
        return workspace


class WorkspaceManager:
    """Manager for workspace operations and persistence."""
    
    def __init__(self, config_dir_path):
        """Initialize workspace manager with config directory."""
        self.config_dir = config_dir_path
        self.workspaces_file = self.config_dir / "workspaces.json"
    
    def load_workspaces(self) -> Dict[str, Workspace]:
        """Load workspaces from storage."""
        if not self.workspaces_file.exists():
            return {}
        
        try:
            with open(self.workspaces_file, 'r') as f:
                data = json.load(f)
            
            workspaces = {}
            for workspace_id, workspace_data in data.items():
                workspaces[workspace_id] = Workspace.from_dict(workspace_data)
            
            return workspaces
        except Exception:
            return {}
    
    def save_workspaces(self, workspaces: Dict[str, Workspace]) -> None:
        """Save workspaces to storage."""
        self.config_dir.mkdir(exist_ok=True)
        
        data = {}
        for workspace_id, workspace in workspaces.items():
            data[workspace_id] = workspace.to_dict()
        
        with open(self.workspaces_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_workspace(self, name: str, description: str = "") -> Workspace:
        """Create a new workspace."""
        workspace = Workspace(name=name, description=description)
        return workspace
    
    def create_sample_workspace(self) -> Workspace:
        """Create a sample workspace with example nodes and rules for demonstration."""
        workspace = self.create_workspace(
            name="Sample Workspace",
            description="A sample workspace demonstrating nodes, rules, and state logic"
        )
        
        # Add sample nodes
        agent_node = Node(
            name="Assistant Agent",
            type=NodeType.AGENT,
            properties={"role": "assistant", "capabilities": ["text", "analysis"]},
            state={"status": "active", "load": 0.3}
        )
        
        task_node = Node(
            name="Analysis Task",
            type=NodeType.TASK,
            properties={"priority": "high", "estimated_time": "30min"},
            state={"status": "pending", "progress": 0}
        )
        
        knowledge_node = Node(
            name="Project Knowledge",
            type=NodeType.KNOWLEDGE,
            properties={"domain": "software", "confidence": 0.8},
            state={"last_updated": datetime.now(timezone.utc).isoformat()}
        )
        
        workspace.add_node(agent_node)
        workspace.add_node(task_node)
        workspace.add_node(knowledge_node)
        
        # Connect nodes
        workspace.connect_nodes(agent_node.id, task_node.id)
        workspace.connect_nodes(agent_node.id, knowledge_node.id)
        
        # Add sample rules
        rule1 = Rule(
            name="Auto-assign available agents",
            description="Automatically assign tasks to available agents",
            condition={
                "type": "node_type_exists",
                "node_type": "agent"
            },
            action={
                "type": "assign_task",
                "target": "available_agent",
                "message": "Assign pending tasks to available agents"
            },
            priority=RulePriority.HIGH
        )
        
        rule2 = Rule(
            name="Knowledge validation",
            description="Validate knowledge before use in high-priority tasks",
            condition={
                "type": "state_equals",
                "key": "task_priority",
                "value": "high"
            },
            action={
                "type": "validate_knowledge",
                "threshold": 0.7,
                "message": "Ensure knowledge confidence meets threshold"
            },
            priority=RulePriority.MEDIUM
        )
        
        workspace.add_rule(rule1)
        workspace.add_rule(rule2)
        
        # Set initial state
        workspace.state = {
            "task_priority": "high",
            "system_load": "normal",
            "active_users": 1
        }
        
        return workspace