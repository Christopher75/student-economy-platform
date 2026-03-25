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


class CloudinaryMediaStorage(Storage):
    """Stores uploaded media files on Cloudinary."""

    def _get_public_id(self, name):
        # Strip extension — Cloudinary stores it separately
        root, _ = os.path.splitext(name)
        return root.replace("\\", "/")

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
        # Return the full public_id with extension so Django stores a usable name
        return result.get("public_id", name)

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
        return cloudinary.CloudinaryImage(public_id).build_url(secure=True)

    def size(self, name):
        try:
            info = cloudinary.api.resource(self._get_public_id(name))
            return info.get("bytes", 0)
        except Exception:
            return 0
