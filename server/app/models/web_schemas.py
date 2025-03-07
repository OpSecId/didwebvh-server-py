"""Pydantic models for the web schemas."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .di_proof import DataIntegrityProof
from .did_document import SecuredDidDocument
from .did_log import InitialLogEntry, LogEntry, WitnessProof


class BaseModel(BaseModel):
    """Base model for all models in the application."""

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Dump the model to a dictionary."""
        return super().model_dump(by_alias=True, exclude_none=True, **kwargs)


class RegisterDID(BaseModel):
    """RegisterDID model."""

    didDocument: SecuredDidDocument = Field()


class RegisterInitialLogEntry(BaseModel):
    """RegisterInitialLogEntry model."""

    logEntry: InitialLogEntry = Field()


class AddLogEntry(BaseModel):
    """AddLogEntry model."""

    logEntry: LogEntry = Field()
    witnessProof: WitnessProof = Field()


# class DeactivateLogEntry(BaseModel):
#     logEntry: LogEntry = Field()
#     witnessProof: WitnessSignature = Field()
