import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)

class FileSystemError(Exception):
    pass

class FileSystemTools:
    """
    File system tools for agent-addressable local I/O operations
    Provides secure file operations within the DATA_ROOT directory
    """
    
    def __init__(self, data_root: str = None):
        self.data_root = Path(data_root or os.getenv("DATA_ROOT", "./data"))
        logger.info(f"FileSystemTools initialized with data_root: {self.data_root.resolve()}")
        self.setup_directories()
    
    def setup_directories(self):
        """Ensure all required directories exist"""
        try:
            required_dirs = [
                self.data_root,
                self.data_root / "knowledge_base",
                self.data_root / "output",
                self.data_root / "output" / "case_studies",
                self.data_root / "output" / "emails",
                self.data_root / "output" / "slides",
                self.data_root / "output" / "context",
                self.data_root / "logs"
            ]
            
            for dir_path in required_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Directory ensured: {dir_path}")
                
        except Exception as e:
            logger.error(f"Error setting up directories: {str(e)}")
            raise FileSystemError(f"Failed to setup directories: {str(e)}")
    
    def _validate_path(self, path: str) -> Path:
        """Validate and resolve path to prevent directory traversal"""
        try:
            # Convert to Path object
            requested_path = Path(path)
            
            # If path is relative, make it relative to data_root
            if not requested_path.is_absolute():
                full_path = self.data_root / requested_path
            else:
                full_path = requested_path
            
            # Resolve the path to handle any .. or . components
            resolved_path = full_path.resolve()
            data_root_resolved = self.data_root.resolve()
            
            logger.debug(f"Path validation - requested: {path}, resolved: {resolved_path}, data_root: {data_root_resolved}")
            
            # Ensure the resolved path is within data_root (fix for Windows path comparison)
            try:
                # Use as_posix() for consistent path comparison on Windows
                resolved_posix = resolved_path.as_posix()
                data_root_posix = data_root_resolved.as_posix()
                
                logger.debug(f"Comparing paths - resolved_posix: {resolved_posix}, data_root_posix: {data_root_posix}")
                
                if not resolved_posix.startswith(data_root_posix):
                    raise FileSystemError(f"Path outside data root: {path} (resolved: {resolved_posix} not in {data_root_posix})")
                    
            except Exception as e:
                logger.error(f"Path validation comparison error: {str(e)}")
                raise FileSystemError(f"Path outside data root: {path}")
            
            return resolved_path
            
        except FileSystemError:
            raise
        except Exception as e:
            logger.error(f"Path validation error: {str(e)}")
            raise FileSystemError(f"Invalid path: {path}")
    
    async def list_files(self, path: str = "", include_hidden: bool = False) -> Dict[str, Any]:
        """
        List files and directories in the specified path
        
        Args:
            path: Relative path within data_root (empty for root)
            include_hidden: Whether to include hidden files
            
        Returns:
            Dictionary containing file listing
        """
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileSystemError(f"Path does not exist: {path}")
            
            if not target_path.is_dir():
                raise FileSystemError(f"Path is not a directory: {path}")
            
            files = []
            directories = []
            
            for item in target_path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                # Calculate relative path safely for Windows
                try:
                    relative_path = item.relative_to(self.data_root)
                    path_str = str(relative_path).replace("\\", "/")
                except ValueError:
                    # If relative_to fails, use a safe fallback
                    path_str = item.name
                
                item_info = {
                    "name": item.name,
                    "path": path_str,
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "type": "file" if item.is_file() else "directory"
                }
                
                if item.is_file():
                    # Add MIME type for files
                    mime_type, _ = mimetypes.guess_type(str(item))
                    item_info["mime_type"] = mime_type or "application/octet-stream"
                    files.append(item_info)
                else:
                    directories.append(item_info)
            
            return {
                "ok": True,
                "path": path,
                "files": files,
                "directories": directories,
                "total_files": len(files),
                "total_directories": len(directories)
            }
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"List files error: {str(e)}")
            return {"ok": False, "error": f"Failed to list files: {str(e)}"}
    
    async def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read contents of a file
        
        Args:
            path: Path to the file relative to data_root
            encoding: Text encoding (default: utf-8)
            
        Returns:
            Dictionary containing file contents
        """
        try:
            file_path = self._validate_path(path)
            
            if not file_path.exists():
                raise FileSystemError(f"File does not exist: {path}")
            
            if not file_path.is_file():
                raise FileSystemError(f"Path is not a file: {path}")
            
            # Check if file is text-based by MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            if mime_type and not mime_type.startswith('text/'):
                # For binary files, just return metadata
                return {
                    "ok": True,
                    "path": path,
                    "size": file_path.stat().st_size,
                    "mime_type": mime_type,
                    "is_binary": True,
                    "content": None
                }
            
            # Read text file
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "ok": True,
                "path": path,
                "content": content,
                "size": len(content),
                "mime_type": mime_type or "text/plain",
                "is_binary": False,
                "encoding": encoding
            }
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except UnicodeDecodeError as e:
            return {"ok": False, "error": f"Encoding error: {str(e)}"}
        except Exception as e:
            logger.error(f"Read file error: {str(e)}")
            return {"ok": False, "error": f"Failed to read file: {str(e)}"}
    
    async def edit_file(self, path: str, old_text: str, new_text: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Edit file by replacing old_text with new_text (Ampcode pattern)
        
        Args:
            path: Path to the file relative to data_root
            old_text: Text to replace
            new_text: New text to replace with
            encoding: Text encoding (default: utf-8)
            
        Returns:
            Dictionary containing operation result
        """
        try:
            file_path = self._validate_path(path)
            
            # Read current content
            if file_path.exists():
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                # Replace old text with new text
                if old_text in content:
                    new_content = content.replace(old_text, new_text)
                    
                    # Write back the modified content
                    with open(file_path, 'w', encoding=encoding) as f:
                        f.write(new_content)
                    
                    return {
                        "ok": True,
                        "path": path,
                        "old_text": old_text,
                        "new_text": new_text,
                        "replacements": content.count(old_text),
                        "size": len(new_content),
                        "encoding": encoding
                    }
                else:
                    return {
                        "ok": False,
                        "error": f"Text '{old_text}' not found in file"
                    }
            else:
                return {
                    "ok": False,
                    "error": f"File does not exist: {path}"
                }
                
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Edit file error: {str(e)}")
            return {"ok": False, "error": f"Failed to edit file: {str(e)}"}

    async def write_file(self, path: str, content: str, encoding: str = "utf-8", append: bool = False) -> Dict[str, Any]:
        """
        Write content to a file
        
        Args:
            path: Path to the file relative to data_root
            content: Content to write
            encoding: Text encoding (default: utf-8)
            append: Whether to append to existing file
            
        Returns:
            Dictionary containing operation result
        """
        try:
            file_path = self._validate_path(path)
            
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            return {
                "ok": True,
                "path": path,
                "size": len(content),
                "mode": "append" if append else "write",
                "encoding": encoding
            }
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Write file error: {str(e)}")
            return {"ok": False, "error": f"Failed to write file: {str(e)}"}
    
    async def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file or directory
        
        Args:
            path: Path to the file/directory relative to data_root
            
        Returns:
            Dictionary containing operation result
        """
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileSystemError(f"Path does not exist: {path}")
            
            if target_path.is_file():
                target_path.unlink()
                return {"ok": True, "path": path, "type": "file"}
            elif target_path.is_dir():
                # Only delete if directory is empty
                if any(target_path.iterdir()):
                    raise FileSystemError(f"Directory not empty: {path}")
                target_path.rmdir()
                return {"ok": True, "path": path, "type": "directory"}
            else:
                raise FileSystemError(f"Unknown file type: {path}")
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Delete file error: {str(e)}")
            return {"ok": False, "error": f"Failed to delete: {str(e)}"}
    
    async def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Create a directory
        
        Args:
            path: Path to the directory relative to data_root
            
        Returns:
            Dictionary containing operation result
        """
        try:
            dir_path = self._validate_path(path)
            
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return {
                "ok": True,
                "path": path,
                "created": True
            }
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Create directory error: {str(e)}")
            return {"ok": False, "error": f"Failed to create directory: {str(e)}"}
    
    async def search_files(self, query: str, path: str = "", file_extensions: List[str] = None) -> Dict[str, Any]:
        """
        Search for files by name or content
        
        Args:
            query: Search query
            path: Directory to search in (relative to data_root)
            file_extensions: List of file extensions to search
            
        Returns:
            Dictionary containing search results
        """
        try:
            search_path = self._validate_path(path)
            
            if not search_path.exists():
                raise FileSystemError(f"Search path does not exist: {path}")
            
            if not search_path.is_dir():
                raise FileSystemError(f"Search path is not a directory: {path}")
            
            matches = []
            
            # Search for files
            for item in search_path.rglob("*"):
                if not item.is_file():
                    continue
                
                # Filter by extension if specified
                if file_extensions and item.suffix.lower() not in file_extensions:
                    continue
                
                # Calculate relative path safely for Windows
                try:
                    relative_path = item.relative_to(self.data_root)
                    path_str = str(relative_path).replace("\\", "/")
                except ValueError:
                    # If relative_to fails, use a safe fallback
                    path_str = item.name
                
                match_info = {
                    "path": path_str,
                    "name": item.name,
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "match_type": None
                }
                
                # Check filename match
                if query.lower() in item.name.lower():
                    match_info["match_type"] = "filename"
                    matches.append(match_info)
                    continue
                
                # Check content match for text files
                try:
                    mime_type, _ = mimetypes.guess_type(str(item))
                    if mime_type and mime_type.startswith('text/'):
                        with open(item, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                match_info["match_type"] = "content"
                                matches.append(match_info)
                except:
                    # Skip files that can't be read
                    continue
            
            return {
                "ok": True,
                "query": query,
                "search_path": path,
                "matches": matches,
                "total_matches": len(matches)
            }
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Search files error: {str(e)}")
            return {"ok": False, "error": f"Failed to search files: {str(e)}"}
    
    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Get detailed information about a file or directory
        
        Args:
            path: Path to the file/directory relative to data_root
            
        Returns:
            Dictionary containing file information
        """
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileSystemError(f"Path does not exist: {path}")
            
            stat = target_path.stat()
            
            info = {
                "path": path,
                "name": target_path.name,
                "size": stat.st_size,
                "is_file": target_path.is_file(),
                "is_directory": target_path.is_dir(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:]
            }
            
            if target_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(target_path))
                info["mime_type"] = mime_type or "application/octet-stream"
            
            return {"ok": True, "info": info}
            
        except FileSystemError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Get file info error: {str(e)}")
            return {"ok": False, "error": f"Failed to get file info: {str(e)}"}