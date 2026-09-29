"""
Validateurs pour uploads de fichiers.

Securite :
- Taille max configuree via DJANGO_MAX_UPLOAD_SIZE (defaut 5MB)
- Types MIME autorises via DJANGO_ALLOWED_UPLOAD_TYPES
- Verification signatures de fichiers (magic numbers) sans dependance externe
"""
import struct
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


# Signatures de fichiers (magic numbers) pour verification fiable
FILE_SIGNATURES = {
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"],
    "image/webp": [b"RIFF"],  # WebP commence par RIFF, puis WEBP a l'offset 8
    "application/pdf": [b"%PDF"],
}


# Extensions autorisees par type MIME
MIME_EXTENSIONS = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "application/pdf": [".pdf"],
}


def _check_file_signature(file, mime_type):
    """
    Verifie la signature du fichier (magic numbers) sans libmagic.
    Lecture des premiers octets du fichier.
    """
    file.seek(0)
    header = file.read(32)
    file.seek(0)

    if not header:
        return False

    signatures = FILE_SIGNATURES.get(mime_type, [])
    for sig in signatures:
        if header.startswith(sig):
            # Cas special WebP : verifier "WEBP" a l'offset 8
            if mime_type == "image/webp":
                if len(header) >= 12 and header[8:12] == b"WEBP":
                    return True
            else:
                return True
    return False


@deconstructible
class FileUploadValidator:
    """
    Validateur complet pour fichiers uploads.
    Verifie : taille, type MIME (magic numbers), extension.
    Pas de dependance externe (utilise signatures binaires).
    """
    def __init__(
        self,
        max_size=None,
        allowed_types=None,
        allowed_extensions=None,
    ):
        self.max_size = max_size or getattr(
            settings, "DATA_UPLOAD_MAX_MEMORY_SIZE", 5242880
        )
        self.allowed_types = allowed_types or getattr(
            settings, "ALLOWED_UPLOAD_TYPES",
            ["image/jpeg", "image/png", "image/webp", "application/pdf"]
        )
        self.allowed_extensions = allowed_extensions or [
            ".jpg", ".jpeg", ".png", ".webp", ".pdf"
        ]

    def __call__(self, file):
        # 1. Taille
        if file.size > self.max_size:
            raise ValidationError(
                f"Fichier trop volumineux. Taille max : {self.max_size // (1024*1024)} MB"
            )

        # 2. Extension
        ext = file.name.lower().rsplit(".", 1)[-1] if "." in file.name else ""
        if f".{ext}" not in self.allowed_extensions:
            raise ValidationError(
                f"Extension non autorisee. Autorisees : {', '.join(self.allowed_extensions)}"
            )

        # 3. Type MIME via signatures binaires (magic numbers)
        # On determine le type MIME attendu par l'extension
        expected_mime = None
        for mime, exts in MIME_EXTENSIONS.items():
            if f".{ext}" in exts:
                expected_mime = mime
                break

        if expected_mime and expected_mime in self.allowed_types:
            if not _check_file_signature(file, expected_mime):
                raise ValidationError(
                    f"Fichier corrompu ou type non correspondant (attendu: {expected_mime})"
                )
        elif expected_mime and expected_mime not in self.allowed_types:
            raise ValidationError(
                f"Type de fichier non autorise : {expected_mime}"
            )

    def __eq__(self, other):
        return (
            isinstance(other, FileUploadValidator)
            and self.max_size == other.max_size
            and self.allowed_types == other.allowed_types
            and self.allowed_extensions == other.allowed_extensions
        )


def validate_image_or_pdf(file):
    """Raccourci pour validateur standard images + PDF."""
    validator = FileUploadValidator()
    return validator(file)