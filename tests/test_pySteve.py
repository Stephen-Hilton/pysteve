from pathlib import Path 
import shutil
from datetime import datetime, timezone, timedelta
import sys, uuid

path_root = Path(__file__).parents[1] 
sys.path.append(str(Path(path_root/ 'src' / 'pySteve')))

import pySteve

nowish = datetime.now().strftime('%Y-%m-%d_%H%M%S')
print(nowish)
data = {'USER':'Bob', 'UUID':'18ac01ba-5d66-40cb-90f9-3b61c87b7c26', 'AGE':33, 'HIEGHT':5.89, 
        'DATETIME':nowish, 'PETS':['fluffy','spot','stinky'],
        'MULTILINE_STRING':"""
        SELECT *
        FROM SCHEMA.TABLE
        WHERE colA = '1'
        LIMIT 10
        """}
data2 = data.copy()
data2['USER'] = 'Steve'
data2['UUID'] = '5d988b17-2536-4c20-90bc-9fcd90ff6f4f'
data3 = data.copy()
data3['USER'] = 'Zelda'
data3['UUID'] = 'db44527e-9df9-4c43-9f5f-c49b52f4d516'

folder = Path( path_root / 'tests/testfiles' )


def test_infer_datatype():
    # python
    assert pySteve.infer_datatype(123)   == (int, 123)
    assert pySteve.infer_datatype('123') == (int, 123)
    assert pySteve.infer_datatype(123.456)   == (float, 123.456)
    assert pySteve.infer_datatype('123.456') == (float, 123.456)
    assert pySteve.infer_datatype(1.8e-5) == (float, 1.8e-05)
    assert pySteve.infer_datatype('1.8e-5') == (float, 1.8e-05)
    assert pySteve.infer_datatype('1.8e-5') == (float, 0.000018)
    assert pySteve.infer_datatype('1.8e+5') == (float, 180000.0)
    assert pySteve.infer_datatype('1.8e05') == (float, 180000.0)
    assert pySteve.infer_datatype('1.8e5') == (float, 180000.0)
    assert pySteve.infer_datatype('toy boat')   == (str, 'toy boat')
    assert pySteve.infer_datatype('"toy boat"') == (str, 'toy boat')
    assert pySteve.infer_datatype('[1, 3, 5, "seven"]') == (list, [1,3,5,'seven'] )
    assert pySteve.infer_datatype('2024-12-31') == (datetime, datetime(2024, 12, 31, 0, 0))
    assert pySteve.infer_datatype('1974-10-15') == (datetime, datetime(1974, 10, 15, 0, 0))
    assert pySteve.infer_datatype('1974-15-10') == (str, '1974-15-10')
    assert pySteve.infer_datatype('2024-09-10 11:12:13') == (datetime, datetime(2024, 9, 10, 11, 12, 13))
    assert pySteve.infer_datatype('2024-08-15 23:59:59.999999') == (datetime, datetime(2024, 8, 15, 23, 59, 59, 999999))
    assert pySteve.infer_datatype('2024-08-15 23:59:59.999999+08:00') == (datetime, datetime(2024, 8, 15, 23, 59, 59, 999999, tzinfo=timezone(timedelta(seconds=28800))))

    # sql
    assert pySteve.infer_datatype(123, True)   == (int, 123, 'TINYINT')
    assert pySteve.infer_datatype('123', True) == (int, 123, 'TINYINT')
    assert pySteve.infer_datatype(12345, True)   == (int, 12345, 'SMALLINT')
    assert pySteve.infer_datatype(123456, True)   == (int, 123456, 'INTEGER')
    assert pySteve.infer_datatype(123456789, True)   == (int, 123456789, 'INTEGER')
    assert pySteve.infer_datatype(12345678901, True)   == (int, 12345678901, 'BIGINT')    
    assert pySteve.infer_datatype(1234567890123456789, True)   == (int, 1234567890123456789, 'BIGINT')    
    assert pySteve.infer_datatype(123.456, True)   == (float, 123.456, 'DECIMAL(6,3)')
    assert pySteve.infer_datatype('123.456', True) == (float, 123.456, 'DECIMAL(6,3)')
    assert pySteve.infer_datatype('123456789.123', True) == (float, 123456789.123, 'DECIMAL(12,3)')
    assert pySteve.infer_datatype(1.8e-5, True) == (float, 1.8e-05, 'DECIMAL(7,6)')
    assert pySteve.infer_datatype('1.8e-5', True) == (float, 1.8e-05, 'DECIMAL(7,6)')
    assert pySteve.infer_datatype('1.8e-5', True) == (float, 0.000018, 'DECIMAL(7,6)')
    assert pySteve.infer_datatype('1.8e+5', True) == (float, 180000.0, 'DECIMAL(7,1)')
    assert pySteve.infer_datatype('1.8e05', True) == (float, 180000.0, 'DECIMAL(7,1)')
    assert pySteve.infer_datatype('1.8e5', True) == (float, 180000.0, 'DECIMAL(7,1)')
    assert pySteve.infer_datatype(355/113*1e50, True) == (float, 3.1415929203539832e+50, 'DECIMAL(52,1)')
    assert pySteve.infer_datatype('toy boat', True)   == (str, 'toy boat', 'VARCHAR(8)')
    assert pySteve.infer_datatype('"toy boat"', True) == (str, 'toy boat', 'VARCHAR(8)')
    assert pySteve.infer_datatype('[1, 3, 5, "seven"]', True) == (list, [1, 3, 5, 'seven'], 'VARCHAR(18)')
    assert pySteve.infer_datatype('2024-12-31', True) == (datetime, datetime(2024, 12, 31, 0, 0), 'DATE')
    assert pySteve.infer_datatype('1974-10-15', True) == (datetime, datetime(1974, 10, 15, 0, 0), 'DATE')
    assert pySteve.infer_datatype('1974-15-10', True) == (str, '1974-15-10', 'VARCHAR(10)')
    assert pySteve.infer_datatype('2024-09-10 11:12:13', True) ==(datetime, datetime(2024, 9, 10, 11, 12, 13), 'TIMESTAMP')
    assert pySteve.infer_datatype('2024-08-15 23:59:59.999999', True) ==(datetime, datetime(2024, 8, 15, 23, 59, 59, 999999), 'TIMESTAMP')
    assert pySteve.infer_datatype('2024-08-15 23:59:59.999999+08:00', True) ==(datetime, datetime(2024, 8, 15, 23, 59, 59, 999999, tzinfo=timezone(timedelta(seconds=28800))), 'TIMESTAMP')
    assert pySteve.infer_datatype('2024-01-15T07:59:40.053+00:00', True) ==(datetime, datetime(2024, 1, 15, 7, 59, 40, 53000, tzinfo=timezone(timedelta(seconds=0))), 'TIMESTAMP')


