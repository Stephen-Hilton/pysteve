setop
echo "Remeber to update the version in the pyproject.toml file."
echo "You can do it now, if needed.  Press enter when ready."
read _ 

cd ~/Dev/pysteve
rm -r dist
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade twine
python3 -m pip install --upgrade build
python3 -m build
# python3 -m twine upload --repository testpypi dist/*
python3 -m twine upload --repository pypi dist/*
