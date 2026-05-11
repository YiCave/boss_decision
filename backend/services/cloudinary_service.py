"""
Cloudinary Service - Handle document uploads to Cloudinary
"""
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class CloudinaryService:
    """Service for uploading and managing documents on Cloudinary"""
    
    def __init__(self):
        # Configure Cloudinary using CLOUDINARY_URL environment variable
        cloudinary_url = os.getenv("CLOUDINARY_URL")
        
        if not cloudinary_url:
            raise ValueError("CLOUDINARY_URL not found in environment variables")
        
        # Parse cloudinary URL manually to avoid import-time configuration
        # Format: cloudinary://api_key:api_secret@cloud_name
        try:
            from urllib.parse import urlparse
            parsed = urlparse(cloudinary_url)
            
            cloudinary.config(
                cloud_name=parsed.hostname,
                api_key=parsed.username,
                api_secret=parsed.password,
                secure=True
            )
        except Exception as e:
            raise ValueError(f"Invalid CLOUDINARY_URL format: {str(e)}")
    
    def upload_document(
        self,
        file_path: str,
        folder: str = "documents",
        public_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a document to Cloudinary
        
        Args:
            file_path: Path to file to upload
            folder: Cloudinary folder path (e.g., "documents/hr")
            public_id: Optional custom public ID
        
        Returns:
            Upload result with URLs and metadata
        """
        try:
            upload_options = {
                "folder": folder,
                "resource_type": "auto",  # Auto-detect file type
                "overwrite": False,
            }
            
            if public_id:
                upload_options["public_id"] = public_id
            
            result = cloudinary.uploader.upload(file_path, **upload_options)
            
            return {
                "success": True,
                "public_id": result.get("public_id"),
                "url": result.get("secure_url"),
                "format": result.get("format"),
                "resource_type": result.get("resource_type"),
                "bytes": result.get("bytes"),
                "created_at": result.get("created_at")
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str = "documents",
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a document from bytes (for API uploads)
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename
            folder: Cloudinary folder (will append doc_type subfolder if provided)
            doc_type: Document type (HR, Sales, Finance, etc.)
        
        Returns:
            Upload result with URLs
        """
        try:
            # Build folder path based on doc_type
            if doc_type:
                doc_type_lower = doc_type.lower().replace(" ", "_")
                full_folder = f"{folder}/{doc_type_lower}"
            else:
                full_folder = folder
            
            # Upload
            result = cloudinary.uploader.upload(
                file_bytes,
                folder=full_folder,
                resource_type="auto",
                public_id=filename.rsplit('.', 1)[0],  # Use filename without extension
                overwrite=False
            )
            
            return {
                "success": True,
                "public_id": result.get("public_id"),
                "url": result.get("secure_url"),
                "format": result.get("format"),
                "resource_type": result.get("resource_type"),
                "bytes": result.get("bytes"),
                "width": result.get("width"),
                "height": result.get("height")
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_document(self, public_id: str) -> Dict[str, Any]:
        """
        Delete a document from Cloudinary
        
        Args:
            public_id: Cloudinary public ID of the document
        
        Returns:
            Deletion result
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="auto")
            return {
                "success": result.get("result") == "ok",
                "result": result.get("result")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_thumbnail_url(
        self,
        public_id: str,
        width: int = 200,
        height: int = 200
    ) -> str:
        """
        Generate thumbnail URL for a document (works for images and PDFs)
        
        Args:
            public_id: Cloudinary public ID
            width: Thumbnail width
            height: Thumbnail height
        
        Returns:
            Thumbnail URL
        """
        try:
            # For PDFs, Cloudinary can generate thumbnails from first page
            thumbnail_url = cloudinary.CloudinaryImage(public_id).build_url(
                width=width,
                height=height,
                crop="fill",
                format="jpg",
                page=1  # First page for PDFs
            )
            return thumbnail_url
        except:
            return None
    
    def get_document_info(self, public_id: str) -> Dict[str, Any]:
        """
        Get information about an uploaded document
        
        Args:
            public_id: Cloudinary public ID
        
        Returns:
            Document metadata
        """
        try:
            result = cloudinary.api.resource(public_id, resource_type="auto")
            return {
                "success": True,
                "public_id": result.get("public_id"),
                "format": result.get("format"),
                "resource_type": result.get("resource_type"),
                "bytes": result.get("bytes"),
                "url": result.get("secure_url"),
                "created_at": result.get("created_at")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_service = None

def get_cloudinary_service() -> CloudinaryService:
    """Get or create CloudinaryService instance"""
    global _service
    if _service is None:
        _service = CloudinaryService()
    return _service
