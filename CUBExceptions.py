class CUBError(Exception):
    """Base class for exceptions in the CUB control system"""
    pass


class CUBClose(CUBError):
    """Exception to be raised when the program is signalled to close

        Attributes:
            exit_point -- Point in program where exit was initialised
            operation -- Operation that was unsuccessful
            message   -- Explanation of the error
    """
    def __init__(self, exit_point, message):
        self.exit_point = exit_point
        self.message = message


class InitialisationError(CUBError):
    """Exception to be raised for errors in Initialising the CUB components

        Attributes:
            component -- Component which was not successfully initialised
            message   -- Explanation of the error
    """
    def __init__(self, component, message):
        self.component = component
        self.message = message


class OperationError(CUBError):
    """Exception to be raised for errors in completing an operation

        Attributes:
            component -- Component which was not successfully initialised
            operation -- Operation that was unsuccessful
            message   -- Explanation of the error
    """
    def __init__(self, component, operation, message):
        self.component = component
        self.operation = operation
        self.message = message


class CommunicationError(CUBError):
    """Exception to be raised for errors in communication between threads

        Attributes:
            component -- Component which received communication
            errorInput -- Input that caused the error
            message    -- Explanation of the error
    """
    def __init__(self, component, error_input, message):
        self.component = component
        self.errorInput = error_input
        self.message = message


class InputError(CUBError):
    """Exception to be raised for errors in processing input

        Attributes:
            errorInput -- Input that caused the error
            message    -- Explanation of the error
    """
    def __init__(self, error_input, message):
        self.errorInput = error_input
        self.message = message
