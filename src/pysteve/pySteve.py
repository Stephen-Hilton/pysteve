from pathlib import Path 
from pprint import pprint
from string import Formatter
import inspect, logging, requests
from datetime import datetime, timedelta

markdown_fileheader="""pySteve is a mish-mash collection of useful functions, rather than an application.  It is particularly useful to people named Steve.""" 
notion_standard_headers = { "Notion-Version": "2022-06-28", "content-type": "application/json"}


class __docstring__():
    marker = '__DOCSTRING_BOUNDRY__'
    def __init__(self, marker:str=None) -> None:
        if marker: self.marker = marker 
    @property
    def prefix(self): return f'$(cat << {self.marker}\n' 
    @property
    def suffix(self): return f'\n{self.marker}\n)'
    

def infer_datatype(value, add_sqltype:bool = False):
    """
    Infers the primative data types based on value characteristics, and returns a tuple of (type, typed_value).
    Currently supports float, int, str, datetime (iso8601), and list (with typed elements using recursive calls).
    If add_sqltype is True, adds the SQL type to the end of the tuple.
    """
    value = str(value)
    rtn = ()

    if value.replace('.','').replace('e','').replace('-','').replace('+','').isnumeric() and \
       value[:1].isnumeric() and value[-1:].isnumeric() and \
       len(value)-len(value.replace('-','')) <2 and \
       len(value)-len(value.replace('e','')) <2 and \
       len(value)-len(value.replace('+','')) <2 and \
       len(value)-len(value.replace('.','')) <2 : # likely numeric
        
        # handle scientific notation:
        if 'e' in value: 
            numary = value.replace('+','').split('e')
            exp = 10**(float(numary[1]))
            num = float(numary[0])
            value = '{:40f}'.format(num*exp).strip()

        if '.' in value: 
            while value[-2:]=='00': value = value[:-1]
            rtn = (float, float(value))
        else:
            rtn = (int, int(value))
        
    elif value.startswith('[') and value.endswith(']'):
        values = [v.strip() for v in value[1:-1].split(',')]
        for i,v in enumerate(values):
            values[i] = v.strip()
            values[i] = infer_datatype(values[i])[1]
        rtn = (list, values)
    
    elif value[:2] in['20','19'] and (value.replace('-','').replace('/','')[:8]).isnumeric:
        rawvalue = value.replace('-','').replace('/','').replace(':','').replace(' ','').replace('T','')
        rawvalueTZ = '' 
        if '+' in rawvalue: 
            rawvalueTZ = rawvalue.split('+')[1]
            rawvalue = rawvalue.split('+')[0]
        if  rawvalue[4:6].isnumeric() and int(rawvalue[4:6]) <= 12 and \
            rawvalue[6:8].isnumeric() and int(rawvalue[6:8]) <= 31:
            fmt = ''
            if len(rawvalue) == 8: fmt = '%Y%m%d'
            elif len(rawvalue) == 14: fmt = '%Y%m%d%H%M%S'
            elif 14 < len(rawvalue) <= 24 and '.' in rawvalue: fmt = '%Y%m%d%H%M%S.%f'
            else: 
                rtn = (str, value) # give up and call it a string
            if len(rawvalueTZ) != 0: 
                fmt += '%z'
                rawvalue += f'+{rawvalueTZ}'
        else:
            rtn = (str, value) # invalid iso8601 date format

        if rtn == ():  rtn = (datetime, datetime.strptime(rawvalue, fmt))
    
    elif (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]

    if rtn == (): rtn = (str, value) # str as default

    if add_sqltype: rtn = ( rtn[0], rtn[1], datatype_py2sql(rtn[0], value) )

    return rtn
    

def datatype_py2sql (pytype:type, sample_data=None) -> str:
    """
    Given a python datatype, returns the corresponding SQL datatype as string.  If sample_data is
    provided, it will attempt match characteristics such as string length, precision, integer sizing, etc.
    """
    if pytype == str: 
        if len(sample_data) >0: 
            return f'VARCHAR({len(sample_data)})'
        else:
            return f'VARCHAR'
    if pytype == int: 
        if len(str(sample_data))==0: return 'INTEGER' # default
        if   abs(int(sample_data)) <= ((2**(8*1))/2)-1: return 'TINYINT'
        elif abs(int(sample_data)) <= ((2**(8*2))/2)-1: return 'SMALLINT'
        elif abs(int(sample_data)) <= ((2**(8*4))/2)-1: return 'INTEGER'
        else: return 'BIGINT'
    if pytype == float: 
        if len(sample_data)==0: return f'DECIMAL(18,2)'
        dec = len(str(sample_data).split('.')[0])
        if dec==0: dec=1
        pre = 0 if '.' not in sample_data else len(str(sample_data).split('.')[1])
        return f'DECIMAL({dec+pre},{pre})'
    if pytype == datetime:
        if len(sample_data) <=12:
            return 'DATE'
        else:
            return 'TIMESTAMP'
    return f'VARCHAR({len(sample_data)})'



def envfile_save(save_path:Path, save_dict:dict = {}, iteration_zero_pad:int = 6, docstring_marker_override:str = None) -> Path:
    """
    Always saves a dict as a shell (zsh) as an env-loadable file, adding folders, file iterations and substitutions as needed.

    The save_path allows for substitution of any name in the dict (within curly brackets) with the value of that entry. 
    For example, if dict = {'date':'2024-01-01'}, save_path = '~/some/path/file_{date}.sh' will become 
    '~/some/path/file_2024-01-01.sh'. Additionally, if the full substituted file exists, the process will append 
    an iterator (1,2,3) to the end to preserve uniqueness.  The final save_path is returned from the function.  
    Because the file needs to be compatible with shell .env files, special characters (spaces, newlines, etc) are 
    removed from all 'names' in the save_dict, and any values with newlines will be wrapped in a docstring using 
    the string saved in variable 'docstring_eom_marker'    

    Args:
        save_path (Path): Where to save the file, with substitution logic.
        save_dict (dict): Dictionary containing file content.
        docstring_marker_override (str): Begin/end marker for docstrings. If supplied, overrides the global docstring_marker

    Returns: 
        Path: Returns the final save_path used (after substitution and iteration).

    """
    if not save_path: raise ValueError(f'save_path must be specified, you provided: {save_path}')
    pth = Path(str(save_path).format(**save_dict)).resolve() if bool(save_dict) else Path(save_path).resolve()
    pth.parent.mkdir(parents=True, exist_ok=True)
    
    # add iteration, if needed
    iter = 0
    extlen = -len(pth.suffix)
    pos1 = len(str(pth)[:extlen])
    while pth.exists(): 
        iter +=1
        pth = Path( '{}.{}{}'.format(str(pth)[:pos1], str(iter).rjust(iteration_zero_pad,'0'), str(pth)[extlen:]) )
        suflen = -len(pth.suffix) - len(str(iter)) -1

    # iterate dict and build rows
    docstr = __docstring__(docstring_marker_override)
    lines = []
    for nm, val in save_dict.items():
        if type(val) not in [str, int, float, list]: continue

        nm = ''.join([c for c in nm if c.isalnum() or c in['_'] ]) 
        q = '' if type(val) in [int, float] else '"'
        val = str(val)
        if '\n' in val: 
            if val[:1]=='\n': val = val[1:]
            val = val.rstrip()
            nm += f'={docstr.prefix}{val}{docstr.suffix}'
        else: 
            nm += f'={q}{val}{q}'
        lines.append( nm )
    
    # write file
    with open(pth, 'w') as fh:
        fh.write( '\n'.join(lines) )

    return Path(pth)



