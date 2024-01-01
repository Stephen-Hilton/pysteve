from pathlib import Path 
import re

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
    

    
def save_dict_as_envfile(save_path:Path, save_dict:dict = {}, iteration_zero_pad = 6 ) -> Path:
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
        save_dict (dict): dictionary containing file content.

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

        if return_sorted[:4] in ['firs', 'earl']:
            pth = Path( pth.parent / valid_files[0] ).resolve()
        else: # last, latest, etc.
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



if __name__ == '__main__':

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