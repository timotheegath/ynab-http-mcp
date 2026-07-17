# YNAB MCP Resources

## Requirements

### Requirement: Resource-Based Data Access
The system SHALL provide MCP resources for read-only data access following FastMCP resource patterns.

#### Scenario: Resources initialization
- **WHEN** the server module is imported and main() is called
- **THEN** all YNAB data resources are registered with the server
- **AND** resources follow FastMCP resource return type requirements

### Requirement: Categories Resource
The system SHALL provide an MCP resource for accessing category data.

#### Scenario: Categories resource available
- **WHEN** the categories resource is registered
- **THEN** a resource with URI `data://categories` is available
- **AND** the resource returns JSON data with MIME type `application/json`
- **AND** the response contains an array of category groups
- **AND** each category group contains its categories

#### Scenario: Categories resource data structure
- **WHEN** the categories resource is accessed
- **THEN** it returns data matching the CategoriesResponse schema:
  ```json
  {
    "category_groups": [
      {
        "id": "string",
        "name": "string",
        "hidden": "boolean",
        "deleted": "boolean",
        "categories": [
          {
            "id": "string",
            "category_group_id": "string",
            "name": "string",
            "hidden": "boolean",
            "deleted": "boolean"
            // ... additional category fields
          }
        ]
      }
    ]
  }
  ```

### Requirement: Resource Error Handling
All MCP resources SHALL handle errors gracefully and return appropriate responses.

#### Scenario: Data validation errors
- **WHEN** a resource encounters data validation issues
- **THEN** it returns a fallback response with available valid data
- **AND** logs validation errors for debugging

#### Scenario: YNAB API errors
- **WHEN** a YNAB API call fails during resource access
- **THEN** the resource returns an appropriate error response
- **AND** logs the error for debugging

### Requirement: Resource Performance
Resources SHALL be optimized for performance and client compatibility.

#### Scenario: JSON serialization
- **WHEN** a resource returns structured data
- **THEN** it uses efficient JSON serialization
- **AND** returns string content for FastMCP compatibility

#### Scenario: MIME type specification
- **WHEN** a resource is registered
- **THEN** it specifies the appropriate MIME type
- **AND** uses `application/json` for JSON data resources