def envfile_load(load_path:Path='.', load_path_sort:str = 'latest', exact_match_only:bool = False, docstring_marker_override:str = None) -> dict: 
    """
    Returns a dictionary containing name/value pairs pulled from the supplied .env formatted shell (zsh) script.

    If load_path does not have a direct match, it is assumed to be a pattern and will be matched given 
    supplied template logic (unless exact_match_only = True), and return with the load_path_sort logic 
    (first or last).  There are several synonyms: [first | earliest | asc] or [last | latest | desc] 
    
    Args:
        load_path (Path): file to load from, with template logic allowed.
        load_path_sort (str): If load_path was a template, indicates which file to select, based on filename sort. 
        exact_match_only (bool): Disallow filename templating, and require exact filename only.
        docstring_marker_override (str): Begin/end marker for docstrings. If supplied, overrides the global docstring_marker
 
    Returns: 
        dict: the dictionary name/value parsed from the supplied file.

    """
    if not load_path: raise ValueError(f'load_path must be specified, you provided: {load_path}')
    pth = Path(load_path).resolve()

    if pth.is_dir(): 
        pth = Path(pth / '.env')

    if not pth.exists(): # do load_path template logic
        filename = pth.name
        if '{' not in filename: raise FileNotFoundError(f'Could not find file or template pattern match for supplied file: {load_path}')
        
        static_segments = parse_placeholders(filename)['static_segments']
        files = sorted([f.name for f in pth.parent.iterdir() ])

        # collect all files, including which are base and which are multi-run iterations
        rtnfiles = parse_filename_iterators(pth.parent)
        files = rtnfiles['all_files']

        # use find() to verify segments exist, in order from left-to-right
        valid_files = []
        for file in files:
            file = file.name
            pos = 0
            keep_file = True
            for seg in static_segments: # skip placeholder segments, only look at static (in order)
                pos = file.find(seg['segment'], pos if pos==0 else pos-1) 
                if pos == -1: 
                    keep_file = False
                    break
                pos += seg['len']
            if keep_file: valid_files.append(file)

        if load_path_sort[:3] in ['fir', 'ear', 'asc']:
            pth = Path( pth.parent / valid_files[0] ).resolve()
        else: # last, latest, desc, etc.
            pth = Path( pth.parent / valid_files[len(valid_files)-1] ).resolve()

    # with correct path selected, load and structure into dict
    with open(pth, 'r') as fh:
        content = fh.read()

    # iter allows next(), ::END:: needed to search for docstring END across newlines
    docstr = __docstring__(docstring_marker_override)
    lines = iter(content.replace(docstr.suffix,'\n::END::').split('\n')) 

    # loop thru and build dict to control load
    rtn = {}
    multiline = None
    for line in lines:
        eq = line.find('=')
        name  = line[:eq]
        value = line[eq+1:]
        if value[:1]=='"' and value[-1:]=='"': value = value[1:-1]
        if value.startswith( docstr.prefix.strip() ):
            multiline = []
            mline = ''
            while True:
                mline = next(lines, '')
                if '::END::' in mline: break
                multiline.append( mline )
            value = '\n'.join(multiline)
        value = infer_datatype(value)[1]
        rtn[name] = value
    rtn['envfile_load--FilePath_Selected'] = str(pth.resolve())
    rtn = {n:v for n,v in rtn.items() if n.strip()!='' and not n.strip().startswith('#')}
    return rtn



def parse_placeholders(value:str = '', wrappers:str = '{}' ):
    """
    From given string, parses out a list of placeholder values, along with their positions.
    """
    ws = wrappers[:1] # starting wrapper
    we = wrappers[1:2] # ending wrapper
    rtn = {'original':value, 'segments':[], 'placeholders':[], 'static_segments':[], 'starting_wrapper':ws, 'closeing_wrapper':we } 
    order = startpos = 0 
    plcflg = False
    segment = lastchar = ''

    for pos, char in enumerate(list(str(value))):
        if char == ws: 
            if len(segment) >0:
                data = {'order':order, 'segment':segment, 'type':'static', 'start':startpos, 'end':pos, 'len': pos - startpos  }
                rtn['segments'].append( data )
                rtn['static_segments'].append( data )
                order +=1
            startpos = pos
            segment = ''

        # always collect the character for the next segment
        segment += char 

        if char == we: 
            if len(segment) >0:
                data = {'order':order, 'segment':segment, 'type':'placeholder', 'start':startpos, 'end':pos+1, 'len': pos - startpos +1,  'name':segment[1:-1] }
                rtn['placeholders'].append( data )
                rtn['segments'].append( data )
                order +=1
            startpos = pos
            segment = ''
        
    if len(segment) > 0: # be sure to collect the last segment
        data = {'order':order, 'segment':segment, 'type':'static', 'start':startpos, 'end':pos, 'len': pos - startpos  }
        rtn['segments'].append( data )
        rtn['static_segments'].append( data )


        
    return rtn



def parse_filename_iterators(folderpath:Path) -> dict:
    """
    Iterate thru all files in the supplied folder, and return a dictionary containing three lists:
     - iter_files, containing files that end in an iterator ( *.000 )
     - base_files, containing files that do not end in an interator (aka base file)
     - all_files, sorted in order with the base file first per pattern, followed by any iterations
    """
    pth = Path(folderpath)
    if not pth.is_dir():
        pth = pth.parent
        if not pth.is_dir():
            raise ValueError('folderpath must be the path to a valid folder (must exist)')
    
    base_files = []
    iter_files = []
    files = sorted([f for f in pth.iterdir() if f.stem != '.DS_Store' ])

    for file in files:
        fileary = str(file.stem).split('.')
        if len(fileary) >0 and str(fileary[len(fileary)-1]).isnumeric():
            iter_files.append(file)
        else:
            base_files.append(file)
    
    all_files = []
    for base_file in base_files:
        all_files.append(base_file)
        for iter_file in iter_files:
            if str(iter_file.stem).startswith(base_file.stem):
                all_files.append(iter_file)

    return {'all_files': all_files, 'base_files':base_files, 'iter_files':iter_files}



