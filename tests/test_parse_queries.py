from pydap.handlers.sql import parse_queries

def test_multiple_selections_for_one_variable():
    selection = ["station_observations.time>='1970-01-01 00:00:00'", "station_observations.time<='2000-12-31 00:00:00'"]
    out, params = parse_queries(selection, {'time': 'obs_time'})

    assert len(out) == 2
    assert len(params.keys()) == 2

    assert out == ['(obs_time >= :0)', '(obs_time <= :1)']
    assert set(params.values()) == set(['2000-12-31 00:00:00', '1970-01-01 00:00:00'])
