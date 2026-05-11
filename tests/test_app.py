import pytest
from copy import deepcopy
from fastapi.testclient import TestClient
from src.app import app, activities

# Store the original activities for test isolation
ORIGINAL_ACTIVITIES = None

@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to original state before each test"""
    global ORIGINAL_ACTIVITIES
    if ORIGINAL_ACTIVITIES is None:
        ORIGINAL_ACTIVITIES = deepcopy(activities)
    
    # Reset to original state
    activities.clear()
    activities.update(deepcopy(ORIGINAL_ACTIVITIES))
    yield
    # Cleanup after test
    activities.clear()
    activities.update(deepcopy(ORIGINAL_ACTIVITIES))

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

# ============================================================================
# GET /activities Tests
# ============================================================================

def test_get_activities(client):
    """Test retrieving all activities"""
    # Arrange
    expected_activity = "Chess Club"
    expected_description = "Learn strategies and compete in chess tournaments"
    
    # Act
    response = client.get("/activities")
    data = response.json()
    
    # Assert
    assert response.status_code == 200
    assert isinstance(data, dict)
    assert expected_activity in data
    assert data[expected_activity]["description"] == expected_description

def test_get_activities_has_participants(client):
    """Test that activities include participant lists"""
    # Arrange
    activity_name = "Chess Club"
    
    # Act
    response = client.get("/activities")
    data = response.json()
    
    # Assert
    assert response.status_code == 200
    assert "participants" in data[activity_name]
    assert isinstance(data[activity_name]["participants"], list)
    assert len(data[activity_name]["participants"]) > 0

def test_get_activities_has_metadata(client):
    """Test that activities include all required fields"""
    # Arrange
    required_fields = ["description", "schedule", "max_participants", "participants"]
    activity_name = "Chess Club"
    
    # Act
    response = client.get("/activities")
    data = response.json()
    activity = data[activity_name]
    
    # Assert
    assert response.status_code == 200
    for field in required_fields:
        assert field in activity, f"Missing required field: {field}"

# ============================================================================
# POST /activities/{activity_name}/signup Tests
# ============================================================================

def test_signup_success(client):
    """Test successful signup for an activity"""
    # Arrange
    activity_name = "Chess Club"
    new_email = "newstudent@mergington.edu"
    
    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={new_email}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Signed up" in data["message"]
    assert new_email in data["message"]

def test_signup_adds_participant(client):
    """Test that signup actually adds the participant to the list"""
    # Arrange
    activity_name = "Chess Club"
    new_email = "newstudent@mergington.edu"
    
    # Act
    client.post(f"/activities/{activity_name}/signup?email={new_email}")
    response = client.get("/activities")
    data = response.json()
    
    # Assert
    assert new_email in data[activity_name]["participants"]

def test_signup_duplicate_fails(client):
    """Test that signing up twice for the same activity fails"""
    # Arrange
    activity_name = "Chess Club"
    existing_email = "michael@mergington.edu"  # Already signed up
    
    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={existing_email}")
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "already signed up" in data["detail"].lower()

def test_signup_nonexistent_activity_fails(client):
    """Test that signup fails when activity doesn't exist"""
    # Arrange
    nonexistent_activity = "Nonexistent Activity"
    email = "student@mergington.edu"
    
    # Act
    response = client.post(f"/activities/{nonexistent_activity}/signup?email={email}")
    
    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_signup_multiple_activities(client):
    """Test that a student can sign up for multiple activities"""
    # Arrange
    email = "newstudent@mergington.edu"
    activities_to_join = ["Chess Club", "Art Club"]
    
    # Act
    for activity in activities_to_join:
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
    
    activities_data = client.get("/activities").json()
    
    # Assert
    for activity in activities_to_join:
        assert email in activities_data[activity]["participants"]

# ============================================================================
# DELETE /activities/{activity_name}/unregister Tests
# ============================================================================