def chunk_lines(list_of_lines:list = [], newchunck_marker_funcs:list = []) -> list:
    """
    Breaks a list of string lines into a list of lists of string lines, based on supplied markers.
    
    Accepts a list of lines (say, from reading a file) and separates those lines into separate lists 
    based on boundries discovered by running lines against a list of marker functions (usually lambdas).
    Each marker function will be passed the line in sequence, and must return a True or False as to 
    whether the line is the beginning of a new section.  If ANY of the marker functions return True, 
    the line is considered the first of a new chunk (list of string lines).  At the end, the new list
    of lists of string lines is returned.   
    For example: after opening and reading lines of a python file, you could send that list of lines
    to this function along with the two lambda functions 
    `  lambda line : str(line).startswith('def')   ` and
    `  lambda line : str(line).startswith('class') ` to split the list of lines by python functions.

    Args:
        list_of_lines (list): List of string lines to match markers against and group.
        newchunck_marker_funcs (list): List of functions, applied to each line to mark new chunk boundries.

    Returns: 
        list: A list of lists of string lines.
    """
    newchunkstarts = []
    for func in newchunck_marker_funcs:
        newchunkstarts.extend( [(i,l) for i,l in enumerate(list_of_lines) if func(l) ] )
    
    rtn = []
    chunkstart = 0
    for chunk in sorted(newchunkstarts):
        if chunkstart == 0:  rtn.append( list_of_lines[:chunk[0]] )
        else:                rtn.append( list_of_lines[chunkstart:chunk[0]] )
        chunkstart = chunk[0]
    rtn.append( list_of_lines[chunkstart:] ) # get last entry
    rtn = [r for r in rtn if r != []]
    return rtn
    


def tokenize_quoted_strings(text:str='', return_quote_type:bool=False) -> (str, dict):
    """
    Tokenizes all quoted segments found inside supplied string, and returns the string plus all tokens.

    Returns a tuple with the tokenized string and a dictionary of all tokens, for later replacement as needed. 
    If return_quote_type is True, also returns the quote type with one more nested layer to the return dict, looking like:
    {"T0": {"text":"'string in quotes, inlcuding quotes', "quote_type":"'"}, "T1":{...}}
    If return_quote_type is False, returns a slightly more flat structure:
    {"T0": "'string in quotes, inlcuding quotes'", "T1":...}

    Args: 
        text (str): String including quotes to tokenize.
        return_quote_type (bool): if True, will also return the type of quote found, if False (default) just returns tokenized text in a flatter dictionary structure.

    Returns: 
        tuple (str, dict): the tokenized text as string, and tokens in a dict. 
    """
    text = str(text)
    quote_chars = ["'",'"','"""']
    quote_char = None
    newchars = []
    newtoken = []
    tokens = {}
    tokenid = 0
    scoot = 0
    for i, c in enumerate(list(text)):
        if scoot >0:
            scoot -=1
            continue
        if c == '"' and text[i:i+3] == '"""': 
            c = '"""'
            scoot = 2

        if c in quote_chars:
            if quote_char is None:  # starting quote
                quote_char = c
                newchars.append('{T' + str(tokenid) + '}') 

            elif c == quote_char:  # closing quote
                newtoken.append(c)
                c = ''
                tokens[f'T{tokenid}'] = {'text':''.join(newtoken), 'quote_type':quote_char}
                quote_char = None
                tokenid +=1
                newtoken = []

            else:  # another type of quote inside starting quote
                pass # we can ignore, as part of the string

        if quote_char: # in a quote:
            newtoken.append(c)
        else: # not in a quote
            newchars.append(c)

    newtext = ''.join(newchars)

    # handle unresolved quotes
    if newtoken != []: 
        newtext = newtext.replace('{T'+str(tokenid)+'}', ''.join(newtoken))
    
    # flatted and remove quote_type, if requested
    if not return_quote_type: tokens = {n:v['text'] for n,v in tokens.items()}

    return (newtext, tokens)
            

