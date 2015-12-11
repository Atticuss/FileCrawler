filecrawler
===========

Variety of file/directory crawling functions such as:
  1. Enumerate and count all file types in a given directory
  2. Line count
  3. Regex search
  4. Restrict to specific file ext

```filecrawler.py [-h, -r, -v, -p, -c, -t, -z, -e <extension(s)>, -o <filename>] -s|-l [<searchterm>] -d|-f <directory|filename>```

filecrawler3
============
Same tool with one additional flag: -n / --num-threads to specify the number of threads to utilize. Defaults to five. Written for Python3 as the multithreaded version of this tool.