def test_unregister_success(client):
    """Test successful unregistration from an activity"""
    # Arrange
    activity_name = "Chess Club"
    email_to_remove = "michael@mergington.edu"  # Already signed up
    
    # Act
    response = client.delete(f"/activities/{activity_name}/unregister?email={email_to_remove}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "Unregistered" in data["message"]
    assert email_to_remove in data["message"]

def test_unregister_removes_participant(client):
    """Test that unregister actually removes the participant from the list"""
    # Arrange
    activity_name = "Chess Club"
    email_to_remove = "michael@mergington.edu"
    
    # Act
    client.delete(f"/activities/{activity_name}/unregister?email={email_to_remove}")
    response = client.get("/activities")
    data = response.json()
    
    # Assert
    assert email_to_remove not in data[activity_name]["participants"]

def test_unregister_not_registered_fails(client):
    """Test that unregistering a non-registered user fails"""
    # Arrange
    activity_name = "Chess Club"
    unregistered_email = "notregistered@mergington.edu"
    
    # Act
    response = client.delete(f"/activities/{activity_name}/unregister?email={unregistered_email}")
    
    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not registered" in data["detail"].lower()

def test_unregister_nonexistent_activity_fails(client):
    """Test that unregister fails when activity doesn't exist"""
    # Arrange
    nonexistent_activity = "Nonexistent Activity"
    email = "student@mergington.edu"
    
    # Act
    response = client.delete(f"/activities/{nonexistent_activity}/unregister?email={email}")
    
    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

# ============================================================================
# GET / Tests
# ============================================================================

def test_root_redirect(client):
    """Test root endpoint redirects to static index"""
    # Arrange
    expected_location = "/static/index.html"
    expected_status = 307
    
    # Act
    response = client.get("/", follow_redirects=False)
    
    # Assert
    assert response.status_code == expected_status
    assert response.headers["location"] == expected_location

# ============================================================================
# Integration Tests (Multi-step workflows)
# ============================================================================

def test_signup_then_unregister_flow(client):
    """Test the complete signup and unregister workflow"""
    # Arrange
    activity_name = "Chess Club"
    new_email = "testuser@mergington.edu"
    
    # Act - Sign up
    signup_response = client.post(f"/activities/{activity_name}/signup?email={new_email}")
    assert signup_response.status_code == 200
    
    # Assert - Participant is added
    activities_data = client.get("/activities").json()
    assert new_email in activities_data[activity_name]["participants"]
    
    # Act - Unregister
    unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={new_email}")
    assert unregister_response.status_code == 200
    
    # Assert - Participant is removed
    activities_data = client.get("/activities").json()
    assert new_email not in activities_data[activity_name]["participants"]

def test_signup_multiple_then_unregister_from_one(client):
    """Test signing up for multiple activities and unregistering from one"""
    # Arrange
    email = "multiuser@mergington.edu"
    activities_list = ["Chess Club", "Art Club", "Drama Club"]
    
    # Act - Sign up for multiple activities
    for activity in activities_list:
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
    
    # Assert - Verify in all activities
    activities_data = client.get("/activities").json()
    for activity in activities_list:
        assert email in activities_data[activity]["participants"]
    
    # Act - Unregister from one activity
    activity_to_leave = "Chess Club"
    response = client.delete(f"/activities/{activity_to_leave}/unregister?email={email}")
    assert response.status_code == 200
    
    # Assert - Removed from one, still in others
    activities_data = client.get("/activities").json()
    assert email not in activities_data[activity_to_leave]["participants"]
    
    remaining_activities = [a for a in activities_list if a != activity_to_leave]
    for activity in remaining_activities:
        assert email in activities_data[activity]["participants"]

def test_multiple_users_same_activity(client):
    """Test multiple different users signing up for the same activity"""
    # Arrange
    activity_name = "Chess Club"
    emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
    
    # Act - Each user signs up
    for email in emails:
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
    
    # Assert - All users are now participants
    activities_data = client.get("/activities").json()
    participants = activities_data[activity_name]["participants"]
    for email in emails:
        assert email in participants

def test_user_cannot_signup_twice_after_unregister_and_signup_again(client):
    """Test that a user can unregister and sign up again"""
    # Arrange
    activity_name = "Chess Club"
    email = "cycleuser@mergington.edu"
    
    # Act - First signup
    response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
    assert response1.status_code == 200
    
    # Act - Unregister
    response2 = client.delete(f"/activities/{activity_name}/unregister?email={email}")
    assert response2.status_code == 200
    
    # Act - Sign up again
    response3 = client.post(f"/activities/{activity_name}/signup?email={email}")
    
    # Assert - Should be able to sign up again
    assert response3.status_code == 200
    activities_data = client.get("/activities").json()
    assert email in activities_data[activity_name]["participants"]
