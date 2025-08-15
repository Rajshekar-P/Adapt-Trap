"""
HoneyPy Plugin Base Class
-------------------------
This module defines the PluginBase class used by all plugins in HoneyPy.
Each plugin must subclass this and implement the startHoneyService() method.
"""

class PluginBase:
    def __init__(self, options=None):
        """
        Initialize the plugin with optional configuration options.
        """
        self.options = options or {}
        self.plugin_name = self.options.get("name", self.__class__.__name__)
        self.plugin_port = self.options.get("port", 10000)
        self.plugin_interface = self.options.get("interface", "0.0.0.0")

    def startHoneyService(self):
        """
        Start the honeypot service.
        This method must be implemented by subclasses.
        """
        raise NotImplementedError("Plugin must implement startHoneyService()")