def test_datatype_py2sql():
    assert pySteve.datatype_py2sql(str, 'sample data') == 'VARCHAR(11)'
    assert pySteve.datatype_py2sql(str, 'sample data'*2) == 'VARCHAR(22)'
    assert pySteve.datatype_py2sql(str, 'sample data'*5) == 'VARCHAR(55)'
    assert pySteve.datatype_py2sql(int, 15) == 'TINYINT'
    assert pySteve.datatype_py2sql(int, 127) == 'TINYINT'
    assert pySteve.datatype_py2sql(int, 128) == 'SMALLINT'
    assert pySteve.datatype_py2sql(int, 12345) == 'SMALLINT'
    assert pySteve.datatype_py2sql(int, 32767) == 'SMALLINT'
    assert pySteve.datatype_py2sql(int, 32768) == 'INTEGER'
    assert pySteve.datatype_py2sql(int, 123456789) == 'INTEGER'
    assert pySteve.datatype_py2sql(int, 2147483647 ) == 'INTEGER'
    assert pySteve.datatype_py2sql(int, 2147483648 ) == 'BIGINT'
    assert pySteve.datatype_py2sql(int, 1234567890987654321 ) == 'BIGINT'


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
    

def test_envfile_save():
    shutil.rmtree('./tests/testfiles', True)

    assert pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data, 3) == Path(folder / 'my_envfile_Bob.sh').resolve()
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data, 3) == Path(folder / 'my_envfile_Bob.001.sh').resolve()
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data, 3) == Path(folder / 'my_envfile_Bob.002.sh').resolve()

    assert pySteve.envfile_save(Path(folder / 'my_envfile_{DATETIME}.sh'), data, 3) == Path(folder / f'my_envfile_{nowish}.sh').resolve()
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{DATETIME}.sh'), data, 3) == Path(folder / f'my_envfile_{nowish}.001.sh').resolve()
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{DATETIME}.sh'), data, 3) == Path(folder / f'my_envfile_{nowish}.002.sh').resolve()
    
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data2, 3) == Path(folder / 'my_envfile_Steve.sh').resolve()
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data2, 3) == Path(folder / 'my_envfile_Steve.001.sh').resolve()
    assert pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data2, 3) == Path(folder / 'my_envfile_Steve.002.sh').resolve()

    # generate many files using the iteration feature, to test picking out the first and last
    for i in range(0,10):
        data2['ID'] = i
        pySteve.envfile_save(Path(folder / 'my_envfile_{USER}.sh'), data2, 6)

    assert pySteve.envfile_save('./tests/testfiles/my_envfile_{USER}.sh', data3, 3) == Path('./tests/testfiles/my_envfile_Zelda.sh').resolve()


