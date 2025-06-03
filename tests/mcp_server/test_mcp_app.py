import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

# Import the Flask app instance
from mcp_server.app import app

# Import Pydantic models
from mcp_server.data_models import (
    LeadProcessingStateCreate,
    AgentEventPayload,
    LeadProcessingStatusEnum,
    AgentExecutionStatusEnum,
    LeadProcessingState as LeadProcessingStatePydantic,
    AgentExecutionRecord as AgentExecutionRecordPydantic
)
# Import ORM models
from mcp_server import models as OrmModels


class TestMCPServerApp(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Mock database session
        self.mock_db_session = MagicMock(spec=Session)

        # It's common for get_db to be a context manager or a generator.
        # If it's `yield session` then `iter([self.mock_db_session])` is correct.
        # If it's `return session` then `self.mock_db_session` directly is fine.
        # Based on typical Flask SQLAlchemy patterns, get_db often yields.
        self.get_db_patcher = patch('mcp_server.database.get_db')
        self.mock_get_db = self.get_db_patcher.start()
        self.mock_get_db.return_value = iter([self.mock_db_session])

    def tearDown(self):
        self.get_db_patcher.stop()

    def test_start_lead_processing_success(self):
        # Mock DB query to indicate lead does not exist
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by().first.return_value = None

        payload_dict = {
            "lead_id": "test_lead_001",
            "run_id": "test_run_001",
            "url": "http://example.com/lead001",
            "current_agent": "InitialAgent",
            "start_time": datetime.utcnow().isoformat()
        }

        response = self.client.post('/api/lead/start', json=payload_dict)

        self.assertEqual(response.status_code, 201)
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once()

        response_data = response.get_json()
        self.assertEqual(response_data['lead_id'], payload_dict['lead_id'])
        self.assertEqual(response_data['status'], LeadProcessingStatusEnum.ACTIVE.value)

    def test_start_lead_processing_already_exists_different_run(self):
        mock_existing_lead = OrmModels.LeadProcessingStateOrm(
            lead_id="test_lead_002", run_id="old_run_id", url="http://example.com/lead002",
            status=LeadProcessingStatusEnum.COMPLETED, start_time=datetime.utcnow() - timedelta(days=1)
        )
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="test_lead_002").first.return_value = mock_existing_lead

        payload_dict = {
            "lead_id": "test_lead_002", # Same lead_id
            "run_id": "new_run_id",    # Different run_id
            "url": "http://example.com/lead002"
        }
        response = self.client.post('/api/lead/start', json=payload_dict)
        self.assertEqual(response.status_code, 409)
        response_data = response.get_json()
        self.assertIn("already being processed or was processed under a different run_id", response_data['message'])

    def test_start_lead_processing_already_exists_same_run(self):
        # Simulate lead already existing with the same run_id (e.g. retry or duplicate call)
        existing_start_time = datetime.utcnow() - timedelta(minutes=5)
        mock_existing_lead = OrmModels.LeadProcessingStateOrm(
            lead_id="test_lead_003", run_id="test_run_003", url="http://example.com/lead003",
            status=LeadProcessingStatusEnum.ACTIVE, start_time=existing_start_time,
            last_update_time=existing_start_time, current_agent="SomeAgent"
        )
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="test_lead_003").first.return_value = mock_existing_lead

        payload_dict = {
            "lead_id": "test_lead_003",
            "run_id": "test_run_003", # Same run_id
            "url": "http://example.com/lead003",
            "current_agent": "InitialAgent", # Could be different if retrying
            "start_time": (existing_start_time + timedelta(seconds=1)).isoformat() # Simulating a slightly later call
        }
        response = self.client.post('/api/lead/start', json=payload_dict)
        self.assertEqual(response.status_code, 200) # Should return existing state
        response_data = response.get_json()
        self.assertEqual(response_data['lead_id'], "test_lead_003")
        self.assertEqual(response_data['status'], LeadProcessingStatusEnum.ACTIVE.value) # Original status


    def test_record_agent_event_success(self):
        mock_lead_state = OrmModels.LeadProcessingStateOrm(lead_id="event_lead_001", run_id="run_event_001", status=LeadProcessingStatusEnum.ACTIVE)
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="event_lead_001").first.return_value = mock_lead_state

        event_payload_dict = {
            "agent_name": "TestAgent",
            "status": AgentExecutionStatusEnum.SUCCESS.value,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": (datetime.utcnow() + timedelta(seconds=10)).isoformat(),
            "processing_time_seconds": 10.0,
            "output_json": json.dumps({"detail": "Agent output data"}),
        }
        response = self.client.post('/api/lead/event_lead_001/event', json=event_payload_dict)

        self.assertEqual(response.status_code, 201)
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()

        response_data = response.get_json()
        self.assertEqual(response_data['agent_event_recorded']['agent_name'], "TestAgent")
        self.assertEqual(response_data['current_lead_state']['current_agent'], "Awaiting next agent after: TestAgent")
        self.assertEqual(response_data['current_lead_state']['status'], LeadProcessingStatusEnum.ACTIVE.value)


    def test_record_agent_event_final_agent_success(self):
        mock_lead_state = OrmModels.LeadProcessingStateOrm(lead_id="final_event_lead_001", run_id="run_final_event_001", status=LeadProcessingStatusEnum.ACTIVE)
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="final_event_lead_001").first.return_value = mock_lead_state

        event_payload_dict = {
            "agent_name": "InternalBriefingSummaryAgent", # Final agent
            "status": AgentExecutionStatusEnum.SUCCESS.value,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": (datetime.utcnow() + timedelta(seconds=15)).isoformat(),
            "processing_time_seconds": 15.0,
            "output_json": json.dumps({"executive_summary": "Final summary", "recommended_next_step": "Outreach"}),
        }
        response = self.client.post('/api/lead/final_event_lead_001/event', json=event_payload_dict)

        self.assertEqual(response.status_code, 201)
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()

        response_data = response.get_json()
        self.assertEqual(response_data['agent_event_recorded']['agent_name'], "InternalBriefingSummaryAgent")
        self.assertEqual(response_data['current_lead_state']['status'], LeadProcessingStatusEnum.COMPLETED.value)
        self.assertIsNotNone(response_data['current_lead_state']['end_time'])
        self.assertIn("Final summary", response_data['current_lead_state']['final_package_summary'])


    def test_record_agent_event_agent_failed(self):
        mock_lead_state = OrmModels.LeadProcessingStateOrm(lead_id="fail_event_lead_001", run_id="run_fail_event_001", status=LeadProcessingStatusEnum.ACTIVE)
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="fail_event_lead_001").first.return_value = mock_lead_state

        event_payload_dict = {
            "agent_name": "FailingAgent",
            "status": AgentExecutionStatusEnum.FAILED.value,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": (datetime.utcnow() + timedelta(seconds=5)).isoformat(),
            "processing_time_seconds": 5.0,
            "error_message": "Something went wrong"
        }
        response = self.client.post('/api/lead/fail_event_lead_001/event', json=event_payload_dict)

        self.assertEqual(response.status_code, 201) # Event is still recorded
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()

        response_data = response.get_json()
        self.assertEqual(response_data['current_lead_state']['status'], LeadProcessingStatusEnum.FAILED.value)
        self.assertEqual(response_data['current_lead_state']['error_message'], "Something went wrong")
        self.assertEqual(response_data['current_lead_state']['current_agent'], "Failed: FailingAgent")


    def test_record_agent_event_lead_not_found(self):
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="non_existent_lead").first.return_value = None
        event_payload_dict = {"agent_name": "TestAgent", "status": "SUCCESS", "start_time": datetime.utcnow().isoformat(), "end_time": datetime.utcnow().isoformat()}
        response = self.client.post('/api/lead/non_existent_lead/event', json=event_payload_dict)
        self.assertEqual(response.status_code, 404)

    def test_get_lead_status_success(self):
        start_time = datetime.utcnow() - timedelta(minutes=10)
        mock_lead_orm = OrmModels.LeadProcessingStateOrm(
            lead_id="status_lead_001", run_id="status_run_001", url="http://example.com/status001",
            status=LeadProcessingStatusEnum.ACTIVE, current_agent="AgentX", start_time=start_time, last_update_time=start_time + timedelta(minutes=1)
        )
        mock_agent_record_orm = OrmModels.AgentExecutionRecordOrm(
            lead_id="status_lead_001", agent_name="AgentX", status=AgentExecutionStatusEnum.SUCCESS,
            start_time=start_time, end_time=start_time + timedelta(minutes=1), processing_time_seconds=60
        )
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="status_lead_001").first.return_value = mock_lead_orm
        self.mock_db_session.query(OrmModels.AgentExecutionRecordOrm).filter_by(lead_id="status_lead_001").order_by().all.return_value = [mock_agent_record_orm]

        response = self.client.get('/api/lead/status_lead_001/status')
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()

        self.assertEqual(response_data['lead_status']['lead_id'], "status_lead_001")
        self.assertEqual(response_data['lead_status']['status'], LeadProcessingStatusEnum.ACTIVE.value)
        self.assertEqual(len(response_data['agent_executions']), 1)
        self.assertEqual(response_data['agent_executions'][0]['agent_name'], "AgentX")

    def test_get_lead_status_not_found(self):
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(lead_id="non_existent_status_lead").first.return_value = None
        response = self.client.get('/api/lead/non_existent_status_lead/status')
        self.assertEqual(response.status_code, 404)

    def test_get_run_status_success(self):
        start_time = datetime.utcnow() - timedelta(hours=1)
        mock_lead1 = OrmModels.LeadProcessingStateOrm(
            lead_id="run_lead_001", run_id="target_run_id", url="http://example.com/run_lead1",
            status=LeadProcessingStatusEnum.COMPLETED, start_time=start_time, end_time=start_time + timedelta(minutes=10)
        )
        mock_lead2 = OrmModels.LeadProcessingStateOrm(
            lead_id="run_lead_002", run_id="target_run_id", url="http://example.com/run_lead2",
            status=LeadProcessingStatusEnum.FAILED, start_time=start_time + timedelta(minutes=5), end_time=start_time + timedelta(minutes=15)
        )
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(run_id="target_run_id").order_by().all.return_value = [mock_lead1, mock_lead2]

        response = self.client.get('/api/run/target_run_id/status')
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()

        self.assertEqual(response_data['run_id'], "target_run_id")
        self.assertEqual(len(response_data['leads']), 2)
        self.assertEqual(response_data['leads'][0]['lead_id'], "run_lead_001")
        self.assertEqual(response_data['leads'][1]['lead_id'], "run_lead_002")
        self.assertEqual(response_data['leads'][0]['status'], LeadProcessingStatusEnum.COMPLETED.value)
        self.assertEqual(response_data['leads'][1]['status'], LeadProcessingStatusEnum.FAILED.value)

    def test_get_run_status_no_leads_found(self):
        self.mock_db_session.query(OrmModels.LeadProcessingStateOrm).filter_by(run_id="empty_run_id").order_by().all.return_value = []
        response = self.client.get('/api/run/empty_run_id/status')
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data['run_id'], "empty_run_id")
        self.assertEqual(len(response_data['leads']), 0)
        self.assertIn("No leads found for this run_id", response_data['message'])


if __name__ == '__main__':
    unittest.main()
