def test_ai_summary_is_not_in_v1(client, django_user_model):
    user = django_user_model.objects.create_user(username='u', email='u@example.com', password='pass')
    client.force_login(user)
    assert client.get('/reports/summary/').status_code == 404
