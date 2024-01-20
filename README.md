# File: pySteve.py
pySteve is a mish-mash collection of useful functions, rather than an application.  It is particularly useful to people named Steve.

## Functions:
### chunk_lines
**Breaks a list of string lines into a list of lists of string lines, based on supplied markers.**

Accepts a list of lines (say, from reading a file) and separates those lines into separate lists based on boundries discovered by running lines against a list of marker functions (usually lambdas). Each marker function will be passed the line in sequence, and must return a True or False as to whether the line is the beginning of a new section. If ANY of the marker functions return True, the line is considered the first of a new chunk (list of string lines). At the end, the new list of lists of string lines is returned. For example: after opening and reading lines of a python file, you could send that list of lines to this function along with the two lambda functions ` lambda line : str(line).startswith('def') ` and ` lambda line : str(line).startswith('class') ` to split the list of lines by python functions.
#### Arguments:
- list_of_lines:list = []
- newchunck_marker_funcs:list = []
#### Argument Details:
- list_of_lines (list): List of string lines to match markers against and group.
 - newchunck_marker_funcs (list): List of functions, applied to each line to mark new chunk boundries.
#### Returns:
- list: A list of lists of string lines.
---
### db_safe_name
**Accepts a string and returns a DB column safe string, absent special characters, and substitute reserved words if provided a list.**

The **kwargs (called **reserved_words_subs) will be added to the reserved word substitution dictionary, allowing for custom reserved word overrides. For example, for Notion Inserts you may want to translate the columns: parent='Parent_ID', object='Object_Type'
#### Arguments:
- original_column_name:str
- reserved_word_prefix:str=None
- **reserved_words
---
### dict_soft_update
**Simply adds one dictionary to another like a dict.update(), except it will NOT overwrite values if found in dict_main.**

#### Arguments:
- dict_main:dict
- dict_addifmissing:dict={}
---
### envfile_load
**Returns a dictionary containing name/value pairs pulled from the supplied .env formatted shell (zsh) script.**

If load_path does not have a direct match, it is assumed to be a pattern and will be matched given supplied template logic (unless exact_match_only = True), and return with the load_path_sorted logic (first or last). There are several synonyms: [first | earliest] or [last | latest]
#### Arguments:
- load_path:Path='.'
- load_path_sorted:str = 'latest'
- exact_match_only:bool = False
#### Argument Details:
- load_path (Path): file to load from, with template logic allowed.
 - load_path_sorted (str): If load_path was a template, indicates which file to select, based on filename sort.
 - exact_match_only (bool): Disallow filename templating, and require exact filename only.
#### Returns:
- dict: the dictionary name/value parsed from the supplied file.
---
### envfile_save
**Always saves a dict as a shell (zsh) as an env-loadable file, adding folders, file iterations and substitutions as needed.**

The save_path allows for substitution of any name in the dict (within curly brackets) with the value of that entry. For example, if dict = {'date':'2024-01-01'}, save_path = '~/some/path/file_{date}.sh' will become '~/some/path/file_2024-01-01.sh'. Additionally, if the full substituted file exists, the process will append an iterator (1,2,3) to the end to preserve uniqueness. The final save_path is returned from the function. Because the file needs to be compatible with shell .env files, special characters (spaces, newlines, etc) are removed from all 'names' in the save_dict, and any values with newlines will be wrapped in a docstring using the string saved in variable 'docstring_eom_marker'
#### Arguments:
- save_path:Path
- save_dict:dict = {}
- iteration_zero_pad:int = 6
#### Argument Details:
- save_path (Path): Where to save the file, with substitution logic.
 - save_dict (dict): Dictionary containing file content.
#### Returns:
- Path: Returns the final save_path used (after substitution and iteration).
---
### generate_markdown_doc
**Parses python files to automatically generate simple markdown documentation (generated this document).**

