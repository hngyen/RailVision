class UpstreamUnavailableError(Exception):
    """Raised when the TfNSW API returns a non-200 response."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
