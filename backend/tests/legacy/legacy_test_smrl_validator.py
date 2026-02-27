"""
Test SMRL Schema Validator
===========================
Test the new OpenAPI/JSON Schema validation against DomainModel.json
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web.services.smrl_validator import get_smrl_validator


def test_validator_initialization():
    """Test validator loads schema correctly"""
    print("=" * 80)
    print("TEST 1: Validator Initialization")
    print("=" * 80)

    validator = get_smrl_validator()

    print(f"✓ Schema loaded: {validator.schema_loaded}")
    print(f"✓ Resource types available: {len(validator.list_resource_types())}")
    print(f"✓ Pre-compiled validators: {len(validator.validators)}")

    print("\nAvailable SMRL resource types:")
    for resource_type in sorted(validator.list_resource_types())[:10]:
        print(f"  - {resource_type}")
    print("  ... (and more)")


def test_valid_resource():
    """Test validation of a valid SMRL resource"""
    print("\n" + "=" * 80)
    print("TEST 2: Valid Resource Validation")
    print("=" * 80)

    validator = get_smrl_validator()

    # Create a valid AccessibleModelTypeConstituent resource (strict schema format)
    valid_resource = {
        "$href": "/api/v1/AccessibleModelTypeConstituent/test-uid-12345",
        "Identifiers": [{"String": "test-uid-12345", "Context": "uid"}],
        "Names": [{"String": "Test Class", "Context": "default"}],
        "CreatedOn": "2025-12-13T10:00:00Z",
        "LastModified": "2025-12-13T10:00:00Z",
        "CreatedBy": {"$ref": "/api/v1/Person/test_user"},
        "ModifiedBy": {"$ref": "/api/v1/Person/test_user"},
        "VersionIdentifiers": [{"String": "1.0", "Context": "version"}],
    }

    is_valid, errors = validator.validate_resource(
        valid_resource, "AccessibleModelTypeConstituent"
    )

    name = (
        valid_resource.get("Names", [{}])[0].get("String", "Unnamed")
        if valid_resource.get("Names")
        else "Unnamed"
    )
    print(f"Resource: {name}")
    print(f"✓ Valid: {is_valid}")
    if errors:
        print(f"✗ Errors:")
        for error in errors[:10]:
            print(f"  - {error}")
    else:
        print("✓ No validation errors")


def test_invalid_resource():
    """Test validation of an invalid SMRL resource"""
    print("\n" + "=" * 80)
    print("TEST 3: Invalid Resource Validation")
    print("=" * 80)

    validator = get_smrl_validator()

    # Create an invalid resource (missing required fields)
    invalid_resource = {
        "name": "Test Class",
        # Missing: uid, href, smrl_type, created_on, last_modified, etc.
    }

    is_valid, errors = validator.validate_resource(
        invalid_resource, "AccessibleModelTypeConstituent"
    )

    print(f"Resource: {invalid_resource.get('name', 'Unnamed')}")
    print(f"✓ Valid: {is_valid}")
    print(f"✓ Detected {len(errors)} validation errors:")
    for error in errors[:5]:  # Show first 5 errors
        print(f"  - {error}")
    if len(errors) > 5:
        print(f"  ... and {len(errors) - 5} more errors")


def test_collection_validation():
    """Test validation of a SMRL collection"""
    print("\n" + "=" * 80)
    print("TEST 4: Collection Validation")
    print("=" * 80)

    validator = get_smrl_validator()

    # Create a valid collection (strict schema format)
    # Note: For collection validation, we need smrl_type to identify resource type
    valid_collection = {
        "items": [
            {
                "smrl_type": "AccessibleModelTypeConstituent",  # Add for collection validation
                "$href": "/api/v1/AccessibleModelTypeConstituent/class-001",
                "Identifiers": [{"String": "class-001", "Context": "uid"}],
                "Names": [{"String": "Class 1", "Context": "default"}],
                "CreatedOn": "2025-12-13T10:00:00Z",
                "LastModified": "2025-12-13T10:00:00Z",
                "CreatedBy": {"$ref": "/api/v1/Person/user1"},
                "ModifiedBy": {"$ref": "/api/v1/Person/user1"},
                "VersionIdentifiers": [{"String": "1.0", "Context": "version"}],
            },
            {
                "smrl_type": "AccessibleModelTypeConstituent",  # Add for collection validation
                "$href": "/api/v1/AccessibleModelTypeConstituent/class-002",
                "Identifiers": [{"String": "class-002", "Context": "uid"}],
                "Names": [{"String": "Class 2", "Context": "default"}],
                "CreatedOn": "2025-12-13T10:00:00Z",
                "LastModified": "2025-12-13T10:00:00Z",
                "CreatedBy": {"$ref": "/api/v1/Person/user1"},
                "ModifiedBy": {"$ref": "/api/v1/Person/user1"},
                "VersionIdentifiers": [{"String": "1.0", "Context": "version"}],
            },
        ],
        "total_count": 2,
        "limit": 100,
        "skip": 0,
    }

    is_valid, errors = validator.validate_collection(valid_collection)

    print(f"Collection with {len(valid_collection['items'])} items")
    print(f"✓ Valid: {is_valid}")
    if errors:
        print(f"✗ Errors:")
        for error in errors[:10]:
            print(f"  - {error}")
    else:
        print("✓ No validation errors")


def test_required_fields():
    """Test getting required fields for a resource type"""
    print("\n" + "=" * 80)
    print("TEST 5: Required Fields Query")
    print("=" * 80)

    validator = get_smrl_validator()

    resource_types = [
        "AccessibleModelTypeConstituent",
        "Requirement",
        "Person",
    ]

    for resource_type in resource_types:
        required = validator.get_required_fields(resource_type)
        print(f"\n{resource_type}:")
        print(f"  Required fields: {', '.join(required) if required else 'None found'}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SMRL SCHEMA VALIDATOR TEST SUITE")
    print("=" * 80)

    try:
        test_validator_initialization()
        test_valid_resource()
        test_invalid_resource()
        test_collection_validation()
        test_required_fields()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
