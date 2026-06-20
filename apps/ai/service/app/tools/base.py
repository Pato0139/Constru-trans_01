from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """Base abstract class for all tools"""
    name: str = "base_tool"
    description: str = "Herramienta base"

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        Returns a dictionary with the result.
        """
        pass