class datetimePlus():
    date_format = '%Y-%m-%d'
    value: datetime = None
    calendar_begins = datetime.strptime('1970-01-01','%Y-%m-%d')

    def __init__(self, datetime_or_string=None) -> None:
        if type(datetime_or_string)==datetime:
            self.value = datetime_or_string
        else:
            self.set_datetime(datetime_or_string)
    
    def set_datetime(self, strptime:str='2023-12-31') -> datetime:
        if not strptime or strptime.lower() in['today','now']: 
            self.value = datetime.now()            
        else:
            self.value = datetime.strptime(strptime, '%Y-%m-%d')
        return self.value
    
    def __str__(self) -> str:
        attr = self.get_attributes()
        attr = [f'{str(n).ljust(25)} : {str(v["data"])[:10].ljust(15)}' for n,v in attr.items() ]
        return f"{'-'*35}\n{self.__class__.__name__} Object\n{'-'*35}\n" + '\n'.join(attr)

    def get_attributes(self, remove_keys:list=[]) -> dict:
        attributes = {a[0]:{'data':a[1]} for a in list(inspect.getmembers(self)) if a[0][:2] !='__' and 'method' not in str(type(a[1]))}
        ord = {'day':1, 'wee':2, 'mon':3, 'qua':4, 'yea':5, 'cal':6, 'fir':7, 'las':7}
        ord2 = {'calendar_date':0, 'calendar_date_start_ts':1, 'calendar_date_end_ts':2, 'calendar_begins':9001, 'leap_year':9000}
        for nm, vals in attributes.items():
            # calculate types:
            vals['pytype'] = str(type(vals['data'])).split("'")[1].split('.')[0]
            vals['sqltype'] = {'str':'VARCHAR', 'int':'INTEGER', 'bool':'INTEGER', 'datetime':'DATE'}[vals['pytype']]
            if nm.endswith('_ts'): vals['sqltype'] = 'TIMESTAMP'
            # calculate order
            nmary = nm.split('_of_')
            if nm in ord2.keys(): 
                vals['order'] = ord2[nm]
            elif len(nmary) >= 2: 
                vals['order'] = (ord[nmary[0][:3]]*1000) + (ord[nmary[1][:3]]*100) + int(len(nm)) + (2 if nm.startswith('last') else 0)
            else: 
                vals['order'] = 8999
        # remove keys:
        for rmv in remove_keys:
            attributes.pop(rmv, '')
        # order and return  
        return dict(sorted(attributes.items(), key=lambda a:a[1]['order']))
    
    def get_create_table(self, tablename:str='schema.Calendar') -> str:
        attr = self.get_attributes( ['date_format','value'] )
        attr = [f'{n.ljust(25)} {v["sqltype"]}' for n,v in attr.items()]
        sql = f"CREATE TABLE {tablename} \n  ( " + '\n  , '.join(attr) + '  \n)'
        return sql

    def get_insert_table(self, tablename:str='schema.Calendar') -> str:
        attr = self.get_attributes( ['date_format','value'] )
        attr['leap_year']['data'] = 1 if attr['leap_year']['data'] else 0
        cols = list(attr.keys())
        vals = [str(v['data']) if v['pytype'] in['int','bool'] else f"'{str(v['data'])[:10]}'" for n,v in attr.items()]
        sql = f"INSERT INTO {tablename} ({', '.join(cols)})\n VALUES ({', '.join(vals)})"
        return sql

    @property
    def calendar_date(self) -> str:
        return self.value.strftime(self.date_format)
    @property
    def calendar_date_start_ts(self) -> str:
        return self.calendar_date + 'T00:00:00.000000'
    @property
    def calendar_date_end_ts(self) -> str:
        return self.calendar_date + 'T23:59:59.999999'
    @property
    def leap_year(self) -> bool:
        return self.value.year % 4 == 0
    
    # LABELS    
    @property
    def yrmth(self) -> int:
        return (self.year_of_calendar*100)+self.month_of_year
    @property
    def yrmthwk(self) -> int:
        return (self.year_of_calendar*1000)+(self.month_of_year*10)+(self.week_of_month)
    @property
    def yr_mth(self) -> str:
        return f'{self.year_of_calendar}-{self.month_of_year:02d}'
    @property
    def yr_mth_wk(self) -> str:
        return f'{self.year_of_calendar}-{self.month_of_year:02d}-{self.week_of_month}'

    @property
    def yrmth_iso(self) -> int:
        return (self.year_of_calendar*100)+self.month_of_year_iso
    @property
    def yrmthwk_iso(self) -> int:
        return (self.year_of_calendar*1000)+(self.month_of_year_iso*10)+(self.week_of_month_iso)
    @property
    def yr_mth_iso(self) -> str:
        return f'{self.year_of_calendar}-{self.month_of_year_iso:02d}'
    @property
    def yr_mth_wk_iso(self) -> str:
        return f'{self.year_of_calendar}-{self.month_of_year_iso:02d}-{self.week_of_month_iso}'

    # DAY
    @property
    def day_of_calendar(self) -> int:
        return int((self.value - self.calendar_begins).days) +1
    @property
    def day_of_year(self) -> int:
        return  int(self.value.strftime('%-j'))
    @property
    def day_of_quarter(self) -> int:
        qtr_begin = datetime(year=self.value.year, month=[1,1,1,4,4,4,7,7,7,10,10,10][self.value.month-1], day=1)
        return int((self.value - qtr_begin).days)+1
    @property
    def day_of_month(self) -> int:
        return  int(self.value.strftime('%-d'))
    @property
    def day_of_week(self) -> int:
        return int(self.value.strftime('%w')) +1 
    @property
    def day_of_week_name(self) -> str:
        return self.value.strftime('%A')
    
    # WEEK
    @property
    def week_of_calendar(self) -> int:
        return int(self.day_of_calendar / 7) +1
    @property
    def week_of_year(self) -> int:
        return  int(self.day_of_year / 7) +1
    @property
    def week_of_year_iso(self) -> int:
        return  int((self.value - self.first_of_year_iso).days / 7) +1        
    @property
    def week_of_quarter(self) -> int:
        return  int(self.day_of_quarter / 7) +1
    @property
    def week_of_quarter_iso(self) -> int:
        isoqtrbegin = self.__isomth_firstdate__()
        while isoqtrbegin.month not in [1,3,6,9]:
            isoqtrbegin = self.__isomth_firstdate__(isoqtrbegin - timedelta(15))
        daydiff = (self.value - isoqtrbegin).days
        return int(daydiff/7)+1
    @property
    def week_of_month(self) -> int:
        return  int(self.day_of_month / 7) +1
    @property
    def week_of_month_iso(self) -> int:
        isomthbegin = self.__isomth_firstdate__()
        daydiff = (self.value - isomthbegin).days
        return int(daydiff/7)+1

    # MONTH
    @property
    def month_of_calendar(self) -> int:
        return int(((self.value.year - self.calendar_begins.year -1) *12) + self.value.month)
    @property
    def month_of_year(self) -> int:
        return int(self.value.month)
    @property
    def month_of_year_iso(self) -> int:
        return int((self.__isomth_firstdate__(self.value) + timedelta(15)).month)
    @property
    def month_of_year_name(self) -> str:
        moy = self.first_of_month
        return datetime(moy.year, moy.month, 15).strftime('%B')
    @property
    def month_of_year_name_iso(self) -> str:
        moy = self.first_of_month_iso
        return datetime(moy.year, moy.month, 15).strftime('%B')
    @property
    def month_of_quarter(self) -> int:
        return int( 3 if self.value.month %3 == 0 else self.value.month %3 )
    @property
    def month_of_quarter_iso(self) -> int:
        isomth = self.month_of_year_iso
        return int( 3 if isomth %3 == 0 else isomth %3 )

    # QUARTER
    @property
    def quarter_of_calendar(self) -> int:
        return int(((self.value.year - self.calendar_begins.year -1) *4) + self.quarter_of_year)
    @property
    def quarter_of_year(self) -> int:
        return int((self.value.month-1)/3)+1
    @property
    def quarter_of_year_name(self) -> int:
        return f'{str(self.year_of_calendar)} Q{str(self.quarter_of_year)}' 
    @property
    def quarter_of_year_iso(self) -> int:
        return int((self.month_of_year_iso-1)/3)+1

    # YEAR    
    @property
    def year_of_calendar(self) -> int:
        return int(self.value.year)

    # FIRST / LAST Dates - Calendar
    @property
    def first_of_year(self) -> datetime:
        return datetime(self.value.year, 1, 1)
    @property
    def last_of_year(self) -> datetime:
        return datetime(self.value.year, 12, 31)
    @property
    def first_of_quarter(self) -> datetime:
        qtrmth = [0,1,1,1,4,4,4,7,7,7,10,10,10][self.value.month]
        return datetime(self.value.year, qtrmth, 1)
    @property
    def last_of_quarter(self) -> datetime:
        nextqtr = self.first_of_quarter + timedelta(110)
        return datetime(nextqtr.year, nextqtr.month, 1) - timedelta(1)
    @property
    def first_of_month_iso(self) -> datetime:
        return self.__isomth_firstdate__()
    @property
    def last_of_month_iso(self) -> datetime:
        middate = self.__isomth_firstdate__() + timedelta(45)
        return (self.__isomth_firstdate__( middate ) - timedelta(1))
    @property
    def first_of_week_iso(self) -> datetime:
        return self.value - timedelta(int(self.value.strftime('%w')))
    @property
    def last_of_week_iso(self) -> datetime:
        return self.first_of_week_iso + timedelta(6)
    
    # FIRST / LAST Dates - ISO
    @property
    def first_of_year_iso(self) -> datetime:
        return self.__isomth_firstdate__(datetime(self.value.year, 1, 15))
    @property
    def last_of_year_iso(self) -> datetime:
        return self.__isomth_firstdate__(datetime(self.value.year +1, 1, 15)) - timedelta(1)
    @property
    def first_of_quarter_iso(self) -> datetime:
        isoqtrbegin = self.__isomth_firstdate__()
        while isoqtrbegin.month not in [1,3,6,9]:
            isoqtrbegin = self.__isomth_firstdate__(isoqtrbegin - timedelta(15))
        return isoqtrbegin
    @property
    def last_of_quarter_iso(self) -> datetime:
        middate = self.first_of_quarter_iso + timedelta(110)
        return (self.__isomth_firstdate__( middate ) - timedelta(1))
    @property
    def first_of_month(self) -> datetime:
        return datetime(self.value.year, self.value.month, 1)
    @property
    def last_of_month(self) -> datetime:
        nextmth = datetime(self.value.year, self.value.month, 28) + timedelta(7)
        return datetime(nextmth.year, nextmth.month, 1) - timedelta(1)
    @property
    def first_of_month_iso(self) -> datetime:
        return self.__isomth_firstdate__()
    @property
    def last_of_month_iso(self) -> datetime:
        middate = self.__isomth_firstdate__() + timedelta(45)
        return (self.__isomth_firstdate__( middate ) - timedelta(1))
    @property
    def first_of_week(self) -> datetime:
        return self.value - timedelta(int(self.value.strftime('%w')))
    @property
    def last_of_week(self) -> datetime:
        return self.first_of_week_iso + timedelta(6)
    
    # Other (internal) Functions
    def __isomth_firstdate__(self, dt:datetime=None) -> datetime:
        if not dt: dt = self.value
        prev_isomth_states = [(1,6),(1,5),(1,4)  ,(2,6),(2,5) ,(3,6)] # day / dayofweek states where iso month is -1 from calendar 
        if (dt.day, int(dt.strftime('%w'))) in prev_isomth_states: # for invalid states, move back to previous calendar month 
            dt = dt - timedelta(7) 
        dt = datetime(dt.year, dt.month, 1) # back up to first day of calendar month for the correct iso month
        offset = 0 if int(dt.strftime('%w')) <= 3 else 7 # if that day is between 0-3, iso_week begins for that month (0 offset) else it's the following week (7 offset)
        dt = dt - timedelta(int(dt.strftime('%w'))) + timedelta(offset) # back up to day zero, applying offset needed
        return dt
    


