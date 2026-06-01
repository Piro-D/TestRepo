from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

import config


def save_upload(file_storage):
    filename = secure_filename(file_storage.filename)
    unique_name = f"{uuid4().hex}_{filename}"
    destination = Path(config.UPLOAD_FOLDER) / unique_name
    file_storage.save(destination)
    return destination


def remove_file(path):
    with suppress(OSError):
        Path(path).unlink()
