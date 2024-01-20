from pathlib import Path 
from pprint import pprint
import inspect
from datetime import datetime, timedelta

docstring_fileheader="""pySteve is a mish-mash collection of useful functions, rather than an application.  It is particularly useful to people named Steve.""" 
docstring_marker = 'EOMsg'
docstring_prefix = f'$(cat << {docstring_marker}\n' 
docstring_suffix = f'\n{docstring_marker}\n)'



def infer_datatype(value):
    """
    Infers the primative data types based on value characteristics, and returns a tuple of (type, typed_value).
    Currently supports float, int, str, and list (with typed elements using recursive calls).
    """
    value = str(value)

    if value.replace('.','').isnumeric(): 
        if '.' in value: 
            return (float, float(value))
        else:
            return (int, int(value))
        
    if value.startswith('[') and value.endswith(']'):
        value = [v.strip() for v in value[1:-1].split(',')]
        for i,v in enumerate(value):
            value[i] = v.strip()
            value[i] = infer_datatype(value[i])[1]
        return (list, value)
    
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return (str, value)
    

    
def save_dict_as_envfile(save_path:Path, save_dict:dict = {}, iteration_zero_pad:int = 6 ) -> Path:
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
    lines = []
    for nm, val in save_dict.items():
        if type(val) not in [str, int, float, list]: continue

        nm = ''.join([c for c in nm if c.isalnum() or c in['_'] ]) 
        q = '' if type(val) in [int, float] else '"'
        val = str(val)
        if '\n' in val: 
            if val[:1]=='\n': val = val[1:]
            val = val.rstrip()
            nm += f'={docstring_prefix}{val}{docstring_suffix}'
        else: 
            nm += f'={q}{val}{q}'
        lines.append( nm )
    
    # write file
    with open(pth, 'w') as fh:
        fh.write( '\n'.join(lines) )

    return Path(pth)



def load_envfile_to_dict(load_path:Path, return_sorted:str = 'latest', exact_match_only:bool = False) -> dict: 
    """
    Returns a dictionary containing name/value pairs pulled from the supplied .env formatted shell (zsh) script.

    If load_path does not have a direct match, it is assumed to be a pattern and will be matched given 
    supplied template logic (unless exact_match_only = True), and return with the return_sorted logic 
    (first or last).  There are several synonyms: [first | earliest] or [last | latest]
    
    Args:
        load_path (Path): file to load from, with template logic allowed.
        return_sorted (str): if template matched, 
        exact_match_only (bool): skip the first/last logic, and require exact filename match
 
    Returns: 
        dict: the dictionary name/value parsed from the supplied file.

    """
    if not load_path: raise ValueError(f'load_path must be specified, you provided: {load_path}')
    pth = Path(load_path).resolve()

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

        if return_sorted[:3] in ['fir', 'ear', 'asc']:
            pth = Path( pth.parent / valid_files[0] ).resolve()
        else: # last, latest, desc, etc.
            pth = Path( pth.parent / valid_files[len(valid_files)-1] ).resolve()

    # with correct path selected, load and structure into dict
    with open(pth, 'r') as fh:
        content = fh.read()

    # iter allows next(), ::END:: needed to search for docstring END across newlines
    lines = iter(content.replace(docstring_suffix,'\n::END::').split('\n')) 

    # loop thru and build dict to control load
    rtn = {}
    multiline = None
    for line in lines:
        eq = line.find('=')
        name  = line[:eq]
        value = line[eq+1:]
        if value[:1]=='"' and value[-1:]=='"': value = value[1:-1]
        if value.startswith( docstring_prefix.strip() ):
            multiline = []
            mline = ''
            while True:
                mline = next(lines, '')
                if '::END::' in mline: break
                multiline.append( mline )
            value = '\n'.join(multiline)
        value = infer_datatype(value)[1]
        rtn[name] = value
    rtn['load_envfile_to_dict--FilePath_Selected'] = str(pth.resolve())
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
        args = ' '.join(args).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        rtn  = ' '.join(rtn ).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
        examples = ' '.join(examples).replace('  ',' ').replace('  ',' ').replace('  ',' ').strip()
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
        fileprefixline = [l for l in srclines if l.replace(' ','').startswith('docstring_fileheader=')]
        if len(fileprefixline)>0:
            fileprefix = fileprefixline[0] 
            _, fileprefixdict = tokenize_quoted_strings(fileprefix, True)
            fileprefix = fileprefixdict['T0']['text'].strip()[3:-3] + '\n'
            srcfiles = [l for l in srclines if fileprefix not in l ] 
        else: 
            fileprefix =f"""Functions and classes from the file {file.name}<br>(to customize this text, add the variable to your file: docstring_fileheader = "Some header message" )""" 
        
        sections = []
        chunks = chunk_lines(srclines, [ lambda line: str(line).startswith('def ') or str(line).startswith('class ') ])
        for chunk in chunks:
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
 
                

                    



if __name__ == '__main__':

    mdstr = generate_markdown_doc('./src/pySteve.py', Path('./README.md') )
    print('done!')
    pass

 