def generate_markdown_doc(source_path:Path = './src', dest_filepath:Path = './README.md', 
                          append:bool = False, include_dunders:bool = False, 
                          py_indent_spaces:int = 4) -> str:
    """
    Parses python files to automatically generate simple markdown documentation (generated this document).

    Parses the file at source_path, or if source_path is a folder, will iterate (alphabetically) thru all .py 
    files and generate markdown content by introspecting all functions, classes, and methods, with a heavy focus
    on using google-style docstrings.  It will always return the markdown as a string, and if the dest_filepath 
    is specified, it will also save to that filename. By default it will replace the dest_filepath, or set 
    append=True to append the markdown to the end. This allows freedom to chose which files /folders to document,
    and structure the mardown files however you'd like.  It also allows for a simple way to auto-generate 
    README.md files, for small projects. 

    Todo: add class support, change source_path to a list of files/folders.

    Args: 
        source_path (Path): Path to a file or folder containing .py files with which to create markdown.
        dest_filepath (Path): If specified, will save the markdown string to the file specified.
        append (bool): Whether to append (True) over overwrite (False, default) the dest_filepath.
        include_dunders (bool): Whether to include (True) or exclude (False, default) files beginning with double-underscores (dunders).
        py_indent_spaces (int): Number of spaces which constitute a python indent.  Defaults to 4.

    Returns:
        str: Markdown text generated.
    """
    source_path = Path(source_path).resolve()
    if not source_path.exists(): raise ValueError('Parameter "source_path" must be a valid file or folder.')
    indent = ' '*py_indent_spaces
    if source_path.is_file():
        srcfiles = [source_path.resolve()]
    elif source_path.is_dir():
        srcfiles = [f for f in source_path.iterdir() if f.suffix == '.py' and not (include_dunders==False and str(f.stem)[:2] =='__') ]

    # subdef to parse apart docstrings
    def parse_docstring(docstr:list) -> dict:
        hdr = []
        body = []
        args = []
        rtn = []
        examples = []
        section = 'headline'
        docstr = [l.replace('"""','').strip() for l in docstr]
        while len(docstr)>0 and docstr[0]=='': docstr.pop(0)
        for line in docstr:
            if section == 'headline' and line !='': hdr.append(line)
            elif line.strip().lower().startswith('args:'):     section = 'Args'  
            elif section == 'Args':                            args.append(line)
            elif line.strip().lower().startswith('returns:'):  section = 'Returns'
            elif section == 'Returns':                         rtn.append(line)
            elif line.strip().lower().startswith('examples:'): section = 'Examples'
            elif section == 'Examples':                        examples.append(line)
            elif section == 'Body' and line !='':              body.append(line)
            elif line.strip() != '': 
                section = 'Body'
                body.append(line)
            if line.strip() == '':  section = 'unknown'
        hdr  = ' '.join(hdr ).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        body = ' '.join(body).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        args = '\n - '.join([r for r in args if len(r)>0]).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        rtn  = '\n - '.join([r for r in rtn if len(r)>0] ).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        examples = '\n - '.join([r for r in examples if len(r)>0]).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        return {'docstr_header': hdr, 'docstr_body': body, 'docstr_args': args, 'docstr_returns': rtn, 'docstr_examples': examples}

    def parse_parms(params:str) -> list:
        (text, tokens) = tokenize_quoted_strings(params)
        parms = [p.strip() for p in text.split(',')]
        rtn = []
        name = typ = default = None
        for parmstr in parms:
            typestart = len(parmstr) if parmstr.find(':')==-1 else parmstr.find(':')
            defaultstart = len(parmstr) if parmstr.find('=')==-1 else parmstr.find('=')
            name = parmstr[:min([typestart, defaultstart])].strip()
            typ = parmstr[typestart+1:defaultstart].strip()
            default = parmstr[defaultstart+1:].strip()
            for nm, val in tokens.items():
                if '{'+nm+'}' in default: 
                    default = default.replace('{'+nm+'}', val)
                    parmstr = parmstr.replace('{'+nm+'}', val)

            rtn.append( {'name':name, 'type':typ, 'default':default, 'full':parmstr} )
        return {'parms': rtn}
        
    # ITERATE all source files found
    rtn = []
    for file in srcfiles:
        with open(file,'r') as fh:
            srclines = [str(f).rstrip() for f in str(fh.read()).split('\n') ]
        fileprefixline = [l for l in srclines if l.replace(' ','').startswith('markdown_fileheader=')]
        if len(fileprefixline)>0:
            fileprefix = fileprefixline[0] 
            _, fileprefixdict = tokenize_quoted_strings(fileprefix, True)
            fileprefix = fileprefixdict['T0']['text'].strip()[3:-3] + '\n'
            srcfiles = [l for l in srclines if fileprefix not in l ] 
        else: 
            fileprefix =f"""Functions and classes from the file {file.name}<br>(to customize this text, add the variable to your file: markdown_fileheader = "Some header message" )""" 
        
        sections = []
        chunks = chunk_lines(srclines, [ lambda line: str(line).startswith('def ') or str(line).startswith('class ') ])
        for chunk in sorted(chunks):
            chunkstr = ' '.join(chunk)
            if chunk[0][:4]=='def ': 
                section = {'type':'def', 'name':str(chunk[0][4:chunk[0].find('(')]) } 
                parms = chunkstr[chunkstr.find('(')+1:chunkstr.find(')')]
                docstr_cnt = 0
                docstr = []
                for line in chunk:
                    if '"""' in line: docstr_cnt +=1
                    if docstr_cnt == 1: docstr.append(line)
                    if docstr_cnt == 2: 
                        docstr.append(line)
                        break 
                section.update( parse_docstring(docstr) )
                section.update( parse_parms(parms) )
            elif chunk[0][:6]=='class ':
                section = {'type':'class', 'name':str(chunk[0][6:chunk[0].find('(')]) } 
            else:
                section = {'type':'other'}
            sections.append(section)

        # build return string
        rtn.append(f'# File: {file.name}')
        rtn.append(f'{fileprefix}')
        rtn.append(f'## Functions:')
        for section in [s for s in sections if s['type']=='def']:
            rtn.append(f"### {section['name']}")
            if section['docstr_header'] !='': rtn.append(f"**{section['docstr_header']}**\n")
            if section['docstr_body'] !='': rtn.append(f"{section['docstr_body']}")
            rtn.append(f"#### Arguments:")
            for parm in section['parms']:
                rtn.append(f"- {parm['full']}")
            if len(section['parms']) == 0: rtn.append('- None')
            if section['docstr_args'] !='': 
                rtn.append(f"#### Argument Details:")
                rtn.append(f"- {section['docstr_args']}")
            if section['docstr_returns'] !='': 
                rtn.append(f"#### Returns:")
                rtn.append(f"- {section['docstr_returns']}")
            if section['docstr_examples'] !='': 
                rtn.append(f"#### Examples:")
                rtn.append(f"```python\n{section['docstr_examples']}\n```")    
            rtn.append('---')
        rtn.append('---\n'*3 + '\n'*2)
        rtn = '\n'.join(rtn)

        if 'PosixPath' in str(type(dest_filepath)):
            dest_filepath = Path(dest_filepath).resolve()
            dest_filepath.parent.mkdir(parents=True, exist_ok=True)
            with dest_filepath.open('a' if append else 'w') as fh:
                fh.write(rtn) 
        return rtn
 
                

