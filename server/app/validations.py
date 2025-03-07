"""Validation functions for evaluating spec text."""

from config import settings

def validate_first_log_entry(log_entry):
    """Function for validating an initial log entry."""
    
    # Version ID
    assert log_entry.get('versionId')
    
    # Version Time
    assert log_entry.get('versionTime')
    
    # Parameters
    parameters = log_entry.get('parameters')
    
    # method
    # This property MUST appear in the first DID log entry.
    assert parameters.get('method'), 'This property MUST appear in the first DID log entry.'
    # assert parameters.get('method') == settings.WEBVH_VERSION
    
    # scid
    assert parameters.get('scid'), 'This property MUST appear in the first DID log entry.'
    
    # updateKeys
    assert parameters.get('updateKeys'), 'This property MUST appear in the first DID log entry.'
    
    # A key from the updateKeys array in the first DID log entry MUST 
    # be used to authorize the initial log entry.
    # TODO check if verification method in updateKeys
    
    # updateKeys MUST have at least 1 entry and MUST NOT be set to an empty list [].
    assert len(parameters.get('updateKeys')) >= 1
    assert parameters.get('updateKeys') != []
    
    # portable
    # If not explicitly set in the first log entry, it MUST be set to false.
    # TODO, clarify statement
    
    # nextKeyHashes
    # If not explicitly set in the first DID Log entry, its value MUST be null.
    # TODO, clarify statement
    
    # nextKeyHashes MUST have at least 1 entry and MUST NOT be set to an empty list [].
    assert len(parameters.get('nextKeyHashes')) >= 1
    assert parameters.get('nextKeyHashes') != []
    
    # witness
    # A witness property in the first DID log entry is immediately “active” and used to define the 
    # witnesses and necessary threshold for witnessing the initial log entry.
    # TODO
    
    # witness MUST have at least 1 entry and MUST NOT be set to an empty list [].
    assert len(parameters.get('witness')) >= 1
    assert parameters.get('witness') != []
    
    # ttl
    # If not specified, its value MUST be null
    
    # State
    
    # Proof

def validate_update_log_entry(log_entry):
    pass