"""
File handling utilities for Nellia Prospector
Provides common file operations and export functionality.
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger


class FileHandler:
    """Handles file operations for the prospector system"""
    
    @staticmethod
    def ensure_directory(path: str) -> Path:
        """Ensure directory exists, create if it doesn't"""
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    @staticmethod
    def save_json(data: Dict[str, Any], file_path: str, ensure_ascii: bool = False) -> bool:
        """Save data to JSON file"""
        try:
            # Ensure directory exists
            directory = Path(file_path).parent
            FileHandler.ensure_directory(str(directory))
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=ensure_ascii, default=str)
            
            logger.info(f"Data saved to JSON: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving JSON to {file_path}: {e}")
            return False
    
    @staticmethod
    def load_json(file_path: str) -> Optional[Dict[str, Any]]:
        """Load data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"JSON loaded from: {file_path}")
            return data
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading JSON from {file_path}: {e}")
            return None
    
    @staticmethod
    def save_csv(data: List[Dict[str, Any]], file_path: str, fieldnames: Optional[List[str]] = None) -> bool:
        """Save data to CSV file"""
        try:
            if not data:
                logger.warning("No data to save to CSV")
                return False
            
            # Ensure directory exists
            directory = Path(file_path).parent
            FileHandler.ensure_directory(str(directory))
            
            # Use provided fieldnames or extract from first row
            if fieldnames is None:
                fieldnames = list(data[0].keys())
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"Data saved to CSV: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving CSV to {file_path}: {e}")
            return False
    
    @staticmethod
    def export_prospects(
        prospects: List[Dict[str, Any]], 
        output_dir: str = "exports", 
        base_filename: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export prospects to multiple formats (JSON, CSV)
        
        Returns:
            Dict mapping format to file path
        """
        if base_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"prospects_{timestamp}"
        
        output_paths = {}
        
        # Create export directory
        export_dir = FileHandler.ensure_directory(output_dir)
        
        # Export to JSON
        json_path = export_dir / f"{base_filename}.json"
        if FileHandler.save_json({"prospects": prospects}, str(json_path)):
            output_paths["json"] = str(json_path)
        
        # Export to CSV (flattened data)
        csv_data = []
        for prospect in prospects:
            if isinstance(prospect, dict):
                # Flatten nested dictionaries
                flattened = FileHandler._flatten_dict(prospect)
                csv_data.append(flattened)
        
        if csv_data:
            csv_path = export_dir / f"{base_filename}.csv"
            if FileHandler.save_csv(csv_data, str(csv_path)):
                output_paths["csv"] = str(csv_path)
        
        return output_paths
    
    @staticmethod
    def _flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary for CSV export"""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(FileHandler._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to comma-separated strings
                if v and all(isinstance(item, str) for item in v):
                    items.append((new_key, ', '.join(v)))
                else:
                    items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    @staticmethod
    def backup_file(file_path: str, backup_dir: str = "backups") -> Optional[str]:
        """Create a backup of an existing file"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File to backup does not exist: {file_path}")
                return None
            
            # Create backup directory
            backup_directory = FileHandler.ensure_directory(backup_dir)
            
            # Generate backup filename with timestamp
            original_path = Path(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{original_path.stem}_{timestamp}{original_path.suffix}"
            backup_path = backup_directory / backup_filename
            
            # Copy file
            import shutil
            shutil.copy2(file_path, backup_path)
            
            logger.info(f"File backed up to: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error backing up file {file_path}: {e}")
            return None
    
    @staticmethod
    def clean_old_files(directory: str, days_old: int = 30, pattern: str = "*") -> int:
        """Clean old files from directory"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return 0
            
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            cleaned_count = 0
            
            for file_path in dir_path.glob(pattern):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned old file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not clean file {file_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned {cleaned_count} old files from {directory}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning old files from {directory}: {e}")
            return 0
