import io
import logging
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, ExifTags

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Data class for file information"""

    file_path: str
    filename: str
    file_size: int
    mime_type: str
    file_type: str
    url: Optional[str] = None
    public_url: Optional[str] = None
    compressed_url: Optional[str] = None  # URL for compressed version
    compressed_public_url: Optional[str] = None  # Public URL for compressed version
    original_size: Optional[int] = None  # Original file size before compression
    compression_ratio: Optional[float] = None  # Compression ratio if compressed
    dimensions: Optional[tuple] = None  # Image dimensions (width, height)
    original_dimensions: Optional[tuple] = None  # Original image dimensions
    compressed_file_path: Optional[str] = None  # Path to compressed file


@dataclass
class ImageCompressionSettings:
    """Settings for image compression"""

    enabled: bool = True
    quality: int = 85  # JPEG quality (1-100)
    max_width: int = 1920
    max_height: int = 1080
    optimize: bool = True
    progressive: bool = True
    keep_exif: bool = False
    auto_orient: bool = True
    format: Optional[str] = None  # Force format conversion (JPEG, PNG, WEBP)


class ImageCompressor:
    """Image compression and optimization utility"""

    def __init__(self, compression_settings: ImageCompressionSettings = None):
        self.settings = compression_settings or ImageCompressionSettings(
            enabled=settings.IMAGE_COMPRESSION_ENABLED,
            quality=settings.IMAGE_QUALITY,
            max_width=settings.IMAGE_MAX_WIDTH,
            max_height=settings.IMAGE_MAX_HEIGHT,
            optimize=settings.IMAGE_OPTIMIZE,
            progressive=settings.IMAGE_PROGRESSIVE,
            keep_exif=settings.IMAGE_KEEP_EXIF,
            auto_orient=settings.IMAGE_AUTO_ORIENT,
        )

    def is_image(self, file: UploadFile) -> bool:
        """Check if file is an image"""
        if not file.content_type:
            return False
        return file.content_type.startswith("image/")

    def compress_image(
        self,
        file: UploadFile,
        custom_settings: Optional[ImageCompressionSettings] = None,
    ) -> tuple[io.BytesIO, dict]:
        """
        Compress image file

        Returns:
            tuple: (compressed_file_buffer, metadata)
        """
        if not self.is_image(file):
            raise ValueError("File is not an image")

        settings_to_use = custom_settings or self.settings

        if not settings_to_use.enabled:
            # Return original file if compression disabled
            file.file.seek(0)
            original_buffer = io.BytesIO(file.file.read())
            file.file.seek(0)
            return original_buffer, {}

        try:
            # Read file content to avoid file pointer issues
            file.file.seek(0)
            file_content = file.file.read()
            original_size = len(file_content)
            file.file.seek(0)  # Reset original file pointer

            # Use the content to create image
            image_buffer = io.BytesIO(file_content)
            image = Image.open(image_buffer)

            original_dimensions = image.size

            # Auto-orient based on EXIF data
            if settings_to_use.auto_orient:
                image = ImageOps.exif_transpose(image)

            # Resize if needed
            if (
                image.width > settings_to_use.max_width
                or image.height > settings_to_use.max_height
            ):
                image.thumbnail(
                    (settings_to_use.max_width, settings_to_use.max_height),
                    Image.Resampling.LANCZOS,
                )

            # Convert format if specified or optimize format
            output_format = settings_to_use.format
            if not output_format:
                if image.format in ["JPEG", "JPG"]:
                    output_format = "JPEG"
                elif image.format == "PNG" and image.mode == "RGBA":
                    output_format = "PNG"
                elif image.format == "PNG" and image.mode == "RGB":
                    output_format = (
                        "JPEG"  # Convert RGB PNG to JPEG for better compression
                    )
                else:
                    output_format = "JPEG"

            # Convert to RGB if saving as JPEG
            if output_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
                # Create white background for transparent images
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                rgb_image.paste(
                    image, mask=image.split()[-1] if image.mode == "RGBA" else None
                )
                image = rgb_image

            # Prepare save options
            save_options = {
                "format": output_format,
                "optimize": settings_to_use.optimize,
            }

            if output_format == "JPEG":
                save_options.update(
                    {
                        "quality": settings_to_use.quality,
                        "progressive": settings_to_use.progressive,
                    }
                )

                # Handle EXIF data
                if settings_to_use.keep_exif and hasattr(image, "_getexif"):
                    exif = image._getexif()
                    if exif:
                        save_options["exif"] = exif

            elif output_format == "PNG":
                save_options.update(
                    {
                        "compress_level": 6,  # PNG compression level
                    }
                )

            elif output_format == "WEBP":
                save_options.update(
                    {
                        "quality": settings_to_use.quality,
                        "method": 6,  # WebP compression method
                    }
                )

            # Save compressed image
            output_buffer = io.BytesIO()
            image.save(output_buffer, **save_options)
            output_buffer.seek(0)

            compressed_size = len(output_buffer.getvalue())
            compression_ratio = (original_size - compressed_size) / original_size * 100

            metadata = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "original_dimensions": original_dimensions,
                "final_dimensions": image.size,
                "format": output_format,
                "quality": (
                    settings_to_use.quality
                    if output_format in ["JPEG", "WEBP"]
                    else None
                ),
            }

            return output_buffer, metadata

        except Exception as e:
            logger.error(f"Failed to compress image: {str(e)}")
            # Return original file if compression fails
            file.file.seek(0)
            original_buffer = io.BytesIO(file.file.read())
            file.file.seek(0)
            return original_buffer, {"error": str(e)}

    def get_image_info(self, file: UploadFile) -> dict:
        """Get image information without compression"""
        if not self.is_image(file):
            return {}

        try:
            # Create a copy to avoid file pointer issues
            file.file.seek(0)
            file_content = file.file.read()
            file.file.seek(0)  # Reset original file pointer

            # Use the copy for image analysis
            image_buffer = io.BytesIO(file_content)
            image = Image.open(image_buffer)

            return {
                "dimensions": image.size,
                "format": image.format,
                "mode": image.mode,
                "has_transparency": image.mode in ("RGBA", "LA")
                or "transparency" in image.info,
            }
        except Exception as e:
            logger.error(f"Failed to get image info: {str(e)}")
            return {"error": str(e)}


class FileStorageInterface(ABC):
    """Abstract interface for file storage"""

    @abstractmethod
    def upload_file(
        self, file: UploadFile, filename: str, folder: str = "", **kwargs
    ) -> FileInfo:
        """Upload file to storage"""
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in storage"""
        pass

    @abstractmethod
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get URL to access file"""
        pass


class LocalFileStorage(FileStorageInterface):
    """Local file storage implementation"""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.LOCAL_UPLOAD_PATH
        self._ensure_directory_exists(self.base_path)

    def _ensure_directory_exists(self, directory: str) -> None:
        """Create directory if it doesn't exist"""
        Path(directory).mkdir(parents=True, exist_ok=True)

    def upload_file(
        self, file: UploadFile, filename: str, folder: str = "", **kwargs
    ) -> FileInfo:
        """Upload file to local storage"""
        # Construct full path
        if folder:
            full_directory = os.path.join(self.base_path, folder)
            self._ensure_directory_exists(full_directory)
            file_path = os.path.join(full_directory, filename)
        else:
            file_path = os.path.join(self.base_path, filename)

        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Get file info
            file_size = os.path.getsize(file_path)
            file_type = (
                file.content_type.split("/")[0] if file.content_type else "unknown"
            )

            return FileInfo(
                file_path=file_path,
                filename=filename,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                file_type=file_type,
                url=file_path,
                public_url=f"/{file_path}",  # Relative URL for local files
            )

        except Exception as e:
            logger.error(f"Failed to save file locally: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to save file: {str(e)}"
            )

    def delete_file(self, file_path: str) -> bool:
        """Delete file from local storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists locally"""
        return os.path.exists(file_path)

    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get URL for local file"""
        return f"/{file_path}"


class DigitalOceanSpacesStorage(FileStorageInterface):
    """DigitalOcean Spaces storage implementation"""

    def __init__(self):
        if not settings.spaces_enabled:
            raise ValueError("DigitalOcean Spaces configuration is incomplete")

        self.client = boto3.client(
            "s3",
            region_name=settings.DO_SPACES_REGION,
            endpoint_url=settings.DO_SPACES_ENDPOINT,
            aws_access_key_id=settings.DO_SPACES_KEY,
            aws_secret_access_key=settings.DO_SPACES_SECRET,
        )
        self.bucket_name = settings.DO_SPACES_BUCKET
        self.cdn_endpoint = settings.DO_SPACES_CDN_ENDPOINT

    def upload_file(
        self,
        file: UploadFile,
        filename: str,
        folder: str = "",
        acl: str = "public-read",
        **kwargs,
    ) -> FileInfo:
        """Upload file to DigitalOcean Spaces"""
        # Construct object key
        if folder:
            object_key = f"{folder.strip('/')}/{filename}"
        else:
            object_key = filename

        try:
            # Get file size before upload to avoid file pointer issues
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset file pointer

            # Upload file
            self.client.upload_fileobj(
                file.file,
                self.bucket_name,
                object_key,
                ExtraArgs={
                    "ACL": acl,
                    "ContentType": file.content_type or "application/octet-stream",
                },
            )

            # Generate URLs
            file_url = f"{settings.DO_SPACES_ENDPOINT}/{self.bucket_name}/{object_key}"
            public_url = (
                f"{self.cdn_endpoint}/{object_key}" if self.cdn_endpoint else file_url
            )

            file_type = (
                file.content_type.split("/")[0] if file.content_type else "unknown"
            )

            return FileInfo(
                file_path=object_key,
                filename=filename,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                file_type=file_type,
                url=file_url,
                public_url=public_url,
            )

        except ClientError as e:
            logger.error(f"Failed to upload file to Spaces: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            )

    def delete_file(self, file_path: str) -> bool:
        """Delete file from DigitalOcean Spaces"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from Spaces: {str(e)}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in DigitalOcean Spaces"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False

    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get pre-signed URL for file"""
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return ""


class FileUploadService:
    """Main file upload service with comprehensive features"""

    def __init__(self, storage_provider: str = None):
        self.storage_provider = storage_provider or settings.STORAGE_PROVIDER
        self.storage = self._get_storage_backend()
        self.image_compressor = ImageCompressor()

    def _get_storage_backend(self) -> FileStorageInterface:
        """Get storage backend based on configuration"""
        if self.storage_provider == "spaces":
            return DigitalOceanSpacesStorage()
        else:
            return LocalFileStorage()

    def validate_file(
        self,
        file: UploadFile,
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None,
        file_category: str = "file",
    ) -> None:
        """Validate uploaded file"""
        if allowed_types is None:
            if file_category == "image":
                allowed_types = settings.ALLOWED_IMAGE_TYPES
            else:
                allowed_types = settings.ALLOWED_FILE_TYPES

        if max_size is None:
            max_size = settings.MAX_FILE_SIZE

        # Check file type
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not allowed. Allowed types: {', '.join(allowed_types)}",
            )

        # Check file size
        if hasattr(file.file, "seek") and hasattr(file.file, "tell"):
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning

            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size {file_size} bytes exceeds maximum allowed size {max_size} bytes",
                )

    def generate_filename(
        self,
        original_filename: str,
        prefix: str = "",
        suffix: str = "",
        include_timestamp: bool = True,
        include_uuid: bool = False,
    ) -> str:
        """Generate unique filename"""
        if not original_filename:
            file_ext = ".bin"
            base_name = "file"
        else:
            path = Path(original_filename)
            file_ext = path.suffix.lower()
            base_name = path.stem

        filename_parts = []

        if prefix:
            filename_parts.append(prefix)

        filename_parts.append(base_name)

        if include_timestamp:
            timestamp = str(int(datetime.utcnow().timestamp() * 1000))
            filename_parts.append(timestamp)

        if include_uuid:
            filename_parts.append(str(uuid.uuid4())[:8])

        if suffix:
            filename_parts.append(suffix)

        return "_".join(filename_parts) + file_ext

    def upload_file(
        self,
        file: UploadFile,
        folder: str = "",
        filename: Optional[str] = None,
        prefix: str = "",
        suffix: str = "",
        file_category: str = "file",
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None,
        replace_existing: bool = False,
        existing_file_path: Optional[str] = None,
        compress_image: bool = None,
        compression_settings: Optional[ImageCompressionSettings] = None,
        upload_original: bool = False,
        **kwargs,
    ) -> FileInfo:
        """
        Upload file with comprehensive options

        Args:
            file: UploadFile object
            folder: Folder to store file in
            filename: Custom filename (if None, will generate)
            prefix: Filename prefix
            suffix: Filename suffix
            file_category: "file" or "image" for validation
            allowed_types: Override allowed file types
            max_size: Override max file size
            replace_existing: Whether to delete existing file
            existing_file_path: Path to existing file to replace
            compress_image: Whether to compress image (None = auto-detect, True = force, False = disable)
            compression_settings: Custom compression settings
            upload_original: Whether to upload both original and compressed versions
            **kwargs: Additional arguments for storage backend

        Returns:
            FileInfo object with file details
        """
        # Store original file content and metadata for compression stats
        original_file_size = None
        compression_metadata = {}
        original_file_content = None

        # Validate file
        self.validate_file(file, allowed_types, max_size, file_category)

        # Check if we should compress the image
        should_compress = compress_image
        if should_compress is None:
            # Auto-detect: compress if it's an image and compression is enabled
            should_compress = (
                file_category == "image"
                and self.image_compressor.is_image(file)
                and settings.IMAGE_COMPRESSION_ENABLED
            )

        # Handle image compression and dual upload scenario
        if should_compress and self.image_compressor.is_image(file):
            try:
                # Get original file size and content
                file.file.seek(0, 2)
                original_file_size = file.file.tell()
                file.file.seek(0)
                original_file_content = file.file.read()
                file.file.seek(0)  # Reset original file pointer

                # Create a copy for compression
                file_copy = UploadFile(
                    file=io.BytesIO(original_file_content),
                    filename=file.filename,
                    headers=file.headers,
                )

                # Compress image using the copy
                compressed_buffer, metadata = self.image_compressor.compress_image(
                    file_copy, compression_settings
                )
                compression_metadata = metadata

                # Generate filename if not provided
                if filename is None:
                    filename = self.generate_filename(
                        file.filename or "upload",
                        prefix=prefix,
                        suffix=suffix,
                        include_timestamp=True,
                        include_uuid=True,
                    )

                # Delete existing file if requested
                if replace_existing and existing_file_path:
                    self.delete_file(existing_file_path)

                # If upload_original is True, upload both versions
                if upload_original:
                    # Upload original file first
                    original_file_upload = UploadFile(
                        file=io.BytesIO(original_file_content),
                        filename=file.filename,
                        headers=file.headers,
                    )

                    # Generate original filename
                    original_filename = f"original_{filename}"
                    file_info = self.storage.upload_file(
                        original_file_upload, original_filename, folder, **kwargs
                    )

                    # Upload compressed version
                    compressed_filename = f"compressed_{filename}"
                    # Update filename extension if format changed
                    if metadata.get("format"):
                        path = Path(compressed_filename)
                        new_ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(
                            metadata["format"], path.suffix
                        )
                        compressed_filename = str(path.with_suffix(new_ext))

                    compressed_file_upload = UploadFile(
                        file=compressed_buffer,
                        filename=file.filename,
                        headers=file.headers,
                    )

                    compressed_file_info = self.storage.upload_file(
                        compressed_file_upload, compressed_filename, folder, **kwargs
                    )

                    # Update file_info with compressed URLs
                    file_info.compressed_url = compressed_file_info.url
                    file_info.compressed_public_url = compressed_file_info.public_url
                    file_info.compressed_file_path = compressed_file_info.file_path

                else:
                    # Upload only compressed version (original behavior)
                    # Update filename extension if format changed
                    if metadata.get("format") and filename:
                        path = Path(filename)
                        new_ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(
                            metadata["format"], path.suffix
                        )
                        filename = str(path.with_suffix(new_ext))

                    # Replace the file content with compressed buffer
                    file.file = compressed_buffer
                    file_info = self.storage.upload_file(
                        file, filename, folder, **kwargs
                    )

            except Exception as e:
                logger.warning(
                    f"Image compression failed, uploading original: {str(e)}"
                )
                # Continue with original file if compression fails
                # Generate filename if not provided
                if filename is None:
                    filename = self.generate_filename(
                        file.filename or "upload",
                        prefix=prefix,
                        suffix=suffix,
                        include_timestamp=True,
                        include_uuid=True,
                    )

                # Delete existing file if requested
                if replace_existing and existing_file_path:
                    self.delete_file(existing_file_path)

                # Upload original file
                file_info = self.storage.upload_file(file, filename, folder, **kwargs)

        else:
            # Generate filename if not provided
            if filename is None:
                filename = self.generate_filename(
                    file.filename or "upload",
                    prefix=prefix,
                    suffix=suffix,
                    include_timestamp=True,
                    include_uuid=True,
                )

            # Delete existing file if requested
            if replace_existing and existing_file_path:
                self.delete_file(existing_file_path)

            # Upload file normally (no compression)
            file_info = self.storage.upload_file(file, filename, folder, **kwargs)

        # Add compression metadata to FileInfo
        if compression_metadata:
            file_info.original_size = original_file_size
            file_info.compression_ratio = compression_metadata.get("compression_ratio")
            file_info.dimensions = compression_metadata.get("final_dimensions")
            file_info.original_dimensions = compression_metadata.get(
                "original_dimensions"
            )
            file_info.compressed_file_path = compression_metadata.get(
                "compressed_file_path"
            )

        # Add image dimensions for images (even if not compressed)
        elif file_category == "image" and self.image_compressor.is_image(file):
            try:
                image_info = self.image_compressor.get_image_info(file)
                if "dimensions" in image_info:
                    file_info.dimensions = image_info["dimensions"]
            except Exception:
                pass  # Ignore errors getting image info

        print(file_info)
        return file_info

    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        return self.storage.delete_file(file_path)

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        return self.storage.file_exists(file_path)

    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get URL to access file"""
        return self.storage.get_file_url(file_path, expires_in)

    def upload_compressed_image(
        self,
        file: UploadFile,
        folder: str = "images",
        quality: int = None,
        max_width: int = None,
        max_height: int = None,
        format: str = None,
        upload_original: bool = False,
        **kwargs,
    ) -> FileInfo:
        """
        Upload image with specific compression settings

        Args:
            file: Image file to upload
            folder: Folder to store image in
            quality: JPEG/WebP quality (1-100)
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            format: Force format conversion (JPEG, PNG, WEBP)
            upload_original: Whether to upload both original and compressed versions
            **kwargs: Additional upload arguments

        Returns:
            FileInfo with compression details
        """
        # Create custom compression settings
        compression_settings = ImageCompressionSettings(
            enabled=True,
            quality=quality or settings.IMAGE_QUALITY,
            max_width=max_width or settings.IMAGE_MAX_WIDTH,
            max_height=max_height or settings.IMAGE_MAX_HEIGHT,
            optimize=settings.IMAGE_OPTIMIZE,
            progressive=settings.IMAGE_PROGRESSIVE,
            keep_exif=settings.IMAGE_KEEP_EXIF,
            auto_orient=settings.IMAGE_AUTO_ORIENT,
            format=format,
        )

        return self.upload_file(
            file=file,
            folder=folder,
            file_category="image",
            compress_image=True,
            compression_settings=compression_settings,
            upload_original=upload_original,
            **kwargs,
        )

    def upload_image_with_variants(
        self,
        file: UploadFile,
        folder: str = "images",
        quality: int = None,
        max_width: int = None,
        max_height: int = None,
        format: str = None,
        **kwargs,
    ) -> FileInfo:
        """
        Upload image with both original and compressed versions
        This is a convenience method that always uploads both variants

        Args:
            file: Image file to upload
            folder: Folder to store image in
            quality: JPEG/WebP quality (1-100)
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            format: Force format conversion (JPEG, PNG, WEBP)
            **kwargs: Additional upload arguments

        Returns:
            FileInfo with both original and compressed URLs
        """
        return self.upload_compressed_image(
            file=file,
            folder=folder,
            quality=quality,
            max_width=max_width,
            max_height=max_height,
            format=format,
            upload_original=True,
            **kwargs,
        )

    def upload_multiple_files(
        self, files: List[UploadFile], folder: str = "", **kwargs
    ) -> List[FileInfo]:
        """Upload multiple files"""
        results = []
        for file in files:
            try:
                result = self.upload_file(file, folder=folder, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {str(e)}")
                # Continue with other files
        return results


# Global instance for easy import
file_upload_service = FileUploadService("spaces")


# Example usage:
"""
# Basic upload with compression only
file_info = file_upload_service.upload_file(
    file=upload_file,
    folder="images",
    file_category="image",
    compress_image=True
)
# Returns: file_info.url (compressed version only)

# Upload with both original and compressed versions
file_info = file_upload_service.upload_file(
    file=upload_file,
    folder="images", 
    file_category="image",
    compress_image=True,
    upload_original=True
)
# Returns: 
# - file_info.url (original version)
# - file_info.compressed_url (compressed version) 
# - file_info.public_url (original public URL)
# - file_info.compressed_public_url (compressed public URL)

# Or use the convenience method
file_info = file_upload_service.upload_image_with_variants(
    file=upload_file,
    folder="images",
    quality=80,
    max_width=1920
)
# Always uploads both original and compressed versions
"""
