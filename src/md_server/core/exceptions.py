class MarkdownConversionError(Exception):
    pass


class UnsupportedFileTypeError(MarkdownConversionError):
    pass


class FileTooLargeError(MarkdownConversionError):
    pass


class URLFetchError(MarkdownConversionError):
    pass


class ConversionTimeoutError(MarkdownConversionError):
    pass