def test_envfile_load():
    # error case: didn't pick up EOM docstring correctly -- it did actually, just not aligned with docstring marker, introduced an override
    assert len(pySteve.envfile_load(Path(folder / '..' / 'error_cases' / 'Table--SXTDemo.Stocks--202402020132.sql'))['CREATE_DDL_TEMPLATE']) >=100
    assert len(pySteve.envfile_load(Path(folder / '..' / 'error_cases' / 'Table--SXTDemo.Stocks--original.sql'), docstring_marker_override='EOM')['CREATE_DDL_TEMPLATE']) >=100

    # STANDARD TESTS
    assert pySteve.envfile_load(Path(folder / 'my_envfile_Bob.sh'))['UUID'] == data['UUID']
    assert pySteve.envfile_load(Path(folder / f'my_envfile_{nowish}.sh'))['UUID'] == data['UUID']
    assert pySteve.envfile_load(Path(folder / 'my_envfile_Steve.sh'))['UUID'] == data2['UUID']
    assert pySteve.envfile_load(Path(folder / 'my_envfile_Steve.{iter}.sh'), 'last')['UUID'] == data2['UUID']
    
    # Zelda will be the last alphabetically, so should be represented below
    assert pySteve.envfile_load(Path(folder / 'my_envfile_{USER}.sh'), 'last')['UUID'] == data3['UUID']
    

def test_parse_filename_iterators():
    files = pySteve.parse_filename_iterators(folder)
    
    assert len(files) == 3
    assert len(files['base_files']) == 4
    assert len(files['iter_files']) >= 10
    assert len(files['base_files']) + len(files['iter_files']) == len(files['all_files'])

    just_bobs =  [f for f in files['all_files'] if 'Bob' in str(f.stem) ]
    assert just_bobs[0].name == 'my_envfile_Bob.sh'
    assert just_bobs[ len(just_bobs)-1 ].name == 'my_envfile_Bob.002.sh'

    just_steves =  [f for f in files['all_files'] if 'Steve' in str(f.stem) ]
    assert just_steves[0].name == 'my_envfile_Steve.sh'
    assert just_steves[ len(just_steves)-1 ].name == 'my_envfile_Steve.002.sh'
    pass


def test_datetimePlus():
    dt = pySteve.datetimePlus('2020-12-17')
    assert dt.calendar_date == '2020-12-17'
    assert dt.year_of_calendar == 2020
    assert dt.month_of_year == 12
    assert dt.day_of_month == 17
    assert dt.leap_year == True
    assert dt.day_of_week_name == 'Thursday'
    assert dt.week_of_month_iso == 3
    assert dt.first_of_month_iso.strftime(dt.date_format) == '2020-11-29'
    assert dt.last_of_month_iso.strftime(dt.date_format) == '2021-01-02'
    assert dt.quarter_of_year_name == '2020 Q4'


