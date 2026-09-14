"""
FastMCP Sample - Python MCP Server Implementation

This file demonstrates a comprehensive FastMCP (Fastest Model Context Protocol) server
implementation with various tool types and best practices.

FastMCP is a high-performance Model Context Protocol library that enables AI models
to access external tools, files, and resources through a standardized interface.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Initialize the FastMCP server
# Name and version define your server's identity
mcp = FastMCP(
    name="FastMCP Sample Server",
    version="1.0.0",
    description="A comprehensive sample MCP server demonstrating FastMCP features",
)

# Sample data structures
SAMPLE_TEXTS = {
    "greeting": "Hello! Welcome to FastMCP.",
    "technical": "FastMCP is designed for high-performance model integrations.",
}

SAMPLE_PROJECTS = {
    "sample-project-1": {
        "name": "Web Development",
        "description": "A modern web application",
        "status": "in-progress",
        "technologies": ["React", "TypeScript", "FastAPI"],
    },
}
@mcp.tool(
    name="text_analyzer",
    description="Analyze text and extract key information",
    parameters={
        "text": {
            "type": "string",
            "description": "The text to analyze",
            "required": True,
        },
        "analysis_type": {
            "type": "string",
            "description": "Type of analysis to perform",
            "enum": ["summary", "keywords", "sentiment", "entities"],
            "default": "summary",
        },
    },
)
def analyze_text(text: str, analysis_type: str = "summary") -> Dict[str, Any]:
    """Analyze text and return structured results"""
    if analysis_type == "summary":
        # Simple summarization
        words = text.split()
        summary = " ".join(words[:min(5, len(words))])
        return {
            "type": "summary",
            "original_length": len(text),
            "summary": summary,
            "word_count": len(words),
        }
    
    elif analysis_type == "keywords":
        # Extract keywords
        words = [word for word in text.split() if len(word) > 3]
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "type": "keywords",
            "total_words": len(words),
            "top_keywords": [
                {"word": word, "frequency": freq} for word, freq in sorted_keywords
            ],
        }
    
    return {"type": "unknown", "error": "Invalid analysis type"}
@mcp.tool(
    name="file_manager",
    description="Manage files and directories",
    parameters={
        "action": {
            "type": "string",
            "description": "Action to perform",
            "enum": ["list", "create", "read"],
            "required": True,
        },
        "path": {
            "type": "string",
            "description": "File or directory path",
            "required": True,
        },
    },
)
def manage_file(action: str, path: str) -> Dict[str, Any]:
    """Manage files and directories"""
    try:
        if action == "list":
            path_obj = Path(path)
            if not path_obj.exists():
                return {"status": "error", "message": f"Path does not exist: {path}"}
            
            items = []
            for item in path_obj.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                })
            return {"status": "directory", "path": str(path_obj), "items": items}
        
        elif action == "create":
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            content = f"Created at {datetime.now().isoformat()}"
            path_obj.write_text(content, encoding="utf-8")
            
            return {"status": "created", "path": str(path_obj)}
        
        elif action == "read":
            path_obj = Path(path)
            if not path_obj.exists():
                return {"status": "error", "message": f"File does not exist: {path}"}
            
            content = path_obj.read_text(encoding="utf-8")
            return {
                "status": "read", "path": str(path_obj), 
                "content": content,
                "size": len(content),
            }
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}
@mcp.tool(
    name="utility_functions",
    description="Various utility functions for common tasks",
    parameters={
        "function_name": {
            "type": "string",
            "description": "Name of utility function to execute",
            "enum": ["current_time", "generate_password", "validate_email"],
            "required": True,
        },
        "input_data": {
            "type": "string",
            "description": "Input data for the function",
            "required": False,
        },
    },
)
def utility_function(function_name: str, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Execute various utility functions"""
    if function_name == "current_time":
        current_time = datetime.now().isoformat()
        return {"function": "current_time", "result": current_time}
    
    elif function_name == "generate_password":
        import random
        import string
        
        length = 8
        if input_data:
            try:
                length = int(input_data)
            except ValueError:
                pass
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(alphabet) for _ in range(length))
        
        return {"function": "generate_password", "length": length, "result": password}
    
    elif function_name == "validate_email":
        if not input_data:
            return {"status": "error", "message": "Input data required for validate_email"}
        
        email = input_data.lower()
        if "@" not in email or "." not in email.split("@")[1]:
            return {"function": "validate_email", "result": False, "issue": "Invalid email format"}
        
        return {"function": "validate_email", "result": True, "email": email}
    
    return {"status": "error", "message": f"Unknown function: {function_name}"}