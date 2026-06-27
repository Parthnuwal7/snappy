from app.services import document_storage as ds


def test_build_storage_path_namespaced():
    path = ds.build_storage_path(7, 42, 'pdf')
    assert path.startswith('7/42/')
    assert path.endswith('.pdf')
    assert ds.build_storage_path(7, 42, 'pdf') != path


def test_bucket_name():
    assert ds.BUCKET == 'case-documents'
