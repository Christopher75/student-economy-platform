"""
Custom Cloudinary storage backend compatible with Django 6.0.
Uses the cloudinary package directly without django-cloudinary-storage.
"""
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.core.files.storage import Storage
from django.conf import settings


# Formats Cloudinary can deliver that we want to keep as-is.
# Everything else falls back to auto-format delivery.
SUPPORTED_FORMATS = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'svg', 'ico', 'avif'}


class CloudinaryMediaStorage(Storage):
    """Stores uploaded media files on Cloudinary."""

    def _get_public_id(self, name):
        """Return the Cloudinary public_id (path without extension)."""
        root, _ = os.path.splitext(name)
        return root.replace("\\", "/")

    def _get_format(self, name):
        """Return the lowercase format extension from the stored name, or None."""
        _, ext = os.path.splitext(name)
        fmt = ext.lstrip(".").lower()
        # Normalise: both 'jpg' and 'jpeg' are valid; keep as-is for Cloudinary
        return fmt if fmt in SUPPORTED_FORMATS else None

    def _open(self, name, mode="rb"):
        raise NotImplementedError("Cloudinary storage does not support opening files.")

    def _save(self, name, content):
        public_id = self._get_public_id(name)
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            overwrite=True,
            resource_type="auto",
        )
        stored_public_id = result.get("public_id", public_id)
        # Preserve the actual format returned by Cloudinary so the URL is explicit
        fmt = result.get("format", "")
        if fmt:
            return f"{stored_public_id}.{fmt}"
        return stored_public_id

    def delete(self, name):
        public_id = self._get_public_id(name)
        try:
            cloudinary.api.delete_resources([public_id])
        except Exception:
            pass

    def exists(self, name):
        try:
            cloudinary.api.resource(self._get_public_id(name))
            return True
        except Exception:
            return False

    def url(self, name):
        public_id = self._get_public_id(name)
        fmt = self._get_format(name)
        kwargs = {"secure": True}
        if fmt:
            kwargs["format"] = fmt
        return cloudinary.CloudinaryImage(public_id).build_url(**kwargs)

    def size(self, name):
        try:
            info = cloudinary.api.resource(self._get_public_id(name))
            return info.get("bytes", 0)
        except Exception:
            return 0
