from typing import Any, Dict, List

from app.core.logging import logger
from app.tools.base import BaseTool


class ToolRegistry:
    """Registry to manage and execute tools"""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        logger.info("ToolRegistry initialized")

    def register(self, tool: BaseTool):
        """Register a new tool"""
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool:
        """Get a tool by name"""
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")
        return tool

    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools with descriptions"""
        return [
            {"name": name, "description": tool.description} for name, tool in self.tools.items()
        ]

    def run_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a registered tool"""
        tool = self.get(name)
        logger.info(f"Running tool: {name}")
        try:
            result = tool.run(**kwargs)
            logger.info(f"Tool {name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error running tool {name}: {str(e)}")
            raise


# Singleton instance
tool_registry = ToolRegistry()
