import pytest


def test_profile_redirects_when_no_session(client):
    """GET /profile with no session should redirect to /login."""
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_returns_200_when_logged_in(client, seeded_user):
    """GET /profile with a valid session should return 200."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get("/profile")
    assert response.status_code == 200


def test_profile_shows_user_name_and_email(client, seeded_user):
    """Profile page should display the logged-in user's name and email."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get("/profile")
    html = response.data.decode()
    assert seeded_user["name"] in html
    assert seeded_user["email"] in html


def test_profile_shows_expense_count_and_total(client, seeded_user):
    """Profile page should show 2 expenses totalling 30.00 for seeded_user."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get("/profile")
    html = response.data.decode()
    assert "2" in html
    assert "30.00" in html


def test_profile_zero_expenses(client, seeded_user_no_expenses):
    """Profile page should show 0 expenses for a user with no expenses."""
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_no_expenses["id"]
    response = client.get("/profile")
    html = response.data.decode()
    assert "0" in html


def test_profile_nonexistent_user_returns_404(client):
    """GET /profile with a non-existent user_id in session should return 404."""
    with client.session_transaction() as sess:
        sess["user_id"] = 99999
    response = client.get("/profile")
    assert response.status_code == 404
