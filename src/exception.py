import sys

def error_message_detail(error, error_detail:sys):
    _,_,exc_tb = error_detail.exc_info()
    file_name = exc_tb.tb_frame.f_code.co_filename
    error_message = "Error occured in python script name [{0}] line number [{1}] error message [{2}]".format(
        file_name, exc_tb.tb_lineno, str(error)
    )
    return error_message

class CustomException(Exception):

    def __init__(self, error_message, error_detail:sys):
        super().__init__(error_message)
        self.error_message = error_message_detail(error_message, error_detail = error_detail)

    def __str__(self):
        return self.error_message


class ExcelParsingError(CustomException):
    """Raised when the Excel file cannot be parsed or is missing required columns."""
    def __init__(self, error_message, error_detail: sys):
        super().__init__(error_message, error_detail=error_detail)


class EmailSendError(CustomException):
    """Raised when an email fails to send via SMTP."""
    def __init__(self, error_message, error_detail: sys):
        super().__init__(error_message, error_detail=error_detail)