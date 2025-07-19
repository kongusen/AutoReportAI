from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """
    Test that the root endpoint returns a 200 OK response.
    """
    response = client.get("/")
    assert response.status_code == 200
    # You can also add more assertions, for example, to check the response content:
    # assert response.json() == {"message": "Hello, World!"}
