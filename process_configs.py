"""Configuration processor for OznoBB."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigProcessor:
    """Process and validate configuration files."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize config processor.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.configs = {}
    
    def load_config(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a configuration file.
        
        Args:
            filename: Configuration filename
            
        Returns:
            Configuration dictionary or None if load fails
        """
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Loaded config: {filename}")
            self.configs[filename] = config
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            return None
        except IOError as e:
            logger.error(f"Failed to read {filename}: {e}")
            return None
    
    def load_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all JSON configuration files from config directory.
        
        Returns:
            Dictionary of all loaded configurations
        """
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return {}
        
        json_files = self.config_dir.glob("*.json")
        
        for config_file in json_files:
            self.load_config(config_file.name)
        
        logger.info(f"Loaded {len(self.configs)} configuration files")
        return self.configs
    
    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.
        
        Args:
            config: Configuration to validate
            schema: Validation schema
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = schema.get('required', [])
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required key: {key}")
                return False
        
        return True
    
    def save_config(self, filename: str, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file.
        
        Args:
            filename: Output filename
            config: Configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        config_path = self.config_dir / filename
        
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved config: {filename}")
            return True
        except IOError as e:
            logger.error(f"Failed to save {filename}: {e}")
            return False
    
    def merge_configs(self, *config_files: str) -> Dict[str, Any]:
        """
        Merge multiple configuration files.
        
        Args:
            *config_files: Filenames to merge
            
        Returns:
            Merged configuration dictionary
        """
        merged = {}
        
        for filename in config_files:
            config = self.load_config(filename)
            if config:
                merged.update(config)
        
        return merged


def main():
    """Example usage of ConfigProcessor."""
    processor = ConfigProcessor(config_dir="config")
    configs = processor.load_all_configs()
    
    for filename, config in configs.items():
        logger.info(f"{filename}: {len(config)} settings")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