def test_chunk_lines():
    files = sorted([f for f in Path(folder).iterdir() if f.is_file()]) 
    chunks = pySteve.chunk_lines(files, [ lambda line : str(line).endswith('001.sh')] )
    assert sum([len(l) for l in chunks]) == len(files)

    filepath = Path(__file__)
    with open(filepath,'r') as fh:
        lines = [str(f).rstrip() for f in fh.readlines()]
    chunks = pySteve.chunk_lines(lines, [ lambda line : str(line).startswith('def ')] )
    assert sum([len(l) for l in chunks]) == len(lines)
    assert len(chunks) == len([l for l in lines if str(l).startswith('def ')]) + 1

    lines = ['something zero', 'something else','nada or one', 
             'NEW SECTION: two', 'section two', 'more stuff',
             'NEW SECTION: three', 'junk', 'more junk', 'so much junk', 
             'NEW SECTION: four', 'trash','everywhere trash','last section coming up',
             'NEW SECTION: pony', 'poo', 'ponies have no concern for where they poo',
             'NEW SECTION: the last']
    chunks = pySteve.chunk_lines(lines, [ lambda line : str(line).startswith('NEW SECTION:') ])
    assert sum([len(l) for l in chunks]) == len(lines)
    assert len(chunks) == len([l for l in lines if str(l).startswith('NEW SECTION:')]) + 1
    assert len(chunks) == 6
    assert len(chunks[2]) == 4
    assert len([l for l in chunks[0] if 'NEW SECTION:' in l]) == 0 # section before first split

    func1 = lambda line : len([n for n in ['zero', 'one','two','three','four'] if n in str(line)]) >0
    func2 = lambda line : 'pony' in str(line)
    chunks = pySteve.chunk_lines(lines, [ func1, func2] )
    assert sum([len(l) for l in chunks]) == len(lines)
    assert len(chunks) == 7
    assert chunks[1] == ['nada or one']

    func3 = lambda line : str(line).startswith('NEW SECTION:')
    func4 = lambda line : 'ponies' in str(line)
    chunks = pySteve.chunk_lines(lines, [ func1, func2, func3, func4] )
    assert sum([len(l) for l in chunks]) == len(lines)
    assert len(chunks) == 9


