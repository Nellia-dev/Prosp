import json
import unittest
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, HttpUrl

# Assuming event_models is in the prospect directory and prospect directory is in PYTHONPATH
from prospect.event_models import LeadEnrichmentEndEvent

# Pydantic models for testing
class DummyPackageModel(BaseModel):
    name: str
    website_url: HttpUrl
    count: int
    details: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class NestedDummyModel(BaseModel):
    nested_link: HttpUrl
    description: str

class MoreComplexDummyPackageModel(BaseModel):
    company_name: str
    main_site: HttpUrl
    contact_points: List[HttpUrl]
    subsidiary: Optional[NestedDummyModel] = None
    metadata: Dict[str, Any]


class TestEventModels(unittest.TestCase):

    def test_lead_enrichment_end_event_serialization_with_httpurl(self):
        """
        Tests that LeadEnrichmentEndEvent with HttpUrl in final_package
        can be correctly serialized to JSON via its to_dict() method.
        """
        now = datetime.now().isoformat()

        # Prepare a complex final_package with HttpUrl instances
        complex_final_package = {
            "company_name": "Test Inc.",
            "website": HttpUrl("http://example.com"), # Top-level HttpUrl
            "contact_email": "contact@example.com",
            "details": {
                "profile_url": HttpUrl("http://linkedin.com/company/testinc"), # Nested HttpUrl
                "address": {
                    "street": "123 Main St",
                    "city": "Testville",
                    "deep_link": HttpUrl("http://maps.example.com/?id=123") # Deeply nested HttpUrl
                },
                "tags": ["test", "example"]
            },
            "simple_list_with_urls": [
                "text_item",
                HttpUrl("http://example.com/resource1"),
                HttpUrl("http://example.com/resource2")
            ],
            "list_of_dicts_with_urls": [
                {"id": 1, "name": "Item 1", "link": HttpUrl("http://example.com/item/1")},
                {"id": 2, "name": "Item 2", "link": "http://example.com/item/2"}, # String URL for comparison
                {"id": 3, "name": "Item 3", "link": HttpUrl("http://example.com/item/3"), "nested_url_list": [HttpUrl("http://example.com/subitem")]}
            ],
            "none_value": None,
            "bool_value": True
        }

        event = LeadEnrichmentEndEvent(
            event_type="lead_enrichment_end",
            timestamp=now,
            job_id="job123",
            user_id="user456",
            lead_id="lead789",
            success=True,
            final_package=complex_final_package
        )

        try:
            # The to_dict() method should handle the conversion
            event_dict = event.to_dict()

            # Attempt to serialize the dictionary to JSON
            # This step will fail if HttpUrl objects are still present
            json_output = json.dumps(event_dict)

            # Verify the HttpUrl fields were converted to strings in the dictionary
            loaded_dict_from_json = json.loads(json_output) # For good measure, check the final JSON output

            # Assertions for top-level and nested HttpUrls
            self.assertEqual(event_dict["final_package"]["website"], "http://example.com/") # Gets a trailing slash
            self.assertEqual(event_dict["final_package"]["details"]["profile_url"], "http://linkedin.com/company/testinc") # Does not get a trailing slash
            self.assertEqual(event_dict["final_package"]["details"]["address"]["deep_link"], "http://maps.example.com/?id=123") # URLs with query params do not get a trailing slash

            # Assertions for HttpUrls in lists
            self.assertEqual(event_dict["final_package"]["simple_list_with_urls"][1], "http://example.com/resource1") # No trailing slash if path exists
            self.assertEqual(event_dict["final_package"]["simple_list_with_urls"][2], "http://example.com/resource2") # No trailing slash if path exists

            # Assertions for HttpUrls in list of dictionaries
            self.assertEqual(event_dict["final_package"]["list_of_dicts_with_urls"][0]["link"], "http://example.com/item/1") # No trailing slash if path exists
            self.assertEqual(event_dict["final_package"]["list_of_dicts_with_urls"][2]["link"], "http://example.com/item/3") # No trailing slash if path exists
            self.assertEqual(event_dict["final_package"]["list_of_dicts_with_urls"][2]["nested_url_list"][0], "http://example.com/subitem") # No trailing slash if path exists

            # Check against the JSON parsed dictionary too
            self.assertEqual(loaded_dict_from_json["final_package"]["website"], "http://example.com/")
            self.assertEqual(loaded_dict_from_json["final_package"]["details"]["profile_url"], "http://linkedin.com/company/testinc")

        except TypeError as e:
            self.fail(f"Serialization of LeadEnrichmentEndEvent's dict failed: {e}. This means HttpUrl objects were not converted by to_dict().")
        except Exception as e:
            self.fail(f"An unexpected error occurred during test: {e}")

    def test_lead_enrichment_end_event_with_pydantic_model_as_package(self):
        """
        Tests that LeadEnrichmentEndEvent with a Pydantic model as final_package
        can be correctly serialized, with HttpUrls converted to strings.
        """
        now = datetime.now().isoformat()

        # Prepare a Pydantic model instance for final_package
        pydantic_package = MoreComplexDummyPackageModel(
            company_name="Pydantic Corp",
            main_site=HttpUrl("http://pydantic.com"),
            contact_points=[
                HttpUrl("http://pydantic.com/contact"),
                HttpUrl("http://pydantic.com/support")
            ],
            subsidiary=NestedDummyModel(
                nested_link=HttpUrl("http://sub.pydantic.com/home"),
                description="Subsidiary details"
            ),
            metadata={"version": "1.0", "status": "active"}
        )

        event = LeadEnrichmentEndEvent(
            event_type="lead_enrichment_end",
            timestamp=now,
            job_id="job789",
            user_id="user001",
            lead_id="lead007",
            success=True,
            final_package=pydantic_package  # Assigning the Pydantic model instance
        )

        try:
            # The to_dict() method should handle the Pydantic model conversion
            event_dict = event.to_dict()

            # Attempt to serialize the dictionary to JSON
            json_output = json.dumps(event_dict)
            loaded_dict_from_json = json.loads(json_output) # For checking final JSON output

            # Assertions for HttpUrl fields within the Pydantic model
            # Based on Pydantic's model_dump(mode='json') behavior for HttpUrl
            self.assertEqual(event_dict["final_package"]["main_site"], "http://pydantic.com/") # Hostname gets trailing slash
            self.assertEqual(event_dict["final_package"]["contact_points"][0], "http://pydantic.com/contact") # Path, no trailing slash
            self.assertEqual(event_dict["final_package"]["contact_points"][1], "http://pydantic.com/support") # Path, no trailing slash
            self.assertIsNotNone(event_dict["final_package"]["subsidiary"])
            if event_dict["final_package"]["subsidiary"]: # Check for type safety if using mypy/pyright
                 self.assertEqual(event_dict["final_package"]["subsidiary"]["nested_link"], "http://sub.pydantic.com/home") # Path, no trailing slash

            # Verify other fields are present
            self.assertEqual(event_dict["final_package"]["company_name"], "Pydantic Corp")
            self.assertEqual(event_dict["final_package"]["metadata"]["status"], "active")

            # Check against the JSON parsed dictionary too
            self.assertEqual(loaded_dict_from_json["final_package"]["main_site"], "http://pydantic.com/")
            self.assertEqual(loaded_dict_from_json["final_package"]["subsidiary"]["nested_link"], "http://sub.pydantic.com/home")

        except TypeError as e:
            self.fail(f"Serialization of LeadEnrichmentEndEvent's dict with Pydantic model failed: {e}.")
        except Exception as e:
            self.fail(f"An unexpected error occurred during test: {e}")


if __name__ == '__main__':
    unittest.main()