def substitute_dict_in_string(text:str='', sub_dict:dict={}, date_delim:str='', time_delim:str='', datetime_delim:str='_') -> str:
    """
    Substitutes dictionary '{name}' with 'value' in provided string.

    This performs a basic string substitution of any "{name}" in a supplied dictionary with the corresponding
    'value' and returns the post-substitution string, doing a basic text.format(**sub_dict).  The reason for 
    this function is a list of pre-loaded values that are also included, such as various filename-safe flavors
    of time.  The time format is always decending in granularity, i.e. Year, Month, Day, Hour, Minute, Second.
    Any of the pre-configured '{name}' values can be overwritten with the supplied dictionary. For example,
    the preloaded substitution {now} will turn into a timestamp, but if sub_dict contains {'now':'pizza'} then
    the preloaded substitution is ignored and instead {now} becomes pizza.

    Args:
        text (str): The string to perform the substitution around.
        sub_dict (dict): Dictionary containing the name/value pairs to substitute.
        date_delim (str): Character(s) used between year, month, and date. 
        time_delim (str): Character(s) used between hour, minute, and second. 
        datetime_delim (str): Character(s) used between the date and time component.

    Return:
        str: the post-substitution string. 
    """
    subdict = {'datetime':datetime.now().strftime(f'%Y{date_delim}%m{date_delim}%d{datetime_delim}%H{time_delim}%M{time_delim}%S'),
               'date':datetime.now().strftime(f'%Y{date_delim}%m{date_delim}%d'),
               'today':datetime.now().strftime(f'%Y{date_delim}%m{date_delim}%d'),
               'time':datetime.now().strftime(f'%H{time_delim}%M{time_delim}%S'),
               'now':datetime.now().strftime(f'%Y{date_delim}%m{date_delim}%d{datetime_delim}%H{time_delim}%M{time_delim}%S') }
    subdict.update(sub_dict)
    expectedNames = [fname for _, fname, _, _ in Formatter().parse(text) if fname] # add back in any missing expected names
    subdict.update({k:f'{{{k}}}' for k in expectedNames if k not in subdict.keys()})
    rtn = text.format(**subdict)
    return rtn 
               


def dict_soft_update(dict_main:dict, dict_addifmissing:dict={}) -> dict:
    """
    Simply adds one dictionary to another like a dict.update(), except it will NOT overwrite values if found in dict_main.
    """
    dict_main.update({n:v for n,v in dict_addifmissing.items() if n not in dict_main.keys()})
    return dict_main



def logger_setup(application_name:str=None, console_level=logging.INFO, filepath_level=logging.DEBUG, 
                 filepath:Path='./logs/{datetime}--{application_name}.log', **kwargs) ->  logging.Logger:
    """
    Sets up a logger in a consistent, default way with both stream(console) and file handlers.

    Args:
        application_name (str): Name of the application logger. Leave None for root logger. 
        console_level (logging.level): Logging level for stream handler (debug, info, warning, error). Set None to disable.
        filepath_level (logging.level): Logging level for file handler  (debug, info, warning, error). Set None to disable.
        filepath (Path): Path location for the file handler log files, supporting substitutions. Set None to disable.
        kwargs:  Any other keyword arguments are treated as {name} = value substitions for the filepath, if enabled.

    Returns: 
        (logger): a reference to the logging object. 
    """
    logger = logging.getLogger(application_name)
    frmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s','%Y-%m-%d_%H:%M:%S')
    logger.setLevel(logging.DEBUG)

    if console_level:
        streamhandler = logging.StreamHandler()
        streamhandler.setFormatter(frmt)
        streamhandler.setLevel(console_level)
        logger.addHandler(streamhandler)

    if filepath_level and filepath:    
        subdict = {'application_name':application_name if application_name else 'root'}
        subdict.update(**kwargs)
        filepath = Path(substitute_dict_in_string( str(Path(filepath).resolve()), subdict))
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filehandler = logging.FileHandler(filename=filepath)
        filehandler.setFormatter(frmt)
        filehandler.setLevel(filepath_level)
        logger.addHandler(filehandler)

    logger.preferred_format = frmt
    return logger 