def test_tokenize_quoted_strings():
    teststring = 'def test123(val:str="some:value")'
    text, tokens = pySteve.tokenize_quoted_strings(teststring, return_quote_type = True)
    assert text == 'def test123(val:str={T0})'
    assert tokens == {'T0': {'text': '"some:value"', 'quote_type': '"'}}
    assert tokens['T0']['quote_type'] == '"'
    assert text.format(T0=tokens['T0']['text']) == teststring
    
    # real world use-case: parsing python
    parms = text[text.find('('):][1:-1]
    assert parms == 'val:str={T0}'
    assert parms.split(':')[0] == 'val'
    assert parms.split(':')[1] == 'str={T0}'
    assert parms.split(':')[1].format(T0=tokens['T0']['text']) == 'str="some:value"'

    teststring = """someimtes "aliens" and "gov't agents" appear and 'borrow' people."""
    text, tokens = pySteve.tokenize_quoted_strings(teststring, return_quote_type = True)
    assert text == 'someimtes {T0} and {T1} appear and {T2} people.'
    assert tokens == {'T0':{'text':'"aliens"', 'quote_type':'"'}, 
                      'T1':{'text':'"gov\'t agents"', 'quote_type':'"'},
                      'T2':{'text':"'borrow'", 'quote_type':"'" }}
    assert text.format(T0=tokens['T0']['text'], T1=tokens['T1']['text'], T2=tokens['T2']['text']) == teststring

    # again, same as above but without the return_quote_type
    text, tokens = pySteve.tokenize_quoted_strings(teststring, return_quote_type = False) # default
    assert text == 'someimtes {T0} and {T1} appear and {T2} people.'
    assert tokens == {'T0':'"aliens"', 
                      'T1':'"gov\'t agents"', 
                      'T2':"'borrow'" }
    assert text.format(T0=tokens['T0'], T1=tokens['T1'], T2=tokens['T2']) == teststring

    teststring = '""" docstrings """ are a powerful agent for "good"'
    text, tokens = pySteve.tokenize_quoted_strings(teststring, return_quote_type = True)
    assert text == '{T0} are a powerful agent for {T1}'
    assert tokens == {'T0': {'text':'""" docstrings """', 'quote_type':'"""'},
                      'T1': {'text':'"good"', 'quote_type':'"'}}
    assert text.format(T0=tokens['T0']['text'], T1=tokens['T1']['text']) == teststring

    teststring = '""" str="this is a big \'test\'" """'
    text, tokens = pySteve.tokenize_quoted_strings(teststring)
    assert text == '{T0}'
    assert tokens == {'T0':'""" str="this is a big \'test\'" """'}
    assert text.format(T0=tokens['T0']) == teststring

    teststring = "What happens when a quote is 'unresolved by the end?"
    text, tokens = pySteve.tokenize_quoted_strings(teststring)
    assert text == "What happens when a quote is 'unresolved by the end?"
    assert tokens == {} # nothing, could be an apostrophe
    assert text == teststring

    teststring = 'docstring_fileheader="""pySteve is a mish-mash collection of useful functions, rather than an application.  It is particularly useful to people named Steve."""'
    text, tokens = pySteve.tokenize_quoted_strings(teststring, True)
    assert text == "docstring_fileheader={T0}"
    assert tokens == {"T0": {'text':teststring[21:], 'quote_type':'"""' }} 
    assert text.format(T0=tokens['T0']['text']) == teststring


def test_dict_soft_update():
    pets = {'luna':'good dog', 'sunny':'good dog'}
    additions = {'sunny':'bad dog', 'zelda':'cats are always bad'}
    assert pySteve.dict_soft_update(pets, additions) == {'luna':'good dog', 'sunny':'good dog', 'zelda':'cats are always bad'}
    # object is directly updated:
    assert pets == {'luna':'good dog', 'sunny':'good dog', 'zelda':'cats are always bad'}


def test_db_safe_name():
    assert pySteve.db_safe_name('my_field_name') == 'my_field_name'
    assert pySteve.db_safe_name(' my field name') == 'my_field_name'
    assert pySteve.db_safe_name('#my {field} name') == 'my_field_name'
    assert pySteve.db_safe_name('123 ^^eyes on me') == '_123_eyes_on_me'
    # reserved words
    assert pySteve.db_safe_name('Type') == '_Type' 
    assert pySteve.db_safe_name('Type', 'My_') == 'My_Type'
    assert pySteve.db_safe_name('Type', '#My-') == 'My_Type'
    # custom reserve word subs
    assert pySteve.db_safe_name('Type',   parent='Parent_ID', object="Object_Type") == '_Type'
    assert pySteve.db_safe_name('Parent', parent='Parent_ID', object="Object_Type") == 'Parent_ID'
    assert pySteve.db_safe_name('parent', parent='Parent_ID', object="Object_Type") == 'Parent_ID'
    assert pySteve.db_safe_name('object', parent='Parent_ID', object="Object_Type") == 'Object_Type'
    assert pySteve.db_safe_name('OBJECT', parent='Parent_ID', object="Object_Type") == 'Object_Type'


def test_generate_markdown_doc():
    srcfiles = Path(Path(__file__).parent.parent / 'src')
    dstMD = Path(Path(__file__).parent.parent / 'README.md')
    doc = pySteve.generate_markdown_doc(srcfiles, dstMD)
    pass


