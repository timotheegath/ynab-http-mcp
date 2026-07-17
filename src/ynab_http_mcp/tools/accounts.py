from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.accounts import AccountsResponse, CleanAccount
from ynab_http_mcp.utils.schema_utils import clean_ynab_data
from ynab_http_mcp.utils.simple_validation import simple_validate

import json


def register(mcp, ynab_service: YnabService):
    @mcp.resource(uri="data://accounts", mime_type="application/json")
    async def get_accounts() -> str:
        """Get a list of all YNAB accounts."""
        # Get raw YNAB response
        raw_response = ynab_service.get_accounts()

        # Convert to dict
        raw_data = raw_response.to_dict()

        # Clean and validate accounts using simplified approach
        cleaned_accounts = []

        for account_data in raw_data.get("data", {}).get("accounts", []):
            try:
                # Clean data using unified function
                cleaned_data = clean_ynab_data(account_data)

                # Validate using simplified approach
                validated_account = simple_validate(cleaned_data, CleanAccount)
                cleaned_accounts.append(validated_account.model_dump())
            except Exception:
                from ynab_http_mcp.debug import debug_exception

                debug_exception(
                    f"Failed to validate account {account_data.get('id', 'unknown')}"
                )
                continue

        # Create final response
        final_response = {"accounts": cleaned_accounts}

        # Validate complete response structure using simplified approach
        try:
            validated_response = simple_validate(final_response, AccountsResponse)
            # Return as JSON string for MCP resource compatibility
            return json.dumps(validated_response.model_dump())
        except Exception:
            from ynab_http_mcp.debug import debug_exception

            debug_exception("Failed to validate final accounts response")
            # Return a fallback response if validation fails
            # Convert dicts back to CleanAccount objects for type safety
            fallback_accounts = []
            for account_dict in cleaned_accounts:
                try:
                    fallback_accounts.append(CleanAccount(**account_dict))
                except Exception:
                    # If conversion fails, skip this account
                    continue

            fallback_response = AccountsResponse(accounts=fallback_accounts)
            return json.dumps(fallback_response.model_dump())