def db_safe_name(original_column_name:str, reserved_word_prefix:str=None, **reserved_words) -> str:
    """
    Accepts a string and returns a DB column safe string, absent special characters, and substitute reserved words if provided a list.

    The **kwargs (called **reserved_words_subs) will be added to the reserved word substitution dictionary, 
    allowing for custom reserved word overrides. For example, for Notion Inserts you may want to translate
    the columns:  parent='Parent_ID', object='Object_Type'    
    """
    def __safechars__(original_column_name:str):
        rtn = original_column_name.strip().replace(' ','_').replace('-','_')
        rtn = [c for c in rtn if c.isalnum() or c=='_']
        if rtn[0] == '_' and original_column_name[0] != '_': rtn.pop(0)
        if rtn[0].isnumeric(): rtn.insert(0,'_')
        rtn = str(''.join(rtn))
        while '__' in rtn:
            rtn = rtn.replace('__','_')
        return rtn 
    
    colname = __safechars__(original_column_name)

    # build reserved word list
    reserved_words = {n.lower():v for n,v in reserved_words.items() if n.lower() == colname.lower() }
    if len(reserved_words) > 0: 
        return __safechars__(reserved_words[colname.lower()])
    
    common_reserved_words = ['type','object','date','time','from','to','int','integer'] 
    if colname.lower() in common_reserved_words: 
        reserved_word_prefix = reserved_word_prefix if reserved_word_prefix else '_'
        return __safechars__(f'{reserved_word_prefix}{colname}')

    return colname



def notion_translate_type(notion_type:str, decimal_precision:int=2, varchar_size:int=None, **kwargs) -> dict:
    """
    Translates notion datatypes into other system data types, like python or DBs. Also indicates whether 
    the notion type is considered an object (needing further drill-downs) or a primative type (like str or int).

    The returned dictionary object will have several entries: "db" for database translation, "py" for python, 
    "pk" for the notion primary key field of that object type, and "obj" boolean as to whether the data type 
    returns an object that requires additional drill-downs. For example, a notion "page" is an object that can 
    contain other types, whereas "text" is a primative data type.  The type map can be extended real-time using 
    the **kwargs.

    Args: 
        notion_type (str): Notion dataset type (text, user, status, page, etc.).
        decimal_precision (int): For types that translate into DB type Decimal, this sets the precision. Omitted if None.
        varchar_size (int): For types that translate into DB type Varchar, this sets the size. Omitted if None.
        kwargs: Added to the typemap, if adheres to the format name={"pk":"...", "db":"...", "py":"...", "obj":bool }

    Returns: 
        dict: Dictionary with various type translations for the notion type provided. The "py" return contains actual types.
    """
    varchar_size = '' if not varchar_size else f'({varchar_size})'
    decimal_precision = '' if not decimal_precision else f'(18,{decimal_precision})'
    typemap = {'multi_select': {'pk':'name',    'db':f'varchar{varchar_size}',      'py':str,      'obj':True  },       
               'select':       {'pk':'name',    'db':f'varchar{varchar_size}',      'py':str,      'obj':False },        
               'status':       {'pk':'name',    'db':f'varchar{varchar_size}',      'py':str,      'obj':False },    
               'user':         {'pk':'id',      'db':f'varchar{varchar_size}',      'py':str,      'obj':True  },  
               'person':       {'pk':'email',   'db':f'varchar{varchar_size}',      'py':str,      'obj':False },  
               'page':         {'pk':'id',      'db':f'varchar{varchar_size}',      'py':str,      'obj':True  },     
               'relation':     {'pk':'id',      'db':f'varchar{varchar_size}',      'py':str,      'obj':True  },     
               'text':         {'pk':'content', 'db':f'varchar{varchar_size}',      'py':str,      'obj':False },  
               'date':         {'pk':'start',   'db':'date'                  ,      'py':datetime, 'obj':False },          
               'number':       {'pk':'number',  'db':f'decimal{decimal_precision}', 'py':float,    'obj':False }
               }  
    typemap.update(**kwargs)
    if notion_type in typemap: 
        return typemap[notion_type]
    else: 
        raise KeyError(f'notion_type supplied ("{notion_type}") does not exist in the notion type map. Try one of the following: {", ".join([t for t in typemap.keys()])}')
    

        
def notion_translate_value(proptype, propobject) -> (str, list, bool):
    """Given a Notion object from the API source, return the value as a string as well as a list.
    Also returns a bool value indicating whether the list value contains multiple discrete items 
    (say, a multi-select type) or just multiple parts of one discrete object (say, rich-text type)."""
    if propobject == '': return '', [], False
    parts = []
    if proptype == 'text': 
        strobj = propobject['plain_text'].strip()
        return strobj, [strobj], False
    elif proptype in ['status','select']: 
        return propobject['name'], [propobject['name']], False
    elif proptype == 'multi_select':
        parts = [p['name'] for p in propobject]
        return ', '.join(parts), parts, True
    elif proptype == 'relation': 
        parts = [p['id'] for p in propobject]
        return ', '.join(parts), parts, True
    elif proptype == 'date': 
        return propobject['start'], [propobject['start']], False
    elif proptype in ['string','checkbox','email','url','phone_number']:
        return str(propobject), [propobject], False 
    elif proptype in ['number']:
        return str(propobject), [propobject], False 
    elif proptype == 'page': 
        return str(propobject['id']), [propobject['id']], False
    elif proptype == 'mention':
        parttype = propobject[propobject['type']]['type']
        if parttype in ['page']:
            return notion_translate_value(parttype, propobject[propobject['type']][parttype])
        else:    
            return notion_translate_value(parttype, [propobject[propobject['type']][parttype]])
    elif proptype in ['rich_text', 'title']:
        for part in propobject: 
            parttype = part['type'] if 'type' in part else 'unknown'
            s, l, m = notion_translate_value(parttype, part)
            parts.extend(l)
        parts = [p for p in parts if p !='']
        return ', '.join(parts), parts, False
    elif proptype in ['people','user']:
        for part in propobject:
            if 'object' in part and 'type' in part and part['object']=='user' and part['type']=='person':
                parts.append(part['name'])
            else:
                parts.append(part['id'])
        return ', '.join(parts), parts, True
    elif proptype == 'formula':
        parttype = propobject['type']
        s, parts, m = notion_translate_value(parttype, propobject[parttype])
        return s, parts, False
    elif proptype[-4:] == 'time':
        strobj = propobject.strip()
        return strobj, [strobj], False
    else:
        strobj = str(propobject).strip()
        return strobj, [strobj], False
        
    


def notion_get_api_key(api_key:str=None, envfile='.') -> str:
    """
    Sets and/or returns the Notion API Key, either directly from from an envfile.

    Args:
        api_key (str): Notion API Key for connecting account.
        envfile (Path|str|dict): Either the path to an envfile, or a dictionary as produced by envfile_load()

    Returns:
        str: The Notion API Key as provided, or parsed from env file.
    """
    if api_key: return api_key
    if envfile: 
        try:
            if type(envfile)==str or 'Path' in str(type(envfile)):
                env = envfile_load(envfile)
            elif type(envfile)==dict:
                env = envfile
            name = ''
            for nm in ['NOTION_API_KEY', 'NOTION_KEY']:
                if nm in env: name=nm 
                if nm.lower() in env: name=nm.lower()
                if nm.replace('_','') in env: name=nm.replace('_','')
                if nm.replace('_','').lower() in env: name=nm.replace('_','').lower()
                if name !='': break 
            return env[name]
        except Exception as ex:
            pass 
    return None



