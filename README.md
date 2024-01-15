# File: pySteve.py
## Functions:
### infer_datatype
**Infers the primative data types based on value characteristics, and returns a tuple of (type, typed_value). Currently supports float, int, str, and list (with typed elements using recursive calls).**

#### Arguments:
- value
---
### save_dict_as_envfile
**Always saves a dict as a shell (zsh) as an env-loadable file, adding folders, file iterations and substitutions as needed.**

The save_path allows for substitution of any name in the dict (within curly brackets) with the value of that entry. For example, if dict = {'date':'2024-01-01'}, save_path = '~/some/path/file_{date}.sh' will become '~/some/path/file_2024-01-01.sh'. Additionally, if the full substituted file exists, the process will append an iterator (1,2,3) to the end to preserve uniqueness. The final save_path is returned from the function. Because the file needs to be compatible with shell .env files, special characters (spaces, newlines, etc) are removed from all 'names' in the save_dict, and any values with newlines will be wrapped in a docstring using the string saved in variable 'docstring_eom_marker'
#### Arguments:
- save_path:Path
- save_dict:dict = {}
- iteration_zero_pad:int = 6
#### Argument Details:
- save_path (Path): Where to save the file, with substitution logic. save_dict (dict): Dictionary containing file content.
#### Returns:
- Path: Returns the final save_path used (after substitution and iteration).
---
### load_envfile_to_dict
**Returns a dictionary containing name/value pairs pulled from the supplied .env formatted shell (zsh) script.**

If load_path does not have a direct match, it is assumed to be a pattern and will be matched given supplied template logic (unless exact_match_only = True), and return with the return_sorted logic (first or last). There are several synonyms: [first | earliest] or [last | latest]
#### Arguments:
- load_path:Path
- return_sorted:str = 'latest'
- exact_match_only:bool = False
#### Argument Details:
- load_path (Path): file to load from, with template logic allowed. return_sorted (str): if template matched, exact_match_only (bool): skip the first/last logic, and require exact filename match
#### Returns:
- dict: the dictionary name/value parsed from the supplied file.
---
### parse_placeholders
**From given string, parses out a list of placeholder values, along with their positions.**

#### Arguments:
- value:str = ''
- wrappers:str = '{}'
---
### parse_filename_iterators
**Iterate thru all files in the supplied folder, and return a dictionary containing three lists: - iter_files, containing files that end in an iterator ( *.000 ) - base_files, containing files that do not end in an interator (aka base file) - all_files, sorted in order with the base file first per pattern, followed by any iterations**

#### Arguments:
- folderpath:Path
---
### chunk_lines
**Breaks a list of string lines into a list of lists of string lines, based on supplied markers.**

Accepts a list of lines (say, from reading a file) and separates those lines into separate lists based on boundries discovered by running lines against a list of marker functions (usually lambdas). Each marker function will be passed the line in sequence, and must return a True or False as to whether the line is the beginning of a new section. If ANY of the marker functions return True, the line is considered the first of a new chunk (list of string lines). At the end, the new list of lists of string lines is returned. For example: after opening and reading lines of a python file, you could send that list of lines to this function along with the two lambda functions ` lambda line : str(line).startswith('def') ` and ` lambda line : str(line).startswith('class') ` to split the list of lines by python functions.
#### Arguments:
- list_of_lines:list = []
- newchunck_marker_funcs:list = []
#### Argument Details:
- list_of_lines (list): List of string lines to match markers against and group. newchunck_marker_funcs (list): List of functions, applied to each line to mark new chunk boundries.
#### Returns:
- list: A list of lists of string lines.
---
### tokenize_quoted_strings
**Takes a text string and replaces all quoted segments with a token, then returns a tuple with the tokenized text and a dictionary of all tokens, for later replacement as needed.**

#### Arguments:
- text:str=''
---
### generate_markdown_doc
**Parses python files to automatically generate simple markdown documentation.**

Parses the file at source_path, or if source_path is a folder, will iterate (alphabetically) thru all .py files and generate markdown content by introspecting all functions, classes, and methods, with a heavy focus on using google-style docstrings. It will always return the markdown as a string, and if the dest_filepath is specified, it will also save to that filename. By default it will replace the dest_filepath, or set append=True to append the markdown to the end. This allows freedom to chose which files /folders to document, and structure the mardown files however you'd like. It also allows for a simple way to auto-generate README.md files, for small projects. Todo: add class support, change source_path to a list of files/folders.
#### Arguments:
- source_path:Path = './src'
- dest_filepath:Path = './README.md'
- append:bool = False
- include_dunders:bool = False
- py_indent_spaces:int = 4
#### Argument Details:
- source_path (Path): Path to a file or folder containing .py files with which to create markdown. dest_filepath (Path): If specified, will save the markdown string to the file specified. append (bool): Whether to append (True) over overwrite (False, default) the dest_filepath. include_dunders (bool): Whether to include (True) or exclude (False, default) files beginning with double-underscores (dunders). py_indent_spaces (int): Number of spaces which constitute a python indent. Defaults to 4.
#### Returns:
- str: Markdown text generated.
---
---
---
---


