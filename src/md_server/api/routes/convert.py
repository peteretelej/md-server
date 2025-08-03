from fastapi import APIRouter, UploadFile, File, HTTPException
from ..deps import FileConverterDep, URLConverterDep
from ..models import URLConvertRequest, MarkdownResponse
from ...core.exceptions import (
    UnsupportedFileTypeError,
    FileTooLargeError,
    URLFetchError,
    ConversionTimeoutError,
)

router = APIRouter()


@router.post("/convert", response_model=MarkdownResponse)
async def convert_file(
    file: UploadFile = File(...), converter: FileConverterDep = None
):
    try:
        markdown = await converter.convert(file)
        return MarkdownResponse(markdown=markdown)
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except ConversionTimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@router.post("/convert/url", response_model=MarkdownResponse)
async def convert_url(request: URLConvertRequest, converter: URLConverterDep = None):
    try:
        markdown = await converter.convert(str(request.url))
        return MarkdownResponse(markdown=markdown)
    except URLFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConversionTimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
