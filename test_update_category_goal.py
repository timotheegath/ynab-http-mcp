#!/usr/bin/env python3
"""
Test script for the new update_category_goal functionality.
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ynab_http_mcp.ynab_service import YnabService
from ynab_http_mcp.schemas.budget_tools import UpdateCategoryRequest
from ynab_http_mcp.tools.budget_management import BudgetManagementTools


def test_update_category_goal():
    """Test the update_category_goal functionality."""

    print("🧪 Testing update_category_goal functionality...")

    try:
        # Initialize YNAB service
        print("🔑 Initializing YNAB service...")
        ynab_service = YnabService()
        print("✅ YNAB service initialized successfully")

        # Get a test category (use first category from list)
        print("📋 Getting categories...")
        categories_response = ynab_service.get_categories()

        if not categories_response.data.category_groups:
            print("❌ No categories found in the budget")
            return False

        # Find a category to test with (preferably one without special constraints)
        test_category = None
        for group in categories_response.data.category_groups:
            for category in group.categories:
                # Skip hidden categories and special categories
                if not category.hidden and not category.deleted:
                    # Prefer categories that aren't credit card payments
                    if not category.name.lower().startswith("credit card"):
                        test_category = category
                        break
            if test_category:
                break

        if not test_category:
            print("❌ No suitable test category found")
            return False

        print(f"🎯 Using test category: {test_category.name} (ID: {test_category.id})")

        # Test 1: Update category name
        print("\n📝 Test 1: Updating category name...")
        try:
            result = ynab_service.update_category(
                category_id=str(test_category.id), name=f"Test {test_category.name}"
            )
            print("✅ Category name updated successfully")
            print(f"   Response: {result.data.category.name}")
        except Exception as e:
            print(f"❌ Failed to update category name: {e}")
            return False

        # Test 2: Set a goal target
        print("\n🎯 Test 2: Setting goal target...")
        try:
            result = ynab_service.update_category(
                category_id=str(test_category.id),
                goal_target=500000,  # $500 in milliunits
                goal_frequency="monthly",
            )
            print("✅ Goal target set successfully")
            print(
                f"   Goal target: {result.data.category.goal_target if hasattr(result.data.category, 'goal_target') else 'N/A'}"
            )
        except Exception as e:
            print(f"❌ Failed to set goal target: {e}")
            return False

        # Test 3: Update category note
        print("\n📝 Test 3: Updating category note...")
        try:
            result = ynab_service.update_category(
                category_id=str(test_category.id),
                note="This is a test category updated via API",
            )
            print("✅ Category note updated successfully")
            print(
                f"   Note: {result.data.category.note if hasattr(result.data.category, 'note') else 'N/A'}"
            )
        except Exception as e:
            print(f"❌ Failed to update category note: {e}")
            return False

        # Test 4: Test the BudgetManagementTools wrapper
        print("\n🔧 Test 4: Testing BudgetManagementTools wrapper...")
        try:
            tools = BudgetManagementTools(ynab_service)

            # Create a request to update the goal
            request = UpdateCategoryRequest(
                category_id=str(test_category.id),
                goal_target=1000000,  # $1000 in milliunits
                goal_target_date="2024-12-31",
                goal_needs_whole_amount=True,
            )

            result = tools.update_category(request)
            print("✅ BudgetManagementTools wrapper works correctly")
            print(f"   Success: {result['success']}")
            print(f"   Category ID: {result['category']['id']}")
        except Exception as e:
            print(f"❌ BudgetManagementTools wrapper failed: {e}")
            return False

        # Test 5: Remove goal by setting target to None
        print("\n🗑️  Test 5: Removing goal...")
        try:
            result = ynab_service.update_category(
                category_id=str(test_category.id), goal_target=None
            )
            print("✅ Goal removed successfully")
        except Exception as e:
            print(f"❌ Failed to remove goal: {e}")
            return False

        # Restore original category name
        print("\n🔄 Restoring original category name...")
        try:
            result = ynab_service.update_category(
                category_id=str(test_category.id),
                name=test_category.name,
                note="",  # Clear the test note
            )
            print("✅ Category restored to original state")
        except Exception as e:
            print(f"⚠️  Warning: Failed to restore category: {e}")

        print("\n🎉 All tests completed successfully!")
        return True

    except Exception as e:
        print(f"💥 Unexpected error during testing: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check if YNAB_API_KEY is set
    if not os.getenv("YNAB_API_KEY"):
        print("❌ YNAB_API_KEY environment variable not set")
        print("Please set YNAB_API_KEY in your .env file or environment")
        sys.exit(1)

    success = test_update_category_goal()
    sys.exit(0 if success else 1)