def test_substitute_dict_in_string():
    assert pySteve.substitute_dict_in_string('The {animal} is out of the {container}', {'animal':'cat','container':'bag'}) == f'The cat is out of the bag'
    assert pySteve.substitute_dict_in_string('The {animal} is out of the {container}', {'animal':'badger','container':'hole'}) == f'The badger is out of the hole'
    assert pySteve.substitute_dict_in_string('The {animal} is out of the {container}', {'animal':'dog','container':'house'}) == f'The dog is out of the house'
    assert pySteve.substitute_dict_in_string('The {animal} is out of the {container}') == 'The {animal} is out of the {container}'

    today = datetime.now().strftime('%Y%m%d')
    assert pySteve.substitute_dict_in_string('today is {date}') == f'today is {today}'
    assert pySteve.substitute_dict_in_string('today is {date}', {'date':'awesome'}) == f'today is awesome'
    
    today = datetime.now().strftime('%Y-%m-%d')
    assert pySteve.substitute_dict_in_string('today is {date}', {}, '-') == f'today is {today}'

    assert '{now}' not in pySteve.substitute_dict_in_string('the current time is {now}')
    assert pySteve.substitute_dict_in_string('today is {datetime}', {}, '-', ':', '_') .count('-') == 2
    assert pySteve.substitute_dict_in_string('today is {datetime}', {}, '-', ':', '_') .count(':') == 2
    assert pySteve.substitute_dict_in_string('today is {datetime}', {}, '-', ':', '_') .count('_') == 1


def test_logger_setup():
    folder = Path('./tests/logs')
    shutil.rmtree(folder, True)
    today = datetime.now().strftime('%Y%m%d')

    lunalog = pySteve.logger_setup('Luna-log', filepath='{folder}/{date}/{pet}_eating_{food}.log', folder=folder, pet='Luna', food='Pizza')
    assert Path(folder / today / 'Luna_eating_Pizza.log' ).exists()
    lunalog.info('this is a log for Luna.')

    sunnylog = pySteve.logger_setup('Sunny-log', filepath='{folder}/{date}/{pet}_eating_{food}.log', folder=folder, pet='Sunny', food='Puke')
    assert Path(folder / today / 'Sunny_eating_Puke.log' ).exists()
    sunnylog.info('this is a log for Sunny.')

    zeldalog = pySteve.logger_setup('Zelda-log', filepath='{folder}/{date}/{pet}_eating_{food}.log', folder=folder, pet='Zelda', food='Tuna')
    assert Path(folder / today / 'Zelda_eating_Tuna.log' ).exists()
    zeldalog.info('this is a log for Zelda.')

    with open(Path(folder /today / 'Zelda_eating_Tuna.log'), 'r') as fh:
        content = fh.read()
    assert 'Zelda' in content 
    assert 'Luna' not in content 
    assert 'Sunny' not in content 

    # TODO: the root logger stops on everyone.
    rootlogger = pySteve.logger_setup(filepath='{folder}/{date}/root.log', folder=folder)
    rootlogger.info('this is my test of the root logger.')
    zeldalog.info('this is not the root logger, this is just for Zelda.')
    with open(Path(folder /today / 'root.log'), 'r') as fh:
        content = fh.read()
    assert 'root logger' in content 
    #assert 'Zelda' not in content  # right now, root logger picks up everything :^\


def test_notion_translate_type():
    assert pySteve.notion_translate_type('text')['db'] == 'varchar'
    assert pySteve.notion_translate_type('text')['py'] == str
    assert pySteve.notion_translate_type('number')['py'] == float

    assert pySteve.notion_translate_type('page', varchar_size=2)['db'] == 'varchar(2)'
    assert pySteve.notion_translate_type('number')['db'] == 'decimal(18,2)'
    assert pySteve.notion_translate_type('number', decimal_precision=None)['db'] == 'decimal'
    assert pySteve.notion_translate_type('number', decimal_precision=17)['db'] == 'decimal(18,17)'

    overrides = { 'number': {'pk':'name', 'db':'DECIMAL(32,6)', 'py':float, 'obj':False },
                  'date':   {'pk':'name', 'db':'INTEGER',       'py':int,   'obj':False }
                 }
    assert pySteve.notion_translate_type('number', **overrides)['db'] == 'DECIMAL(32,6)'
    assert pySteve.notion_translate_type('date', **overrides)['db'] == 'INTEGER'
    # one-off substitution:
    assert pySteve.notion_translate_type('number', number={'db':'INTEGER' })['db'] == 'INTEGER'