Parses the file at source_path, or if source_path is a folder, will iterate (alphabetically) thru all .py files and generate markdown content by introspecting all functions, classes, and methods, with a heavy focus on using google-style docstrings. It will always return the markdown as a string, and if the dest_filepath is specified, it will also save to that filename. By default it will replace the dest_filepath, or set append=True to append the markdown to the end. This allows freedom to chose which files /folders to document, and structure the mardown files however you'd like. It also allows for a simple way to auto-generate README.md files, for small projects. Todo: add class support, change source_path to a list of files/folders.
#### Arguments:
- source_path:Path = './src'
- dest_filepath:Path = './README.md'
- append:bool = False
- include_dunders:bool = False
- py_indent_spaces:int = 4
#### Argument Details:
- source_path (Path): Path to a file or folder containing .py files with which to create markdown.
 - dest_filepath (Path): If specified, will save the markdown string to the file specified.
 - append (bool): Whether to append (True) over overwrite (False, default) the dest_filepath.
 - include_dunders (bool): Whether to include (True) or exclude (False, default) files beginning with double-underscores (dunders).
 - py_indent_spaces (int): Number of spaces which constitute a python indent. Defaults to 4.
#### Returns:
- str: Markdown text generated.
---
### infer_datatype
**Infers the primative data types based on value characteristics, and returns a tuple of (type, typed_value). Currently supports float, int, str, and list (with typed elements using recursive calls).**

#### Arguments:
- value
---
### logger_setup
**Sets up a logger in a consistent, default way with both stream(console) and file handlers.**

#### Arguments:
- application_name:str=None
- console_level=logging.INFO
- filepath_level=logging.DEBUG
- filepath:Path='./logs/{datetime}--{application_name}.log'
- **kwargs
#### Argument Details:
- application_name (str): Name of the application logger. Leave None for root logger.
 - console_level (logging.level): Logging level for stream handler (debug, info, warning, error). Set None to disable.
 - filepath_level (logging.level): Logging level for file handler (debug, info, warning, error). Set None to disable.
 - filepath (Path): Path location for the file handler log files, supporting substitutions. Set None to disable.
 - kwargs: Any other keyword arguments are treated as {name} = value substitions for the filepath, if enabled.
#### Returns:
- (logger): a reference to the logging object.
---
### notion_get_api_key
**Sets and/or returns the Notion API Key, either directly from from an envfile.**

#### Arguments:
- api_key:str=None
- envfile='.'
#### Argument Details:
- api_key (str): Notion API Key for connecting account.
 - envfile (Path|str|dict): Either the path to an envfile, or a dictionary as produced by envfile_load()
#### Returns:
- str: The Notion API Key as provided, or parsed from env file.
---
### notion_translate_type
**Translates notion datatypes into other system data types, like python or DBs. Also indicates whether the notion type is considered an object (needing further drill-downs) or a primative type (like str or int).**

The returned dictionary object will have several entries: "db" for database translation, "py" for python, "pk" for the notion primary key field of that object type, and "obj" boolean as to whether the data type returns an object that requires additional drill-downs. For example, a notion "page" is an object that can contain other types, whereas "text" is a primative data type. The type map can be extended real-time using the **kwargs.
#### Arguments:
- notion_type:str
- decimal_precision:int=2
- varchar_size:int=None
- **kwargs
#### Argument Details:
- notion_type (str): Notion dataset type (text, user, status, page, etc.).
 - decimal_precision (int): For types that translate into DB type Decimal, this sets the precision. Omitted if None.
 - varchar_size (int): For types that translate into DB type Varchar, this sets the size. Omitted if None.
 - kwargs: Added to the typemap, if adheres to the format name={"pk":"...", "db":"...", "py":"...", "obj":bool }
#### Returns:
- dict: Dictionary with various type translations for the notion type provided. The "py" return contains actual types.
---
### notion_translate_value
**Given a Notion object from the API source, return the value as a string as well as a list. Also returns a bool value indicating whether the list value contains multiple discrete items (say, a multi-select type) or just multiple parts of one discrete object (say, rich-text type).**

#### Arguments:
- proptype
- propobject
---
### notionapi_get_dataset
**Connect to Notion and retrieve a dataset (aka table, aka database) by NotionID.**

