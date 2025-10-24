#!/usr/bin/env python3
"""
Test script to validate UNTP credentials against their JSON schemas.
"""

import json
import httpx
from jsonschema import validate, ValidationError
from datetime import datetime


# Schema URLs
SCHEMAS = {
    "DCC": "https://test.uncefact.org/vocabulary/untp/dcc/untp-dcc-schema-0.6.0.json",
    "DIA": "https://test.uncefact.org/vocabulary/untp/dia/untp-dia-schema-0.6.0.json",
    "DPP": "https://test.uncefact.org/vocabulary/untp/dpp/untp-dpp-schema-0.6.0.json",
}


def create_test_dcc():
    """Create a test Mines Act Permit (DCC) credential."""
    return {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://test.uncefact.org/vocabulary/untp/dcc/0.6.0/"
        ],
        "type": ["DigitalConformityCredential", "VerifiableCredential"],
        "id": "did:webvh:localhost:bc-gov:cpo/credentials/mines-permit-001",
        "issuer": {
            "type": ["CredentialIssuer"],
            "id": "did:webvh:localhost:bc-gov:cpo",
            "name": "Chief Permitting Officer",
            "issuerAlsoKnownAs": [
                {
                    "id": "https://www2.gov.bc.ca/gov/content/industry/mineral-exploration-mining",
                    "name": "BC Ministry of Energy, Mines and Low Carbon Innovation",
                    "registeredId": "BC-EMLI"
                }
            ]
        },
        "validFrom": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "credentialSubject": {
            "type": ["ConformityAttestation", "Attestation"],
            "id": "urn:uuid:mines-permit-tek-001",
            "name": "Mines Act Permit - Tek Copper Mine",
            "assessorLevel": "Self",
            "assessmentLevel": "GovtApproval",
            "attestationType": "certification",
            "description": "Operating permit for copper mining operations under the BC Mines Act",
            "issuedToParty": {
                "id": "urn:uuid:org-tek-mines",
                "name": "Tek Mines",
                "registeredId": "A0061056",
                "idScheme": {
                    "type": ["IdentifierScheme"],
                    "id": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00",
                    "name": "BC Business Corporations Act - Registry ID"
                }
            },
            "authorisation": [
                {
                    "type": ["Endorsement"],
                    "id": "urn:uuid:permit-ma-2024-001",
                    "name": "BC Mines Act Operating Permit",
                    "identifier": {
                        "registeredId": "M-24-0001-COPPER",
                        "idScheme": {
                            "type": ["IdentifierScheme"],
                            "id": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96293_01#section10",
                            "name": "BC Mines Act - Section 10 Permits"
                        }
                    },
                    "issuingAuthority": {
                        "id": "did:webvh:localhost:bc-gov:cpo",
                        "name": "Chief Permitting Officer"
                    },
                    "effectiveDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            ],
            "conformityTopic": "governance.compliance",
            "assessedFacility": {
                "type": ["FacilityVerification"],
                "facility": {
                    "id": "urn:uuid:facility-tek-mine-001",
                    "name": "Tek Copper Mine",
                    "registeredId": "MINE-BC-001"
                },
                "IDverifiedByCAB": True
            },
            "assessedProduct": {
                "type": ["ProductVerification"],
                "product": {
                    "id": "urn:uuid:product-copper-ore",
                    "name": "Copper Ore",
                    "registeredId": "7403.11"
                },
                "IDverifiedByCAB": True
            },
            "regulation": [
                {
                    "type": ["Regulation"],
                    "id": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96293_01",
                    "name": "Mines Act [RSBC 1996] CHAPTER 293",
                    "jurisdictionCountry": "CA",
                    "administeredBy": {
                        "id": "https://www2.gov.bc.ca/gov/content/industry/mineral-exploration-mining",
                        "name": "BC Ministry of Energy, Mines and Low Carbon Innovation"
                    },
                    "effectiveDate": "1996-01-01"
                }
            ]
        }
    }


def validate_credential(credential: dict, schema_url: str, cred_type: str):
    """Validate a credential against its JSON schema."""
    print(f"\nValidating {cred_type} credential...")
    print(f"Schema: {schema_url}")
    
    try:
        # Fetch schema
        response = httpx.get(schema_url, timeout=10.0)
        response.raise_for_status()
        schema = response.json()
        
        # Validate credential
        validate(instance=credential, schema=schema)
        
        print(f"✓ {cred_type} credential is VALID")
        return True
        
    except httpx.HTTPError as e:
        print(f"✗ Failed to fetch schema: {e}")
        return False
    except ValidationError as e:
        print(f"✗ {cred_type} credential is INVALID")
        print(f"  Error: {e.message}")
        print(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        return False
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False


def create_test_dia():
    """Create a test BC Registration (DIA) credential."""
    return {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://test.uncefact.org/vocabulary/untp/dia/0.6.0/"
        ],
        "type": ["VerifiableCredential", "DigitalIdentityAnchor"],
        "id": "did:webvh:localhost:bc-gov:roc/credentials/bc-registration-A0061056",
        "issuer": {
            "type": ["CredentialIssuer"],
            "id": "did:webvh:localhost:bc-gov:roc",
            "name": "BC Registrar of Companies",
            "issuerAlsoKnownAs": [
                {
                    "id": "https://www2.gov.bc.ca/gov/content/governments/organizational-structure/ministries-organizations/ministries/citizens-services/bc-registries",
                    "name": "BC Registries and Online Services",
                    "registeredId": "BC-REGISTRIES"
                }
            ]
        },
        "validFrom": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "credentialSubject": {
            "type": ["RegisteredIdentity"],
            "id": "did:webvh:localhost:tekmines:org",
            "name": "Teck Resources Limited",
            "registeredId": "A0061056",
            "idScheme": {
                "type": ["IdentifierScheme"],
                "id": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00",
                "name": "BC Business Corporations Act [SBC 2002] CHAPTER 57"
            },
            "registerType": "Business",
            "registrationScopeList": [
                "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00#section13"
            ]
        }
    }


def main():
    """Run credential validation tests."""
    print("="*70)
    print("UNTP Credential Schema Validation Tests")
    print("="*70)
    
    # Test DCC (Mines Act Permit)
    dcc = create_test_dcc()
    dcc_valid = validate_credential(dcc, SCHEMAS["DCC"], "DCC")
    
    # Test DIA (BC Registration)
    dia = create_test_dia()
    dia_valid = validate_credential(dia, SCHEMAS["DIA"], "DIA")
    
    # Summary
    print("\n" + "="*70)
    print("Validation Summary")
    print("="*70)
    print(f"  DCC (Mines Act Permit): {'✓ PASS' if dcc_valid else '✗ FAIL'}")
    print(f"  DIA (BC Registration): {'✓ PASS' if dia_valid else '✗ FAIL'}")
    # print(f"  DPP (Product Passport): {'✓ PASS' if dpp_valid else '✗ FAIL'}")
    print("="*70 + "\n")
    
    all_valid = dcc_valid and dia_valid
    
    if all_valid:
        print("✓ All credentials are valid!")
    else:
        print("✗ Some credentials failed validation")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

