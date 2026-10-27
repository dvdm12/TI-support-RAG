"""Bounded, single-image uploads with server-owned temporary filenames."""
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import warnings

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from PIL import Image, UnidentifiedImageError


class UploadError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class BoundedImageUploadHandler(FileUploadHandler):
    """Stop receiving a file at the limit, including misleading Content-Length."""
    def __init__(self, request):
        super().__init__(request)
        self.error = None
        self.file_count = 0
        self.received = 0
        self.buffer = None

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.file_count += 1
        if self.file_count != 1 or self.field_name != 'imagen':
            self.error = UploadError('invalid_input', 'Envía un único archivo en el campo imagen.')
            raise StopUpload(connection_reset=True)
        self.received = 0
        self.buffer = BytesIO()

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > settings.OCR_MAX_UPLOAD_BYTES:
            self.error = UploadError('body_too_large', 'La imagen supera el límite de 5 MiB.', 413)
            self.buffer.close()
            raise StopUpload(connection_reset=True)
        self.buffer.write(raw_data)
        return None

    def file_complete(self, file_size):
        self.buffer.seek(0)
        return InMemoryUploadedFile(self.buffer, self.field_name, self.file_name,
                                    self.content_type, file_size, self.charset)

    def upload_interrupted(self):
        if self.buffer is not None:
            self.buffer.close()


FORMATS = {
    'PNG': ({'.png'}, 'image/png', '.png'),
    'JPEG': ({'.jpg', '.jpeg'}, 'image/jpeg', '.jpg'),
    'WEBP': ({'.webp'}, 'image/webp', '.webp'),
}


def validated_image_bytes(upload):
    # Bound actual bytes, not only the client-supplied size or filename.
    data = upload.read(settings.OCR_MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.OCR_MAX_UPLOAD_BYTES:
        raise UploadError('body_too_large', 'La imagen supera el límite de 5 MiB.', 413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                specification = FORMATS.get(image.format)
                if specification is None:
                    raise UploadError('unsupported_image', 'Usa una imagen PNG, JPEG o WebP.', 415)
                extensions, mime, suffix = specification
                if Path(upload.name).suffix.lower() not in extensions or (upload.content_type or '').lower() != mime:
                    raise UploadError('unsupported_image', 'El formato real, la extensión y el tipo de imagen no coinciden.', 415)
                width, height = image.size
                if (width * height > settings.OCR_MAX_IMAGE_PIXELS
                        or max(width, height) > settings.OCR_MAX_IMAGE_SIDE):
                    raise UploadError('image_too_large', 'Recorta la captura: máximo 4 megapíxeles y 4096 píxeles por lado.', 413)
                if getattr(image, 'n_frames', 1) != 1:
                    raise UploadError('unsupported_image', 'La imagen debe tener un único fotograma.', 415)
                image.verify()
            # Header verification alone does not guarantee a decodable pixel payload.
            with Image.open(BytesIO(data)) as image:
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise UploadError('image_too_large', 'La imagen excede las dimensiones permitidas.', 413) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        if isinstance(exc, UploadError):
            raise
        raise UploadError('invalid_image', 'El archivo no es una imagen válida o está dañado.') from exc
    return data, suffix


@contextmanager
def temporary_ocr_image(upload):
    data, suffix = validated_image_bytes(upload)
    with TemporaryDirectory(prefix='ti-support-ocr-') as directory:
        path = Path(directory) / ('input' + suffix)
        path.write_bytes(data)
        # Cleanup runs on success, failed extraction and failed budget validation.
        yield path
