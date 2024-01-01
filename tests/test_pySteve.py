from pathlib import Path 
import shutil
from datetime import datetime
import sys, uuid

path_root = Path(__file__).parents[1] 
sys.path.append(str(Path(path_root/ 'src')))

import pySteve

nowish = datetime.now().strftime('%Y-%m-%d_%H%M%S')
data = {'USER':'Bob', 'UUID':str(uuid.uuid4()), 'AGE':33, 'HIEGHT':5.89, 
        'DATETIME':nowish, 'PETS':['fluffy','spot','stinky'],
        'MULTILINE_STRING':"""
        SELECT *
        FROM SCHEMA.TABLE
        WHERE colA = '1'
        LIMIT 10
        """}
data2 = data.copy()
data2['USER'] = 'Steve'
data2['UUID'] = str(uuid.uuid4())
data3 = data.copy()
data3['USER'] = 'Zelda'
data3['UUID'] = str(uuid.uuid4())

folder = Path( path_root / 'tests/testfiles' )


def test_infer_datatype():
    assert pySteve.infer_datatype(123) == (int, 123)
    assert pySteve.infer_datatype('123') == (int, 123)
    assert pySteve.infer_datatype(123.456) == (float, 123.456)
    assert pySteve.infer_datatype('123.456') == (float, 123.456)
    assert pySteve.infer_datatype('toy boat') == (str, 'toy boat')
    assert pySteve.infer_datatype('"toy boat"') == (str, 'toy boat')
    assert pySteve.infer_datatype('[1, 3, 5, "seven"]') == (list, [1,3,5,'seven'] )


def test_parse_placeholders():
    assert pySteve.parse_placeholders('some_{test1}_string')['original'] == 'some_{test1}_string'
    assert len(pySteve.parse_placeholders('some_{test1}_string')['placeholders']) == 1
    assert len(pySteve.parse_placeholders('some_{test1}{_string}')['placeholders']) == 2

    teststr = 'some_{test1}_{test2}'
    testresults = pySteve.parse_placeholders(teststr)
    placeholders = testresults['placeholders']
    static_segments = testresults['static_segments']
    all_segments = testresults['segments']

    assert placeholders[0]['name'] == 'test1'
    assert placeholders[0]['segment'] == '{test1}'
    assert placeholders[0]['start'] == 5
    assert placeholders[0]['end'] == 12
    assert placeholders[0]['order'] == 1
    assert teststr[placeholders[0]['start']:placeholders[0]['end']] == '{test1}'

    assert placeholders[1]['name'] == 'test2'
    assert placeholders[1]['segment'] == '{test2}'
    assert placeholders[1]['start'] == 13
    assert placeholders[1]['end'] == 20
    assert placeholders[1]['order'] == 3
    assert teststr[placeholders[1]['start']:placeholders[1]['end']] == '{test2}'

    assert len(all_segments) == 4
    assert all_segments[0]['segment'] == 'some_'
    assert all_segments[1]['segment'] == '{test1}'
    assert all_segments[2]['segment'] == '_'
    assert all_segments[3]['segment'] == '{test2}'

    teststr = '{test0}_{test1}_{test2}'
    testresults = pySteve.parse_placeholders(teststr)
    placeholders = testresults['placeholders']
    static_segments = testresults['static_segments']
    all_segments = testresults['segments']

    assert len(all_segments) == 5
    assert all_segments[0]['segment'] == '{test0}'
    assert all_segments[1]['segment'] == '_'
    assert all_segments[2]['segment'] == '{test1}'
    assert all_segments[3]['segment'] == '_'
    assert all_segments[4]['segment'] == '{test2}'

    assert placeholders[0]['name'] == 'test0'
    assert placeholders[0]['segment'] == '{test0}'
    assert placeholders[0]['start'] == 0
    assert placeholders[0]['end'] == 7
    assert teststr[placeholders[0]['start']:placeholders[0]['end']] == '{test0}'

    teststr = 'this is a fully static string'
    testresults = pySteve.parse_placeholders(teststr)
    placeholders = testresults['placeholders']
    static_segments = testresults['static_segments']
    all_segments = testresults['segments']
    
    assert len(all_segments) == 1
    assert len(static_segments) == 1
    assert len(placeholders) == 0
    assert static_segments[0]['segment'] == teststr
    assert all_segments[0]['segment'] == teststr

    teststr = '{fully_placeholder_string}'
    testresults = pySteve.parse_placeholders(teststr)
    placeholders = testresults['placeholders']
    static_segments = testresults['static_segments']
    all_segments = testresults['segments']
    
    assert len(all_segments) == 1
    assert len(static_segments) == 0
    assert len(placeholders) == 1
    assert placeholders[0]['segment'] == teststr
    assert placeholders[0]['name'] == teststr[1:-1]
    assert all_segments[0]['segment'] == teststr
    
    teststr = '-{1}{2}{3}{4}{5}--{6}{7}{8}{9}{10}'
    testresults = pySteve.parse_placeholders(teststr)
    placeholders = testresults['placeholders']
    static_segments = testresults['static_segments']
    all_segments = testresults['segments']
    
    assert len(all_segments) == 12
    assert len(static_segments) == 2
    assert len(placeholders) == 10

    for i in range(1,6):
        assert all_segments[i]['segment'] == '{' + str(i) + '}'
    for i in range(6,11):
        assert all_segments[i+1]['segment'] == '{' + str(i) + '}'
    assert static_segments[0]['segment'] == '-'
    assert static_segments[1]['segment'] == '--'

    assert [s for s in all_segments if s['type']=='static'] == static_segments
    assert [s for s in all_segments if s['type']=='placeholder'] == placeholders
    

