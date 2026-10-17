"""Integração real em schema isolado: não altera a coleção do usuário."""
import os
import uuid
from contextlib import contextmanager
import numpy as np
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
import pytest
from escuta.repository import Repository
from escuta.schemas import Filters


@pytest.fixture
def repo():
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL não definida; integração PostgreSQL não executada')
    schema = 'test_' + uuid.uuid4().hex
    with psycopg.connect(url) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    class IsolatedRepository(Repository):
        @contextmanager
        def connection(self):
            with psycopg.connect(self.url, row_factory=dict_row) as conn:
                conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
                yield conn
    instance = IsolatedRepository(url, 3)
    try:
        instance.migrate()
        yield instance
    finally:
        with psycopg.connect(url) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_transaction_activation_hybrid_filters_and_audit(repo):
    docs = [dict(id='a',text='Produto quebrado entrega atrasada',score=1,date='2018-02-01',purchase_date='2018-01-01',categories=['moveis'],delivery_late=True,order_status='delivered'),
            dict(id='b',text='Produto excelente entrega rápida',score=5,date='2018-02-02',purchase_date='2018-01-02',categories=['livros'],delivery_late=False,order_status='delivered'),
            dict(id='c',text='Entrega não recebida',score=2,date='',purchase_date=None,categories=[],delivery_late=None,order_status='shipped')]
    repo.begin_collection('first',{'indexed':3})
    repo.insert_documents('first', docs, np.eye(3))
    with pytest.raises(ValueError): repo.activate('first',4)
    assert repo.active() is None
    repo.activate('first',3)
    hits = repo.retrieve('first',[1,0,0],'produto',Filters(category='moveis',delivery='late',purchase_start='2018-01-01',purchase_end='2018-01-01'))
    assert [d['id'] for d in hits] == ['a']
    assert hits[0]['similarity'] == pytest.approx(1)
    assert len(repo.retrieve('first',[0,0,1],'entrega',Filters(delivery='unknown'))) == 1
    assert not repo.retrieve('first',[0,0,1],'entrega',Filters(delivery='unknown',purchase_end='2030-01-01'))
    assert not repo.retrieve('first',[1,0,0],'produto',Filters(category="x' OR true --"))
    repo.begin_collection('second',{'indexed':1})
    with pytest.raises(ValueError): repo.activate('second',1)
    assert repo.active()['id'] == 'first'
    repo.insert_documents('second', docs[:1], [[1,0,0]])
    repo.activate('second',1)
    assert repo.active()['id'] == 'second'
    request_id = str(uuid.uuid4())
    repo.audit(request_id,'second','hash','answered',10,['a'],{})
    assert repo.prune_audit(30) == 0
    repo.migrate()  # idempotência e dimensão persistida
    repo.dimensions = 4
    with pytest.raises(ValueError): repo.migrate()