You must setup an Integration and add datasets, otherwise you'll get a "not authorized" error, even with a valid API Key. For more information, see: https://developers.notion.com/docs/create-a-notion-integration#create-your-integration-in-notion
#### Arguments:
- api_key:str
- notion_id:str
- row_limit:int=-1
- filter_json:dict = {}
- **headers
#### Argument Details:
- api_key (str): A valid Notion API Key.
 - notion_id (str): The Notion ID for the data table you're trying to access.
 - row_limit (int): The number of rows to return. To get all rows, set to -1 (default)
 - filter_json (dict): The API filter object. See: https://developers.notion.com/reference/post-database-query-filter
 - **headers (kwargs): Any name/value pairs provided will be added to the API request header.
#### Returns:
- tuple: ('Name of table', [{rows as tabular data}], [{rows as key/value pairs}], [{column definitions}] )
---
### notionapi_get_dataset_info
**-------------------- Retrieves database and column information from a notion dataset (table).**

You must setup an Integration and add datasets, otherwise you'll get a "not authorized" error, even with a valid API Key. For more information, see: https://developers.notion.com/docs/create-a-notion-integration#create-your-integration-in-notion
#### Arguments:
- api_key:str
- notion_id:str
- **headers
#### Argument Details:
- api_key (str): A valid Notion API Key.
 - notion_id (str): The Notion ID for the data table you're trying to access.
 - **headers (kwargs): Any name/value pairs provided will be added to the API request header.
#### Returns:
- str: Title of database (table)
 - dict: Column name mapping between Notion (key) and DB (value)
---
### notionapi_get_users
**Query Notion and return a set of all users in the organization, with optional ability to 'include' only certain users by name.**

#### Arguments:
- api_key:str
- include:list = ['all']
- full_json:bool = False
- **headers
---
### parse_filename_iterators
**Iterate thru all files in the supplied folder, and return a dictionary containing three lists: - iter_files, containing files that end in an iterator ( *.000 ) - base_files, containing files that do not end in an interator (aka base file) - all_files, sorted in order with the base file first per pattern, followed by any iterations**

#### Arguments:
- folderpath:Path
---
### parse_placeholders
**From given string, parses out a list of placeholder values, along with their positions.**

#### Arguments:
- value:str = ''
- wrappers:str = '{}'
---
### substitute_dict_in_string
**Substitutes dictionary '{name}' with 'value' in provided string.**

This performs a basic string substitution of any "{name}" in a supplied dictionary with the corresponding 'value' and returns the post-substitution string, doing a basic text.format(**sub_dict). The reason for this function is a list of pre-loaded values that are also included, such as various filename-safe flavors of time. The time format is always decending in granularity, i.e. Year, Month, Day, Hour, Minute, Second. Any of the pre-configured '{name}' values can be overwritten with the supplied dictionary. For example, the preloaded substitution {now} will turn into a timestamp, but if sub_dict contains {'now':'pizza'} then the preloaded substitution is ignored and instead {now} becomes pizza. Return: str: the post-substitution string.
#### Arguments:
- text:str=''
- sub_dict:dict={}
- date_delim:str=''
- time_delim:str=''
- datetime_delim:str='_'
#### Argument Details:
- text (str): The string to perform the substitution around.
 - sub_dict (dict): Dictionary containing the name/value pairs to substitute.
 - date_delim (str): Character(s) used between year, month, and date.
 - time_delim (str): Character(s) used between hour, minute, and second.
 - datetime_delim (str): Character(s) used between the date and time component.
---
### tokenize_quoted_strings
**Tokenizes all quoted segments found inside supplied string, and returns the string plus all tokens.**

Returns a tuple with the tokenized string and a dictionary of all tokens, for later replacement as needed. If return_quote_type is True, also returns the quote type with one more nested layer to the return dict, looking like: {"T0": {"text":"'string in quotes, inlcuding quotes', "quote_type":"'"}, "T1":{...}} If return_quote_type is False, returns a slightly more flat structure: {"T0": "'string in quotes, inlcuding quotes'", "T1":...}
#### Arguments:
- text:str=''
- return_quote_type:bool=False
#### Argument Details:
- text (str): String including quotes to tokenize.
 - return_quote_type (bool): if True, will also return the type of quote found, if False (default) just returns tokenized text in a flatter dictionary structure.
#### Returns:
- tuple (str, dict): the tokenized text as string, and tokens in a dict.
---
---
---
---


