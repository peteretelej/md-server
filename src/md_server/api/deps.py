from typing import Annotated
from fastapi import Depends
from ..core.config import Settings, get_settings

def get_converter_service():
    from ..converters.file_converter import FileConverter
    settings = get_settings()
    return FileConverter(settings)

def get_url_converter():
    from ..converters.url_converter import URLConverter
    settings = get_settings()
    return URLConverter(settings)

SettingsDep = Annotated[Settings, Depends(get_settings)]
FileConverterDep = Annotated[object, Depends(get_converter_service)]
URLConverterDep = Annotated[object, Depends(get_url_converter)]