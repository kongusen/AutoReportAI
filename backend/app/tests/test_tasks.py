import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, schemas
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate


def create_random_user(db_session: Session, is_superuser: bool = False) -> User:
    """Create a random user for testing"""
    import random
    import string
    
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    user_data = schemas.UserCreate(
        username=username,
        password="testpassword123",
        is_superuser=is_superuser
    )
    return crud.user.create(db=db_session, obj_in=user_data)


def create_superuser_token(client: TestClient, db_session: Session) -> str:
    """Create a superuser and return authentication token"""
    superuser = create_random_user(db_session, is_superuser=True)
    login_data = {
        "username": superuser.username,
        "password": "testpassword123",
    }
    response = client.post("/api/v1/auth/access-token", data=login_data)
    return response.json()["access_token"]


def create_regular_user_token(client: TestClient, db_session: Session) -> tuple[str, User]:
    """Create a regular user and return authentication token and user object"""
    user = create_random_user(db_session, is_superuser=False)
    login_data = {
        "username": user.username,
        "password": "testpassword123",
    }
    response = client.post("/api/v1/auth/access-token", data=login_data)
    return response.json()["access_token"], user


def create_test_data_source(db_session: Session, name_suffix: str = "") -> int:
    """Create a test data source and return its ID"""
    from app.schemas.data_source import DataSourceCreate
    
    data_source_data = DataSourceCreate(
        name=f"Test Data Source {name_suffix}",
        source_type="sql",
        db_query="SELECT * FROM test_table",
    )
    data_source = crud.data_source.create(db=db_session, obj_in=data_source_data)
    return data_source.id


def create_test_template(db_session: Session, name_suffix: str = "") -> int:
    """Create a test template and return its ID"""
    from app.schemas.template import TemplateCreate
    
    template_data = TemplateCreate(
        name=f"Test Template {name_suffix}",
        description="Test template for task testing",
    )
    template = crud.template.create(
        db=db_session, 
        obj_in=template_data,
        file_path=f"/tmp/test_template_{name_suffix}.docx",
        parsed_structure={"placeholders": []}
    )
    return template.id