def test_save_dict_as_envfile():
    shutil.rmtree('./tests/testfiles', True)

    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data, 3) == Path('./tests/testfiles/my_envfile_Bob.sh').resolve()
    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data, 3) == Path('./tests/testfiles/my_envfile_Bob.001.sh').resolve()
    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data, 3) == Path('./tests/testfiles/my_envfile_Bob.002.sh').resolve()

    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{DATETIME}.sh', data, 3) == Path(f'./tests/testfiles/my_envfile_{nowish}.sh').resolve()
    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{DATETIME}.sh', data, 3) == Path(f'./tests/testfiles/my_envfile_{nowish}.001.sh').resolve()
    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{DATETIME}.sh', data, 3) == Path(f'./tests/testfiles/my_envfile_{nowish}.002.sh').resolve()

    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data2, 3) == Path('./tests/testfiles/my_envfile_Steve.sh').resolve()
    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data2, 3) == Path('./tests/testfiles/my_envfile_Steve.001.sh').resolve()
    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data2, 3) == Path('./tests/testfiles/my_envfile_Steve.002.sh').resolve()

    # generate many files using the iteration feature, to test picking out the first and last
    for i in range(0,10):
        data2['ID'] = i
        pySteve.save_dict_as_envfile(Path(folder / 'my_envfile_{USER}.sh'), data2, 6)

    assert pySteve.save_dict_as_envfile('./tests/testfiles/my_envfile_{USER}.sh', data3, 3) == Path('./tests/testfiles/my_envfile_Zelda.sh').resolve()


def test_parse_filename_iterators():
    files = pySteve.parse_filename_iterators(folder)
    
    assert len(files['base_files']) == 4
    assert len(files['iter_files']) == 16
    assert len(files['base_files']) + len(files['iter_files']) == len(files['all_files'])

    just_bobs =  [f for f in files['all_files'] if 'Bob' in str(f.stem) ]
    assert just_bobs[0].name == 'my_envfile_Bob.sh'
    assert just_bobs[ len(just_bobs)-1 ].name == 'my_envfile_Bob.002.sh'

    just_steves =  [f for f in files['all_files'] if 'Steve' in str(f.stem) ]
    assert just_steves[0].name == 'my_envfile_Steve.sh'
    assert just_steves[ len(just_steves)-1 ].name == 'my_envfile_Steve.002.sh'
    pass


def test_load_envfile_to_dict():
    assert pySteve.load_envfile_to_dict(Path(folder / 'my_envfile_Bob.sh'))['UUID'] == data['UUID']
    assert pySteve.load_envfile_to_dict(Path(folder / f'my_envfile_{nowish}.sh'))['UUID'] == data['UUID']
    assert pySteve.load_envfile_to_dict(Path(folder / 'my_envfile_Steve.sh'))['UUID'] == data2['UUID']
    assert pySteve.load_envfile_to_dict(Path(folder / 'my_envfile_Steve.{iter}.sh'), 'last')['UUID'] == data2['UUID']
    
    # Zelda will be the last alphabetically, so should be represented below
    assert pySteve.load_envfile_to_dict(Path(folder / 'my_envfile_{USER}.sh'), 'last')['UUID'] == data3['UUID']
    
    
    # assert pySteve.load_envfile_to_dict('./tests/testfiles/my_envfile_{latest}.sh') == data
    


if __name__ == '__main__':
    test_save_dict_as_envfile()
    test_load_envfile_to_dict()