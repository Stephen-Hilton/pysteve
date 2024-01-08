from pathlib import Path 
import inspect
from datetime import datetime, timedelta

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
                          indent_spaces:int = 4) -> str:
    """
    Parses python files to automatically generate simple markdown documentation.

    Parses the file at source_path, or if source_path is a folder, will iterate (alphabetically) thru all .py 
    files and generate markdown content by introspecting all functions, classes, and methods, with a heavy focus
    on using google-style docstrings.  It will always return the markdown as a string, and if the dest_filepath 
    is specified, it will also save to that filename. By default it will replace the dest_filepath, or set 
    append=True to append the markdown to the end. This allows freedom to chose which files /folders to document,
    and structure the mardown files however you'd like.  It also allows for a simple way to auto-generate 
    README.md files, for small projects. 

    Args: 
        source_path (Path): Path to a file or folder containing .py files with which to create markdown.
        dest_filepath (Path): If specified, will save the markdown string to the file specified.
        append (bool): Whether to append (True) over overwrite (False, default) the dest_filepath.
        include_dunders (bool): Whether to include (True) or exclude (False, default) files beginning with double-underscores (dunders).
        indent_spaces (int): Number of spaces which constitute a python indent.  Defaults to 4.

    Returns:
        str: Markdown text generated.
    """
    source_path = Path(source_path).resolve()
    if not source_path.exists(): raise ValueError('Parameter "source_path" must be a valid file or folder.')
    indent = ' '*indent_spaces
    if source_path.is_file():
        srcfiles = [source_path.resolve()]
    elif source_path.is_dir():
        srcfiles = [f for f in source_path.iterdir() if f.suffix == '.py' and not (include_dunders==False and str(f.stem)[:2] =='__') ]
        
    # ITERATE all source files found
    for file in srcfiles:
        with open(file,'r') as fh:
            srclines = str(fh.read()).split('\n')
        
        defs = []
        continued_line_def = False
        continued_line_docstring = False
        skip_to_line = -1

        for li, line in enumerate(srclines):
            # skip forward lines on demand
            if li <= skip_to_line: continue

            # process "def" function/modules:
            if line.startswith('def ') or continued_line_def: 
                if line.strip() == '': break

                if not continued_line_def:
                    cdef = {'name':line.split('(')[0].strip()[3:].strip(), 'returns':'', 'file':file.name, 'line':li, 'args':[], 'docstring':{'line':-1,'body':[] } }
                    line = line[3:].strip()
                    line = line.replace(cdef['name'],'').strip()

                    # markers for parsing remainder of parameters
                    parens = 0
                    quotetype = ''
                    isquote = False
                    segment_type = 'arg name'
                    segment_text = ''
                    tokens = []
                else:
                    line = line.strip()

                # tokenize remaining values in the arg header
                for i, char in enumerate(list(line)):
                    # special handling for 2-char symbol (return type)
                    if char == '-' and segment_type != 'quote' and list(line)[i+1]=='>': char = '->'
                    if char == '>' and segment_type != 'quote' and list(line)[i-1]=='-': char = ''

                    match char:
                        # handle quoted strings
                        case '"' | "'":
                            if not isquote: # start of quote 
                                isquote = True
                                quotetype = char
                            elif isquote and char == quotetype: # end of quote
                                isquote = False
                                quotetype = ''
                            segment_text += char 

                        # track paren depth 
                        case '(': parens +=1
                        case ')': parens -=1

                        # track different parts of the args
                        case '->':
                            tokens.append({'type':segment_type, 'value': segment_text})
                            segment_type = 'return type'
                            segment_text = ''
                        case ',': 
                            tokens.append({'type':segment_type, 'value': segment_text})
                            segment_type = 'arg name'
                            segment_text = ''
                        case ':': 
                            tokens.append({'type':segment_type, 'value': segment_text})
                            segment_type = 'arg type'
                            segment_text = ''
                        case '=': 
                            tokens.append({'type':segment_type, 'value': segment_text})
                            segment_type = 'arg default'
                            segment_text = ''

                        case _:
                            segment_text += char 
                tokens = [{k:str(v).strip() for k,v in d.items()} for d in tokens]
                continued_line_def = (i == len(line)-1 and parens != 0)

                # pull tokens back into args, with name/type/default (and def return type)
                if not continued_line_def:
                    argi = 0
                    for token in tokens:
                        match token['type']:
                            case 'arg name': 
                                cdef['args'].append( {'name':token['value'], 'type':'', 'default':''} )
                                arg = cdef['args'][len(cdef['args'])-1]
                            case 'arg type':    arg['type'] = token['value']
                            case 'arg default': arg['default'] = token['value']
                            case 'return type': cdef['returns'] = token['value']

            # Process DOCSTRINGS (must follow def line and start with """)
            if (line.strip().startswith('"""') and li == cdef['line']+1):
                continued_line_docstring = True
                cdef['docstring']['line'] = li
                line = line.replace('"""','').strip()
            if continued_line_docstring: 
                line = line.replace('"""','').strip()
                line_p1 = srclines[li+1].replace('"""','').strip()
                line_p2 = srclines[li+2].replace('"""','').strip()
                line_m1 = srclines[li-1].replace('"""','').strip()

                # headline: current line is 1 or 2 in docstring, not empty but previous and next lines are (or def line)
                if (li == cdef['docstring']['line']+0 and line !='' and line_p1=='') or \
                   (li == cdef['docstring']['line']+1 and line !='' and line_p1=='' and line_m1==''):
                    line =  f'<b>{line}</b><br>'

                # section headers
                elif ':' in line:
                    tmpline = line.strip()
                    while '  ' in tmpline:
                        tmpline.replace('  ',' ')
                    first_colon = tmpline.find(':')
                    words_before_first_colon = len(tmpline[:first_colon].replace('(','').replace(')','').split(' '))

                    # if stand-alone header
                    if tmpline.endswith(':') and words_before_first_colon <= 2:
                        line = f'<h3>{tmpline}</h3>'    

                    # if list of "Name (Type): Value" pairs
                    elif words_before_first_colon <= 2: # header only
                        line = f'**{tmpline[:first_colon]}**: {tmpline[first_colon:]}'
                    
                if line !='': cdef['docstring']['body'].append( line )

                if line.strip().endswith('"""'): 
                    continued_line_docstring = False
                    i = 1
                    while srclines[li+i].startswith(indent): 
                        i +=1
                    skip_to_line = li + i 

            pass

                    
                

                    

                
                 

            # Docstrings:
            # if line.startswith(f'{indent}"""'): 
                    

        

    pass 





if __name__ == '__main__':


    mdstr = generate_markdown_doc()

    from datetime import datetime
    from pathlib import Path 

    nowish = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    data = {'USER':'Bob', 'AGE':33, 'HIEGHT':5.89, 'DATETIME':nowish, 'PETS':['fluffy','spot','stinky'] }
    data2 = data.copy()
    data2['USER'] = 'Steve'
    folder = Path( Path( __file__ ).parent.parent / 'tests/testfiles' )

    files = parse_filename_iterators(folderpath=folder)

    rtn = load_envfile_to_dict(Path(folder / 'my_envfile_Bob.sh')) 
    rtn = load_envfile_to_dict(Path(folder / 'my_envfile_Steve.sh')) 
    rtn = load_envfile_to_dict(Path(folder / 'my_envfile_{USER}.sh'), 'last')
    print( data )

    pass