def test_create_task_success(client: TestClient, db_session: Session):
    """Test successful task creation"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "create_task")
    template_id = create_test_template(db_session, "create_task")
    
    task_data = {
        "name": "Test Task",
        "description": "Test task description",
        "data_source_id": data_source_id,
        "template_id": template_id,
        "schedule": "0 9 * * 1",  # Every Monday at 9 AM
        "recipients": ["test@example.com", "user@example.com"],
    }
    
    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == task_data["name"]
    assert data["description"] == task_data["description"]
    assert data["data_source_id"] == data_source_id
    assert data["template_id"] == template_id
    assert data["schedule"] == task_data["schedule"]
    assert data["recipients"] == task_data["recipients"]
    assert data["owner_id"] == user.id
    assert "id" in data


def test_create_task_with_invalid_data_source(client: TestClient, db_session: Session):
    """Test task creation with non-existent data source"""
    token, _ = create_regular_user_token(client, db_session)
    template_id = create_test_template(db_session, "invalid_ds")
    
    task_data = {
        "name": "Test Task",
        "data_source_id": 99999,  # Non-existent ID
        "template_id": template_id,
    }
    
    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 404
    assert "Data source not found" in response.json()["detail"]


def test_create_task_with_invalid_template(client: TestClient, db_session: Session):
    """Test task creation with non-existent template"""
    token, _ = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "invalid_template")
    
    task_data = {
        "name": "Test Task",
        "data_source_id": data_source_id,
        "template_id": 99999,  # Non-existent ID
    }
    
    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 404
    assert "Template not found" in response.json()["detail"]


def test_create_task_with_invalid_schedule(client: TestClient, db_session: Session):
    """Test task creation with invalid cron schedule"""
    token, _ = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "invalid_schedule")
    template_id = create_test_template(db_session, "invalid_schedule")
    
    task_data = {
        "name": "Test Task",
        "data_source_id": data_source_id,
        "template_id": template_id,
        "schedule": "invalid cron",
    }
    
    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 422
    assert "Invalid expression" in str(response.json())


def test_create_task_with_invalid_recipients(client: TestClient, db_session: Session):
    """Test task creation with invalid email recipients"""
    token, _ = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "invalid_recipients")
    template_id = create_test_template(db_session, "invalid_recipients")
    
    task_data = {
        "name": "Test Task",
        "data_source_id": data_source_id,
        "template_id": template_id,
        "recipients": ["invalid-email", "test@example.com"],
    }
    
    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 422
    assert "Invalid email format" in str(response.json())


def test_get_tasks_as_regular_user(client: TestClient, db_session: Session):
    """Test getting tasks as a regular user (only own tasks)"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "get_tasks_regular")
    template_id = create_test_template(db_session, "get_tasks_regular")
    
    # Create a task for this user
    task_data = TaskCreate(
        name="User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    crud.task.create(db=db_session, obj_in=task_data, owner_id=user.id)
    
    # Create a task for another user
    other_user = create_random_user(db_session)
    other_task_data = TaskCreate(
        name="Other User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    crud.task.create(db=db_session, obj_in=other_task_data, owner_id=other_user.id)
    
    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "User Task"
    assert data[0]["owner_id"] == user.id


def test_get_tasks_as_superuser(client: TestClient, db_session: Session):
    """Test getting tasks as a superuser (all tasks)"""
    superuser_token = create_superuser_token(client, db_session)
    regular_token, regular_user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "get_tasks_super")
    template_id = create_test_template(db_session, "get_tasks_super")
    
    # Create tasks for different users
    task_data = TaskCreate(
        name="Regular User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    crud.task.create(db=db_session, obj_in=task_data, owner_id=regular_user.id)
    
    other_user = create_random_user(db_session)
    other_task_data = TaskCreate(
        name="Other User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    crud.task.create(db=db_session, obj_in=other_task_data, owner_id=other_user.id)
    
    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # Should see all tasks


def test_get_single_task_success(client: TestClient, db_session: Session):
    """Test getting a single task by ID"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "get_single_task")
    template_id = create_test_template(db_session, "get_single_task")
    
    task_data = TaskCreate(
        name="Single Task Test",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=user.id)
    
    response = client.get(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["name"] == task_data.name


def test_get_single_task_not_found(client: TestClient, db_session: Session):
    """Test getting a non-existent task"""
    token, _ = create_regular_user_token(client, db_session)
    
    response = client.get(
        "/api/v1/tasks/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_get_single_task_permission_denied(client: TestClient, db_session: Session):
    """Test getting another user's task (permission denied)"""
    token, _ = create_regular_user_token(client, db_session)
    other_user = create_random_user(db_session)
    data_source_id = create_test_data_source(db_session, "permission_denied")
    template_id = create_test_template(db_session, "permission_denied")
    
    task_data = TaskCreate(
        name="Other User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=other_user.id)
    
    response = client.get(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_task_success(client: TestClient, db_session: Session):
    """Test successful task update"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "update_task")
    template_id = create_test_template(db_session, "update_task")
    
    task_data = TaskCreate(
        name="Original Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=user.id)
    
    update_data = {
        "name": "Updated Task Name",
        "description": "Updated description",
        "schedule": "0 10 * * 2",  # Every Tuesday at 10 AM
    }
    
    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["schedule"] == update_data["schedule"]


def test_update_task_with_new_data_source(client: TestClient, db_session: Session):
    """Test updating task with new data source"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "update_task_ds1")
    new_data_source_id = create_test_data_source(db_session, "update_task_ds2")
    template_id = create_test_template(db_session, "update_task_ds")
    
    task_data = TaskCreate(
        name="Task to Update",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=user.id)
    
    update_data = {"data_source_id": new_data_source_id}
    
    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data_source_id"] == new_data_source_id


def test_update_task_with_invalid_data_source(client: TestClient, db_session: Session):
    """Test updating task with non-existent data source"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "update_invalid_ds")
    template_id = create_test_template(db_session, "update_invalid_ds")
    
    task_data = TaskCreate(
        name="Task to Update",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=user.id)
    
    update_data = {"data_source_id": 99999}
    
    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 404
    assert "Data source not found" in response.json()["detail"]


def test_update_task_permission_denied(client: TestClient, db_session: Session):
    """Test updating another user's task (permission denied)"""
    token, _ = create_regular_user_token(client, db_session)
    other_user = create_random_user(db_session)
    data_source_id = create_test_data_source(db_session, "update_permission")
    template_id = create_test_template(db_session, "update_permission")
    
    task_data = TaskCreate(
        name="Other User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=other_user.id)
    
    update_data = {"name": "Attempted Update"}
    
    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_delete_task_success(client: TestClient, db_session: Session):
    """Test successful task deletion"""
    token, user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "delete_task")
    template_id = create_test_template(db_session, "delete_task")
    
    task_data = TaskCreate(
        name="Task to Delete",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=user.id)
    
    response = client.delete(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    assert "Task deleted successfully" in response.json()["msg"]
    
    # Verify task is deleted
    deleted_task = crud.task.get(db=db_session, id=task.id)
    assert deleted_task is None


def test_delete_task_not_found(client: TestClient, db_session: Session):
    """Test deleting a non-existent task"""
    token, _ = create_regular_user_token(client, db_session)
    
    response = client.delete(
        "/api/v1/tasks/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_delete_task_permission_denied(client: TestClient, db_session: Session):
    """Test deleting another user's task (permission denied)"""
    token, _ = create_regular_user_token(client, db_session)
    other_user = create_random_user(db_session)
    data_source_id = create_test_data_source(db_session, "delete_permission")
    template_id = create_test_template(db_session, "delete_permission")
    
    task_data = TaskCreate(
        name="Other User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=other_user.id)
    
    response = client.delete(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_superuser_can_access_all_tasks(client: TestClient, db_session: Session):
    """Test that superuser can access and modify any task"""
    superuser_token = create_superuser_token(client, db_session)
    _, regular_user = create_regular_user_token(client, db_session)
    data_source_id = create_test_data_source(db_session, "superuser_access")
    template_id = create_test_template(db_session, "superuser_access")
    
    # Create task owned by regular user
    task_data = TaskCreate(
        name="Regular User Task",
        data_source_id=data_source_id,
        template_id=template_id,
    )
    task = crud.task.create(db=db_session, obj_in=task_data, owner_id=regular_user.id)
    
    # Superuser should be able to read the task
    response = client.get(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    
    # Superuser should be able to update the task
    update_data = {"name": "Updated by Superuser"}
    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated by Superuser"
    
    # Superuser should be able to delete the task
    response = client.delete(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200


def test_tasks_require_authentication(client: TestClient, db_session: Session):
    """Test that all task endpoints require authentication"""
    # Test GET /tasks/
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 401
    
    # Test POST /tasks/
    response = client.post("/api/v1/tasks/", json={"name": "Test"})
    assert response.status_code == 401
    
    # Test GET /tasks/{id}
    response = client.get("/api/v1/tasks/1")
    assert response.status_code == 401
    
    # Test PUT /tasks/{id}
    response = client.put("/api/v1/tasks/1", json={"name": "Test"})
    assert response.status_code == 401
    
    # Test DELETE /tasks/{id}
    response = client.delete("/api/v1/tasks/1")
    assert response.status_code == 401 