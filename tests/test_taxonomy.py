from apps.taxonomy.models import Project


def test_legacy_taxonomy_model_still_loads(db):
    project = Project.objects.create(name='Legacy', slug='legacy')
    assert str(project) == 'Legacy'