def test_notion_translate_value():
    assert pySteve.notion_translate_value('text', {'plain_text':'something cool'}) == ('something cool', ['something cool'], False)
    assert pySteve.notion_translate_value('number', 123) == ('123',[123],False)
    assert pySteve.notion_translate_value('formula', {'type':'number','number':123}) == ('123',[123],False)
    assert pySteve.notion_translate_value('multi_select', [{'name':'one'},{'name':'two'},{'name':'five'}]) == ('one, two, five', ['one','two','five'], True)


def test_notion_get_api_key():
    assert pySteve.notion_get_api_key(api_key='notion_key12345') == 'notion_key12345'
    assert pySteve.notion_get_api_key(envfile=Path(Path(__file__).parent / 'test.env')) == 'notion_key67890'


def test_notionapi_get_users():
    your_name = 'Stephen Hilton'
    env = pySteve.envfile_load()
    apikey = pySteve.notion_get_api_key(envfile=env)
    users = pySteve.notionapi_get_users(apikey)
    assert len(users) >5
    assert type(users) == dict
    assert [v for n,v in users.items() if v['name'] == your_name ][0]['name'] == your_name
    users = pySteve.notionapi_get_users(apikey, include=['Stephen Hilton','Cedric Blair'], full_json=True)
    assert len(users) >= 2
    assert 'full_json' in [v for n,v in users.items()][0]
    

def test_notionapi_get_dataset_info():
    env = pySteve.envfile_load()
    apikey = pySteve.notion_get_api_key(envfile=env)
    tablename, columns = pySteve.notionapi_get_dataset_info(apikey, env['NOTION_CRM_ACCOUNTS'])
    assert tablename.lower() == 'Accounts'.lower()
    assert len(columns) > 30
    assert [c for c in columns if c['notion_name']=='id'][0]['db_name'] == 'Account_id'
    assert [c for c in columns if c['notion_name']=='Data Scale'][0]['db_name'] == 'Data_Scale'
    assert [c for c in columns if c['notion_name']=='Can Mention Externally?'][0]['db_name'] == 'Can_Mention_Externally'


def test_notionapi_get_dataset():
    env = pySteve.envfile_load()
    apikey = pySteve.notion_get_api_key(envfile=env)
    tablename, rows, keypairs, columns = pySteve.notionapi_get_dataset(apikey, env['NOTION_CRM_CHAINS'])
    assert tablename.lower() == 'Chains'.lower()
    assert 'Polygon' in [r['Name'] for r in rows]
    assert 'Ethereum' in [r['Name'] for r in rows]
    assert sum([1 for r in rows if r['VM']=='EVM']) >= 8
    assert len(rows) < len(keypairs)

    ethrow = [r for r in rows if r['Name']=='Ethereum'][0]['id']
    assert len([r for r in keypairs if r['RowID']==ethrow]) > 10
    assert [r for r in keypairs if r['RowID']==ethrow][0]['CellCount'] == len([r for r in keypairs if r['RowID']==ethrow])
    assert [c for c in columns if c['notion_name']=='id'][0]['db_name'] == 'Chain_id'

    for notion_table, notion_id in {n:v for n,v in env.items() if n[:10] == 'NOTION_CRM'}.items():
        tablename, rows, keypairs, columns = pySteve.notionapi_get_dataset(apikey, notion_id, 2000)
        print(f'---------------------')
        print(f'Notion Table : {tablename}')
        print(f'EnvVar Table : {notion_table}')
        print(f'Rows         : {len(rows)}')
        print(f'Keypairs     : {len(keypairs)}')
        print(f'Columns      : {len(columns)}')
        assert f"NOTION_CRM_{tablename.upper().replace(' ','_')}" == notion_table
        assert len(rows) > 0
        assert len(keypairs) > 0
        assert len(columns) > 0
        if notion_table == 'NOTION_CRM_ACCOUNTS':
            assert len(rows) > 101


if __name__ == '__main__':
    test_notionapi_get_dataset_info()
    pass