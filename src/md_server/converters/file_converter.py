from fastapi import UploadFile
from .base_converter import BaseConverter
from ..adapters.markitdown_adapter import MarkItDownAdapter
from ..core.exceptions import UnsupportedFileTypeError, FileTooLargeError
from ..core.markitdown_config import MarkItDownConfig


class FileConverter(BaseConverter):
    def __init__(self, settings, markitdown_config: MarkItDownConfig = None):
        super().__init__(settings)
        self.adapter = MarkItDownAdapter(
            config=markitdown_config, timeout_seconds=settings.timeout_seconds
        )

    async def convert(self, file: UploadFile) -> str:
        self._validate_file(file)

        content = await file.read()
        return await self.adapter.convert_content(content, file.filename)

    def _validate_file(self, file: UploadFile):
        if file.content_type not in self.settings.allowed_file_types:
            raise UnsupportedFileTypeError(
                f"File type {file.content_type} not supported"
            )

        if file.size and file.size > self.settings.max_file_size:
            raise FileTooLargeError(
                f"File size {file.size} exceeds limit {self.settings.max_file_size}"
            )