def notionapi_get_users(api_key:str, include:list = ['all'], full_json:bool = False, **headers):
    """
    Query Notion and return a set of all users in the organization, with optional ability to 'include' only certain users by name.
    """
    if len(include)==0: include = ['all']
    if 'Authorization' not in headers: headers['Authorization'] =  f"Bearer {api_key}"
    headers.update({n:v for n,v in notion_standard_headers.items() if n not in headers.keys()})
    
    resp = requests.get("https://api.notion.com/v1/users", headers=headers)
    resp.raise_for_status()

    users = {}
    for obj in resp.json()['results']:
        if obj['object'] == 'user' and obj['type'] == 'person':
            users[ obj['id'] ] = { 'id': obj['id'], 'name': obj['name'], 'email': obj['person']['email'] }
            if full_json: users[ obj['id'] ]['full_json'] = obj

    # apply filter
    users = {k:v for k,v in users.items() if v['name'].lower() in [n.lower() for n in include] or 'all' in include }
    return users 



def notionapi_get_dataset_info(api_key:str, notion_id:str, **headers) -> (str,dict):
    """--------------------
    Retrieves database and column information from a notion dataset (table).

    You must setup an Integration and add datasets, otherwise you'll get a "not authorized" error, even 
    with a valid API Key. For more information, see:  
    https://developers.notion.com/docs/create-a-notion-integration#create-your-integration-in-notion

    Args:
        api_key (str): A valid Notion API Key.
        notion_id (str): The Notion ID for the data table you're trying to access.
        **headers (kwargs): Any name/value pairs provided will be added to the API request header.
    
    Returns:
        str: Title of database (table)
        dict: Column name mapping between Notion (key) and DB (value)
    """
    # get database / table name and high-level information
    url = f'https://api.notion.com/v1/databases/{notion_id}'
    if 'Authorization' not in headers: headers['Authorization'] =  f"Bearer {api_key}"
    headers.update({n:v for n,v in notion_standard_headers.items() if n not in headers.keys()})

    hdrresp = requests.get(url=url, headers=headers)
    hdrresp.raise_for_status()
    hdrrespjson = hdrresp.json()
    tabletitle = ' '.join([h['plain_text'] for h in hdrrespjson['title']])
    tabletitle_singular = tabletitle[:-1] if tabletitle[-1:] == 's' else tabletitle
    # grab ID for db_table:
    columns = [ {'notion_name':'id', 'db_name':f'{tabletitle_singular}_id', 'order':0, 'notion_type':f'id', 'db_type':'varchar' } ]
    for col, val in hdrrespjson['properties'].items():
        coldb = db_safe_name(col, tabletitle_singular, parent='Parent_ID', object='Object_Type')
        typ = val['type']
        typdb = db_safe_name(typ)
        columns.append( {'notion_name':col, 'db_name':coldb, 'notion_type':typ, 'db_type':typdb, 'order':500 } )
    for col, typ in [('parent', 'varchar'),('object', 'varchar'),('url', 'varchar'),
                        ('public_url', 'varchar'),('created_time', 'timestamp'),('created_by', 'varchar'),
                        ('last_edited_time', 'timestamp'),('last_edited_by', 'varchar')]:
        coldb = db_safe_name(col, tabletitle_singular, parent='Parent_ID', object='Object_Type')
        columns.append ({ 'notion_name':col, 'db_name':coldb, 'notion_type':'text', 'db_type':typ, 'order':999 })
    return tabletitle, columns



def notionapi_get_dataset(api_key:str, notion_id:str, row_limit:int=-1, filter_json:dict = {}, **headers):
    """
    Connect to Notion and retrieve a dataset (aka table, aka database) by NotionID. 

    You must setup an Integration and add datasets, otherwise you'll get a "not authorized" error, even 
    with a valid API Key. For more information, see:  
    https://developers.notion.com/docs/create-a-notion-integration#create-your-integration-in-notion

    Args: 
        api_key (str): A valid Notion API Key.
        notion_id (str): The Notion ID for the data table you're trying to access.
        row_limit (int): The number of rows to return. To get all rows, set to -1 (default)
        filter_json (dict): The API filter object. See: https://developers.notion.com/reference/post-database-query-filter
        **headers (kwargs): Any name/value pairs provided will be added to the API request header.

    Returns:
        tuple: ('Name of table', [{rows as tabular data}], [{rows as key/value pairs}], [{column definitions}] )

    """
    if 'Authorization' not in headers: headers['Authorization'] =  f"Bearer {api_key}"
    headers.update({n:v for n,v in notion_standard_headers.items() if n not in headers.keys()})
    url = f'https://api.notion.com/v1/databases/{notion_id}/query'

    # get dataset tablename and column definitions:
    tabletitle, columndefinitions = notionapi_get_dataset_info(api_key, notion_id)

    # pull all data records (in groups of 100):
    has_more = True 
    bodydata = {}
    rows = []
    while has_more: 
        resp = requests.post(url=url, headers=headers, json=filter_json, data=bodydata)
        resp.raise_for_status()

        respjson = resp.json()
        has_more = bool(respjson['has_more'])
        if has_more: bodydata = '{ "start_cursor": "' + respjson["next_cursor"] + '" }'
        rows.extend(respjson['results'])
        
        if row_limit > 0 and len(rows) > row_limit:  
            # only true if hit user defined limit, rather than EOF
            has_more = False
            rows = rows[:row_limit]

    # structure rows for return
    multiset_rows = []
    newrows = []

    for row in rows:
        # first load all the top-level properties, notion-required and normally not visible:
        newrow =   {f'id':row['id'], 
                    'parent_id':row['parent']['database_id'],
                    'object_type':row['object'],
                    'url':row['url'], 
                    'public_url':row['public_url'],
                    'created_time':row['created_time'],
                    'created_by':row['created_by']['id'],
                    'last_edited_time':row['last_edited_time'],
                    'last_edited_by':row['last_edited_by']['id']
                    }
        
        # now loop thru properties and add:
        for propname, fullpropvalue in row['properties'].items():

            proptype = fullpropvalue['type']
            propvalue = '' if not fullpropvalue[proptype] else fullpropvalue[proptype]
            
            valstr, vallist, is_multiset = notion_translate_value(proptype, propvalue)
            newrow[propname] = valstr 

            if is_multiset:
                for val in vallist:
                    multiset_rows.append( 
                        {'Notion_DBName':tabletitle, 
                        'ColumnName':propname,
                        'ColumnType':proptype,
                        'RowID':row['id'],
                        'CellValue':str(val),
                        'CellCount':len(vallist)} )
            
        newrows.append(newrow)

    return tabletitle, newrows, multiset_rows, columndefinitions



if __name__ == '__main__':
    
    for x in [ '1.8e-05', 2.9e16, 3.34462e+05, 'a','1',1,[1], '2024-01-31',]:
        # print('PY:   ', x, '==', infer_datatype(x))
        print('SQL:  ', x, '==', infer_datatype(x,'sql'))
    
    pass

 